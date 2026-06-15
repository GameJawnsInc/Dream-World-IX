"""Phase-3: the field event-script (``.eb``) structural LINTER -- the ``ailint`` analogue for FIELD scripts.

Validates a field's ``.eb`` control flow OFFLINE (the "I can't see the game" superpower applied to the field
stack), so an in-place edit (Phases 2/4) can be re-checked before deploy and a verbatim fork can be vetted up
front. The ERROR checks are SOUND -- every shipping field lints with ZERO errors (proven by a sweep over all
676 real fields; 29382 functions, 0 decode/jump/switch/reachability faults), so an error only ever flags a
genuine structural break.

Checks (per entry/function):
  * decode (error) -- the body decodes cleanly to its declared boundary (a truncated/desynced eb).
  * jump bounds (error) -- every relative jump (JMP/JMP_IFNOT/JMP_IF) lands ON an instruction boundary inside
    its own function (engine-correct signedness; reuses :func:`eb.disasm.jump_target`).
  * switch bounds (error) -- every switch (0x06/0x0B/0x0D) case + default target lands on an instruction
    boundary (:func:`eb.disasm.decode_switch`, Phase 1) -- the field stack's primary dispatch, which the battle
    linter treats as opaque. A switch whose operands are computed is a WARNING (its targets can't be checked).
  * reachable terminator (error) -- a forward walk (follow jumps + SWITCH ARMS + fall-through, bounded by
    visited offsets) flags a path that falls off the function end without a terminator (the engine would run
    the IP into adjacent bytecode at runtime).
  * call resolution (warning) -- a ``RunScript[Async|Sync](uid, tag)`` whose uid resolves statically (self /
    Main_Init / a sibling object entry) should call a tag that entry defines; a dangling call is the #5
    softlock class. WARNING not error: 25 shipping fields have a statically-dangling call (engine no-ops it or
    it's an unreachable beat), so it can't be a soundness error -- but it's exactly what an editor wants flagged.
    Player/party/computed targets are skipped (not resolvable offline).

Read-only + offline. ``clean`` == zero ERRORS (warnings are advisory).
"""
from __future__ import annotations

from dataclasses import dataclass

from .eb import disasm
from .eb.disasm import JUMP_OPS, SWITCH_OPS, TERMINATOR_OPS, decode_switch, jump_target
from .eb.model import EbScript

_RUNSCRIPT_OPS = frozenset({0x10, 0x12, 0x14})    # RunScript[Async|Sync](level, uid, tag)


@dataclass
class EbIssue:
    severity: str               # "error" | "warning"
    where: str                  # e.g. "entry7/tag3 @4210"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.where}: {self.message}"


def _lint_function(eb, e, f, *, player_entries) -> list:
    data, start, end, where = eb.data, f.abs_start, f.abs_end, f"entry{e.index}/tag{f.tag}"
    issues: list = []
    instrs: dict = {}
    try:
        for ins in disasm.iter_code(data, start, end):
            instrs[ins.off] = ins
    except (IndexError, KeyError):
        return [EbIssue("error", where, "bytecode does not decode cleanly (truncated/corrupt)")]
    if not instrs:
        return [EbIssue("error", where, "empty function body")]
    last = instrs[max(instrs)]
    if last.end != end:
        return [EbIssue("error", where, f"bytecode does not decode to the function boundary "
                                        f"(last instr ends at {last.end}, boundary {end})")]

    def _bad(t):                                              # a target that isn't an in-function instr boundary
        return t < start or t >= end or t not in instrs

    for off, ins in instrs.items():
        if ins.op in JUMP_OPS:
            tgt = jump_target(ins)
            if tgt is not None and _bad(tgt):
                issues.append(EbIssue("error", f"{where} @{off}",
                                      f"{disasm.op_name(ins.op)} target {tgt} is outside the function / not an "
                                      f"instruction boundary [{start}..{end})"))
        elif ins.op in SWITCH_OPS:
            sw = decode_switch(ins)
            if sw is None:
                issues.append(EbIssue("warning", f"{where} @{off}",
                                      "switch operands are computed -- its targets can't be validated"))
            else:
                for ed in sw.edges:
                    if _bad(ed.target):
                        arm = "default" if ed.is_default else f"case {ed.value}"
                        issues.append(EbIssue("error", f"{where} @{off}",
                                              f"switch {arm} target {ed.target} is outside the function / not an "
                                              f"instruction boundary [{start}..{end})"))
        elif ins.op in _RUNSCRIPT_OPS:
            issues += _check_call(eb, e.index, off, ins, where, player_entries)

    # reachability -- forward walk, follow jumps + switch arms + fall-through; flag a path off the end.
    seen: set = set()
    stack = [start]
    ran_off = False
    while stack:
        o = stack.pop()
        if o >= end:
            ran_off = True
            continue
        if o in seen or o not in instrs:                     # explored, or a bad target (already flagged)
            continue
        seen.add(o)
        ins = instrs[o]
        op = ins.op
        if op in TERMINATOR_OPS:
            continue
        if op in SWITCH_OPS:                                 # dispatches to its arms; never falls through
            sw = decode_switch(ins)
            if sw is None:                                   # computed switch -> can't follow; treat as a stop
                continue
            for ed in sw.edges:
                stack.append(ed.target)
            continue
        if op == 0x01:                                       # unconditional JMP -> its target only
            tgt = jump_target(ins)
            stack.append(tgt if tgt is not None else ins.end)
        elif op in (0x02, 0x03):                             # conditional -> target AND fall-through
            tgt = jump_target(ins)
            if tgt is not None:
                stack.append(tgt)
            stack.append(ins.end)
        else:
            stack.append(ins.end)
    if ran_off:
        issues.append(EbIssue("error", where, "a control-flow path runs off the end of the function without a "
                                              "terminator (RET/TerminateEntry) -- the engine would execute "
                                              "adjacent bytecode at runtime"))
    return issues


def _check_call(eb, entry_index, off, ins, where, player_entries) -> list:
    """A RunScript(uid, tag) whose uid resolves to a concrete entry (self/Main_Init/sibling object) must call a
    tag that entry defines -- else a dangling dispatch (warning; 25 shipping fields trip it, so not an error)."""
    from . import eventscan
    uid, tag = ins.imm(1), ins.imm(2)
    if uid is None or tag is None:
        return []
    kind, targets = eventscan.resolve_uid(uid, entry_index, player_entries, eb.entry_count)
    if kind == "player":                                     # any player entry defining the tag is fine
        if targets and not any(0 <= t < eb.entry_count and not eb.entry(t).empty
                               and eb.entry(t).func_by_tag(tag) is not None for t in targets):
            return [EbIssue("warning", f"{where} @{off}",
                            f"RunScript directs the player at tag {tag}, which no player entry defines")]
        return []
    if kind not in ("self", "main", "object") or not targets:
        return []                                            # party / computed / unknown -> not checkable
    t = targets[0]
    te = eb.entry(t) if 0 <= t < eb.entry_count else None
    if te is not None and not te.empty and te.func_by_tag(tag) is None:
        return [EbIssue("warning", f"{where} @{off}",
                        f"RunScript to entry {t} tag {tag}, which that entry doesn't define (dangling call)")]
    return []


def lint_eb(eb_bytes: bytes) -> list:
    """Lint a field's ``.eb`` -> a list of :class:`EbIssue` (no ERRORS == structurally clean; warnings are
    advisory). Read-only + offline."""
    if not eb_bytes:
        return [EbIssue("error", "eb", "empty or missing .eb data")]
    try:
        eb = EbScript.from_bytes(eb_bytes)
    except (ValueError, IndexError, TypeError) as ex:
        return [EbIssue("error", "eb", f"malformed field .eb: {type(ex).__name__}: {ex}")]
    from . import eventscan
    try:                                                      # the player-entry pre-pass DECODES every function;
        player_entries = eventscan.resolve_player_entries(eb)  # malformed bytecode here would crash before the
    except (IndexError, KeyError):                            # per-function decode guard can flag it -> degrade so
        player_entries = []                                  # _lint_function emits the clean "doesn't decode" error
    issues: list = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            issues += _lint_function(eb, e, f, player_entries=player_entries)
    return issues


def errors(issues) -> list:
    return [i for i in issues if i.severity == "error"]
