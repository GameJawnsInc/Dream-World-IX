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


# ---------------------------------------------------------------------------------------------------------------
# Phase-6c (productized): INSERT a branch into an existing function (the length-changing primitive made declarative)
# + the HP-PHASE convenience that generates the branch. `ai_function` REPLACES a whole function; these SPLICE a
# fragment into one -- the missing surface that the in-game-proven coin-flip / HP-phase branches needed by hand.
# ---------------------------------------------------------------------------------------------------------------

_VAR_RE = __import__("re").compile(r"^[A-Za-z]+\.[A-Za-z0-9]+\[\d+\]$")   # a Source.Type[i] variable token


def _func_pretty(eb_bytes: bytes, entry_index: int, tag: int):
    """(EbScript, Func, [(off, mnemonic, [operand_str]) ...]) for entry/tag -- the NAMED decode (battleai)."""
    from .battleai import _decode_func_pretty
    eb = _check_entry(eb_bytes, entry_index)
    f = eb.entries[entry_index].func_by_tag(tag)
    if f is None:
        raise AiAuthorError(f"entry {entry_index} has no function tag {tag} ({AI_PHASE_TAGS.get(tag, '?')})")
    instrs = list(_decode_func_pretty(eb.data, f.abs_start, min(f.abs_end, len(eb.data))))
    return eb, f, instrs


def _locate_insert(f, instrs, spec, n: int) -> int:
    """Resolve a spec's locator to an ABSOLUTE byte offset inside function ``f``. Locators: ``before``/``after`` =
    a command mnemonic (insert before / after the FIRST match), or ``at`` = a body offset (0 = prepend)."""
    have = [k for k in ("before", "after", "at") if k in spec]
    if len(have) != 1:
        raise AiAuthorError(f"#{n} needs exactly one locator: before = \"<mnemonic>\" | after = \"<mnemonic>\" | "
                            f"at = <body offset> (got {have or 'none'})")
    boundaries = {off for off, _, _ in instrs}           # the instruction-start offsets = the only valid insert points
    if "at" in spec:
        try:
            rel = int(spec["at"])
        except (TypeError, ValueError):
            raise AiAuthorError(f"#{n} at must be an integer body offset")
        if not 0 <= rel < f.length:                      # f.length (the end) is NOT insertable -- see the append note
            raise AiAuthorError(f"#{n} at = {rel} is outside the func body (0-{f.length - 1}); to add code at the "
                                f"end, splice before the terminator (before = \"RET\"), not after it")
        if f.abs_start + rel not in boundaries:          # mid-instruction insert would split an opcode -> corrupt
            valid = sorted(o - f.abs_start for o in boundaries)
            raise AiAuthorError(f"#{n} at = {rel} is not an instruction boundary (would split an instruction); "
                                f"valid body offsets are {valid}")
        return f.abs_start + rel
    key = "before" if "before" in spec else "after"
    mnem = spec[key]
    offs = [off for off, mn, _ in instrs if mn == mnem]   # offsets of each instruction with that mnemonic
    if not offs:
        present = sorted({mn for _, mn, _ in instrs})
        raise AiAuthorError(f"#{n} {key} = {mnem!r}: no such instruction in the function (has: {', '.join(present)})")
    if key == "before":
        return offs[0]
    seq = [off for off, _, _ in instrs] + [f.abs_end]    # after: the byte AFTER the first match = the next instr's off
    nxt = seq[seq.index(offs[0]) + 1]
    if nxt == f.abs_end:                                 # the match is the LAST instruction -> would append past the
        raise AiAuthorError(f"#{n} after = {mnem!r}: that is the function's LAST instruction; you cannot append "    # end
                            f"after the final instruction -- splice before the terminator instead (before = ...)")
    return nxt


def apply_ai_inserts(eb_bytes: bytes, specs) -> bytes:
    """Apply a list of ``[[scene.ai_insert]]`` specs IN ORDER. Each splices an assembled FRAGMENT into a function:
    ``entry`` + ``tag`` (which function), a locator (``before``/``after`` = a command mnemonic, or ``at`` = a body
    offset), and ``source`` (the `cmdasm` block -- a FRAGMENT, NOT required to end in RET; it flows into the rest of
    the function). Splice = :func:`eb.edit.insert_in_function` (fpos fixup; it refuses if one of the function's own
    jumps STRADDLES the insert point -- surfaced as a clean error). Length-changing -> run AFTER `ai_patch`."""
    if not isinstance(specs, list):
        raise AiAuthorError("[[scene.ai_insert]] must be a list of tables")
    eb = eb_bytes
    for n, spec in enumerate(specs, 1):
        if not isinstance(spec, dict):
            raise AiAuthorError(f"[[scene.ai_insert]] #{n} must be a table (got {type(spec).__name__})")
        try:
            entry, tag = int(spec["entry"]), int(spec["tag"])
        except (KeyError, TypeError, ValueError):
            raise AiAuthorError(f"[[scene.ai_insert]] #{n} needs integer entry + tag")
        source = spec.get("source")
        if not isinstance(source, str) or not source.strip():
            raise AiAuthorError(f"[[scene.ai_insert]] #{n} needs a non-empty source string")
        try:
            body = cmdasm.assemble_block(source.replace(";", "\n"))
        except cmdasm.CmdAsmError as ex:
            raise AiAuthorError(f"[[scene.ai_insert]] #{n} source did not assemble: {ex}")
        _eb, f, instrs = _func_pretty(eb, entry, tag)
        abs_off = _locate_insert(f, instrs, spec, n)
        try:
            eb = _edit.insert_in_function(eb, entry, tag, abs_off - f.abs_start, body)
        except ValueError as ex:                          # a straddling jump / bad offset from the splice primitive
            raise AiAuthorError(f"[[scene.ai_insert]] #{n}: {ex}")
    return eb


def _gen_hp_phase(stat: str, below: float, then_atk: int, else_atk: int, var: str, n: int,
                  atk_count: int | None = None) -> str:
    """Generate the `cmdasm` source for a stat-threshold branch: when SELF ``stat`` < ``below`` of max, set the
    attack-index var to ``then_atk``, else ``else_atk``. Uses the exact ``_E``/``B_PICK``/``B_COUNT`` extract idiom
    56 shipping bosses use for 'cur vs fraction-of-max' (the ``_E`` ops bind the read target via the SysList)."""
    pair = {"hp": ("cur.hp", "max.hp"), "mp": ("cur.mp", "max.mp"), "at": ("cur.at", "max.at")}.get(stat)
    if pair is None:
        raise AiAuthorError(f"[[scene.ai_phase]] #{n}: stat must be hp/mp/at (got {stat!r})")
    if not 0.0 < below < 1.0:
        raise AiAuthorError(f"[[scene.ai_phase]] #{n}: below must be a fraction 0<below<1 (e.g. 0.5 = half)")
    div = round(1.0 / below)                              # the proven idiom is cur < max/DIV (a unit fraction)
    if not 2 <= div <= 0xFFFF or abs(1.0 / div - below) > 1e-6:   # div is emitted as a 2-byte const(N) -> <= 0xFFFF
        raise AiAuthorError(f"[[scene.ai_phase]] #{n}: below = {below} must be a unit fraction 1/N with 2<=N<=65535 "
                            f"(0.5, 0.25, 0.2, …) to use the cur < max/N idiom")
    # then/else index the scene's GLOBAL enemy_attack[] table. The offline lint CANNOT range-check it (the value is
    # written into a variable, so the Attack operand is an expression, not an immediate) -- so guard it HERE when the
    # scene's attack count is known, else fall back to the byte ceiling.
    hi = (atk_count - 1) if atk_count else 0xFF
    for nm, v in (("then", then_atk), ("else", else_atk)):
        if not 0 <= v <= hi:
            scope = f" (scene has {atk_count} attacks)" if atk_count else ""
            raise AiAuthorError(f"[[scene.ai_phase]] #{n}: {nm} attack index {v} out of range (0-{hi}){scope}")
    cur, mx = pair
    return "\n".join([
        f"SET({{B_SYSLIST[1] B_MEMBER({cur}) B_SYSLIST[1] B_MEMBER({mx}) B_PICK const({div}) B_DIV B_LT_E B_COUNT B_EXPR_END}})",
        "JMP_IFNOT(L_phase_else)",
        f"SET({{{var} const({then_atk}) B_LET B_EXPR_END}})",
        "JMP(L_phase_done)",
        "L_phase_else:",
        f"SET({{{var} const({else_atk}) B_LET B_EXPR_END}})",
        "L_phase_done:",
    ])


def _infer_attack_var(instrs, n: int) -> str:
    """The variable an `Attack` command reads as its index, so the phase branch can override it. Requires exactly
    one `Attack` whose operand is a single ``{ Source.Type[i] B_EXPR_END }`` expression."""
    atks = [ops for _, mn, ops in instrs if mn == "Attack"]
    if len(atks) != 1:
        raise AiAuthorError(f"[[scene.ai_phase]] #{n}: the function must have exactly ONE Attack (found "
                            f"{len(atks)}) -- use [[scene.ai_insert]] with an explicit source instead")
    toks = atks[0][0].strip().strip("{}").split() if atks[0] else []
    if len(toks) != 2 or toks[1] != "B_EXPR_END" or not _VAR_RE.match(toks[0]):
        raise AiAuthorError(f"[[scene.ai_phase]] #{n}: the Attack must read a single variable (e.g. "
                            f"Attack({{Instance.Byte[18] B_EXPR_END}})); this one is Attack({atks[0][0] if atks[0] else ''}) "
                            f"-- use [[scene.ai_insert]] instead")
    return toks[0]


def apply_ai_phases(eb_bytes: bytes, specs, *, atk_count: int | None = None) -> bytes:
    """Apply ``[[scene.ai_phase]]`` specs: a high-level "enrage below X% HP" surface that GENERATES an HP-threshold
    branch and splices it before the function's `Attack`. Each spec: ``entry`` + ``tag``; ``stat`` (hp/mp/at,
    default hp); ``below`` (unit fraction, default 0.5); ``then`` / ``else`` (the attack index below / above the
    threshold). The attack-index variable is INFERRED from the function's `Attack`. Built on `apply_ai_inserts``.
    ``atk_count`` (when known) range-checks then/else against the scene's attack table -- the one fault the composed
    lint can't see, since the index flows through a runtime variable."""
    if not isinstance(specs, list):
        raise AiAuthorError("[[scene.ai_phase]] must be a list of tables")
    eb = eb_bytes
    for n, spec in enumerate(specs, 1):
        if not isinstance(spec, dict):
            raise AiAuthorError(f"[[scene.ai_phase]] #{n} must be a table (got {type(spec).__name__})")
        try:
            entry, tag = int(spec["entry"]), int(spec["tag"])
            then_atk, else_atk = int(spec["then"]), int(spec["else"])
            below = float(spec.get("below", 0.5))            # a non-numeric below -> a clean AiAuthorError, not a crash
        except (KeyError, TypeError, ValueError):
            raise AiAuthorError(f"[[scene.ai_phase]] #{n} needs integer entry, tag, then, else and a numeric below")
        stat = str(spec.get("stat", "hp"))
        _eb, _f, instrs = _func_pretty(eb, entry, tag)
        var = _infer_attack_var(instrs, n)
        source = _gen_hp_phase(stat, below, then_atk, else_atk, var, n, atk_count=atk_count)
        eb = apply_ai_inserts(eb, [{"entry": entry, "tag": tag, "source": source, "before": "Attack"}])
    return eb


def validate_ai_edits(eb_bytes: bytes, *, inserts=None, phases=None, atk_count: int | None = None) -> list:
    """Dry-run :func:`apply_ai_inserts` / :func:`apply_ai_phases` + LINT the composed result (for the build's offline
    validate). Returns error strings (empty == ok) -- never raises on a bad spec (returns it as an error string)."""
    from . import ailint as _ailint
    out = eb_bytes
    try:
        if phases:
            out = apply_ai_phases(out, phases, atk_count=atk_count)
        if inserts:
            out = apply_ai_inserts(out, inserts)
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
