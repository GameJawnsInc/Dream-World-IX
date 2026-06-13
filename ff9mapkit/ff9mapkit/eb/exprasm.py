"""Phase-6c-i: the `.eb` EXPRESSION ASSEMBLER -- the exact inverse of :func:`disasm.pretty_expr`.

Authoring new enemy-AI logic (a phase-switch condition, a counter trigger) means writing the RPN expression
token stream the engine evaluates. This assembles that stream from the SAME readable form the disassembler
prints, so the round trip is the identity:

    assemble(disasm.pretty_expr(bytes)[0]) == bytes            (byte-exact, for canonical bytecode)
    disasm.pretty_expr(assemble(text))[0]  == text

Each whitespace-separated token in a ``{ ... }`` form maps to one encoded token (the inverse of every branch of
pretty_expr): a bare op mnemonic (``B_LT``, ``B_CURHP`` …) -> its op_binary byte; ``const(N)`` -> ``B_CONST``
(0x7D + 2 LE bytes); ``const4(N)`` -> ``B_CONST4`` (0x7E + 4 LE bytes); ``Source.Type[i]`` -> the ``0xC0`` var
token (source 0-3, type, + a 1- or 2-byte index, the engine's minimal encoding); ``B_SYSVAR[i]`` / ``B_SYSLIST[i]``
/ ``obj(uid=U).f[F]`` / ``B_MEMBER(i)`` / ``B_PTR(i)`` -> their operand tokens; ``B_EXPR_END`` (0x7F) terminates.

Provenance: only the open-source op_binary / VariableSource / VariableType NAMES are used (via
:mod:`ff9mapkit.eb._exprtable`); no SE bytes. This is the keystone for Phase-6c new-branch authoring (the command
assembler + length-changing ``add_function`` insertion + a battle linter build on top).
"""
from __future__ import annotations

import re

from ._exprtable import EXPR_OP_NAMES, VAR_SOURCE, VAR_TYPE

_OP_BY_NAME = {n: v for v, n in EXPR_OP_NAMES.items()}
_SRC_BY_NAME = {n: v for v, n in VAR_SOURCE.items()}
_TYPE_BY_NAME = {n: v for v, n in VAR_TYPE.items()}

_RE_CONST = re.compile(r"^const\((-?\d+)\)$")
_RE_CONST4 = re.compile(r"^const4\((-?\d+)\)$")
_RE_VAR = re.compile(r"^([A-Za-z]+)\.([A-Za-z0-9]+)\[(\d+)\]$")
_RE_SYS = re.compile(r"^(B_SYSVAR|B_SYSLIST)\[(\d+)\]$")
_RE_OBJ = re.compile(r"^obj\(uid=(\d+)\)\.f\[(\d+)\]$")
_RE_MEMPTR = re.compile(r"^(B_MEMBER|B_PTR)\(([\w.]+)\)$")   # operand may be a number OR a member name (B_MEMBER)
_RE_OPHEX = re.compile(r"^op([0-9A-Fa-f]{2})$")            # the disassembler's fallback for an UNNAMED operator byte

# the operand-bearing tokens -- they MUST be written in their operand form (pretty_expr always does), never bare:
# a bare "B_CONST" / "B_MEMBER" would emit the opcode alone and DROP the operand byte(s), desyncing the stream.
_OPERAND_OPS = {"B_CONST": "const(N)", "B_CONST4": "const4(N)", "B_SYSVAR": "B_SYSVAR[i]", "B_SYSLIST": "B_SYSLIST[i]",
                "B_OBJSPECA": "obj(uid=U).f[F]", "B_MEMBER": "B_MEMBER(i)", "B_PTR": "B_PTR(i)"}


class AssembleError(ValueError):
    pass


def _u16(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF))


def _u32(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))


def assemble_token(tok: str) -> bytes:
    """Encode ONE pretty_expr token -> its bytes. Raises AssembleError on an unknown token / out-of-range value."""
    m = _RE_CONST.match(tok)
    if m:
        v = int(m.group(1))                                 # B_CONST -- a 2-byte literal (engine reads getShortIP,
        if not -0x8000 <= v <= 0xFFFF:                      # a signed Int16; accept the signed-or-unsigned window)
            raise AssembleError(f"{tok}: const out of 16-bit range (-32768..65535)")
        return bytes((0x7D,)) + _u16(v & 0xFFFF)
    m = _RE_CONST4.match(tok)
    if m:
        v = int(m.group(1))                                 # B_CONST4 -- a 4-byte literal (the engine masks the read
        if not -0x80000000 <= v <= 0xFFFFFFFF:              # to 26 bits, but the 4 bytes are byte-faithful here)
            raise AssembleError(f"{tok}: const4 out of 32-bit range")
        return bytes((0x7E,)) + _u32(v & 0xFFFFFFFF)
    m = _RE_SYS.match(tok)                                  # B_SYSVAR[i] / B_SYSLIST[i] -- 1-byte index
    if m:
        idx = int(m.group(2))
        if not 0 <= idx <= 0xFF:
            raise AssembleError(f"{tok}: index out of range (0-255)")
        return bytes((0x7A if m.group(1) == "B_SYSVAR" else 0x79, idx))
    m = _RE_OBJ.match(tok)                                  # obj(uid=U).f[F] -- B_OBJSPECA, uid then field
    if m:
        uid, fld = int(m.group(1)), int(m.group(2))
        if not (0 <= uid <= 0xFF and 0 <= fld <= 0xFF):
            raise AssembleError(f"{tok}: uid/field out of range (0-255)")
        return bytes((0x78, uid, fld))
    m = _RE_MEMPTR.match(tok)                               # B_MEMBER(i) / B_PTR(i) -- 1-byte operand, a number OR
    if m:                                                   # (for B_MEMBER) a field NAME -> the GetCharacterData id
        op_name, raw = m.group(1), m.group(2)
        if raw.lstrip("-").isdigit():
            n = int(raw)
        elif op_name == "B_MEMBER":
            from ._membertable import member_selector
            n = member_selector(raw)
            if n is None:
                raise AssembleError(f"{tok}: unknown member name {raw!r} (e.g. cur.hp, max.hp, cur.mp -- see "
                                    f"_membertable.MEMBER_NAMES) -- or use the numeric selector")
        else:
            raise AssembleError(f"{tok}: B_PTR takes a numeric operand, not a name")
        if not 0 <= n <= 0xFF:
            raise AssembleError(f"{tok}: operand out of range (0-255)")
        return bytes((0x29 if op_name == "B_MEMBER" else 0x5F, n))
    m = _RE_VAR.match(tok)                                  # Source.Type[index] -- the 0xC0 variable token
    if m:
        src_name, typ_name, idx = m.group(1), m.group(2), int(m.group(3))
        src = _SRC_BY_NAME.get(src_name)
        typ = _TYPE_BY_NAME.get(typ_name)
        if src is None or typ is None:
            raise AssembleError(f"{tok}: unknown variable Source.Type (got {src_name}.{typ_name})")
        if not 0 <= src <= 3:
            raise AssembleError(f"{tok}: only Global/Map/Instance/Null are 0xC0 vars (Object/System/Member use "
                                f"their own tokens obj(...)/B_SYSLIST/B_MEMBER)")
        if not 0 <= idx <= 0xFFFF:
            raise AssembleError(f"{tok}: index out of range (0-65535)")
        token = 0xC0 | (typ << 2) | src
        if idx > 0xFF:                                      # long index -> the 0x20 bit + a 2-byte index
            return bytes((token | 0x20,)) + _u16(idx)
        return bytes((token, idx))                          # short index -> 1 byte (the engine's minimal encoding)
    if tok in _OPERAND_OPS:                                 # caught a bare operand-op -> would drop its operand
        raise AssembleError(f"{tok} takes an operand -- write it as {_OPERAND_OPS[tok]}, not bare")
    if tok in _OP_BY_NAME:                                  # a bare operator mnemonic (B_LT, B_CURHP, B_EXPR_END…)
        return bytes((_OP_BY_NAME[tok],))
    m = _RE_OPHEX.match(tok)                                # opXX -- the disasm fallback for an UNNAMED pure operator
    if m:
        val = int(m.group(1), 16)
        if val in EXPR_OP_NAMES:                            # a NAMED op (incl. the operand-bearing const/var/sys/
            raise AssembleError(f"{tok} is {EXPR_OP_NAMES[val]} -- write it by name, not as opXX")  # member/ptr ops)
        if val >= 0xC0:                                     # a 0xC0 variable token -- emitting it bare drops its
            raise AssembleError(f"{tok}: 0x{val:02X} is a variable token -- write it as Source.Type[i]")  # index
        return bytes((val,))                               # only a genuinely-unnamed pure operator byte gets through
    raise AssembleError(f"unknown expression token {tok!r}")


def assemble(text) -> bytes:
    """Assemble a pretty_expr expression -> its byte stream. ``text`` is the ``{ tok tok ... }`` form (braces
    optional) or a list of token strings. The stream MUST end with ``B_EXPR_END``. Round-trips with
    :func:`disasm.pretty_expr` byte-exactly for canonical bytecode."""
    if isinstance(text, str):
        tokens = text.strip().strip("{}").split()
    elif isinstance(text, (list, tuple)):
        tokens = [str(t) for t in text]
    else:
        raise AssembleError("assemble() takes a '{ ... }' string or a list of token strings")
    if not tokens:
        raise AssembleError("empty expression")
    if tokens[-1] != "B_EXPR_END":
        raise AssembleError("an expression must end with B_EXPR_END")
    out = bytearray()
    for tok in tokens:
        out += assemble_token(tok)
    b = bytes(out)
    # Self-verify the round trip at the library boundary: the assembled stream MUST re-parse to exactly itself --
    # consume every byte, no mid-stream B_EXPR_END, no token desync. This makes the round-trip guarantee an
    # INVARIANT of assemble() (a caller can never receive bytes that don't round-trip), so any future encoding
    # hole surfaces here as a clean AssembleError instead of a downstream crash / a silently-corrupt eb.
    from .disasm import pretty_expr as _pretty_expr
    try:
        _text, pos = _pretty_expr(b, 0)
    except (IndexError, KeyError, ValueError) as ex:        # a desynced stream runs the decoder off the end
        raise AssembleError(f"assembled stream does not re-parse ({b.hex(' ')}): {type(ex).__name__}: {ex}")
    if pos != len(b):                                       # a mid-stream B_EXPR_END leaves trailing bytes unread
        raise AssembleError(f"B_EXPR_END must be the LAST token -- {len(b) - pos} byte(s) follow the first one")
    return b
