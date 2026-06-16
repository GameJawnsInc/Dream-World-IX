"""The raw17 sequence ASSEMBLER -- the inverse of :mod:`seqdis` (the analog of ``eb/cmdasm`` for enemy AI). Turns
a textual sequence source into the instruction bytes the engine interprets, so a NET-NEW attack choreography can
be authored from scratch (then spliced by :mod:`seqauthor` with the length-changing :func:`seqcodec.serialize_repacked`
repack). A sequence has NO control flow (no jumps/labels) -- it is a flat list of ``Name(field=value, ...)``
instructions ending in a terminator -- so the assembler is a direct line-by-line transcription, with each operand
range-checked against its field width/signedness.

Round-trip INVARIANT (proven over the 562-corpus): ``assemble(to_source(instrs)) == instrs`` and
``to_source(parse_instr(b))`` re-assembles to the original bytes -- the assembler and the codec decoder are exact
mutual inverses. Only the open-source opcode NAMES are committed.
"""
from __future__ import annotations

import re as _re

from . import seqcodec as _sc


class SeqAsmError(ValueError):
    pass


_NAME_TO_OP = {nm: op for op, (nm, _f) in _sc._OPS.items()}
_LINE_RE = _re.compile(r"^\s*(?:\[\d+\]\s*)?([A-Za-z_]\w*)\s*(?:\(([^()]*)\))?\s*$")   # tolerates a [offset] prefix


def _parse_int(tok: str) -> int:
    tok = tok.strip()
    try:
        return int(tok, 0)                            # accepts 10, 0x0a, -5
    except ValueError:
        raise SeqAsmError(f"operand value {tok!r} is not an integer")


def _field_range(width: int, signed: bool):
    return (-(1 << (8 * width - 1)), (1 << (8 * width - 1)) - 1) if signed else (0, (1 << (8 * width)) - 1)


def assemble_instr_text(line: str) -> _sc.Instr:
    """One ``Name(field=value, ...)`` line -> an :class:`seqcodec.Instr` (offset 0). A leading ``[offset]`` and a
    trailing ``# comment`` are tolerated (so a disassembly line pastes back in). Every real operand must be given
    (the 0x19 ``Sfx`` ``_pad`` hole defaults to 0); each is range-checked against its field."""
    line = line.split("#", 1)[0].strip()
    m = _LINE_RE.match(line)
    if not m:
        raise SeqAsmError(f"cannot parse instruction {line!r} (expected `Name(field=value, ...)`)")
    name, argstr = m.group(1), (m.group(2) or "").strip()
    op = _NAME_TO_OP.get(name)
    if op is None:
        raise SeqAsmError(f"unknown opcode name {name!r} (see `battle-seq` / the seqcodec opcode table)")
    fields = _sc._OPS[op][1]
    provided: dict = {}
    if argstr:
        for part in argstr.split(","):
            if "=" not in part:
                raise SeqAsmError(f"{name}: operand {part.strip()!r} must be `field=value`")
            k, v = part.split("=", 1)
            provided[k.strip()] = _parse_int(v)
    fieldnames = {fn for fn, _o, _w, _s, _k in fields}
    unknown = set(provided) - fieldnames
    if unknown:
        raise SeqAsmError(f"{name}: unknown operand(s) {sorted(unknown)} (fields: {sorted(fieldnames) or 'none'})")
    operands = []
    for fn, _o, w, signed, _k in fields:
        if fn in provided:
            val = provided[fn]
        elif fn == "_pad":
            val = 0                                    # the discarded Sfx hole -- default 0 (engine ignores it)
        else:
            raise SeqAsmError(f"{name}: missing operand {fn!r}")
        lo, hi = _field_range(w, signed)
        if not lo <= val <= hi:
            raise SeqAsmError(f"{name}.{fn} = {val} is out of range [{lo}, {hi}] "
                              f"({w}-byte {'signed' if signed else 'unsigned'})")
        operands.append(val)
    return _sc.Instr(op, 0, operands)


def assemble(source: str) -> list:
    """A multi-line / ``;``-separated sequence source -> ``[Instr]``. Must end in a terminator (End/FastEnd) and
    contain NO terminator before the end (an unreachable tail is a likely authoring error). Blank lines + ``#``
    comments are ignored. The byte form is ``b"".join(seqcodec.emit_instr(i) for i in assemble(src))``."""
    raw_lines = [ln for chunk in source.replace(";", "\n").splitlines() for ln in [chunk.strip()] if ln]
    instrs = []
    for ln in raw_lines:
        if ln.split("#", 1)[0].strip():               # skip pure-comment / blank lines
            instrs.append(assemble_instr_text(ln))
    if not instrs:
        raise SeqAsmError("empty sequence source (need at least a terminator)")
    if instrs[-1].op not in _sc.TERMINATORS:
        raise SeqAsmError(f"a sequence must end in a terminator (End or FastEnd); got {instrs[-1].name}")
    for i, ins in enumerate(instrs[:-1]):
        if ins.op in _sc.TERMINATORS:
            raise SeqAsmError(f"terminator {ins.name} at instruction {i} is not last -- the tail is unreachable")
    out = assemble_bytes(instrs)                       # SELF-VERIFY: the bytes re-decode to exactly these instrs
    redec, _end = _sc._decode_body(out, 0, len(out))
    if [(i.op, tuple(i.operands)) for i in redec] != [(i.op, tuple(i.operands)) for i in instrs]:
        raise SeqAsmError("internal: assembled bytes did not re-decode to the source instructions")
    return instrs


def assemble_fragment(source: str) -> list:
    """A sequence FRAGMENT (for a mid-body splice via :func:`seqauthor.insert_sequence`) -> ``[Instr]``. Like
    :func:`assemble` but with NO terminator: a fragment is inserted INTO a body, so it must NOT contain End/FastEnd
    (which would truncate the body early)."""
    raw_lines = [ln for chunk in source.replace(";", "\n").splitlines() for ln in [chunk.strip()] if ln]
    instrs = [assemble_instr_text(ln) for ln in raw_lines if ln.split("#", 1)[0].strip()]
    if not instrs:
        raise SeqAsmError("empty fragment source")
    for ins in instrs:
        if ins.op in _sc.TERMINATORS:
            raise SeqAsmError(f"a fragment must not contain a terminator ({ins.name}) -- it is spliced mid-body")
    return instrs


def assemble_bytes(instrs) -> bytes:
    return b"".join(_sc.emit_instr(i) for i in instrs)


def to_source(instrs, *, multiline: bool = True) -> str:
    """The canonical (round-trippable) source for an instruction list -- includes EVERY operand (incl. the Sfx
    ``_pad``), so ``assemble(to_source(x)) == x`` byte-for-byte. (The human ``seqdis`` view hides ``_pad`` + adds
    notes; this is the machine form.)"""
    lines = []
    for ins in instrs:
        args = ", ".join(f"{fn}={val}" for (fn, _o, _w, _s, _k), val in zip(ins.fields, ins.operands))
        lines.append(f"{ins.name}({args})" if args else ins.name)
    return "\n".join(lines) if multiline else "; ".join(lines)
