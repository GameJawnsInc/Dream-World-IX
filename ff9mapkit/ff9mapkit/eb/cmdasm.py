"""Phase-6c-ii: the `.eb` COMMAND ASSEMBLER -- assemble whole instructions (the inverse of `disasm.read_code`).

Phase-6c-i (`exprasm`) assembles one EXPRESSION; this assembles a whole INSTRUCTION (opcode + arg-flag +
operands) and a BLOCK of them -- the body of a new enemy-AI branch that the existing length-changing primitives
(`eb.edit.add_function` / `replace_function_body`) splice into a forked battle `.eb`. It MIRRORS `read_code`'s
byte-walk step for step (the `0xFF` extended page, the `argFlag` byte for `op >= 0x10`, the forced-expr `SET`=0x05,
the stream-read operand count for the variable ops 0x06/0x0B/0x0D and the count-prefixed 0x29), so it reproduces
the exact bytes `read_code` decoded -- given operands in the PRETTY-decoded form (mnemonic via the disassembler's
`_cmd_name`, expression operands as `{ ... }` from `pretty_expr`, the form `battleai._decode_func_pretty` emits).
Expression operands go through `exprasm.assemble`; immediates are little-endian of the opcode's `argsize`.

`assemble_block` adds the authoring layer: `label:` lines + symbolic jump targets (`JMP done`,
`JMP_IF {expr} loop`) resolved to the signed relative offsets the engine expects, in a two-pass walk (instruction
sizes are independent of jump *values* -- a jump immediate is always 2 bytes -- so offsets are known before the
targets are). Provenance-clean: only the open-source opcode/operator NAMES are used.
"""
from __future__ import annotations

from . import exprasm
from ._optables import OP_ARG_COUNT, OP_NAMES
from .disasm import argsize

# the control-op overlay (mirrors battleai._CTRL_NAMES / disasm naming precedence): the low ops EBin handles in
# jumpToCommand, which OP_NAMES leaves unnamed. The disassembler names a command CTRL-first, then OP_NAMES.
_CTRL_NAMES = {0x01: "JMP", 0x02: "JMP_IFNOT", 0x03: "JMP_IF", 0x04: "RET", 0x05: "SET", 0x06: "SWITCHEX",
               0x0B: "SWITCH", 0x0D: "SWITCH2"}

# name -> opcode, the inverse of disasm._cmd_name. Build OP_NAMES first, then OVERLAY the control names (so they
# win for 0x01-0x0D exactly as the decoder's precedence does).
_OP_BY_NAME: dict[str, int] = {}
for _op, _nm in OP_NAMES.items():
    _OP_BY_NAME.setdefault(_nm, _op)
for _op, _nm in _CTRL_NAMES.items():
    _OP_BY_NAME[_nm] = _op

# the jump ops whose single immediate is a SIGNED relative offset (target = instr_end + offset) -- the only ops
# whose operand may be a symbolic label in a block.
_JUMP_OPS = {0x01, 0x02, 0x03}


class CmdAsmError(ValueError):
    pass


def _resolve_op(name: str) -> int:
    """Mnemonic -> opcode (the inverse of disasm naming). Accepts the `op_XX` fallback for an unnamed opcode."""
    if name in _OP_BY_NAME:
        return _OP_BY_NAME[name]
    if name.startswith("op_"):
        try:
            return int(name[3:], 16)
        except ValueError:
            pass
    raise CmdAsmError(f"unknown command mnemonic {name!r}")


def _emit_op(op: int) -> bytearray:
    out = bytearray()
    if op >= 0x100:                                         # extended page -- a 0xFF prefix selects it
        out += bytes((0xFF, op & 0xFF))
    else:
        out.append(op)
    return out


def _imm_bytes(op: int, i: int, value: int) -> bytes:
    sz = argsize(op, i)
    if sz <= 0:
        raise CmdAsmError(f"{OP_NAMES.get(op, hex(op))} operand {i} has no immediate width (expected an expression?)")
    if not 0 <= value <= (1 << (8 * sz)) - 1:
        raise CmdAsmError(f"operand {i} value {value} out of range for a {sz}-byte immediate")
    return value.to_bytes(sz, "little")


def assemble_instruction(name: str, operands, *, label_offsets=None, instr_end: int | None = None) -> bytes:
    """Assemble ONE instruction -> its bytes, the exact inverse of `read_code`. ``operands`` is the decoded
    operand list (each an immediate int/str, a ``{ ... }`` expression string, or -- for a jump -- a label name).
    ``label_offsets``/``instr_end`` are only consulted to resolve a symbolic jump target (see assemble_block)."""
    operands = [str(o) for o in operands]
    op = _resolve_op(name)
    out = _emit_op(op)
    ac0 = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
    is_expr = [o.startswith("{") for o in operands]

    if op >= 0x10 and ac0 != 0:                             # an argFlag byte: bit i set == operand i is an expr
        flag = 0
        for i, e in enumerate(is_expr):
            if e:
                flag |= 1 << i
        out.append(flag)
    # op 0x05 (SET) forces argFlag=1 with NO byte on the wire -- its single operand is always an expression.
    if op == 0x05 and (len(operands) != 1 or not is_expr[0]):
        raise CmdAsmError("SET (0x05) takes exactly one { ... } expression operand")

    if ac0 < 0:                                             # a variable operand count, read from the stream
        c = len(operands)
        if op == 0x06:                                      # SWITCHEX: count = 1 + 2n  ->  n
            if c < 1 or (c - 1) % 2:
                raise CmdAsmError(f"SWITCHEX needs an odd operand count (1+2n), got {c}")
            out.append((c - 1) // 2)
        elif op == 0x0B:                                    # SWITCH: count = 2 + n
            if c < 2:
                raise CmdAsmError(f"SWITCH needs >=2 operands, got {c}")
            out.append(c - 2)
        elif op == 0x0D:                                    # SWITCH2: count = 2 + n, n is 2 bytes
            if c < 2:
                raise CmdAsmError(f"SWITCH2 needs >=2 operands, got {c}")
            out += (c - 2).to_bytes(2, "little")
        else:                                               # 0x29 etc.: a plain 1-byte count == operand count
            out.append(c)
    elif op != 0x05 and len(operands) != ac0:
        raise CmdAsmError(f"{name} takes {ac0} operand(s), got {len(operands)}")

    for i, o in enumerate(operands):
        if is_expr[i]:
            out += exprasm.assemble(o)
        elif op in _JUMP_OPS and not o.lstrip("-").isdigit():   # a symbolic label target
            if label_offsets is None or instr_end is None:
                raise CmdAsmError(f"jump to label {o!r} outside assemble_block (no label table)")
            if o not in label_offsets:
                raise CmdAsmError(f"undefined label {o!r}")
            rel = label_offsets[o] - instr_end
            if op == 0x02 and rel < 0:                       # JMP_IFNOT (beq) reads its offset UNSIGNED in-engine
                raise CmdAsmError(f"JMP_IFNOT cannot branch BACKWARD to {o!r}: the engine reads its skip offset "
                                  f"unsigned, so a negative target executes as a ~64KB forward jump (crash). Use "
                                  f"JMP_IF over a forward JMP, or invert the condition. (JMP/JMP_IF are signed.)")
            out += (rel & 0xFFFF).to_bytes(2, "little")
        else:
            out += _imm_bytes(op, i, int(o))
    return bytes(out)


def _split_operands(inner: str) -> list:
    """Split an instruction's operand list on top-level commas (respecting ``{}`` / ``()`` / ``[]`` nesting)."""
    out, depth, cur = [], 0, ""
    for ch in inner:
        if ch in "{([":
            depth += 1
        elif ch in "})]":
            depth -= 1
            if depth < 0:
                raise CmdAsmError(f"unbalanced bracket in operands: {inner!r}")
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if depth != 0:
        raise CmdAsmError(f"unbalanced bracket in operands: {inner!r}")
    if cur.strip():
        out.append(cur.strip())
    return out


def _parse_line(line: str):
    """A source line -> ('label', name) | ('instr', name, [operands]) | None (blank/comment)."""
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    if line.endswith(":") and "(" not in line:
        return ("label", line[:-1].strip())
    if not line.endswith(")") or "(" not in line:
        raise CmdAsmError(f"malformed instruction line {line!r} (want Mnemonic(op, op) or label:)")
    name, inner = line[:line.index("(")].strip(), line[line.index("(") + 1:-1]
    return ("instr", name, _split_operands(inner))


def _instr_len(name: str, operands) -> int:
    """Byte length of an instruction. A jump's immediate is always 2 bytes regardless of its (maybe still-unknown)
    target, so substitute a placeholder 0 for a symbolic-label operand and assemble it to MEASURE the length."""
    op = _resolve_op(name)
    probe = list(operands)
    if op in _JUMP_OPS and probe and not str(probe[0]).startswith("{") and not str(probe[0]).lstrip("-").isdigit():
        probe[0] = 0
    return len(assemble_instruction(name, probe))


def assemble_block(text: str) -> bytes:
    """Assemble a BLOCK of instructions (one per line, ``label:`` lines allowed) -> the branch-body bytes.

    Two passes: pass 1 lays out instruction offsets (sizes are known up front -- a jump immediate is always 2
    bytes) and records each ``label:``'s offset; pass 2 emits, resolving every symbolic jump target to the signed
    relative offset (``target - instr_end``) the engine reads. The output is the ``body`` for
    `eb.edit.add_function` / `replace_function_body`."""
    items = [p for p in (_parse_line(ln) for ln in text.splitlines()) if p is not None]
    if not any(it[0] == "instr" for it in items):
        raise CmdAsmError("empty block")

    # pass 1 -- offsets + label table
    label_offsets: dict[str, int] = {}
    pos = 0
    for it in items:
        if it[0] == "label":
            if it[1] in label_offsets:
                raise CmdAsmError(f"duplicate label {it[1]!r}")
            label_offsets[it[1]] = pos
        else:
            pos += _instr_len(it[1], it[2])

    # pass 2 -- emit with resolved jumps (instr_end = this instruction's end offset)
    out = bytearray()
    for it in items:
        if it[0] == "label":
            continue
        instr_end = len(out) + _instr_len(it[1], it[2])
        out += assemble_instruction(it[1], it[2], label_offsets=label_offsets, instr_end=instr_end)
    return bytes(out)
