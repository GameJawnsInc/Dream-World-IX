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

    def __str__(self) -> str:
        parts = []
        for v, is_expr in zip(self.args, self.arg_is_expr):
            parts.append(v if is_expr else str(v))
        return f"[{self.off}] {self.name}({', '.join(parts)})"


def read_expr(raw: bytes, pos: int) -> tuple[str, int]:
    """Decode an expression token stream; returns (text, new_pos). Mirrors the engine."""
    ops = []
    while True:
        o = raw[pos]; pos += 1
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


def pretty_expr(raw: bytes, pos: int) -> tuple[str, int]:
    """Decode an expression token stream to a HUMAN-READABLE form; returns (text, new_pos). Same byte-walk as
    :func:`read_expr` but names each operator via the ``op_binary`` table and decodes a variable token into its
    ``Source.Type[index]`` form (so a story-flag read shows as ``Global.Bit[8512]``, an enemy-HP read as
    ``B_CURHP``). The read side of the battle-AI inspector; field scripts read the same way."""
    from ._exprtable import expr_op_name, decode_var
    out = []
    while True:
        o = raw[pos]; pos += 1
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:                       # a pure operator (no inline operand bytes)
            out.append(expr_op_name(o))
            if o == 0x7F:                                   # B_EXPR_END
                break
            continue
        if o == 0x7E:                                       # B_CONST4 -- a 4-byte literal
            v = raw[pos] | (raw[pos + 1] << 8) | (raw[pos + 2] << 16) | (raw[pos + 3] << 24); pos += 4
            out.append(f"const({v})")
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
