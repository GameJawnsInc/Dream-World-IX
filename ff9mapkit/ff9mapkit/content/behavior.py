"""BEHAVIOR TREES compiled to pure `.eb` — rung 0 of `studies/behavior-trees/PLAN.md`.

Designer-authored trees (Selector / Sequence / Cond / Do + Once / Cooldown / Invert)
compile into the CENTRAL-TICKER architecture proven by the fort-condor benches
([[project-ff9-fort-condor-rts]]): one seated brain entry ticks every unit's tree per
frame; units only ever run smooth BLOCKED synchronous walks on GLOB-fed targets (the
sync-walk law); exclusive actions are dispatched as added body functions at REQ level 4
and abort COOPERATIVELY. Everything is stock-Memoria-safe `.eb` — zero DLL.

THE LAWS ARE COMPILER INVARIANTS here (the study's core value):
  1. player-ref eval law — object-referencing tokens (`obj(`, `B_PTR`, `B_DISTANCEA`)
     are REFUSED in user Cond text; perception happens through the alive-gated mirror
     service, and the player mirror sits behind a staged-latch (IsMovementEnabled has
     been 1 at least once this field).
  2. sync-walk law — movement is only expressible as the universal duty body (a blocked
     `InitWalk`+`Walk` on the unit's target GLOBs); the ticker never blocks.
  3. orbit law — the duty body carries snap turns (SetWalkTurnSpeed 255).
  4. poll cadence — the ticker loop is `Wait(tick)` with tick defaulting to 1; cooldowns
     are decorators (allocated timer bytes), never loop-bottom waits.
  5. Int24 — all proximity math is Chebyshev boxes on Int16 mirrors (no squares).

TWO ACTION CLASSES (the shape the referee converged on):
  * FEED actions (WalkTo / Hold / Chase / Patrol) — selecting one makes the TICKER write
    the unit's target GLOBs; the duty body's blocked walk re-reads them per frame (live
    retarget with the engine's own smooth walk). Feeds have no body and no latch.
  * DISPATCH actions (SwingAt / Die / custom) — a per-unit added function (tags 15+),
    started via `RunScriptAsync(4, unit, tag)`. The SELECTED/RUNNING protocol makes
    switching race-free on cooperative-abort-only hardware: the ticker writes
    ``selected``; every body loop iteration checks ``selected == my id`` and exits
    otherwise, managing ``running`` (set at entry, cleared at exit); the ticker
    dispatches only when ``selected`` names a dispatch action AND ``running == 0``.

Per-unit ``selected`` doubles as the LIVE TRACE: watch it in the ~ Flags panel (the
compile report prints every byte index and action id).

v1 semantics are REACTIVE: conditions read the world/blackboard each tick; action
Success/Failure does NOT propagate (a `Do` must be the last child of its Sequence — the
compiler enforces it). Result plumbing, `Parallel`, and per-unit brains are deferred
(see the study charter).
"""
from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass

from ..eb import exprasm, opcodes
from ..eb.labelasm import JMP, JMP_IF, JMP_IFNOT, asm, label

OP_SET_OBJECT_FLAGS = 0x93
OP_WALK = 0x23
STAGE_SYSVAR = 2                    # B_SYSVAR[2] = IsMovementEnabled (the staged-latch source)
DISPATCH_LEVEL = 4                  # field 574's walking-actor redirect level
FIRST_ACTION_TAG = 15               # stock's redirect-function tag family
PLAYER = "player"                   # the pseudo-unit (uid 250, mirror behind the staged latch)
PLAYER_UID = 250

_FORBIDDEN_COND = re.compile(r"obj\(|B_PTR|B_DISTANCEA")


class BehaviorError(ValueError):
    pass


# ------------------------------------------------------------------ blackboard
class Blackboard:
    """Named GLOB allocation over the safe band — compiled, never hand-assigned.

    Defaults start ABOVE the fort-condor bench's hand map (bytes 1102-1214, flags
    8800-8853) purely as collision insurance if a field ever hosts both systems; every
    allocation is cleared/preset by the emitted Main_Init prepend, so nothing leaks
    into saves. ``report()`` is the ~ Flags debugging map."""

    def __init__(self, *, byte_base: int = 1220, byte_end: int = 2040,
                 flag_base: int = 8860, flag_end: int = 9080):
        self._next_byte, self._byte_end = byte_base, byte_end
        self._next_flag, self._flag_end = flag_base, flag_end
        self._names: dict[str, tuple[str, int]] = {}

    def _take(self, name: str, kind: str, width: int) -> int:
        if name in self._names:
            k, idx = self._names[name]
            if k != kind:
                raise BehaviorError(f"blackboard name {name!r} reallocated as {kind} (was {k})")
            return idx
        if kind == "flag":
            if self._next_flag > self._flag_end:
                raise BehaviorError("blackboard flag band exhausted")
            idx = self._next_flag
            self._next_flag += 1
        else:
            if self._next_byte % width:
                self._next_byte += width - (self._next_byte % width)
            if self._next_byte + width - 1 > self._byte_end:
                raise BehaviorError("blackboard byte band exhausted")
            idx = self._next_byte
            self._next_byte += width
        self._names[name] = (kind, idx)
        return idx

    def flag(self, name: str) -> int:
        return self._take(name, "flag", 1)

    def byte(self, name: str) -> int:
        return self._take(name, "byte", 1)

    def int16(self, name: str) -> int:
        return self._take(name, "int16", 2)

    def report(self) -> str:
        rows = [f"  {kind:5s} {idx:5d}  {name}" for name, (kind, idx) in
                sorted(self._names.items(), key=lambda kv: kv[1][1])]
        return "blackboard (GLOB; watch in ~ Flags):\n" + "\n".join(rows)


# ------------------------------------------------------------------ tree nodes
class Node:
    pass


@dataclass
class Selector(Node):
    children: tuple

    def __init__(self, *children: Node):
        self.children = tuple(children)


@dataclass
class Sequence(Node):
    children: tuple

    def __init__(self, *children: Node):
        self.children = tuple(children)


@dataclass
class Cond(Node):
    """A condition leaf: pretty-expr text WITHOUT the trailing B_EXPR_END.

    User text may not reference objects (the player-ref eval law) — perception goes
    through the mirror helpers on :class:`FieldBehavior`. ``_trusted`` marks
    compiler-generated text (mirror math), which skips the scan."""
    text: str
    _trusted: bool = False

    def __post_init__(self):
        if not self._trusted and _FORBIDDEN_COND.search(self.text):
            raise BehaviorError(
                f"Cond text {self.text!r} references an object (obj()/B_PTR/B_DISTANCEA) — "
                f"the player-ref eval law forbids raw object reads in conditions; use the "
                f"mirror helpers (near/near_point/hp_*/active) instead")


@dataclass
class Do(Node):
    action: "Action"


@dataclass
class Invert(Node):
    child: Node

    def __post_init__(self):
        if not isinstance(self.child, Cond):
            raise BehaviorError("v1 Invert wraps a Cond only")


@dataclass
class Once(Node):
    name: str
    child: Node


@dataclass
class Cooldown(Node):
    frames: int
    child: Node

    def __post_init__(self):
        if not 1 <= int(self.frames) <= 255:
            raise BehaviorError("Cooldown frames must be 1..255 (a GLOB byte timer)")


# ------------------------------------------------------------------ actions
class Action:
    feed = False


@dataclass
class WalkTo(Action):
    point: tuple
    feed = True


@dataclass
class Hold(Action):
    point: tuple
    feed = True


@dataclass
class Chase(Action):
    target: str
    feed = True


@dataclass
class Patrol(Action):
    points: tuple
    arrive_r: int = 150
    feed = True

    def __post_init__(self):
        self.points = tuple(tuple(p) for p in self.points)
        if not 2 <= len(self.points) <= 8:
            raise BehaviorError("Patrol takes 2..8 waypoints (unrolled if-chain)")


@dataclass
class SwingAt(Action):
    """Melee ticks against another unit's HP byte (the proven fight-body shape,
    minus death policy — death is a TREE branch, e.g. Cond(hp==0) -> Do(Die()))."""
    target: str
    interval: int = 30
    damage: int = 1


@dataclass
class Die(Action):
    """Clear my active flag (mirrors stop — the dead-uid firewall), then TerminateEntry."""


# ------------------------------------------------------------------ unit spec
@dataclass
class UnitSpec:
    name: str
    entry: int                       # .eb entry index == engine uid (proven convention)
    spawn: tuple                     # (x, z) — the duty walk's preset target
    hp: int | None = None            # allocate + preset an HP byte when set
    walk_speed: int = 50
    tree: Node | None = None


# ------------------------------------------------------------------ the compiler
def _stmt(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def _set_flag(idx: int, v: int) -> bytes:
    return _stmt(f"Global.Bit[{idx}] const({v}) B_LET")


def _set_byte(idx: int, v: int) -> bytes:
    return _stmt(f"Global.Byte[{idx}] const({v}) B_LET")


def _box(ax: str, az: str, bx, bz, r: int) -> str:
    """Chebyshev |a-b|<r on both axes; b terms may be var text or int consts."""
    if isinstance(bx, str):
        return (f"{ax} {bx} const({r}) B_MINUS B_GT {ax} {bx} const({r}) B_PLUS B_LT "
                f"B_ANDAND {az} {bz} const({r}) B_MINUS B_GT B_ANDAND "
                f"{az} {bz} const({r}) B_PLUS B_LT B_ANDAND")
    return (f"{ax} const({bx - r}) B_GT {ax} const({bx + r}) B_LT B_ANDAND "
            f"{az} const({bz - r}) B_GT B_ANDAND {az} const({bz + r}) B_LT B_ANDAND")


@dataclass
class CompiledBehavior:
    ticker_body: bytes
    duty_bodies: dict                # unit name -> tag-1 body bytes
    action_funcs: dict               # unit name -> [(tag, bytes)]
    main_init: bytes
    report: str

    def stable_hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.ticker_body + self.main_init)
        for name in sorted(self.duty_bodies):
            h.update(self.duty_bodies[name])
        for name in sorted(self.action_funcs):
            for tag, body in self.action_funcs[name]:
                h.update(bytes([tag]) + body)
        return h.hexdigest()[:16]


class FieldBehavior:
    """The per-field behavior compilation unit: a roster of units + one tree each."""

    def __init__(self, units: list[UnitSpec], *, blackboard: Blackboard | None = None,
                 tick: int = 1):
        self.bb = blackboard or Blackboard()
        self.units = {u.name: u for u in units}
        if PLAYER in self.units:
            raise BehaviorError(f"{PLAYER!r} is the reserved pseudo-unit name")
        if len(self.units) != len(units):
            raise BehaviorError("duplicate unit names")
        self.tick = int(tick)
        self._cooldowns: list[tuple[str, int]] = []      # (timer name, frames)
        self._reset_bytes: list[int] = []                # extra bytes Main_Init zeroes
        self._reset_flags: list[int] = []                # extra flags Main_Init clears
        self._label_ctr = 0                              # unique labels for feed effects
        # per-unit allocations (the player pseudo-unit gets mirrors + the staged latch)
        self._staged = self.bb.flag("player.staged")
        self.bb.int16(f"{PLAYER}.mx")
        self.bb.int16(f"{PLAYER}.mz")
        for u in units:
            self.bb.flag(f"{u.name}.active")
            self.bb.byte(f"{u.name}.selected")
            self.bb.byte(f"{u.name}.running")
            self.bb.int16(f"{u.name}.mx")
            self.bb.int16(f"{u.name}.mz")
            self.bb.int16(f"{u.name}.tx")
            self.bb.int16(f"{u.name}.tz")
            if u.hp is not None:
                self.bb.byte(f"{u.name}.hp")

    # ---------------- perception / condition helpers (mirror-safe by construction)
    def _mx(self, unit: str) -> str:
        return f"Global.Int16[{self.bb.int16(f'{unit}.mx')}]"

    def _mz(self, unit: str) -> str:
        return f"Global.Int16[{self.bb.int16(f'{unit}.mz')}]"

    def _check_unit(self, unit: str):
        if unit != PLAYER and unit not in self.units:
            raise BehaviorError(f"unknown unit {unit!r}")

    def near(self, a: str, b: str, r: int) -> Cond:
        self._check_unit(a)
        self._check_unit(b)
        return Cond(_box(self._mx(a), self._mz(a), self._mx(b), self._mz(b), r),
                    _trusted=True)

    def near_point(self, unit: str, point: tuple, r: int) -> Cond:
        self._check_unit(unit)
        x, z = point
        return Cond(_box(self._mx(unit), self._mz(unit), int(x), int(z), r), _trusted=True)

    def active(self, unit: str) -> Cond:
        if unit == PLAYER:
            return Cond(f"Global.Bit[{self._staged}]", _trusted=True)
        self._check_unit(unit)
        return Cond(f"Global.Bit[{self.bb.flag(f'{unit}.active')}]", _trusted=True)

    def hp_gt(self, unit: str, n: int) -> Cond:
        return Cond(f"Global.Byte[{self.bb.byte(f'{unit}.hp')}] const({n}) B_GT",
                    _trusted=True)

    def hp_le(self, unit: str, n: int) -> Cond:
        return Cond(f"Global.Byte[{self.bb.byte(f'{unit}.hp')}] const({n}) B_LE",
                    _trusted=True)

    def flag(self, name: str) -> Cond:
        return Cond(f"Global.Bit[{self.bb.flag(name)}]", _trusted=True)

    def raw(self, text: str, *, unsafe_ok: bool = False) -> Cond:
        return Cond(text, _trusted=unsafe_ok)

    # ---------------- compilation
    def _collect_actions(self, unit: UnitSpec) -> list[Action]:
        out: list[Action] = []

        def walk(n: Node):
            if isinstance(n, (Selector, Sequence)):
                for c in n.children:
                    walk(c)
            elif isinstance(n, (Once, Cooldown)):
                walk(n.child)
            elif isinstance(n, Do):
                out.append(n.action)
        walk(unit.tree)
        return out

    def _fallback_feed(self, unit: UnitSpec) -> Action:
        """The tree's unconditional fallback must be a STATIC feed (WalkTo/Hold/Patrol)
        so Main_Init can preset the duty target — enforced, per the charter."""
        node = unit.tree
        while True:
            if isinstance(n := node, Selector):
                node = n.children[-1]
            elif isinstance(node, Sequence):
                # a fallback Sequence must be condition-free to be unconditional
                if any(isinstance(c, (Cond, Invert)) for c in node.children):
                    raise BehaviorError(
                        f"{unit.name}: the tree's last branch must be UNCONDITIONAL — "
                        f"a static feed fallback (WalkTo/Hold/Patrol)")
                node = node.children[-1]
            elif isinstance(node, Do):
                a = node.action
                if isinstance(a, (WalkTo, Hold)):
                    return a
                if isinstance(a, Patrol):
                    return a
                raise BehaviorError(
                    f"{unit.name}: the fallback action must be a static feed "
                    f"(WalkTo/Hold/Patrol), not {type(a).__name__}")
            else:
                raise BehaviorError(
                    f"{unit.name}: the tree needs an unconditional Do fallback "
                    f"(got {type(node).__name__})")

    def compile(self) -> CompiledBehavior:
        for u in self.units.values():
            if u.tree is None:
                raise BehaviorError(f"unit {u.name!r} has no tree")

        duty_bodies: dict[str, bytes] = {}
        action_funcs: dict[str, list] = {}
        ticker: list = [label("top"), _stmt(f"B_SYSVAR[{STAGE_SYSVAR}] "
                                            f"Global.Bit[{self._staged}] B_OROR"),
                        (JMP_IFNOT, "mirrors"),
                        _set_flag(self._staged, 1),
                        label("mirrors")]
        # the player mirror, behind the staged latch (the player-ref eval law)
        ticker += [
            _stmt(f"Global.Bit[{self._staged}]"),
            (JMP_IFNOT, "m_player_skip"),
            _stmt(f"Global.Int16[{self.bb.int16(f'{PLAYER}.mx')}] "
                  f"obj(uid={PLAYER_UID}).f[0] B_LET"),
            _stmt(f"Global.Int16[{self.bb.int16(f'{PLAYER}.mz')}] "
                  f"obj(uid={PLAYER_UID}).f[2] B_LET"),
            label("m_player_skip"),
        ]
        for u in self.units.values():                    # unit mirrors, active-gated
            ticker += [
                _stmt(f"Global.Bit[{self.bb.flag(f'{u.name}.active')}]"),
                (JMP_IFNOT, f"m_{u.name}_skip"),
                _stmt(f"Global.Int16[{self.bb.int16(f'{u.name}.mx')}] "
                      f"obj(uid={u.entry}).f[0] B_LET"),
                _stmt(f"Global.Int16[{self.bb.int16(f'{u.name}.mz')}] "
                      f"obj(uid={u.entry}).f[2] B_LET"),
                label(f"m_{u.name}_skip"),
            ]
        # cooldown timers tick down once per pass
        cooldown_blocks_at = len(ticker)                 # patched in after tree walks

        main_init = bytearray()
        main_init += _set_flag(self._staged, 0)
        report: list[str] = []

        for u in self.units.values():
            actions = self._collect_actions(u)
            if not actions:
                raise BehaviorError(f"{u.name}: tree selects no actions")
            ids: dict[int, int] = {}                     # id(action) -> action id
            for a in actions:
                ids.setdefault(id(a), len(ids) + 1)
            fallback = self._fallback_feed(u)
            sel = self.bb.byte(f"{u.name}.selected")
            run = self.bb.byte(f"{u.name}.running")
            act_flag = self.bb.flag(f"{u.name}.active")
            tx = self.bb.int16(f"{u.name}.tx")
            tz = self.bb.int16(f"{u.name}.tz")

            # ---- main_init: activate, reset protocol bytes, preset the duty target
            main_init += _set_flag(act_flag, 1)
            main_init += _set_byte(sel, 0) + _set_byte(run, 0)
            px, pz = (fallback.points[0] if isinstance(fallback, Patrol)
                      else fallback.point)
            main_init += _stmt(f"Global.Int16[{tx}] const({int(px)}) B_LET")
            main_init += _stmt(f"Global.Int16[{tz}] const({int(pz)}) B_LET")
            if u.hp is not None:
                main_init += _set_byte(self.bb.byte(f"{u.name}.hp"), int(u.hp))

            # ---- the duty body (universal blocked walk on the target GLOBs)
            duty_bodies[u.name] = asm([
                label("top"),
                opcodes.encode(OP_SET_OBJECT_FLAGS, 7)
                + opcodes.set_walk_speed(u.walk_speed)
                + opcodes.set_pathing(1)
                + opcodes.set_walk_turn_speed(255),
                _stmt(f"Global.Bit[{act_flag}]"),
                (JMP_IFNOT, "wait"),
                opcodes.init_walk()
                + opcodes.encode(OP_WALK,
                                 exprasm.assemble(f"Global.Int16[{tx}] B_EXPR_END"),
                                 exprasm.assemble(f"Global.Int16[{tz}] B_EXPR_END"),
                                 arg_flags=0b11),
                label("wait"),
                opcodes.wait(1),
                (JMP, "top"),
                opcodes.RETURN,
            ])

            # ---- dispatch-action bodies (tags 15+) + the per-unit tree in the ticker
            funcs: list = []
            dispatch_tag: dict[int, int] = {}
            for a in actions:
                aid = ids[id(a)]
                if a.feed:
                    continue
                tag = FIRST_ACTION_TAG + len(funcs)
                dispatch_tag[aid] = tag
                funcs.append((tag, self._dispatch_body(u, a, aid, sel, run)))
            action_funcs[u.name] = funcs

            ticker += [
                _stmt(f"Global.Bit[{act_flag}]"),
                (JMP_IFNOT, f"t_{u.name}_done"),
            ]
            ticker += self._compile_tree(u, u.tree, ids, fail=f"t_{u.name}_fellthrough")
            ticker += [
                label(f"t_{u.name}_fellthrough"),        # unreachable (fallback is
                label(f"t_{u.name}_selected"),           # unconditional) — lint safety
            ]
            for aid, tag in dispatch_tag.items():        # dispatch tail
                ticker += [
                    _stmt(f"Global.Byte[{sel}] const({aid}) B_EQ"),
                    (JMP_IFNOT, f"t_{u.name}_d{aid}"),
                    _stmt(f"Global.Byte[{run}] const(0) B_EQ"),
                    (JMP_IFNOT, f"t_{u.name}_d{aid}"),
                    opcodes.run_script_async(DISPATCH_LEVEL, u.entry, tag),
                    label(f"t_{u.name}_d{aid}"),
                ]
            ticker += [label(f"t_{u.name}_done")]

            acts = ", ".join(f"{ids[id(a)]}={type(a).__name__}" for a in actions)
            report.append(f"  {u.name}: entry {u.entry}, selected@{sel} running@{run} "
                          f"actions[{acts}]")

        # cooldown decrements (allocated during tree walks) — spliced after mirrors
        cd_blocks: list = []
        for name, _frames in self._cooldowns:
            t = self.bb.byte(name)
            cd_blocks += [
                _stmt(f"Global.Byte[{t}] const(0) B_GT"),
                (JMP_IFNOT, f"cd_{t}"),
                _stmt(f"Global.Byte[{t}] Global.Byte[{t}] const(1) B_MINUS B_LET"),
                label(f"cd_{t}"),
            ]
        ticker[cooldown_blocks_at:cooldown_blocks_at] = cd_blocks
        for name, _frames in self._cooldowns:
            main_init += _set_byte(self.bb.byte(name), 0)
        for idx in self._reset_bytes:
            main_init += _set_byte(idx, 0)
        for idx in self._reset_flags:
            main_init += _set_flag(idx, 0)

        ticker += [label("wait"), opcodes.wait(self.tick), (JMP, "top"), opcodes.RETURN]
        return CompiledBehavior(
            ticker_body=asm(ticker),
            duty_bodies=duty_bodies,
            action_funcs=action_funcs,
            main_init=bytes(main_init),
            report=self.bb.report() + "\nunits:\n" + "\n".join(report),
        )

    # ---------------- tree → ticker blocks
    def _compile_tree(self, u: UnitSpec, node: Node, ids: dict, fail: str,
                      _ctr=None, on_select: list | None = None) -> list:
        if _ctr is None:
            _ctr = [0]
        _ctr[0] += 1
        me = f"t_{u.name}_n{_ctr[0]}"
        out: list = []
        if isinstance(node, Selector):
            for i, c in enumerate(node.children):
                nxt = f"{me}_alt{i}" if i + 1 < len(node.children) else fail
                out += self._compile_tree(u, c, ids, nxt, _ctr, on_select)
                if i + 1 < len(node.children):
                    out.append(label(nxt))
            return out
        if isinstance(node, Sequence):
            for i, c in enumerate(node.children):
                if isinstance(c, Do) and i + 1 != len(node.children):
                    raise BehaviorError(
                        f"{u.name}: v1 is reactive — a Do must be the LAST child of its "
                        f"Sequence (no action-result plumbing yet)")
                out += self._compile_tree(u, c, ids, fail, _ctr, on_select)
            return out
        if isinstance(node, Cond):
            return [_stmt(node.text), (JMP_IFNOT, fail)]
        if isinstance(node, Invert):
            return [_stmt(node.child.text), (JMP_IF, fail)]
        if isinstance(node, Once):
            # STICKY semantics (rung-1 design fix): a reactive ticker re-selects every
            # tick, so a select-time latch would fire for ONE tick. Instead: selecting
            # the child ENGAGES; while engaged the gate is bypassed (the child's own
            # conditions keep deciding); the first child-FAIL while engaged disengages
            # and latches — "chase me while I'm near, never again once I escape".
            latch = self.bb.flag(f"{u.name}.once.{node.name}")
            eng = self.bb.flag(f"{u.name}.onceeng.{node.name}")
            self._reset_flags += [latch, eng]
            myfail = f"{me}_dfail"
            ff = f"{me}_dff"
            extra = (on_select or []) + [_set_flag(eng, 1)]
            return ([_stmt(f"Global.Bit[{latch}]"), (JMP_IF, myfail)]
                    + self._compile_tree(u, node.child, ids, myfail, _ctr, extra)
                    + [label(myfail),
                       _stmt(f"Global.Bit[{eng}]"), (JMP_IFNOT, ff),
                       _set_flag(eng, 0), _set_flag(latch, 1),
                       label(ff), (JMP, fail)])
        if isinstance(node, Cooldown):
            # sticky like Once: engage on select, and start the TIMER at DISENGAGE
            # (the child failing while engaged), so the cooldown measures time since
            # the behavior ENDED, not since it began.
            name = f"{u.name}.cd{_ctr[0]}"
            t = self.bb.byte(name)
            eng = self.bb.flag(f"{u.name}.cdeng{_ctr[0]}")
            self._cooldowns.append((name, node.frames))
            self._reset_flags.append(eng)
            myfail = f"{me}_dfail"
            ff = f"{me}_dff"
            extra = (on_select or []) + [_set_flag(eng, 1)]
            return ([_stmt(f"Global.Byte[{t}] const(0) B_EQ Global.Bit[{eng}] B_OROR"),
                     (JMP_IFNOT, fail)]
                    + self._compile_tree(u, node.child, ids, myfail, _ctr, extra)
                    + [label(myfail),
                       _stmt(f"Global.Bit[{eng}]"), (JMP_IFNOT, ff),
                       _set_flag(eng, 0), _set_byte(t, node.frames),
                       label(ff), (JMP, fail)])
        if isinstance(node, Do):
            aid = ids[id(node.action)]
            sel = self.bb.byte(f"{u.name}.selected")
            out = list(on_select or [])
            out.append(_set_byte(sel, aid))
            out += self._feed_effect(u, node.action)
            out.append((JMP, f"t_{u.name}_selected"))
            return out
        raise BehaviorError(f"unknown node {type(node).__name__}")

    def _feed_effect(self, u: UnitSpec, a: Action) -> list:
        tx = self.bb.int16(f"{u.name}.tx")
        tz = self.bb.int16(f"{u.name}.tz")
        if isinstance(a, (WalkTo, Hold)):
            x, z = a.point
            return [_stmt(f"Global.Int16[{tx}] const({int(x)}) B_LET"),
                    _stmt(f"Global.Int16[{tz}] const({int(z)}) B_LET")]
        if isinstance(a, Chase):
            self._check_unit(a.target)
            gate = (f"Global.Bit[{self._staged}]" if a.target == PLAYER
                    else f"Global.Bit[{self.bb.flag(f'{a.target}.active')}]")
            self._label_ctr += 1
            skip = f"t_{u.name}_ch{self._label_ctr}"
            return [_stmt(gate), (JMP_IFNOT, skip),
                    _stmt(f"Global.Int16[{tx}] {self._mx(a.target)} B_LET"),
                    _stmt(f"Global.Int16[{tz}] {self._mz(a.target)} B_LET"),
                    label(skip)]
        if isinstance(a, Patrol):
            wp = self.bb.byte(f"{u.name}.wp")
            if wp not in self._reset_bytes:
                self._reset_bytes.append(wp)
            self._label_ctr += 1
            p = f"t_{u.name}_p{self._label_ctr}"
            out: list = []
            n = len(a.points)
            for i, (px, pz) in enumerate(a.points):
                out += [_stmt(f"Global.Byte[{wp}] const({i}) B_EQ"), (JMP_IFNOT, f"{p}_w{i}")]
                out += [_stmt(_box(self._mx(u.name), self._mz(u.name),
                                   int(px), int(pz), a.arrive_r)),
                        (JMP_IFNOT, f"{p}_f{i}"),
                        _set_byte(wp, (i + 1) % n),
                        (JMP, f"{p}_end")]
                out += [label(f"{p}_f{i}"),
                        _stmt(f"Global.Int16[{tx}] const({int(px)}) B_LET"),
                        _stmt(f"Global.Int16[{tz}] const({int(pz)}) B_LET"),
                        (JMP, f"{p}_end"),
                        label(f"{p}_w{i}")]
            out += [_set_byte(wp, 0), label(f"{p}_end")]
            return out
        return []                                        # dispatch actions: no feed

    def install(self, eb_bytes: bytes, compiled: CompiledBehavior | None = None) -> bytes:
        """Install a compiled behavior into a BUILT field's `.eb` (the generalized
        `swarm_bench.patch_eb` shape): replace each unit's tag-1 with its duty body,
        `add_function` the dispatch tags, seat + activate the ticker (the coop
        inject_hold entry pattern), prepend the Main_Init reset, and gate on an eblint
        BASELINE DIFF (pre-existing issues pass; a NEW error fails the install)."""
        from .. import eblint
        from ..eb import edit as eb_edit
        from . import object as _object
        cb = compiled or self.compile()
        baseline = {str(p) for p in eblint.lint_eb(bytes(eb_bytes))}
        out = bytes(eb_bytes)
        for u in self.units.values():
            out = eb_edit.replace_function_body(out, u.entry, 1, cb.duty_bodies[u.name])
            for tag, body in cb.action_funcs[u.name]:
                out = eb_edit.add_function(out, u.entry, tag, body)
        ticker_entry = (bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + cb.ticker_body)
        out, slot = _object.seat_entry(out, ticker_entry)
        out = eb_edit.activate_block(out, opcodes.init_code(slot, 0))
        out = eb_edit.insert_in_function(out, 0, 0, 0, cb.main_init)
        fresh = [p for p in eblint.lint_eb(out)
                 if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
        if fresh:
            raise BehaviorError("install produced NEW lint errors:\n"
                                + "\n".join(map(str, fresh)))
        return out

    def _dispatch_body(self, u: UnitSpec, a: Action, aid: int, sel: int, run: int) -> bytes:
        head: list = [_set_byte(run, aid), label("loop"),
                      _stmt(f"Global.Byte[{sel}] const({aid}) B_EQ"),
                      (JMP_IFNOT, "out")]
        tail: list = [label("wait"), opcodes.wait(1), (JMP, "loop"),
                      label("out"), _set_byte(run, 0), opcodes.RETURN]
        if isinstance(a, Die):
            return asm([
                _set_flag(self.bb.flag(f"{u.name}.active"), 0),   # mirrors stop first
                opcodes.terminate_entry(255),
                opcodes.RETURN,
            ])
        if isinstance(a, SwingAt):
            self._check_unit(a.target)
            if a.target == PLAYER:
                raise BehaviorError("SwingAt(player) is not a v1 action")
            t_hp = self.bb.byte(f"{a.target}.hp")
            t_act = self.bb.flag(f"{a.target}.active")
            timer = self.bb.byte(f"{u.name}.swing{aid}")
            self._reset_bytes.append(timer)
            work: list = [
                _stmt(f"Global.Bit[{t_act}]"), (JMP_IFNOT, "out"),
                _stmt(f"Global.Byte[{t_hp}] const(0) B_GT"), (JMP_IFNOT, "out"),
                _stmt(f"Global.Byte[{timer}] Global.Byte[{timer}] const(1) B_PLUS B_LET"),
                _stmt(f"Global.Byte[{timer}] const({a.interval}) B_LT"),
                (JMP_IF, "wait"),
                _set_byte(timer, 0),
                opcodes.turn_toward_object(self.units[a.target].entry, 16),
                _stmt(f"Global.Byte[{t_hp}] Global.Byte[{t_hp}] const({a.damage}) "
                      f"B_MINUS B_LET"),
            ]
            return asm(head + work + tail)
        raise BehaviorError(f"no dispatch body for {type(a).__name__}")
