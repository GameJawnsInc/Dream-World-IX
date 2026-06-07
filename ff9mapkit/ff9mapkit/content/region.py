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

# --- expression var classes (the engine's variable scopes) ---
# A var token byte = 0xC0 | (VariableType << 2) | VariableSource (EBin.getVarOperation). CRITICAL: the
# SOURCE decides PERSISTENCE -- Global (src 0) reads/writes the SAVE-BACKED gEventGlobal (survives
# field reloads); Map (src 1) is a PER-FIELD array WIPED on every field load. (HW's naming is
# inverted: HW "GenBool" = engine Global = persistent; HW "GlobBool" = engine Map = transient.)
GLOB_BOOL = 0xC4      # Global + Bit  -> SAVE-PERSISTENT bool (story flags, chest "once", etc.)
MAP_BOOL = 0xC5       # Map + Bit     -> transient per-field bool (resets on reload; rarely what you want)
GLOB_UINT8 = 0xD5     # Map + Byte    -> transient byte (the camera-switch flag; reset per load by design)
GLOB_UINT16 = 0xDC    # Global + UInt16 -> save-backed 16-bit word. Read via the EXPRESSION path it is
                      # UNSIGNED (0..65535, no sign-extension -- EBin.GetVariableValueInternal), so it
                      # holds a choice availability mask without the 0xFFFF->-1 sign trap of a literal.
VAR_CLASSES = {"glob_bool": GLOB_BOOL, "map_bool": MAP_BOOL, "glob_uint8": GLOB_UINT8}

# A scratch word high in gEventGlobal (byte offset; vars index BYTES, bits index BITS -- so byte 2040
# is bits 16320+, clear of base-game vars [low offsets] AND the kit's 8000+ bit-flags [bytes ~1000]).
# Rebuilt every time a choice opens (set_var -> or_var), so its transient value never matters across
# opens; F10's gEventGlobal reset is harmless to it.
MASK_SCRATCH_IDX = 2040

# --- expression opcodes / tokens ---
EXPR_OP = 0x05        # expression statement (its single operand is a token stream)
T_CONST = 0x7D        # 0x7D <i16>
T_NOT = 0x0E
T_EQ = 0x20
T_ASSIGN = 0x2C       # B_LET ('=')
T_OR_ASSIGN = 0x3F    # B_OR_LET ('|='); real-field verified (Dali/Storage 407: `VAR |= 2` = 05 .. 3F 7F)
T_LT = 0x18           # B_LT ('<')
T_ITEMCOUNT = 0x64    # GetItemCount: unary fn token -- pops an item-id const, pushes the held count
                      # (real-field verified, Dali/Storage 407 chest guard `GetItemCount(236) < 99`)
T_SYSVAR = 0x7A       # push GetSysvar(<code>) -- EBin.B_SYSVAR (122); reads the next byte as the code
T_END = 0x7F

# A couple of useful system-variable codes (EventEngine.GetSysvar switch): 2 = usercontrol
# (IsMovementEnabled), 9 = ETb.GetChoose() = the index the player picked in the last choice window.
SYSVAR_USERCONTROL = 2
SYSVAR_CHOICE = 9
JMP_FALSE = 0x02      # jump-if-false  02 <skip:i16>
JMP_TRUE = 0x03       # jump-if-true   03 <skip:i16>
SETREGION_OP = 0x29
REGION_ENTRY_TYPE = 1
RANGE_TAG = 2         # the player-in-region (tread) trigger func -- runs EVERY frame in the quad
INTERACT_TAG = 3      # the press-action-while-in-quad func -- fires on the action button (a lever/sign)


def _cls(var_class) -> int:
    if isinstance(var_class, str):
        return VAR_CLASSES[var_class]
    return int(var_class) & 0xFF


def _i16(v: int) -> bytes:
    return struct.pack("<h", int(v))


def _push_var(var_class, idx: int) -> bytes:
    """Encode a variable reference token. Index <= 0xFF -> ``<cls> <idx>``; a larger index sets the
    long-index bit (0x20) on the class byte and uses a 2-byte little-endian index, exactly as the
    engine encodes it (EBin.getVarOperation: ``index << 8``, ``| 0x20`` when index > 0xFF). This lets
    flags live high in gEventGlobal (clear of base-game flags) and still decode correctly."""
    c = _cls(var_class)
    if 0 <= idx <= 0xFF:
        return bytes([c, idx])
    return bytes([c | 0x20]) + struct.pack("<H", idx & 0xFFFF)


# --- expression statements (opcode 0x05 + token stream) ---
def set_var(var_class, idx: int, value: int) -> bytes:
    """``set VAR = value`` -> ``05 <var> 7D <value:i16> 2C 7F``."""
    return bytes([EXPR_OP]) + _push_var(var_class, idx) + bytes([T_CONST]) + _i16(value) + bytes([T_ASSIGN, T_END])


def or_var(var_class, idx: int, value: int) -> bytes:
    """``VAR |= value`` -> ``05 <var> 7D <value:i16> 3F 7F`` (B_OR_LET). Used to OR a bit into a mask
    scratch (real-field verified: Dali/Storage builds its moogle-mail availability mask this way)."""
    return bytes([EXPR_OP]) + _push_var(var_class, idx) + bytes([T_CONST]) + _i16(value) + bytes([T_OR_ASSIGN, T_END])


def var_expr(var_class, idx: int) -> bytes:
    """A BARE variable read for use as an opcode EXPRESSION-arg (no leading ``0x05`` statement byte):
    ``<var-token> 7F``. Pass with ``arg_flags`` bit set so the engine evaluates it (``getv`` -> CalcExpr).
    Real-field verified (Dali/Storage 407: a CHOOSEPARAM arg is ``d6 09 7f`` = bare var + END)."""
    return _push_var(var_class, idx) + bytes([T_END])


def cond_truthy(var_class, idx: int) -> bytes:
    """``if (VAR)`` condition expr -> ``05 <var> 7F``."""
    return bytes([EXPR_OP]) + _push_var(var_class, idx) + bytes([T_END])


def cond_not(var_class, idx: int) -> bytes:
    """``if (!VAR)`` condition expr -> ``05 <var> 0E 7F``."""
    return bytes([EXPR_OP]) + _push_var(var_class, idx) + bytes([T_NOT, T_END])


def cond_eq(var_class, idx: int, value: int) -> bytes:
    """``if (VAR == value)`` condition expr -> ``05 <var> 7D <value:i16> 20 7F``."""
    return bytes([EXPR_OP]) + _push_var(var_class, idx) + bytes([T_CONST]) + _i16(value) + bytes([T_EQ, T_END])


def cond_item_count_lt(item_id: int, limit: int = 99) -> bytes:
    """``if (GetItemCount(item) < limit)`` condition expr -> ``05 7D <item:i16> 64 7D <limit:i16> 18 7F``.
    The FF9 treasure-chest space guard: don't open/give if the player can't carry it (default cap 99).
    Real-field verified (Dali/Storage 407: ``05 7d ec 00 64 7d 63 00 18 7f`` = ``GetItemCount(236) < 99``)."""
    return (bytes([EXPR_OP, T_CONST]) + _i16(item_id) + bytes([T_ITEMCOUNT, T_CONST])
            + _i16(limit) + bytes([T_LT, T_END]))


def push_sysvar(code: int) -> bytes:
    """A system-variable read token: ``7A <code>`` -> push ``GetSysvar(code)`` (EBin.B_SYSVAR). The
    movement gate is exactly this for code 2 (``05 7A 02 7F`` = IsMovementEnabled), so it's proven."""
    return bytes([T_SYSVAR, code & 0xFF])


def cond_sysvar_eq(code: int, value: int) -> bytes:
    """``if (GetSysvar(code) == value)`` condition expr -> ``05 7A <code> 7D <value:i16> 20 7F``.

    With ``code`` = :data:`SYSVAR_CHOICE` (9) this is the dialogue-choice test: branch on which row the
    player picked in the preceding choice window (``ETb.GetChoose()``)."""
    return bytes([EXPR_OP]) + push_sysvar(code) + bytes([T_CONST]) + _i16(value) + bytes([T_EQ, T_END])


# --- control flow ---
# 'ifnot (IsMovementEnabled) { return }' -- the verbatim region-trigger prologue (gates the body on
# usercontrol, exactly like every real exit/switch region). 7a 02 = IsMovementEnabled builtin.
MOVEMENT_GATE = bytes([EXPR_OP, 0x7A, 0x02, T_END, JMP_TRUE, 0x01, 0x00, opcodes.RETURN[0]])


def if_block(cond: bytes, body: bytes) -> bytes:
    """``if (cond) { body }`` -> cond + ``02 <len(body):i16>`` (jump-if-false past body) + body."""
    return cond + bytes([JMP_FALSE]) + _i16(len(body)) + body


def if_not_block(cond: bytes, body: bytes) -> bytes:
    """``if (!cond) { body }`` -> cond + ``03 <len(body):i16>`` (jump-if-TRUE past body) + body."""
    return cond + bytes([JMP_TRUE]) + _i16(len(body)) + body


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


def gated_set_region(zone, var_class, idx: int) -> bytes:
    """An Init body that defines the region quad ONLY while flag ``idx`` is CLEAR (else nothing) + a
    return. So a spent one-shot trigger sets up no quad on a later visit -> no leftover interaction
    prompt / tread. ``if (flag) skip SetRegion`` == :func:`if_not_block` over :func:`cond_truthy`."""
    return if_not_block(cond_truthy(var_class, idx), set_region(zone)) + opcodes.RETURN


def build_region_entry(zone, range_body: bytes, *, init_extra: bytes = b"", tag: int = RANGE_TAG,
                       init_body: bytes | None = None) -> bytes:
    """Assemble a type-1 region entry: Init (tag 0 = SetRegion(zone) + ``init_extra``; return) + a
    trigger func at ``tag`` (default :data:`RANGE_TAG` 2 = tread, every frame in the quad;
    :data:`INTERACT_TAG` 3 = press-action-in-quad, a lever/sign). ``init_extra`` runs once on field
    load (when InitRegion arms the region) -- e.g. a ``set flag = 0`` to re-arm a once-per-visit
    tread trigger each visit. ``init_body`` overrides the Init body entirely (e.g.
    :func:`gated_set_region` for a one-shot trigger that vanishes once spent)."""
    ib = init_body if init_body is not None else (set_region(zone) + init_extra + opcodes.RETURN)
    funcs = [(0, ib), (tag, range_body)]
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
                  spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0, init_extra: bytes = b"",
                  tag: int = RANGE_TAG, init_body: bytes | None = None):
    """Append a conditional region (Init=SetRegion(zone) + ``init_extra``, Range=range_body) into a
    free slot.

    Returns ``(new_bytes, slot)``. If ``activate`` (default), the region is turned on at field load
    by overwriting a Main_Init ``Wait(n)`` filler with ``InitRegion(slot, 0)`` -- shift-free. Pass
    ``activate=False`` for a zone that another zone enables at runtime (the switch-pair toggle).
    ``init_extra`` runs in the region's Init on each load (e.g. a flag reset for once-per-visit)."""
    eb = EbScript.from_bytes(data)
    if slot is None:
        slot = eb.first_free_slot()
    entry = build_region_entry(zone, range_body, init_extra=init_extra, tag=tag, init_body=init_body)
    out = edit.append_entry(data, slot, entry)
    if activate:
        out = edit.activate(out, opcodes.init_region(slot, 0), spawn_wait_n=spawn_wait_n,
                            spawn_wait_occurrence=spawn_wait_occurrence)
    return out, slot
