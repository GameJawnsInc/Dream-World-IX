"""Phase-6c-iii: the enemy-AI LINTER -- validate a battle scene's AI bytecode OFFLINE (the "I can't see the game"
superpower applied to the AI stack). The capstone of Phase 6c: 6a reads the AI, 6b patches a constant, 6c-i/-ii
author expressions/branches, and this CHECKS the result before deploy.

The checks are all SOUND -- a shipping scene must lint CLEAN (validated by a sweep over real battle scenes), so
every check passes valid AI and only flags a genuine fault:

  * decode -- every entry/function decodes cleanly to its declared boundary (a truncated/corrupt eb).
  * jump bounds -- every relative jump (JMP/JMP_IFNOT/JMP_IF) lands ON an instruction inside its own function (a
    jump out of bounds / into the middle of an instruction = a desync/crash; this also catches a backward
    JMP_IFNOT, whose offset the engine reads UNSIGNED -> a huge out-of-bounds target).
  * reachable terminator -- a forward reachability walk (follow jumps + fall-through, conditional = both, bound by
    visited offsets so loops terminate); flag a function where a path falls through the END without hitting a
    terminator (RET 0x04 / TerminateEntry 0x1C). The engine has NO per-function length bound, so such a path runs
    the IP off into adjacent bytecode. (Trailing NOP padding after a RET/loop is correctly UNREACHABLE -> clean.)
  * attack index -- an IMMEDIATE Attack (0x38) operand must be < the scene's attack count (an out-of-range index
    reads past the scene's `atk[]` table). Skipped when the index is an expression (computed at runtime) or when
    the attack count is unknown.

Read-only + offline. Provenance: only opcode NAMES are used; the donor bytes are read live.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..eb import disasm
from ..eb.model import EbScript

# the flow-TERMINATOR opcodes -- a path reaching one ENDS (the engine's per-function dispatch stops via adFin(),
# the IP never advances into adjacent bytecode). RET (case 4) + DELETE/TerminateEntry (case 28) are the common
# pair; the high ops whose DoEventCode return code (3-8) also routes through adFin() terminate identically:
# Battle 0x2A / Field 0x2B / WorldMap 0xB6 / STOP 0x4F / TetraMaster 0xAE / GameOver 0xF5 (verified vs EBin.cs).
# (Shared with aiauthor's authoring guard so the two never drift.)
TERMINATOR_OPS = {0x04, 0x1C, 0x2A, 0x2B, 0x4F, 0xAE, 0xB6, 0xF5}
_TERMINATORS = TERMINATOR_OPS
_JUMP_OPS = {0x01, 0x02, 0x03}  # JMP / JMP_IFNOT / JMP_IF (op<0x10, a 2-byte relative offset operand)
_JUMP_TABLE_OPS = {0x06, 0x0B, 0x0D}   # SWITCHEX / SWITCH / SWITCH2 -- a multi-target dispatch (conservatively
#                                        treated as terminating a reachability path: it transfers control onward)
_ATTACK_OP = 0x38               # the Attack command -- operand 0 selects an attack from the scene's atk[] table


@dataclass
class AiIssue:
    severity: str               # "error" | "warning"
    where: str                  # e.g. "entry1/tag5 @1159"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.where}: {self.message}"


def _jump_target(ins) -> int | None:
    """The absolute target of a relative jump, or None if its offset is an expression (computed at runtime).

    Signedness MATCHES the engine: JMP (0x01, ``bra``) and JMP_IF (0x03, ``bne``->``bra``) read a SIGNED int16
    (``getShortIP``); JMP_IFNOT (0x02, ``beq``) reads its skip offset UNSIGNED (``getUShortIP``) -- so a backward
    JMP_IFNOT becomes a huge forward target the bounds check flags (the exact fault the linter exists to catch)."""
    if ins.arg_is_expr[0]:
        return None
    raw = ins.imm(0)
    if ins.op == 0x02:                                           # JMP_IFNOT (beq) -- engine reads this UNSIGNED
        return ins.end + raw
    return ins.end + (raw - 0x10000 if raw >= 0x8000 else raw)   # JMP / JMP_IF -- signed int16


def _lint_function(data: bytes, where: str, start: int, end: int, atk_count) -> list:
    issues: list = []
    instrs: dict = {}
    try:
        for ins in disasm.iter_code(data, start, end):
            instrs[ins.off] = ins
    except (IndexError, KeyError):
        return [AiIssue("error", where, "bytecode does not decode cleanly (truncated/corrupt)")]
    if not instrs:
        return [AiIssue("error", where, "empty function body")]
    last = instrs[max(instrs)]
    if last.end != end:                                     # decode under/overran the declared boundary
        return [AiIssue("error", where, f"bytecode does not decode to the function boundary "
                                        f"(last instr ends at {last.end}, boundary {end})")]

    # jump bounds + attack index (per instruction)
    for off, ins in instrs.items():
        if ins.op in _JUMP_OPS:
            tgt = _jump_target(ins)
            if tgt is not None and (tgt < start or tgt >= end or tgt not in instrs):
                issues.append(AiIssue("error", f"{where} @{off}",
                                      f"{disasm.op_name(ins.op)} target {tgt} is outside the function / not an "
                                      f"instruction boundary [{start}..{end})"))
        elif ins.op == _ATTACK_OP and atk_count is not None and ins.args and not ins.arg_is_expr[0]:
            idx = ins.imm(0)
            if idx is not None and idx >= atk_count:
                issues.append(AiIssue("error", f"{where} @{off}",
                                      f"Attack index {idx} >= the scene's attack count {atk_count}"))

    # reachable terminator -- a forward walk; flag a path that falls through the end without a terminator
    seen: set = set()
    stack = [start]
    ran_off = False
    while stack:
        o = stack.pop()
        if o >= end:                                        # a path fell through the function boundary
            ran_off = True
            continue
        if o in seen or o not in instrs:                    # already explored, or a bad target (already flagged)
            continue
        seen.add(o)
        op = instrs[o].op
        if op in _TERMINATORS or op in _JUMP_TABLE_OPS:     # path ends here (RET / dispatched onward)
            continue
        if op == 0x01:                                      # unconditional JMP -> its target only
            tgt = _jump_target(instrs[o])
            stack.append(tgt if tgt is not None else instrs[o].end)
        elif op in (0x02, 0x03):                            # conditional -> the target AND the fall-through
            tgt = _jump_target(instrs[o])
            if tgt is not None:
                stack.append(tgt)
            stack.append(instrs[o].end)
        else:
            stack.append(instrs[o].end)                     # fall through to the next instruction
    if ran_off:
        issues.append(AiIssue("error", where, "a control-flow path runs off the end of the function without a "
                                              "terminator (RET/TerminateEntry) -- the engine would execute "
                                              "adjacent bytecode at runtime"))
    return issues


def lint_ai(eb_bytes: bytes, *, atk_count: int | None = None) -> list:
    """Lint a battle scene's enemy-AI ``.eb`` -> a list of :class:`AiIssue` (empty == clean). ``atk_count`` (the
    scene's attack-table size, from ``scene_data.parse_counts``) enables the Attack-index range check. Read-only."""
    try:
        eb = EbScript.from_bytes(eb_bytes)
    except (ValueError, IndexError) as ex:
        return [AiIssue("error", "eb", f"malformed battle .eb: {type(ex).__name__}: {ex}")]
    issues: list = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            issues += _lint_function(eb.data, f"entry{e.index}/tag{f.tag}", f.abs_start, f.abs_end, atk_count)
    return issues
