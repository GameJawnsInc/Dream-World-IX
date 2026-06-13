"""Phase-6c-ii: enemy-AI branch AUTHORING -- the write-side companion to the 6a disassembler + 6b same-length
patcher. Where 6b retunes a CONSTANT in place (no byte moves), this ADDS or REPLACES a whole AI function (a new
phase branch, a counter, a rewritten body) -- the first LENGTH-CHANGING AI edit.

It is a thin bridge: assemble the readable AI source with the Phase-6c command assembler
(:func:`ff9mapkit.eb.cmdasm.assemble_block`), then splice the resulting body into the forked battle ``.eb`` with
the existing byte-safe length-changing primitives (:mod:`ff9mapkit.eb.edit`), which do the entry-table + intra-entry
``fpos`` fixup. Battle ``.eb`` is the same container/interpreter as a field script, and ``replace_function_body``
is already used on battle ebs (to re-author Main_Init for an edited spawn), so the machinery is proven; what 6c
adds is the way to WRITE the new bytecode by hand.

The AI-phase tags the engine dispatches (project-ff9-battle-tuning): 1 Main, 6 Counter, 7 ATB, 9 Dying (tag 0 =
the entry's Init). A fuller battle linter -- valid tags, an Attack index in range, a terminating RET -- is the next
step (Phase 6c-iii); these wrappers stay deliberately thin.
"""
from __future__ import annotations

from ..eb import cmdasm, disasm
from ..eb import edit as _edit
from ..eb.model import EbScript

# the AI-phase function tags an enemy-type entry dispatches (0 = Init, the spawn binding, edited via Main_Init).
AI_PHASE_TAGS = {1: "Main", 6: "Counter", 7: "ATB", 9: "Dying"}

# the flow-TERMINATOR opcodes that end the engine's per-function dispatch loop (EBin.jumpToCommand): RET (case 4)
# and DELETE/TerminateEntry (case 28). The engine has NO per-function length bound -- a body that doesn't end in
# one of these runs the instruction pointer off into the NEXT function / later entries = a runaway/garbage AI turn.
_TERMINATOR_OPS = {0x04, 0x1C}


class AiAuthorError(ValueError):
    pass


def _check_entry(eb_bytes: bytes, entry_index: int):
    """Re-parse + bounds-check the entry; returns the parsed EbScript. Raises a clean error on a bad index."""
    try:
        eb = EbScript.from_bytes(eb_bytes)
    except (ValueError, IndexError) as ex:
        raise AiAuthorError(f"malformed battle .eb: {type(ex).__name__}: {ex}")
    if not 0 <= entry_index < len(eb.entries) or eb.entries[entry_index].empty:
        raise AiAuthorError(f"entry {entry_index} is out of range / empty "
                            f"({sum(not e.empty for e in eb.entries)} non-empty entries)")
    return eb


def add_ai_function(eb_bytes: bytes, entry_index: int, tag: int, block_text: str) -> bytes:
    """Assemble ``block_text`` (cmdasm) and ADD it as a NEW function ``tag`` to enemy-AI entry ``entry_index``.

    Returns the new eb bytes (the entry's function table grows by one slot, every existing func's ``fpos`` and
    every later entry's table offset are fixed up by :func:`eb.edit.add_function`). Raises if ``tag`` already
    exists on that entry (use :func:`replace_ai_function` to rewrite an existing one)."""
    eb = _check_entry(eb_bytes, entry_index)
    if eb.entries[entry_index].func_by_tag(tag) is not None:
        raise AiAuthorError(f"entry {entry_index} already has a function with tag {tag} "
                            f"({AI_PHASE_TAGS.get(tag, '?')}) -- use replace_ai_function to rewrite it")
    body = _assemble(block_text)
    return _edit.add_function(eb_bytes, entry_index, tag, body)


def replace_ai_function(eb_bytes: bytes, entry_index: int, tag: int, block_text: str) -> bytes:
    """Assemble ``block_text`` and REPLACE function ``tag``'s body in entry ``entry_index`` (any length).

    The later functions' ``fpos`` + later entries' offsets shift by the size delta (handled by
    :func:`eb.edit.replace_function_body`). Raises if ``tag`` is absent."""
    eb = _check_entry(eb_bytes, entry_index)
    if eb.entries[entry_index].func_by_tag(tag) is None:
        raise AiAuthorError(f"entry {entry_index} has no function with tag {tag} -- use add_ai_function to add it")
    body = _assemble(block_text)
    return _edit.replace_function_body(eb_bytes, entry_index, tag, body)


def _assemble(block_text: str) -> bytes:
    try:
        body = cmdasm.assemble_block(block_text)
    except cmdasm.CmdAsmError as ex:
        raise AiAuthorError(f"AI source did not assemble: {ex}")
    # Require a flow terminator: the engine has no per-function length bound, so a body that doesn't end in RET
    # (0x04) / TerminateEntry (0x1C) runs the IP off the end into adjacent bytecode at runtime (a runaway AI turn).
    last = None
    for last in disasm.iter_code(body, 0, len(body)):
        pass
    if last is None or last.op not in _TERMINATOR_OPS:
        raise AiAuthorError("an AI branch must END in RET() (or TerminateEntry) -- otherwise the engine runs the "
                            "instruction pointer off the function into adjacent bytecode at runtime")
    return body
