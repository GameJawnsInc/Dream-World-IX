"""FF9 field event-script (.eb) disassembler — decodes the bytecode stream.

This is the read side of the ``.eb`` library. It decodes one instruction at a time using the
baked opcode tables (``_optables``), so it needs no Memoria source at runtime. ``read_code``
returns a structured :class:`Instr` (offset, opcode, decoded immediate args, byte length) that
the model and the content injectors use to locate features symbolically — e.g. "find the
``Wait(2)`` in Main_Init" — instead of relying on hardcoded byte offsets.

The decoding mirrors Memoria's ``EventEngine`` byte reader exactly:
  * a leading ``0xFF`` byte selects the extended (2-byte) opcode page,
  * opcodes >= 0x10 with operands carry a 1-byte ``argFlag`` bitmask; a set bit means that
    operand is an *expression* (RPN-ish token stream) rather than a fixed-width immediate,
  * a few opcodes have a variable operand count read from the stream (0x06 switch, 0x0B, 0x0D).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ._optables import OP_ARG_COUNT, OP_ARG_SIZE, OP_NAMES

SWITCH_OPS = (0x06, 0x0B, 0x0D)   # JMP_SWITCHEX (explicit value/offset pairs) / JMP_SWITCH (contiguous range) /
#                                   JMP_SWITCH with a 2-byte case count. See decode_switch.


def op_name(op: int) -> str:
    return OP_NAMES.get(op, f"op_{op:02X}")


def argsize(op: int, i: int) -> int:
    """Byte width of operand *i* of *op* (immediate form)."""
    if op == 0x29:
        return 4
    if op in (0x06, 0x0B, 0x0D):
        return 2
    a = OP_ARG_SIZE[op] if op < len(OP_ARG_SIZE) else None
    return a[i] if (a and i < len(a)) else 0


@dataclass
class Instr:
    """One decoded instruction.

    off       : absolute byte offset where the instruction begins
    op         : opcode (0x100 | x for extended/0xFF-prefixed opcodes)
    args       : decoded operands — ints for immediates, str tokens for expression operands
    arg_is_expr: parallel bool list; True where the operand was an expression
    length     : total bytes consumed (off .. off+length)
    """

    off: int
    op: int
    args: list = field(default_factory=list)
    arg_is_expr: list = field(default_factory=list)
    length: int = 0

    @property
    def name(self) -> str:
        return op_name(self.op)

    @property
    def end(self) -> int:
        return self.off + self.length

    def imm(self, i: int):
        """Immediate operand *i* as int, or None if it was an expression."""
        return self.args[i] if (i < len(self.args) and not self.arg_is_expr[i]) else None

    @property
    def is_switch(self) -> bool:
        return self.op in SWITCH_OPS

    def switch(self) -> "SwitchInfo | None":
        """Structured (case value -> absolute target) decode if this is a switch; else None."""
        return decode_switch(self)

    def __str__(self) -> str:
        parts = []
        for v, is_expr in zip(self.args, self.arg_is_expr):
            parts.append(v if is_expr else str(v))
        return f"[{self.off}] {self.name}({', '.join(parts)})"


@dataclass
class SwitchEdge:
    """One arm of a switch: a selector ``value`` (None = the default arm) -> an absolute byte ``target``."""
    value: int | None
    target: int
    is_default: bool = False


@dataclass
class SwitchInfo:
    """A decoded switch dispatch table. ``base`` = the lowest selector value of the contiguous-range form
    (0x0B/0x0D), or None for the explicit value/offset form (0x06). ``edges`` = the cases then the default.
    Targets are ABSOLUTE byte offsets (same space as ``Instr.off`` / ``Func.abs_start``), valid only within
    the owning function. The selector itself is popped from the expression stack at runtime (pushed by the
    preceding ``0x05``), so it is not part of this inline-table decode."""
    op: int
    base: int | None
    edges: list


def _sx_hi(w: int) -> int:
    """Sign-extend only the HIGH byte of a 16-bit word -- the engine reads the contiguous-form base as
    ``offsetL | ((SByte)offsetH << 8)`` (EBin.cs JMP_SWITCH), so a base 0xFFFE means selector -2, not 65534."""
    return (w & 0xFF) | ((((w >> 8) & 0xFF) ^ 0x80) - 0x80) * 256


def decode_switch(instr: Instr) -> "SwitchInfo | None":
    """Decode a switch instruction (0x06 / 0x0B / 0x0D) into a :class:`SwitchInfo` of absolute case+default
    targets, or None if *instr* isn't a switch (or its operands aren't plain immediates). Derived from the
    Memoria engine (EBin.cs JMP_SWITCH / JMP_SWITCHEX) and validated 100% boundary-aligned across all 5563
    switches in the 676 shipping fields.

    Layout (O = ``instr.off``; ``a`` = the flat 2-byte operands :attr:`Instr.args`):
      * 0x06 (explicit): ``a[0]`` = default reloffset, then n pairs ``(value=a[1+2k], reloffset=a[2+2k])``;
        anchor = O+4; target = anchor + reloffset.
      * 0x0B (contiguous): ``base = sx_hi(a[0])``, ``a[1]`` = default reloffset, ``a[2..]`` = n contiguous
        case reloffsets for selectors base..base+n-1; anchor = O+1.
      * 0x0D (contiguous, 2-byte count): identical to 0x0B with anchor = O+2 (none ship; by-construction).
    All reloffsets are unsigned u16 (the engine only jumps forward)."""
    op = instr.op
    if op not in SWITCH_OPS:
        return None
    a = instr.args
    if any(not isinstance(x, int) for x in a):     # a switch never has expression operands; bail if malformed
        return None
    O = instr.off
    if op == 0x06:
        if not a:
            return None
        anchor = O + 4
        n = (len(a) - 1) // 2
        edges = [SwitchEdge(a[1 + 2 * k], anchor + a[2 + 2 * k]) for k in range(n)]
        edges.append(SwitchEdge(None, anchor + a[0], True))
        return SwitchInfo(op, None, edges)
    if len(a) < 2:
        return None
    anchor = O + (2 if op == 0x0D else 1)
    base = _sx_hi(a[0])
    n = len(a) - 2
    edges = [SwitchEdge(base + i, anchor + a[2 + i]) for i in range(n)]
    edges.append(SwitchEdge(None, anchor + a[1], True))
    return SwitchInfo(op, base, edges)


# --- control-flow facts (engine ABI) ----------------------------------------------------------------
# The flow-TERMINATOR opcodes: a path reaching one ENDS (the engine's per-function dispatch stops via
# adFin(); the IP never advances into adjacent bytecode). RET 0x04 / TerminateEntry 0x1C + the high ops
# whose DoEventCode return code routes through adFin(): Battle 0x2A / Field 0x2B / STOP 0x4F /
# TetraMaster 0xAE / WorldMap 0xB6 / GameOver 0xF5 (verified vs EBin.cs). NOTE: battle/ailint.py keeps a
# parallel private copy (it predates this) -- both are guarded by their whole-corpus soundness sweeps, which
# would fail if either drifted from the engine.
TERMINATOR_OPS = frozenset({0x04, 0x1C, 0x2A, 0x2B, 0x4F, 0xAE, 0xB6, 0xF5})
JUMP_OPS = frozenset({0x01, 0x02, 0x03})   # JMP / JMP_IFNOT / JMP_IF -- a 2-byte relative offset operand


def jump_target(ins: Instr) -> "int | None":
    """The absolute byte target of a relative jump (0x01/0x02/0x03), or None if its offset is an expression.
    Signedness MATCHES the engine: JMP (0x01) / JMP_IF (0x03) read a SIGNED int16; JMP_IFNOT (0x02) reads its
    skip UNSIGNED -- so a backward JMP_IFNOT becomes a huge forward target a bounds check catches."""
    if not ins.arg_is_expr or ins.arg_is_expr[0]:
        return None
    raw = ins.imm(0)
    if raw is None:
        return None
    if ins.op == 0x02:                                          # JMP_IFNOT -- engine reads this UNSIGNED
        return ins.end + raw
    return ins.end + (raw - 0x10000 if raw >= 0x8000 else raw)  # JMP / JMP_IF -- signed int16


def read_expr(raw: bytes, pos: int) -> tuple[str, int]:
    """Decode an expression token stream; returns (text, new_pos). Mirrors the engine."""
    ops = []
    while True:
        o = raw[pos]; pos += 1
        if o == 0xD3:                       # flexible_varfunc (Memoria): u16 id + u8 argc.
            fid = raw[pos] | (raw[pos + 1] << 8)   # The engine carves 0xD3 OUT of the var-token
            ops.append(f"op{o:02X}({fid},{raw[pos + 2]})")   # space (EBin.expr checks it first) --
            pos += 3                        # decoding it as a short-index var desyncs by 2 bytes.
            continue
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:
            ops.append(f"op{o:02X}")
            if o == 0x7F:
                break
            continue
        if o == 0x7E:
            a = [raw[pos], raw[pos + 1], raw[pos + 2], raw[pos + 3]]; pos += 4
        elif o >= 0xE0 or o in (0x78, 0x7D):
            a = [raw[pos], raw[pos + 1]]; pos += 2
        else:
            a = [raw[pos]]; pos += 1
        ops.append(f"op{o:02X}({','.join(str(x) for x in a)})")
    return "{" + " ".join(ops) + "}", pos


def const4_engine_value(u32: int) -> int:
    """What the engine reads from a B_CONST4's 4 bytes: the low 26 bits, sign-extended (EBin.cs B_CONST4 masks
    ``& 0x3FFFFFF``, getv reads ``(t0 << 6) >> 6``). The 4 bytes are the ordinary spelling of that value iff
    ``const4_engine_value(u) & 0xFFFFFFFF == u``; stock also ships two literals that are NOT (0x80000000, which
    reads 0, and 0x02000000, which reads -2^25), so the two can differ."""
    w = u32 & 0x3FFFFFF
    return w - (1 << 26) if w & (1 << 25) else w


def pretty_expr(raw: bytes, pos: int) -> tuple[str, int]:
    """Decode an expression token stream to a HUMAN-READABLE form; returns (text, new_pos). Same byte-walk as
    :func:`read_expr` but names each operator via the ``op_binary`` table and decodes a variable token into its
    ``Source.Type[index]`` form (so a story-flag read shows as ``Global.Bit[8512]``, an enemy-HP read as
    ``B_CURHP``). The read side of the battle-AI inspector; field scripts read the same way."""
    from ._exprtable import expr_op_name, decode_var, flex_fn_name
    out = []
    while True:
        o = raw[pos]; pos += 1
        if o == 0xD3:                                       # flexible_varfunc: u16 id + u8 argc
            fid = raw[pos] | (raw[pos + 1] << 8)
            out.append(flex_fn_name(fid, raw[pos + 2]))
            pos += 3
            continue
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:                       # a pure operator (no inline operand bytes)
            out.append(expr_op_name(o))
            if o == 0x7F:                                   # B_EXPR_END
                break
            continue
        if o == 0x7E:                                       # B_CONST4 -- a 4-byte literal (distinct token so an
            u = raw[pos] | (raw[pos + 1] << 8) | (raw[pos + 2] << 16) | (raw[pos + 3] << 24); pos += 4
            v = const4_engine_value(u)                      # assemble() can round-trip it back to B_CONST4), printed
            if v & 0xFFFFFFFF == u:                         # as the value the ENGINE reads -- or, for bytes that are
                out.append(f"const4({v})")                  # not that value's sign-extended form (stock ships two),
            else:                                           # as the raw bytes, so the text never claims a value
                out.append(f"const4raw(0x{u:08X})")         # the engine does not read
        elif o == 0x7D:                                     # B_CONST -- a 2-byte literal
            v = raw[pos] | (raw[pos + 1] << 8); pos += 2
            out.append(f"const({v})")
        elif o == 0x78:                                     # B_OBJSPECA -- obj-var read: uid (hi) + field (lo)
            out.append(f"obj(uid={raw[pos]}).f[{raw[pos + 1]}]"); pos += 2
        elif o in (0x79, 0x7A):                             # B_SYSLIST / B_SYSVAR -- 1-byte index
            out.append(f"{expr_op_name(o)}[{raw[pos]}]"); pos += 1
        elif o in (0x29, 0x5F):                             # B_MEMBER / B_PTR -- 1-byte operand
            out.append(f"{expr_op_name(o)}({raw[pos]})"); pos += 1
        elif o >= 0xE0:                                     # a long-index variable (2-byte index)
            out.append(decode_var(o, raw[pos] | (raw[pos + 1] << 8))); pos += 2
        else:                                               # a short-index variable (0xC0..0xDF, 1-byte index)
            out.append(decode_var(o, raw[pos])); pos += 1
    return "{" + " ".join(out) + "}", pos


def read_code(raw: bytes, pos: int) -> tuple[Instr, int]:
    """Decode one instruction at *pos*; returns (Instr, new_pos)."""
    start = pos
    op = raw[pos]; pos += 1
    if op == 0xFF:
        op = 0x100 | raw[pos]; pos += 1
    ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
    arg_flag = 0
    if op >= 0x10 and ac != 0:
        arg_flag = raw[pos]; pos += 1
    if op == 0x05:
        arg_flag = 1
    if ac < 0:
        ac = raw[pos]; pos += 1
        if op == 0x0D:
            ac |= raw[pos] << 8; pos += 1
        if op == 0x06:
            ac = 1 + 2 * ac
        elif op in (0x0B, 0x0D):
            ac = 2 + ac
    args: list = []
    is_expr: list[bool] = []
    for i in range(ac):
        if arg_flag & (1 << i):
            s, pos = read_expr(raw, pos)
            args.append(s); is_expr.append(True)
        else:
            sz = argsize(op, i)
            v = 0
            for k in range(sz):
                v |= raw[pos + k] << (8 * k)
            pos += sz
            args.append(v); is_expr.append(False)
    return Instr(start, op, args, is_expr, pos - start), pos


def iter_code(raw: bytes, start: int, end: int):
    """Yield Instr objects decoded from raw[start:end]. Stops cleanly at *end*."""
    pos = start
    guard = 0
    while pos < end and guard < 100000:
        instr, pos = read_code(raw, pos)
        yield instr
        guard += 1


def _expr_uid_offsets(raw: bytes, pos: int) -> tuple[int, list]:
    """Walk one expression token stream (mirrors :func:`read_expr`); return (new_pos, uid_offsets) where
    each uid_offset is the absolute byte offset of a ``0x78`` (B_OBJSPECA) token's UID operand byte (the
    first of its two data bytes -- ``78 <uid> <field>``, uid first)."""
    offs = []
    while True:
        o = raw[pos]; pos += 1
        if o == 0xD3:                         # flexible_varfunc: u16 id + u8 argc (no uid inside)
            pos += 3
            continue
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:
            if o == 0x7F:
                break
            continue
        if o == 0x7E:
            pos += 4
        elif o >= 0xE0 or o in (0x78, 0x7D):
            if o == 0x78:
                offs.append(pos)              # the UID byte (first data byte of the obj-var token)
            pos += 2
        else:
            pos += 1
    return pos, offs


def expr_obj_uid_offsets(raw: bytes, start: int, end: int) -> list:
    """Absolute byte offsets of every ``0x78`` (B_OBJSPECA, obj-var read) token's UID operand byte in
    ``raw[start:end]``. Decodes instruction-by-instruction exactly like :func:`read_code` and walks each
    EXPRESSION operand's token stream -- NOT a raw-byte ``0x78`` scan (which false-positives on const data,
    per docs/OBJECT_CARRY.md S3 invariant 2). The object graft uses this to remap a sibling uid read inside
    an expression operand (a same-length 1-byte patch). Mirrors ``read_code``'s operand decode."""
    out = []
    pos = start
    while pos < end:
        op = raw[pos]; pos += 1
        if op == 0xFF:
            op = 0x100 | raw[pos]; pos += 1
        ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
        arg_flag = 0
        if op >= 0x10 and ac != 0:
            arg_flag = raw[pos]; pos += 1
        if op == 0x05:
            arg_flag = 1
        if ac < 0:
            ac = raw[pos]; pos += 1
            if op == 0x0D:
                ac |= raw[pos] << 8; pos += 1
            if op == 0x06:
                ac = 1 + 2 * ac
            elif op in (0x0B, 0x0D):
                ac = 2 + ac
        for i in range(ac):
            if arg_flag & (1 << i):
                pos, uoffs = _expr_uid_offsets(raw, pos)
                out.extend(uoffs)
            else:
                pos += argsize(op, i)
    return out


def _expr_const_offsets(raw: bytes, pos: int, operand_index: int, out: list) -> int:
    """Walk one expression token stream (mirrors :func:`read_expr`), appending
    ``(abs_payload_off, value, operand_index)`` for every 2-byte ``0x7D`` (B_CONST) literal; returns new_pos.
    ``abs_payload_off`` is the offset of the literal's first (low) byte -- an in-place LE overwrite there is
    length-preserving by construction. 4-byte ``0x7E`` (B_CONST4) literals are skipped, not collected."""
    while True:
        o = raw[pos]; pos += 1
        if o == 0xD3:                         # flexible_varfunc: u16 id + u8 argc (no B_CONST inside)
            pos += 3
            continue
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:
            if o == 0x7F:
                break
            continue
        if o == 0x7E:
            pos += 4
        elif o >= 0xE0 or o in (0x78, 0x7D):
            if o == 0x7D:
                out.append((pos, raw[pos] | (raw[pos + 1] << 8), operand_index))
            pos += 2
        else:
            pos += 1
    return pos


def _expr_tokens(raw: bytes, pos: int) -> tuple[int, list]:
    """Walk one expression token stream (mirrors :func:`read_expr` byte for byte) into DECODED tokens; return
    ``(new_pos, [(op, value), ...])``. ``value`` per token: ``0x7D`` B_CONST -> signed Int16; ``0x7E`` B_CONST4 ->
    :func:`const4_engine_value`; ``0x5F`` B_PTR / ``0x29`` B_MEMBER / ``0x79`` B_SYSLIST / ``0x7A`` B_SYSVAR -> its
    byte; ``0x78`` B_OBJSPECA -> ``(uid, field)``; ``0xD3`` flexible_varfunc -> ``(fid, argc)``; a ``0xC0+`` var token
    -> its index; a pure operator -> None. The terminating ``0x7F`` is kept as the last token."""
    toks = []
    while True:
        o = raw[pos]; pos += 1
        if o == 0xD3:                         # flexible_varfunc: u16 id + u8 argc (carved out of the var space)
            toks.append((o, (raw[pos] | (raw[pos + 1] << 8), raw[pos + 2])))
            pos += 3
            continue
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:
            toks.append((o, None))
            if o == 0x7F:
                break
            continue
        if o == 0x7E:
            u = raw[pos] | (raw[pos + 1] << 8) | (raw[pos + 2] << 16) | (raw[pos + 3] << 24); pos += 4
            toks.append((o, const4_engine_value(u)))
        elif o == 0x7D:
            v = raw[pos] | (raw[pos + 1] << 8); pos += 2
            toks.append((o, v - 0x10000 if v >= 0x8000 else v))
        elif o == 0x78:
            toks.append((o, (raw[pos], raw[pos + 1]))); pos += 2
        elif o >= 0xE0:                       # a long-index variable (2-byte index)
            toks.append((o, raw[pos] | (raw[pos + 1] << 8))); pos += 2
        else:                                 # 0x29/0x5F/0x79/0x7A + a short-index variable (1 byte)
            toks.append((o, raw[pos])); pos += 1
    return pos, toks


def instr_expr_tokens(raw: bytes, ins: Instr) -> list:
    """Per operand of *ins*: its decoded expression tokens (:func:`_expr_tokens`) when that operand is an
    expression, else None. Re-decodes the instruction exactly like :func:`read_code`; the walk SELF-VERIFIES by
    landing on ``ins.end`` (a mismatch raises ValueError, never a silently shifted token stream)."""
    pos = ins.off
    op = raw[pos]; pos += 1
    if op == 0xFF:
        op = 0x100 | raw[pos]; pos += 1
    ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
    arg_flag = 0
    if op >= 0x10 and ac != 0:
        arg_flag = raw[pos]; pos += 1
    if op == 0x05:
        arg_flag = 1
    if ac < 0:
        ac = raw[pos]; pos += 1
        if op == 0x0D:
            ac |= raw[pos] << 8; pos += 1
        if op == 0x06:
            ac = 1 + 2 * ac
        elif op in (0x0B, 0x0D):
            ac = 2 + ac
    out: list = []
    for i in range(ac):
        if arg_flag & (1 << i):
            pos, toks = _expr_tokens(raw, pos)
            out.append(toks)
        else:
            pos += argsize(op, i)
            out.append(None)
    if pos != ins.end:
        raise ValueError(f"instr_expr_tokens: operand walk ended at {pos}, expected {ins.end} "
                         f"(op {op:#x} @{ins.off} -- decode disagreement with read_code)")
    return out


# --- walkmesh-id reads: the fork walkmesh-literal lint's scanner (build._lint_fork_walkmesh_ids) -------------------
# B_BGIID (0x70) / B_BGIFLOOR (0x71) push the engine's walkmesh TRIANGLE id (global .bgi file order) / FLOOR index
# (floorList position) for the uid on the stack (rung 0, studies/walkmesh-sensor/PLAN.md); EnablePathTriangle 0x9A
# (BGI_triSetActive) / EnablePath 0xCB (BGI_floorSetActive, WalkMesh.cs:1005 -- floorList[floorNdx]) toggle one by
# id. All four key donor logic on walkmesh ids as LITERALS, which a rebuilt/renumbered walkmesh silently moves.
_B_BGIID, _B_BGIFLOOR = 0x70, 0x71
_WALK_READ_KIND = {_B_BGIID: "tri", _B_BGIFLOOR: "floor"}
_WALK_TOGGLE_KIND = {0x9A: "enable", 0xCB: "floor_enable"}
_CMP_OPS = frozenset(range(0x18, 0x24))    # B_LT/GT/LE/GE 0x18-0x1B, their _E forms 0x1C-0x1F, B_EQ/NE 0x20/21 + _E 0x22/23
_LET_OPS = frozenset(range(0x2C, 0x46))    # B_LET 0x2C .. B_OR_LET_E 0x45 -- every *_LET assignment operator
_CONST_OPS = (0x7D, 0x7E)                  # B_CONST / B_CONST4


@dataclass(frozen=True)
class WalkmeshRead:
    """One walkmesh-id use in decoded bytecode (see :func:`walkmesh_reads`)."""
    off: int          # absolute offset of the instruction carrying the read
    op: int           # that instruction's opcode (0x05 statement, 0x9A, ...)
    kind: str         # "tri" (B_BGIID 0x70) | "floor" (B_BGIFLOOR 0x71) | "enable" (EnablePathTriangle 0x9A)
    #                   | "floor_enable" (EnablePath 0xCB -- a floor index)
    subject: str      # "B_PTR(n)" | "const(n)" | "expr" | "" (a toggle)
    role: str         # "compare" | "switch" | "store" | "other" | "immediate"
    literals: tuple   # ids/floors the logic keys on (signed; negatives dropped)


def _is_leaf(tok) -> bool:
    """True for a token that PUSHES one value and pops nothing (a literal / pointer / variable read)."""
    o, v = tok
    if o in _CONST_OPS or o in (0x5F, 0x78, 0x79, 0x7A):
        return True
    if o == 0xD3:
        return v[1] == 0                  # a flexible_varfunc with no stack args
    return o >= 0xC0


def walkmesh_reads(raw: bytes, start: int, end: int) -> list:
    """Every walkmesh-id use in ``raw[start:end]`` as :class:`WalkmeshRead` records, in byte order. A DECODED scan
    -- instruction by instruction via :func:`iter_code`, each expression operand walked token by token like
    :func:`read_expr` (:func:`instr_expr_tokens`) -- NEVER a byte regex: a ``0x70``/``0x71`` byte inside a literal,
    an immediate or a var index is not a read (a raw scan false-positives on ``7E 5F 15 70 ..``).

    For each ``0x70``/``0x71`` token at position ``j``:
      * subject -- the token at ``j-1``: ``B_PTR(n)`` / ``const(n)`` (B_CONST or B_CONST4) / else ``expr``;
      * ``compare`` -- ``tok[j+1]`` is a literal and ``tok[j+2]`` a compare op, or ``tok[j-2]`` is a literal,
        ``tok[j-1]`` a single-token operand and ``tok[j+1]`` a compare op -> that literal;
      * ``store`` -- ``tok[j+1]`` is ``B_LET`` or another ``*_LET`` op;
      * ``switch`` -- the read is the last token before ``B_EXPR_END`` of a ``0x05`` statement and the NEXT
        instruction is a switch (0x06/0x0B/0x0D) -> its case values (never the default);
      * ``other`` -- anything else (a derived use the scan cannot trace).
    ``0x9A``/``0xCB`` with an immediate first arg -> ``role="immediate"``, ``literals=(arg,)``; an expression first
    arg -> ``role="other"`` (its own tokens are scanned like any operand). Negative literals are dropped."""
    raw = bytes(raw)
    instrs = list(iter_code(raw, start, end))
    out = []
    for n, ins in enumerate(instrs):
        tk = _WALK_TOGGLE_KIND.get(ins.op)
        if tk is not None and ins.args:
            v = ins.imm(0)
            if v is None:
                out.append(WalkmeshRead(ins.off, ins.op, tk, "", "other", ()))
            else:
                out.append(WalkmeshRead(ins.off, ins.op, tk, "", "immediate", (v,) if v >= 0 else ()))
        if not any(ins.arg_is_expr):
            continue
        nxt = instrs[n + 1] if n + 1 < len(instrs) else None
        for toks in instr_expr_tokens(raw, ins):
            if toks is None:
                continue
            for j, (o, _v) in enumerate(toks):
                kind = _WALK_READ_KIND.get(o)
                if kind is None:
                    continue
                prev = toks[j - 1] if j >= 1 else None
                if prev is not None and prev[0] == 0x5F:
                    subject = f"B_PTR({prev[1]})"
                elif prev is not None and prev[0] in _CONST_OPS:
                    subject = f"const({prev[1]})"
                else:
                    subject = "expr"
                nx1 = toks[j + 1] if j + 1 < len(toks) else None
                nx2 = toks[j + 2] if j + 2 < len(toks) else None
                lits: tuple = ()
                if nx1 is not None and nx2 is not None and nx1[0] in _CONST_OPS and nx2[0] in _CMP_OPS:
                    role, lits = "compare", (nx1[1],)
                elif (nx1 is not None and nx1[0] in _CMP_OPS and j >= 2 and prev is not None and _is_leaf(prev)
                      and toks[j - 2][0] in _CONST_OPS):
                    role, lits = "compare", (toks[j - 2][1],)
                elif nx1 is not None and nx1[0] in _LET_OPS:
                    role = "store"
                elif (ins.op == 0x05 and nx1 is not None and nx1[0] == 0x7F and j + 2 == len(toks)
                      and nxt is not None and nxt.is_switch):
                    role = "switch"
                    si = decode_switch(nxt)
                    lits = tuple(e.value for e in si.edges if not e.is_default) if si else ()
                else:
                    role = "other"
                out.append(WalkmeshRead(ins.off, ins.op, kind, subject, role,
                                        tuple(x for x in lits if x >= 0)))
    return out


def instr_expr_consts(raw: bytes, ins: Instr) -> list:
    """``[(abs_payload_off, value, operand_index), ...]`` for every 2-byte ``B_CONST`` (0x7D) literal inside
    *ins*'s EXPRESSION operands, in byte order. Re-decodes the instruction exactly like :func:`read_code`
    but tracking positions; the walk SELF-VERIFIES by landing on ``ins.end`` (a mismatch raises ValueError,
    never a silent wrong offset). Immediate operands carry no expression consts. The write-side companion of
    the ``op7D(lo,hi)`` tokens :func:`read_expr` renders -- logic_edit's ``expr_literal`` kind patches these."""
    pos = ins.off
    op = raw[pos]; pos += 1
    if op == 0xFF:
        op = 0x100 | raw[pos]; pos += 1
    ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
    arg_flag = 0
    if op >= 0x10 and ac != 0:
        arg_flag = raw[pos]; pos += 1
    if op == 0x05:
        arg_flag = 1
    if ac < 0:
        ac = raw[pos]; pos += 1
        if op == 0x0D:
            ac |= raw[pos] << 8; pos += 1
        if op == 0x06:
            ac = 1 + 2 * ac
        elif op in (0x0B, 0x0D):
            ac = 2 + ac
    out: list = []
    for i in range(ac):
        if arg_flag & (1 << i):
            pos = _expr_const_offsets(raw, pos, i, out)
        else:
            pos += argsize(op, i)
    if pos != ins.end:
        raise ValueError(f"instr_expr_consts: operand walk ended at {pos}, expected {ins.end} "
                         f"(op {op:#x} @{ins.off} -- decode disagreement with read_code)")
    return out
