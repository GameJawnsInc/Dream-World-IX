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

Lock hygiene (warnings; studies/movement/SURVEY.md 10 Tier-2): the engine has NO dialog lock -- control is
a script convention -- so the only defense against a shipped softlock is static. Per function:
  * unpaired lock -- ``DisableMove`` with no ``EnableMove``, no field-leaving op (Field / WorldMap /
    ExitField / Battle / GameOver / TetraMaster -- stock's own never-closed warp idiom, B1), and no
    statically-resolvable ``RunScript`` callee that re-enables or leaves; only when a plain RETURN is
    reachable (an infinite poller like the conductor watchdog is exempt by construction). Subroutines
    (RunScript targets -- the caller owns the bracket) and Init funcs (an Init-time lock is the
    arrive-locked idiom) are exempt. Stock residue after the exemptions is the survey's own unresolved
    tail: cross-OBJECT choreography (another entry's script re-enables later), statically invisible.
  * guard under lock -- the canonical ``ifnot (IsMovementEnabled) return`` prologue reached while a
    ``DisableMove`` is active on the same path always early-returns (the shipped gate-inside-talk softlock,
    the Lantern Hall ferry); also flagged when a locked path dispatches into a callee that OPENS with it.
    ZERO stock sites trip either form (calibrated over all 818 real fields).
  * (a tread-freeze check was calibrated OUT -- see the note at the constants: 518 stock tag-2 bodies
    block under their own lock and work, so the naive signature is unsound.)
Cross-field: :func:`lint_warp_grants` -- a literal ``Field(N)`` into a sibling whose script never
``EnableMove``s at all ships a guaranteed arrival softlock (the engine grants nothing; the survey's 7).

Read-only + offline. ``clean`` == zero ERRORS (warnings are advisory).
"""
from __future__ import annotations

from dataclasses import dataclass

from .eb import disasm
from .eb.disasm import JUMP_OPS, SWITCH_OPS, TERMINATOR_OPS, decode_switch, jump_target
from .eb.model import EbScript

_RUNSCRIPT_OPS = frozenset({0x10, 0x12, 0x14})    # RunScript[Async|Sync](level, uid, tag)

# --- lock hygiene (movement survey Tier-2 item 6) ---
# CALIBRATION NOTE (2026-08-03, all-818-real-field sweep): a "blocking op under its own lock in a region
# tag-2 body" check was built and DROPPED here -- stock ships 518 such sites that all work (e.g. field 51
# entry11/tag2: macro-lock, Wait(4)/Wait(5)/Wait(25), Field(53), ALL inline in the tread body). The
# engine gate at ProcessEvents.cs:180-181 is on DISPATCH (new CollisionRequests need usercontrol), not on
# stepping an already-running body -- so the kit's in-game forced-ATE tread freeze has some OTHER
# discriminant (survey 11). The tread-delegation shape stays the kit's proven-good idiom; it just has no
# sound static defect signature.
_DISABLE_MOVE = 0x2D
_ENABLE_MOVE = 0x2E
_EXIT_FIELD = 0x9E                # zeroes usercontrol AND starts the walk-out -- the warp idiom's own lock
# Ops that LEAVE the field/scene: an open lock at one of these is stock's own idiom (B1's 3,044
# never-closed warp brackets -- the destination, or the battle's Main_Reinit, re-grants).
_LEAVE_OPS = frozenset({0x2B, 0xB6, 0x2A, 0xF5, 0xAE, _EXIT_FIELD})
# The canonical trigger guard `ifnot (IsMovementEnabled) { return }` -- region.MOVEMENT_GATE, byte-for-byte
# stock's universal prologue: push sysvar 2, JMP_IF over a RETURN, the RETURN. Matched verbatim so the
# conductor's grant-spin (which also reads sysvar 2, but to BREAK a wait loop) can never false-positive.
_GATE = bytes([0x05, 0x7A, 0x02, 0x7F, 0x03, 0x01, 0x00, 0x04])


@dataclass
class EbIssue:
    severity: str               # "error" | "warning"
    where: str                  # e.g. "entry7/tag3 @4210"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.where}: {self.message}"


def _callee_funcs(eb, entry_index, ins, player_entries):
    """The statically-resolvable target function(s) of a RunScript instr, or ``None`` when the target
    is party/computed/dangling -- the lock checks treat unresolvable as benign (never a false alarm)."""
    from . import eventscan
    uid, tag = ins.imm(1), ins.imm(2)
    if uid is None or tag is None:
        return None
    kind, targets = eventscan.resolve_uid(uid, entry_index, player_entries, eb.entry_count)
    if kind not in ("self", "main", "object", "player") or not targets:
        return None
    out = []
    for t in targets:
        if 0 <= t < eb.entry_count:
            te = eb.entry(t)
            if not te.empty:
                fn = te.func_by_tag(tag)
                if fn is not None:
                    out.append(fn)
    return out or None                                   # dangling -> _check_call already warns; no credit here


def _func_ops(eb, fn, opcache) -> frozenset:
    """The set of opcodes a function's body decodes to (cached by abs offset; empty on a decode fault)."""
    ops = opcache.get(fn.abs_start)
    if ops is None:
        try:
            ops = frozenset(i.op for i in disasm.iter_code(eb.data, fn.abs_start, fn.abs_end))
        except (IndexError, KeyError):
            ops = frozenset()
        opcache[fn.abs_start] = ops
    return ops


def _lint_locks(eb, e, f, instrs, *, player_entries, opcache, called=frozenset()) -> list:
    """The lock-hygiene warnings (module docstring): a path walk carrying a (locked, exited) state for the
    guard-under-lock class, then the function-level unpaired-lock check. The walk mirrors the structural
    reachability walk exactly (jumps + switch arms + fall-through), just with lock state. ``called`` =
    the field-wide set of statically-resolved RunScript targets ``(entry, tag)`` -- a function invoked as
    a subroutine is exempt from the unpaired check (its CALLER owns the bracket: stock's lock-in-callee /
    enable-in-caller split, the mirror of B3)."""
    data, start, end = eb.data, f.abs_start, f.abs_end
    where = f"entry{e.index}/tag{f.tag}"
    issues: list = []
    seen: set = set()
    stack = [(start, False, False)]                      # (offset, locked, exited-the-field)
    ret_reachable = False
    flagged: set = set()                                 # (kind, offset) -- one warning per site, not per state
    while stack:
        o, locked, exited = stack.pop()
        if o >= end or (o, locked, exited) in seen or o not in instrs:
            continue
        seen.add((o, locked, exited))
        ins = instrs[o]
        op = ins.op
        if locked and not exited:
            if op == 0x05 and ("gate", o) not in flagged and data[o:o + len(_GATE)] == _GATE:
                flagged.add(("gate", o))
                issues.append(EbIssue("warning", f"{where} @{o}",
                                      "IsMovementEnabled guard reached under an active DisableMove -- it "
                                      "always early-returns here (the gate-inside-talk softlock class); "
                                      "the guard belongs at the trigger head, before the lock"))
            if op in _RUNSCRIPT_OPS and ("cgate", o) not in flagged:
                for fn in (_callee_funcs(eb, e.index, ins, player_entries) or []):
                    if data[fn.abs_start:fn.abs_start + len(_GATE)] == _GATE:
                        flagged.add(("cgate", o))
                        issues.append(EbIssue("warning", f"{where} @{o}",
                                              "dispatches (while locked) into a function that OPENS with the "
                                              "IsMovementEnabled guard -- the callee always early-returns "
                                              "(the gate-inside-talk softlock class)"))
                        break
        if op == _DISABLE_MOVE:
            locked = True
        elif op == _ENABLE_MOVE:
            locked = False
        elif op == _EXIT_FIELD:
            exited = True
        if op == 0x04:                                   # a plain RETURN ends the path
            ret_reachable = True
            continue
        if op in TERMINATOR_OPS:
            continue
        if op in SWITCH_OPS:
            sw = decode_switch(ins)
            if sw is None:
                continue
            for ed in sw.edges:
                stack.append((ed.target, locked, exited))
            continue
        if op == 0x01:
            tgt = jump_target(ins)
            stack.append((tgt if tgt is not None else ins.end, locked, exited))
        elif op in (0x02, 0x03):
            tgt = jump_target(ins)
            if tgt is not None:
                stack.append((tgt, locked, exited))
            stack.append((ins.end, locked, exited))
        else:
            stack.append((ins.end, locked, exited))

    # unpaired lock, function-level (NOT path-level: the stock macro's conditional arms would make every
    # dialogue bracket a false positive on the infeasible lock-here-skip-enable-there path). The survey's
    # own taxonomy: of stock's 2,049 in-function-unpaired disables, 1,704 warp, 28 GameOver, 206 delegate
    # -- all excused below -- leaving only the genuinely unresolved tail, which is exactly this class.
    # Exempt: subroutines (``called``) -- the caller owns the bracket; and Init (tag 0) -- an Init-time
    # lock is the arrive-locked idiom (the grant belongs to a later scene by design, stock's 64 sites).
    if f.tag == 0 or (e.index, f.tag) in called:
        return issues
    opset = frozenset(i.op for i in instrs.values())
    if (_DISABLE_MOVE in opset and _ENABLE_MOVE not in opset
            and not (opset & _LEAVE_OPS) and ret_reachable):
        credited = unknown = False
        for ins in instrs.values():
            if ins.op not in _RUNSCRIPT_OPS:
                continue
            fns = _callee_funcs(eb, e.index, ins, player_entries)
            if fns is None:
                unknown = True                           # party/computed target -> lenient, no warning
                continue
            for fn in fns:
                cops = _func_ops(eb, fn, opcache)
                if _ENABLE_MOVE in cops or (cops & _LEAVE_OPS):
                    credited = True
        if not credited and not unknown:
            issues.append(EbIssue("warning", where,
                                  "DisableMove with no EnableMove, no field-leaving op, and no delegated "
                                  "re-enable -- every path out of this function leaves the player locked "
                                  "(softlock risk)"))
    return issues


def _called_targets(eb, player_entries) -> frozenset:
    """Every statically-resolved RunScript target ``(entry, tag)`` in the field -- the subroutine set the
    unpaired-lock check exempts (a callee's bracket balance is its caller's business)."""
    from . import eventscan
    out: set = set()
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            try:
                for ins in disasm.iter_code(eb.data, f.abs_start, f.abs_end):
                    if ins.op not in _RUNSCRIPT_OPS:
                        continue
                    uid, tag = ins.imm(1), ins.imm(2)
                    if uid is None or tag is None:
                        continue
                    kind, targets = eventscan.resolve_uid(uid, e.index, player_entries, eb.entry_count)
                    if kind not in ("self", "main", "object", "player") or not targets:
                        continue
                    for t in targets:
                        if 0 <= t < eb.entry_count:
                            out.add((t, tag))
            except (IndexError, KeyError):
                continue
    return frozenset(out)


def _lint_function(eb, e, f, *, player_entries, opcache=None, called=frozenset()) -> list:
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
    issues += _lint_locks(eb, e, f, instrs, player_entries=player_entries,
                          opcache=opcache if opcache is not None else {}, called=called)
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
    opcache: dict = {}
    called = _called_targets(eb, player_entries)
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            issues += _lint_function(eb, e, f, player_entries=player_entries, opcache=opcache,
                                     called=called)
    return issues


def errors(issues) -> list:
    return [i for i in issues if i.severity == "error"]


# --- cross-field lock hygiene ------------------------------------------------------------------


def enables_movement(eb_bytes) -> "bool | None":
    """Whether this ``.eb`` contains any ``EnableMove`` at all (``None`` if it doesn't parse). The engine
    grants nothing on entry -- the script's own EnableMove is the SOLE control grant -- so a field with
    none strands every arrival locked (legitimate only for a play-and-warp-away pure-cutscene field)."""
    try:
        eb = EbScript.from_bytes(bytes(eb_bytes))
    except (ValueError, IndexError, TypeError):
        return None
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            try:
                for ins in disasm.iter_code(eb.data, f.abs_start, f.abs_end):
                    if ins.op == _ENABLE_MOVE:
                        return True
            except (IndexError, KeyError):
                return None
    return False


def warp_targets(eb_bytes) -> set:
    """The LITERAL ``Field(N)`` destinations this ``.eb`` warps to (computed/expression targets are
    invisible offline and skipped -- so this is a floor, never a ceiling)."""
    out: set = set()
    try:
        eb = EbScript.from_bytes(bytes(eb_bytes))
    except (ValueError, IndexError, TypeError):
        return out
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            try:
                for ins in disasm.iter_code(eb.data, f.abs_start, f.abs_end):
                    if ins.op == 0x2B and ins.imm(0) is not None:
                        out.add(int(ins.imm(0)))
            except (IndexError, KeyError):
                continue
    return out


def lint_warp_grants(eb_by_id: dict) -> list:
    """Cross-field lock hygiene over a set of sibling fields (``field id -> .eb bytes`` -- a campaign /
    journey build): warn on every literal ``Field(N)`` whose destination IS in the set and whose script
    never ``EnableMove``s -- a guaranteed arrival softlock no single-field validator can see. Destinations
    outside the set (real fields, other mods) are out of scope."""
    issues: list = []
    grants = {fid: enables_movement(data) for fid, data in eb_by_id.items()}
    for fid, data in sorted(eb_by_id.items()):
        for tgt in sorted(warp_targets(data)):
            if tgt != fid and grants.get(tgt) is False:
                issues.append(EbIssue("warning", f"field {fid}",
                                      f"Field({tgt}) warps into a sibling field whose script never enables "
                                      f"movement -- arrivals stay locked forever (is its entry grant "
                                      f"missing, or every entrance locked with no unlock hook?)"))
    return issues
