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
from .ailint import TERMINATOR_OPS as _TERMINATOR_OPS    # the flow-terminators (RET/TerminateEntry/GameOver/...),

# the AI-phase function tags an enemy-type entry dispatches (0 = Init, the spawn binding, edited via Main_Init).
AI_PHASE_TAGS = {1: "Main", 6: "Counter", 7: "ATB", 9: "Dying"}

# (`_TERMINATOR_OPS` shared with the linter so the two never drift.) The engine has NO per-function length bound,
# so an authored body that doesn't END in one of these runs the IP off into adjacent bytecode at runtime.


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


def apply_ai_functions(eb_bytes: bytes, specs) -> bytes:
    """Apply a list of ``[[scene.ai_function]]`` specs (add / replace AI functions) to ``eb_bytes`` IN ORDER.

    Each spec is a table: ``entry`` (int, the enemy-type entry), ``tag`` (int, the AI-phase tag), ``source`` (str,
    the `cmdasm` command block), and optional ``replace`` (bool, default false -> add; true -> replace the body).
    Length-changing -- run this AFTER the same-length `[[scene.ai_patch]]` so the patch offsets are still valid."""
    if not isinstance(specs, list):
        raise AiAuthorError("[[scene.ai_function]] must be a list of tables")
    eb = eb_bytes
    for n, spec in enumerate(specs, 1):
        if not isinstance(spec, dict):
            raise AiAuthorError(f"[[scene.ai_function]] #{n} must be a table (got {type(spec).__name__})")
        try:
            entry, tag = int(spec["entry"]), int(spec["tag"])
        except (KeyError, TypeError, ValueError):
            raise AiAuthorError(f"[[scene.ai_function]] #{n} needs integer entry + tag (and a source string)")
        if not 0 <= tag <= 0xFFFF:                          # the func-table slot stores tag as a u16 (else struct
            raise AiAuthorError(f"[[scene.ai_function]] #{n} tag {tag} out of range (0-65535); the AI-phase tags "
                                f"are {sorted(AI_PHASE_TAGS)}")   # would raise a raw error deep in eb.edit)
        source = spec.get("source")
        if not isinstance(source, str) or not source.strip():
            raise AiAuthorError(f"[[scene.ai_function]] #{n} needs a non-empty source string")
        src = source.replace(";", "\n")                     # accept ';' as a line separator (one-line TOML source)
        eb = replace_ai_function(eb, entry, tag, src) if spec.get("replace") else add_ai_function(eb, entry, tag, src)
    return eb


def validate_ai_functions(eb_bytes: bytes, specs, *, atk_count: int | None = None) -> list:
    """Dry-run :func:`apply_ai_functions` + LINT the result; return error strings (empty == ok) for the offline
    build validate. Catches a bad entry/tag/source, a duplicate/missing tag, AND a structural fault in the
    authored AI (a non-terminating branch, an out-of-bounds jump, an out-of-range Attack index when ``atk_count``
    is given) via :mod:`ff9mapkit.battle.ailint`."""
    from . import ailint as _ailint
    try:
        out = apply_ai_functions(eb_bytes, specs)
    except AiAuthorError as ex:
        return [str(ex)]
    return [f"lint: {i}" for i in _ailint.lint_ai(out, atk_count=atk_count)]


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
