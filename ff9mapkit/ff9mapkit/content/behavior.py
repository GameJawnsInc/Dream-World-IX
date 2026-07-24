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
  * FEED actions (WalkTo / Hold / Chase / Patrol / Flee / Wander) — selecting one makes
    the TICKER write the unit's target GLOBs; the duty body's blocked walk re-reads them
    per frame (live retarget with the engine's own smooth walk). Feeds have no body and
    no latch. Wander's randomness is B_SYSVAR[0] (= Comn.random8(), the engine's
    expression-side RNG — EventEngine.GetSysvar case 0).
  * DISPATCH actions (SwingAt / Die / custom) — a per-unit added function (tags 15+),
    started via `RunScriptAsync(4, unit, tag)`. The SELECTED/RUNNING protocol makes
    switching race-free on cooperative-abort-only hardware: the ticker writes
    ``selected``; every body loop iteration checks ``selected == my id`` and exits
    otherwise, managing ``running`` (set at entry, cleared at exit); the ticker
    dispatches only when ``selected`` names a dispatch action AND ``running == 0``.

Per-unit ``selected`` doubles as the LIVE TRACE: watch it in the ~ Flags panel (the
compile report prints every byte index and action id).

PER-ACTION SPEED (rung 3): every feed action takes ``speed=``; the duty head applies the
unit's speed GLOB (MSPEED's arg is an expression), and because the engine re-reads
``actor.speed`` on EVERY frame of a blocked walk (EventEngine.MoveToward.cs), a tiny
level-4 "speed nudge" body — dispatched by the ticker on the same SELECTED/RUNNING
protocol as action bodies — makes a change land MID-walk (a fleeing unit speeds up the
tick it starts fleeing, not when its current walk arrives).

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
        self.flag_band = (flag_base, flag_end)   # for EXPLICIT-index collision checks
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
    """An action leaf. ``raise_flags``/``clear_flags`` name blackboard flags written
    every tick this action is selected (idempotent) — the alarm mechanism: the watcher
    who Announces the raid also raises "alarm", and every other tree gates on it.
    Raised/cleared flags join the Main_Init reset (~ Reload clears them)."""
    action: "Action"
    raise_flags: tuple = ()
    clear_flags: tuple = ()

    def __post_init__(self):
        self.raise_flags = ((self.raise_flags,) if isinstance(self.raise_flags, str)
                            else tuple(self.raise_flags))
        self.clear_flags = ((self.clear_flags,) if isinstance(self.clear_flags, str)
                            else tuple(self.clear_flags))


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
    speed: int | None = None
    feed = True


@dataclass
class Hold(Action):
    point: tuple
    speed: int | None = None
    feed = True


@dataclass
class Chase(Action):
    """Pursue a unit's live mirror — stopping at ``standoff`` (playtest-1 lesson:
    walk-through pursuers otherwise phase onto the target's exact position)."""
    target: str
    standoff: int = 140
    speed: int | None = None
    feed = True


@dataclass
class Patrol(Action):
    points: tuple
    arrive_r: int = 150
    speed: int | None = None
    feed = True

    def __post_init__(self):
        self.points = tuple(tuple(p) for p in self.points)
        if not 2 <= len(self.points) <= 8:
            raise BehaviorError("Patrol takes 2..8 waypoints (unrolled if-chain)")


@dataclass
class March(Action):
    """Walk the waypoints in order and HOLD the last one — Patrol that stops.
    Multi-leg one-way routes as ONE feed (probe-driven layouts route around
    concave obstacles; a straight WalkTo would wedge in a notch). Interruptions
    (a duel preempting) resume at the current waypoint."""
    points: tuple
    arrive_r: int = 150
    speed: int | None = None
    feed = True

    def __post_init__(self):
        self.points = tuple(tuple(p) for p in self.points)
        if not 2 <= len(self.points) <= 8:
            raise BehaviorError("March takes 2..8 waypoints (unrolled if-chain)")


@dataclass
class Flee(Action):
    """Retreat to the FIRST of ``points`` (priority order) the threat is NOT within
    ``avoid_r`` of; if the threat camps them all, the last. This is the deliberate
    flee design: refuges are author-picked WALKABLE points (targets always on-mesh,
    no RPN vector math, no clamp problem) and the priority chain reads as gameplay —
    "fall back to the keep; if it's overrun, the gate"."""
    threat: str
    points: tuple
    avoid_r: int = 600
    speed: int | None = None
    feed = True

    def __post_init__(self):
        self.points = tuple(tuple(p) for p in self.points)
        if not 2 <= len(self.points) <= 4:
            raise BehaviorError("Flee takes 2..4 refuge points (priority order)")
        if not 1 <= int(self.avoid_r) <= 4000:
            raise BehaviorError("Flee avoid_r must be 1..4000")


@dataclass
class Wander(Action):
    """Random idle drift: every ``hold`` ticks pick a fresh target in the box
    (center ± radius) — offset = (B_SYSVAR[0] − 128) × radius / 128, two independent
    draws for x and z (each evaluation is a fresh Comn.random8()). A roll that lands
    off-mesh self-heals: the walk shoves the mesh edge at worst until the next roll."""
    center: tuple
    radius: int = 400
    hold: int = 90
    speed: int | None = None
    feed = True

    def __post_init__(self):
        self.center = tuple(self.center)
        if not 1 <= int(self.radius) <= 4000:      # Int24-safe: 128 * 4000 << 2^23
            raise BehaviorError("Wander radius must be 1..4000")
        if not 1 <= int(self.hold) <= 255:
            raise BehaviorError("Wander hold must be 1..255 (a GLOB byte timer)")


@dataclass
class HoldPost(Action):
    """Hold at MY placement post — the per-unit ``px``/``pz`` GLOBs. For a pooled unit
    the post is written at ACTIVATION (the player's press-time position = where it was
    placed); for a boot-spawned unit the post presets to its own spawn (equivalent to
    ``Hold(spawn)``). The placement-defender idiom: fallback ``hold_post`` + chase/swing
    branches gated on proximity = a unit that guards wherever you drop it."""
    speed: int | None = None
    feed = True


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


@dataclass
class Battle(Action):
    """Fire a REAL battle — ``Battle(0, scene)``, the donor-grounded shape (field
    559's tread battles: a usercontrol gate, then the bare op; the ENGINE owns the
    swirl/fade). ONE-SHOT PER FIELD LOAD by construction: a compiled latch flag gates
    the dispatch and the body sets it first, so a reactive tree re-selecting the
    branch after the battle returns can never re-fire it (~ Reload re-arms). The
    build ensures the entry-0 tag-10 Main_Reinit (the after-battle resume law —
    without it `EnterBattleEnd` suspends every object forever) whenever a behavior
    compiles a Battle. Use a STOCK scene id to avoid new BattlePatch lines."""
    scene: int

    def __post_init__(self):
        if not 0 <= int(self.scene) <= 0xFFFF:
            raise BehaviorError("Battle scene must be 0..65535")


@dataclass
class Announce(Action):
    """Open a dialogue window ONCE per engagement (a breach popup, a war cry). The body
    shows the window then idles while selected — re-dispatch (and window spam) can't
    happen until the tree deselects and later re-selects the branch; wrap in Once for
    a once-ever announcement."""
    txid: int
    window: int = 0


DEFAULT_HIRE_BUTTONS = 0x80001           # Special|Select — the rung-3 binding hedge
                                         # ("Special never fires on this user's binding")


@dataclass
class PoolSpec:
    """Economy/UX config for one POOL (its ``name`` matches pooled units' ``pool``).

    ``price``: the activation block gains a gil gate (``B_SYSVAR[6] >= price``, the
    inn-553 idiom) at its head and a ``RemoveGil`` at the SPAWN site — a request with
    insufficient gil (or an empty pool) is consumed WITHOUT charging.
    ``button``: emit a BUY-ANYWHERE POLLER entry (the rung-3 in-game-proven shape:
    Wait(1) poll on ``const4(mask) B_KEYON`` AND usercontrol, the Hunt's announce blip,
    then ``RunScriptSync(4, <parked choice>, 3)``; the Wait(12) debounce comes ONLY
    after a menu round — the eaten-button lesson). A PSX button mask int, or pass
    ``DEFAULT_HIRE_BUTTONS``.
    ``request_flag``: an EXPLICIT GLOB bit index for this pool's spawn request instead
    of a blackboard allocation — REQUIRED with ``button`` (the parked hire [[choice]]'s
    row must ``set_flag`` a concrete index) and it must sit OUTSIDE the blackboard
    flag band."""
    name: str
    price: int | None = None
    button: int | None = None
    request_flag: int | None = None


# ------------------------------------------------------------------ unit spec
@dataclass
class UnitSpec:
    name: str
    entry: int                       # .eb entry index == engine uid (proven convention)
    spawn: tuple                     # (x, z) — the duty walk's preset target
    hp: int | None = None            # allocate + preset an HP byte when set
    walk_speed: int = 50
    tree: Node | None = None
    pooled: bool = False             # not boot-spawned; activated by a pool request
    pool: str = "pool"               # request-lane name (pooled units only)


# ------------------------------------------------------------------ the compiler
def _stmt(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def _set_flag(idx: int, v: int) -> bytes:
    return _stmt(f"Global.Bit[{idx}] const({v}) B_LET")


def _set_byte(idx: int, v: int) -> bytes:
    return _stmt(f"Global.Byte[{idx}] const({v}) B_LET")


def _set_int16(idx: int, v: int) -> bytes:
    return _stmt(f"Global.Int16[{idx}] const({v}) B_LET")


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
                 tick: int = 1, warmup: int = 45, pools: list[PoolSpec] | tuple = (),
                 timer: int | None = None):
        """``warmup``: frames after the player is staged before ANY unit activates —
        the field loads dead-still (no walking, no pathing) while the engine settles
        the camera (rung-1 playtest: five actors pathing during entry-settle dragged
        the framerate and stretched the settle to ~5-6s)."""
        self.bb = blackboard or Blackboard()
        self.warmup = max(1, int(warmup))
        if timer is not None and not 1 <= int(timer) <= 30000:
            raise BehaviorError("timer must be 1..30000 seconds (the countdown HUD)")
        self.timer = int(timer) if timer is not None else None
        self.units = {u.name: u for u in units}
        if PLAYER in self.units:
            raise BehaviorError(f"{PLAYER!r} is the reserved pseudo-unit name")
        if len(self.units) != len(units):
            raise BehaviorError("duplicate unit names")
        self.tick = int(tick)
        self._cooldowns: list[tuple[str, int]] = []      # (timer name, frames)
        self._reset_bytes: list[int] = []                # extra bytes Main_Init zeroes
        self._reset_flags: list[int] = []                # extra flags Main_Init clears
        self._preset16: dict[int, int] = {}              # int16 idx -> Main_Init preset
        self._alternators: list[tuple[str, int, int, int]] = []  # (name, flag, timer, frames)
        self._label_ctr = 0                              # unique labels for feed effects
        # per-unit allocations (the player pseudo-unit gets mirrors + the staged latch)
        self._staged = self.bb.flag("player.staged")
        # THE EXISTENCE SOURCE: set by the player's OWN Init right after
        # DefinePlayerCharacter (install() inserts it) — B_SYSVAR[2] (usercontrol)
        # alone does NOT prove uid 250 is bound (the New-Game auto-warp entry has
        # usercontrol set before the player binds → obj(250) NullRef → CalcStack
        # desync, the bench-30413 log). The latch requires BOTH.
        self._pbound = self.bb.flag("player.bound")
        self.bb.int16(f"{PLAYER}.mx")
        self.bb.int16(f"{PLAYER}.mz")
        self._pools: dict[str, list[str]] = {}           # pool name -> pooled units, roster order
        for u in units:
            if not 1 <= int(u.walk_speed) <= 255:
                raise BehaviorError(f"{u.name}: walk_speed must be 1..255")
            self.bb.flag(f"{u.name}.active")
            self.bb.byte(f"{u.name}.selected")
            self.bb.byte(f"{u.name}.running")
            self.bb.byte(f"{u.name}.spd")                # desired walk speed (per-action)
            self.bb.byte(f"{u.name}.spdap")              # applied speed (the nudge shadow)
            self.bb.int16(f"{u.name}.mx")
            self.bb.int16(f"{u.name}.mz")
            self.bb.int16(f"{u.name}.tx")
            self.bb.int16(f"{u.name}.tz")
            if u.hp is not None:
                self.bb.byte(f"{u.name}.hp")
            if u.pooled:                                 # the runtime-activation lane
                if not re.fullmatch(r"[A-Za-z0-9_]+", u.pool or ""):
                    raise BehaviorError(f"{u.name}: pool name {u.pool!r} must be "
                                        f"[A-Za-z0-9_]+ (it becomes jump labels)")
                self.bb.flag(f"{u.name}.spawned")        # consumed-once latch (v1: no respawn)
                self.bb.int16(f"{u.name}.px")            # the placement post (press-time pos)
                self.bb.int16(f"{u.name}.pz")
                self._pools.setdefault(u.pool, []).append(u.name)
        # pool ECONOMY/UX specs (price / buy-anywhere button / explicit request flag)
        self.pool_specs: dict[str, PoolSpec] = {}
        for ps in pools:
            if ps.name not in self._pools:
                raise BehaviorError(f"[behavior] pool spec {ps.name!r}: no pooled unit "
                                    f"declares pool = {ps.name!r}")
            if ps.name in self.pool_specs:
                raise BehaviorError(f"[behavior] pool spec {ps.name!r} given twice")
            if ps.price is not None and not 0 <= int(ps.price) <= 0xFFFFFF:
                raise BehaviorError(f"pool {ps.name!r}: price must be 0..16777215 (24-bit gil)")
            if ps.button is not None and ps.request_flag is None:
                raise BehaviorError(f"pool {ps.name!r}: button needs an explicit "
                                    f"request_flag = N (the parked hire [[choice]] row "
                                    f"must set_flag a concrete index)")
            if ps.request_flag is not None:
                lo, hi = self.bb.flag_band
                if lo <= int(ps.request_flag) <= hi:
                    raise BehaviorError(f"pool {ps.name!r}: request_flag "
                                        f"{ps.request_flag} sits inside the behavior "
                                        f"blackboard band {lo}-{hi} — pick one outside it")
            self.pool_specs[ps.name] = ps
        # one spawn-request flag per pool — SET FROM OUTSIDE (a Hire [[choice]] row's
        # set_flag); consumed by the ticker's activation block, reset on ~ Reload.
        # An explicit PoolSpec.request_flag wins over blackboard allocation.
        self.pool_flags: dict[str, int] = {}
        for pname in self._pools:
            ps = self.pool_specs.get(pname)
            if ps is not None and ps.request_flag is not None:
                idx = int(ps.request_flag)
            else:
                idx = self.bb.flag(f"pool.{pname}.spawn")
            self.pool_flags[pname] = idx
            self._reset_flags.append(idx)

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

    def any_flag(self, *names: str) -> Cond:
        toks = []
        for i, n in enumerate(names):
            toks.append(f"Global.Bit[{self.bb.flag(n)}]")
            if i:
                toks.append("B_OROR")
        return Cond(" ".join(toks), _trusted=True)

    def public_flag(self, name: str) -> int:
        """Allocate (or fetch) a flag meant to be SET FROM OUTSIDE the compiled system —
        a kit `[[choice]]` lever row's `set_flag`, a gateway gate. It joins the
        Main_Init reset (so ~ Reload clears it) and its INDEX is returned for the
        external author. Deterministic across gen/deploy as long as the FieldBehavior
        is constructed identically (same units, same tree-build order)."""
        idx = self.bb.flag(name)
        if idx not in self._reset_flags:
            self._reset_flags.append(idx)
        return idx

    def any_of(self, *conds: Cond) -> Cond:
        """OR-compose Conds (each pushes exactly one stack value, so RPN
        concatenation + B_OROR is structurally valid). Inputs were already
        law-scanned at their own construction."""
        if len(conds) < 2:
            raise BehaviorError("any_of takes 2+ Conds")
        toks = []
        for i, c in enumerate(conds):
            if not isinstance(c, Cond):
                raise BehaviorError("any_of takes Cond nodes")
            toks.append(c.text)
            if i:
                toks.append("B_OROR")
        return Cond(" ".join(toks), _trusted=True)

    def all_of(self, *conds: Cond) -> Cond:
        """AND-compose Conds into ONE Cond — for use INSIDE any_of (a Sequence is the
        normal AND at branch level): any_of(all_of(active(a), near(w, a, r)), ...)."""
        if len(conds) < 2:
            raise BehaviorError("all_of takes 2+ Conds")
        toks = []
        for i, c in enumerate(conds):
            if not isinstance(c, Cond):
                raise BehaviorError("all_of takes Cond nodes")
            toks.append(c.text)
            if i:
                toks.append("B_ANDAND")
        return Cond(" ".join(toks), _trusted=True)

    def time_below(self, seconds: int) -> Cond:
        """True once the countdown HUD (``B_SYSVAR[17]`` = TimerUI.Time, remaining
        seconds) has dropped below ``seconds`` — the Hunt's wave-band shape
        (``GetTimerTime > 600/540/480/…`` inverted). Needs ``timer=`` on the field."""
        if not 0 <= int(seconds) <= 30000:
            raise BehaviorError("time_below seconds must be 0..30000")
        return Cond(f"B_SYSVAR[17] const({int(seconds)}) B_LT", _trusted=True)

    def time_above(self, seconds: int) -> Cond:
        if not 0 <= int(seconds) <= 30000:
            raise BehaviorError("time_above seconds must be 0..30000")
        return Cond(f"B_SYSVAR[17] const({int(seconds)}) B_GT", _trusted=True)

    def alternator(self, name: str, frames: int) -> Cond:
        """A shift clock: the flag ``name`` FLIPS every ``frames`` ticks (patrol
        shifts, work rotations). Registered once per name; returns the flag Cond
        (gate the other phase with Invert). The clock holds during warm-up and
        resets on ~ Reload (timer preset, flag cleared)."""
        if not 1 <= int(frames) <= 30000:
            raise BehaviorError("alternator frames must be 1..30000 (an Int16 timer)")
        if any(n == name for n, *_ in self._alternators):
            raise BehaviorError(f"alternator {name!r} already registered")
        f = self.bb.flag(name)
        t = self.bb.int16(f"{name}.clock")
        self._alternators.append((name, f, t, int(frames)))
        return self.flag(name)

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
                # every feed with a STATIC first target qualifies (Main_Init can
                # preset the duty walk): Patrol/March/Flee -> points[0], Wander ->
                # center, HoldPost -> the unit's own spawn (its post preset)
                if isinstance(a, (WalkTo, Hold, Patrol, March, Flee, Wander, HoldPost)):
                    return a
                raise BehaviorError(
                    f"{unit.name}: the fallback action must be a static feed "
                    f"(WalkTo/Hold/Patrol/March/Flee/Wander/HoldPost), not {type(a).__name__}")
            else:
                raise BehaviorError(
                    f"{unit.name}: the tree needs an unconditional Do fallback "
                    f"(got {type(node).__name__})")

    def has_battle_actions(self) -> bool:
        """True when any unit's tree fires a :class:`Battle` — the build must then
        ensure the entry-0 tag-10 Main_Reinit (the after-battle resume law)."""
        return any(isinstance(a, Battle)
                   for u in self.units.values() if u.tree is not None
                   for a in self._collect_actions(u))

    def compile(self) -> CompiledBehavior:
        for u in self.units.values():
            if u.tree is None:
                raise BehaviorError(f"unit {u.name!r} has no tree")

        duty_bodies: dict[str, bytes] = {}
        action_funcs: dict[str, list] = {}
        wu = self.bb.byte("warmup")
        ticker: list = [label("top"),
                        # latch = (player BOUND and usercontrol) or already latched —
                        # bound proves obj(250) resolves; usercontrol keeps the proven
                        # wake timing (movement enabled = the field has settled)
                        _stmt(f"Global.Bit[{self._pbound}] B_SYSVAR[{STAGE_SYSVAR}] "
                              f"B_ANDAND Global.Bit[{self._staged}] B_OROR"),
                        (JMP_IFNOT, "wait"),
                        _set_flag(self._staged, 1),
                        # THE WARM-UP GATE: after the player stages, count down before
                        # activating ANYONE — the field loads dead-still while the
                        # engine settles (rung-1 playtest: actors pathing during the
                        # entry-settle dragged the framerate for ~5-6s)
                        _stmt(f"Global.Byte[{wu}] const(0) B_GT"),
                        (JMP_IFNOT, "run"),
                        _stmt(f"Global.Byte[{wu}] Global.Byte[{wu}] const(1) "
                              f"B_MINUS B_LET"),
                        _stmt(f"Global.Byte[{wu}] const(0) B_EQ"),
                        (JMP_IFNOT, "wait")]
        for u in self.units.values():                    # warm-up expiry: wake everyone
            if u.pooled:                                 # ...except pooled units — they
                continue                                 # wake at ACTIVATION only
            ticker.append(_set_flag(self.bb.flag(f"{u.name}.active"), 1))
        ticker += [(JMP, "wait"), label("run")]
        # the player mirror (staged is guaranteed on the run path)
        ticker += [
            _stmt(f"Global.Int16[{self.bb.int16(f'{PLAYER}.mx')}] "
                  f"obj(uid={PLAYER_UID}).f[0] B_LET"),
            _stmt(f"Global.Int16[{self.bb.int16(f'{PLAYER}.mz')}] "
                  f"obj(uid={PLAYER_UID}).f[2] B_LET"),
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
        main_init += _set_flag(self._pbound, 0)
        main_init += _set_byte(wu, self.warmup)
        if self.timer is not None:
            # the countdown HUD — the Hunt's exact start triplet (★ proven on a
            # custom id, fort-condor playtest 2); re-runs on ~ Reload = clock reset
            main_init += (opcodes.encode(0x69, self.timer)   # ChangeTimerTime(sec)
                          + opcodes.encode(0x8D, 1)          # ShowTimer(1)
                          + opcodes.encode(0x7D, 1))         # RunTimer(1)
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

            spd = self.bb.byte(f"{u.name}.spd")
            spdap = self.bb.byte(f"{u.name}.spdap")

            # ---- main_init: units start INACTIVE (the ticker's warm-up wakes them),
            # reset protocol bytes, preset the duty target
            main_init += _set_flag(act_flag, 0)
            main_init += _set_byte(sel, 0) + _set_byte(run, 0)
            main_init += _set_byte(spd, u.walk_speed) + _set_byte(spdap, u.walk_speed)
            if isinstance(fallback, (Patrol, March, Flee)):
                px, pz = fallback.points[0]
            elif isinstance(fallback, Wander):
                px, pz = fallback.center
            elif isinstance(fallback, HoldPost):
                px, pz = u.spawn
            else:
                px, pz = fallback.point
            main_init += _set_int16(tx, int(px))
            main_init += _set_int16(tz, int(pz))
            if u.hp is not None:
                main_init += _set_byte(self.bb.byte(f"{u.name}.hp"), int(u.hp))
            if u.pooled or any(isinstance(a, HoldPost) for a in actions):
                # the placement post: presets to the unit's own spawn; a pooled
                # activation overwrites it with the press-time position
                main_init += _set_int16(self.bb.int16(f"{u.name}.px"), int(u.spawn[0]))
                main_init += _set_int16(self.bb.int16(f"{u.name}.pz"), int(u.spawn[1]))
            if u.pooled:
                main_init += _set_flag(self.bb.flag(f"{u.name}.spawned"), 0)

            # ---- the duty body (universal blocked walk on the target GLOBs); the
            # speed op reads the unit's speed GLOB so per-action speed applies at
            # every loop iteration (mid-walk changes land via the nudge dispatch)
            duty_bodies[u.name] = asm([
                label("top"),
                opcodes.encode(OP_SET_OBJECT_FLAGS, 7)
                + opcodes.encode(0x26, exprasm.assemble(f"Global.Byte[{spd}] B_EXPR_END"),
                                 arg_flags=0b1)
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
            battle_latch: dict[int, int] = {}            # aid -> one-shot latch flag
            for a in actions:
                aid = ids[id(a)]
                if a.feed or aid in dispatch_tag:        # same object in 2+ Do sites
                    continue
                tag = FIRST_ACTION_TAG + len(funcs)
                dispatch_tag[aid] = tag
                if isinstance(a, Battle):
                    li = self.bb.flag(f"{u.name}.battled{aid}")
                    battle_latch[aid] = li
                    if li not in self._reset_flags:
                        self._reset_flags.append(li)
                funcs.append((tag, self._dispatch_body(u, a, aid, sel, run)))
            # the SPEED NUDGE (always the last tag): MSPEED from the speed GLOB, then
            # record it applied. Straight-line at level 4 — preempts a mid-flight
            # blocked walk, which resumes at the new speed (actor.speed is re-read
            # every walk frame). Same running-protocol shape as action bodies.
            nudge_tag = FIRST_ACTION_TAG + len(funcs)
            funcs.append((nudge_tag, asm([
                _set_byte(run, 255),
                opcodes.encode(0x26, exprasm.assemble(f"Global.Byte[{spd}] B_EXPR_END"),
                               arg_flags=0b1),
                _stmt(f"Global.Byte[{spdap}] Global.Byte[{spd}] B_LET"),
                _set_byte(run, 0),
                opcodes.RETURN,
            ])))
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
                ]
                if aid in battle_latch:                  # a Battle fires ONCE per load:
                    ticker += [                          # the latch gates re-dispatch
                        _stmt(f"Global.Bit[{battle_latch[aid]}]"),
                        (JMP_IF, f"t_{u.name}_d{aid}"),
                    ]
                ticker += [
                    opcodes.run_script_async(DISPATCH_LEVEL, u.entry, tag),
                    label(f"t_{u.name}_d{aid}"),
                ]
            # the nudge dispatch: only when level 4 is free AND a FEED is selected
            # (a selected dispatch action owns the level-4 REQ this tick — mutual
            # exclusion by construction, never two REQs on one unit per tick)
            nl = f"t_{u.name}_nudge"
            ticker += [
                _stmt(f"Global.Byte[{run}] const(0) B_EQ"), (JMP_IFNOT, nl),
                _stmt(f"Global.Byte[{spd}] Global.Byte[{spdap}] B_EQ"), (JMP_IF, nl),
            ]
            for aid in dispatch_tag:
                ticker += [_stmt(f"Global.Byte[{sel}] const({aid}) B_EQ"), (JMP_IF, nl)]
            ticker += [opcodes.run_script_async(DISPATCH_LEVEL, u.entry, nudge_tag),
                       label(nl)]
            ticker += [label(f"t_{u.name}_done")]

            acts = ", ".join(dict.fromkeys(          # dedupe shared-object Do sites
                f"{ids[id(a)]}={type(a).__name__}" for a in actions))
            report.append(f"  {u.name}: entry {u.entry}, selected@{sel} running@{run} "
                          f"spd@{spd} actions[{acts}]")

        # cooldown decrements + alternator clocks — spliced after mirrors, so they
        # tick once per run pass (and HOLD during warm-up, which never reaches here)
        cd_blocks: list = []
        for name, _frames in self._cooldowns:
            t = self.bb.byte(name)
            cd_blocks += [
                _stmt(f"Global.Byte[{t}] const(0) B_GT"),
                (JMP_IFNOT, f"cd_{t}"),
                _stmt(f"Global.Byte[{t}] Global.Byte[{t}] const(1) B_MINUS B_LET"),
                label(f"cd_{t}"),
            ]
        for _name, f, t, frames in self._alternators:
            cd_blocks += [
                _stmt(f"Global.Int16[{t}] const(0) B_GT"),
                (JMP_IFNOT, f"alt_{t}_flip"),
                _stmt(f"Global.Int16[{t}] Global.Int16[{t}] const(1) B_MINUS B_LET"),
                (JMP, f"alt_{t}_end"),
                label(f"alt_{t}_flip"),
                _set_int16(t, frames),
                _stmt(f"Global.Bit[{f}] Global.Bit[{f}] const(1) B_XOR B_LET"),
                label(f"alt_{t}_end"),
            ]
        # pool activation blocks — the runtime-activation lane (fort-condor rung-3's
        # in-game-proven spawn-at-feet shape, now a compiler invariant): a set request
        # flag spawns the FIRST never-spawned unit of that pool AT THE PLAYER'S
        # press-time position. Sits on the run path AFTER the mirrors (player.mx/mz
        # fresh) and BEFORE the tree blocks (the new unit ticks with seeded mirrors
        # the same pass). Law-clean: InitObject precedes every obj-referencing token;
        # the 2-frame settle between InitObject and the DPOS is the proven recipe.
        pmx = f"Global.Int16[{self.bb.int16(f'{PLAYER}.mx')}]"
        pmz = f"Global.Int16[{self.bb.int16(f'{PLAYER}.mz')}]"
        for pname, unames in self._pools.items():
            req = self.pool_flags[pname]
            price = getattr(self.pool_specs.get(pname), "price", None)
            cd_blocks += [_stmt(f"Global.Bit[{req}]"), (JMP_IFNOT, f"pl_{pname}_end")]
            if price:
                # the gil gate (the inn-553 idiom): broke -> consume the request,
                # charge NOTHING (RemoveGil sits at the SPAWN site below, so an
                # exhausted pool never charges either)
                cd_blocks += [_stmt(f"B_SYSVAR[6] const({int(price)}) B_GE"),
                              (JMP_IFNOT, f"pl_{pname}_done")]
            for i, un in enumerate(unames):
                pu = self.units[un]
                spawned = self.bb.flag(f"{un}.spawned")
                upx = self.bb.int16(f"{un}.px")
                upz = self.bb.int16(f"{un}.pz")
                nxt = f"pl_{pname}_t{i + 1}" if i + 1 < len(unames) else f"pl_{pname}_done"
                cd_blocks += [
                    _stmt(f"Global.Bit[{spawned}]"), (JMP_IF, nxt),
                ] + ([opcodes.remove_gil(int(price))] if price else []) + [
                    # the placement post = the press-time player position
                    _stmt(f"Global.Int16[{upx}] {pmx} B_LET"),
                    _stmt(f"Global.Int16[{upz}] {pmz} B_LET"),
                    opcodes.init_object(pu.entry, 0),
                    opcodes.wait(2),                     # let the pooled Init complete
                    opcodes.move_instant_ex(
                        pu.entry,
                        exprasm.assemble(f"Global.Int16[{upx}] B_EXPR_END"),
                        exprasm.assemble(f"Global.Int16[{upz}] B_EXPR_END")),
                    # seed the unit's mirrors (its tree ticks THIS pass) + wake it
                    _stmt(f"Global.Int16[{self.bb.int16(f'{un}.mx')}] "
                          f"Global.Int16[{upx}] B_LET"),
                    _stmt(f"Global.Int16[{self.bb.int16(f'{un}.mz')}] "
                          f"Global.Int16[{upz}] B_LET"),
                    _set_flag(spawned, 1),
                    _set_flag(self.bb.flag(f"{un}.active"), 1),
                    (JMP, f"pl_{pname}_done"),
                ]
                if i + 1 < len(unames):
                    cd_blocks.append(label(nxt))
            cd_blocks += [label(f"pl_{pname}_done"),     # exhausted pool falls through
                          _set_flag(req, 0),             # here too: consume the request
                          label(f"pl_{pname}_end")]
        ticker[cooldown_blocks_at:cooldown_blocks_at] = cd_blocks
        for name, _frames in self._cooldowns:
            main_init += _set_byte(self.bb.byte(name), 0)
        for _name, f, t, frames in self._alternators:
            main_init += _set_int16(t, frames) + _set_flag(f, 0)
        for idx in self._reset_bytes:
            main_init += _set_byte(idx, 0)
        for idx in self._reset_flags:
            main_init += _set_flag(idx, 0)
        for idx, v in self._preset16.items():             # Wander target seeds
            main_init += _set_int16(idx, v)

        ticker += [label("wait"), opcodes.wait(self.tick), (JMP, "top"), opcodes.RETURN]
        pools_txt = ""
        if self._pools:
            def _pdesc(p):
                ps = self.pool_specs.get(p)
                extra = ""
                if ps is not None and ps.price:
                    extra += f", price {ps.price} gil"
                if ps is not None and ps.button is not None:
                    extra += f", hire button mask 0x{ps.button:X}"
                return (f"  {p}: spawn-request flag {self.pool_flags[p]}{extra}, "
                        f"units [{', '.join(self._pools[p])}]")
            pools_txt = "\npools (set the spawn flag from a [[choice]] row to activate):\n" \
                + "\n".join(_pdesc(p) for p in self._pools)
        return CompiledBehavior(
            ticker_body=asm(ticker),
            duty_bodies=duty_bodies,
            action_funcs=action_funcs,
            main_init=bytes(main_init),
            report=self.bb.report() + "\nunits:\n" + "\n".join(report) + pools_txt,
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
            self._reset_flags += [i for i in (latch, eng) if i not in self._reset_flags]
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
            if name not in [n for n, _f in self._cooldowns]:
                self._cooldowns.append((name, node.frames))
            if eng not in self._reset_flags:
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
            for nm in node.raise_flags:
                fi = self.bb.flag(nm)
                if fi not in self._reset_flags:
                    self._reset_flags.append(fi)
                out.append(_set_flag(fi, 1))
            for nm in node.clear_flags:
                fi = self.bb.flag(nm)
                if fi not in self._reset_flags:
                    self._reset_flags.append(fi)
                out.append(_set_flag(fi, 0))
            if node.action.feed:
                spd_v = node.action.speed if node.action.speed is not None else u.walk_speed
                if not 1 <= int(spd_v) <= 255:
                    raise BehaviorError(f"{u.name}: action speed must be 1..255")
                out.append(_set_byte(self.bb.byte(f"{u.name}.spd"), int(spd_v)))
                out += self._feed_effect(u, node.action)
            else:
                # selecting a DISPATCH action HALTS the duty walk the same tick (feed
                # own mirror) — otherwise the stale target keeps pulling the unit for
                # the tick(s) until the body preempts (rung-1 playtest: duelists
                # carried momentum into near-overlap)
                tx = self.bb.int16(f"{u.name}.tx")
                tz = self.bb.int16(f"{u.name}.tz")
                out += [_stmt(f"Global.Int16[{tx}] {self._mx(u.name)} B_LET"),
                        _stmt(f"Global.Int16[{tz}] {self._mz(u.name)} B_LET")]
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
        if isinstance(a, HoldPost):
            upx = self.bb.int16(f"{u.name}.px")
            upz = self.bb.int16(f"{u.name}.pz")
            return [_stmt(f"Global.Int16[{tx}] Global.Int16[{upx}] B_LET"),
                    _stmt(f"Global.Int16[{tz}] Global.Int16[{upz}] B_LET")]
        if isinstance(a, Chase):
            self._check_unit(a.target)
            gate = (f"Global.Bit[{self._staged}]" if a.target == PLAYER
                    else f"Global.Bit[{self.bb.flag(f'{a.target}.active')}]")
            self._label_ctr += 1
            skip = f"t_{u.name}_ch{self._label_ctr}"
            near_lbl = f"t_{u.name}_chs{self._label_ctr}"
            return [_stmt(gate), (JMP_IFNOT, skip),
                    # inside standoff: hold ground (feed own mirror) — pursuers must
                    # never occupy the target's tile (rung-1 playtest: phasing)
                    _stmt(_box(self._mx(u.name), self._mz(u.name),
                               self._mx(a.target), self._mz(a.target), int(a.standoff))),
                    (JMP_IFNOT, near_lbl),
                    _stmt(f"Global.Int16[{tx}] {self._mx(u.name)} B_LET"),
                    _stmt(f"Global.Int16[{tz}] {self._mz(u.name)} B_LET"),
                    (JMP, skip),
                    label(near_lbl),
                    _stmt(f"Global.Int16[{tx}] {self._mx(a.target)} B_LET"),
                    _stmt(f"Global.Int16[{tz}] {self._mz(a.target)} B_LET"),
                    label(skip)]
        if isinstance(a, Flee):
            self._check_unit(a.threat)
            gate = (f"Global.Bit[{self._staged}]" if a.threat == PLAYER
                    else f"Global.Bit[{self.bb.flag(f'{a.threat}.active')}]")
            self._label_ctr += 1
            L = f"t_{u.name}_fl{self._label_ctr}"
            p0x, p0z = a.points[0]
            out = [_stmt(gate), (JMP_IFNOT, f"{L}_ng")]  # threat gone -> primary refuge
            for i, (px, pz) in enumerate(a.points[:-1]):
                out += [_stmt(_box(self._mx(a.threat), self._mz(a.threat),
                                   int(px), int(pz), int(a.avoid_r))),
                        (JMP_IF, f"{L}_n{i}"),           # threat camps it -> next refuge
                        _set_int16(tx, int(px)), _set_int16(tz, int(pz)),
                        (JMP, f"{L}_end"),
                        label(f"{L}_n{i}")]
            lx, lz = a.points[-1]
            out += [_set_int16(tx, int(lx)), _set_int16(tz, int(lz)), (JMP, f"{L}_end"),
                    label(f"{L}_ng"),
                    _set_int16(tx, int(p0x)), _set_int16(tz, int(p0z)),
                    label(f"{L}_end")]
            return out
        if isinstance(a, Wander):
            wtx = self.bb.int16(f"{u.name}.wtx")
            wtz = self.bb.int16(f"{u.name}.wtz")
            wt = self.bb.byte(f"{u.name}.wtimer")
            if wt not in self._reset_bytes:              # 0 -> fresh roll on first select
                self._reset_bytes.append(wt)
            cx, cz = int(a.center[0]), int(a.center[1])
            self._preset16.setdefault(wtx, cx)
            self._preset16.setdefault(wtz, cz)
            self._label_ctr += 1
            L = f"t_{u.name}_wn{self._label_ctr}"
            roll = (f"const(128) B_MINUS const({int(a.radius)}) B_MULT "
                    f"const(128) B_DIV B_PLUS B_LET")
            return [
                _stmt(f"Global.Byte[{wt}] const(0) B_GT"), (JMP_IFNOT, f"{L}_roll"),
                _stmt(f"Global.Byte[{wt}] Global.Byte[{wt}] const(1) B_MINUS B_LET"),
                (JMP, f"{L}_feed"),
                label(f"{L}_roll"),
                _set_byte(wt, int(a.hold)),
                _stmt(f"Global.Int16[{wtx}] const({cx}) B_SYSVAR[0] {roll}"),
                _stmt(f"Global.Int16[{wtz}] const({cz}) B_SYSVAR[0] {roll}"),
                label(f"{L}_feed"),
                _stmt(f"Global.Int16[{tx}] Global.Int16[{wtx}] B_LET"),
                _stmt(f"Global.Int16[{tz}] Global.Int16[{wtz}] B_LET"),
            ]
        if isinstance(a, March):
            wp = self.bb.byte(f"{u.name}.wp")        # shared with Patrol: an
            if wp not in self._reset_bytes:          # out-of-range wp resets to 0
                self._reset_bytes.append(wp)
            self._label_ctr += 1
            p = f"t_{u.name}_m{self._label_ctr}"
            out: list = []
            n = len(a.points)
            for i, (px, pz) in enumerate(a.points):
                out += [_stmt(f"Global.Byte[{wp}] const({i}) B_EQ"),
                        (JMP_IFNOT, f"{p}_w{i}")]
                if i < n - 1:                        # advance on arrival, except last
                    out += [_stmt(_box(self._mx(u.name), self._mz(u.name),
                                       int(px), int(pz), a.arrive_r)),
                            (JMP_IFNOT, f"{p}_f{i}"),
                            _set_byte(wp, i + 1),
                            (JMP, f"{p}_end"),
                            label(f"{p}_f{i}")]
                out += [_set_int16(tx, int(px)), _set_int16(tz, int(pz)),
                        (JMP, f"{p}_end"),
                        label(f"{p}_w{i}")]
            out += [_set_byte(wp, 0), label(f"{p}_end")]
            return out
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

    def _announce_player_bound(self, data: bytes) -> bytes:
        """THE STAGED-LATCH EXISTENCE FIX: insert a ``player.bound`` flag-set
        immediately after EVERY ``DefinePlayerCharacter`` (0x2C) in a tag-0 Init —
        the player's own entry announces that uid 250 resolves, and the ticker's
        latch requires the announcement (insert_in_function's docstring pattern:
        right after 0x2C is the blessed safe insert point). No 0x2C anywhere =
        no player can ever bind = the ticker's obj(250) reads can never be safe →
        refuse the install."""
        from ..eb import disasm as D
        from ..eb import edit as eb_edit
        from ..eb.model import EbScript
        eb = EbScript.from_bytes(data)
        announce = _set_flag(self._pbound, 1)
        sites = []                               # (entry, rel offset AFTER the 0x2C)
        for i in range(eb.entry_count):
            e = eb.entry(i)
            if e.size <= 0:
                continue
            f0 = e.func_by_tag(0)
            if f0 is None:
                continue
            for ins in D.iter_code(data, f0.abs_start, f0.abs_end):
                if ins.op == 0x2C:
                    sites.append((i, ins.end - f0.abs_start))
        if not sites:
            raise BehaviorError(
                "behavior install: no DefinePlayerCharacter (0x2C) in any Init — a "
                "behavior field needs a bound player (the ticker reads obj(250); "
                "without a binding the staged latch could never safely pass)")
        out = bytes(data)
        for i, rel in sorted(sites, key=lambda s: (s[0], -s[1])):  # per-entry descending
            out = eb_edit.insert_in_function(out, i, 0, rel, announce)
        return out

    def _poller_body(self, mask: int, choice_slot: int) -> bytes:
        """The buy-anywhere BUTTON POLLER (rung-3 in-game-proven shape, verbatim):
        poll ``const4(mask) B_KEYON AND usercontrol`` at Wait(1) — a button TRIGGER
        lasts ONE frame, so the poll cadence must be every frame (the playtest-7
        eaten-button lesson); on press: the Hunt's announce blip, then
        ``RunScriptSync(4, <parked choice>, 3)`` pops the hire menu (the zone trigger
        is bypassed — the kit dispatch body is self-contained); the Wait(12) debounce
        runs ONLY after a menu round."""
        return asm([
            label("top"),
            _stmt(f"const4({int(mask)}) B_KEYON B_SYSVAR[{STAGE_SYSVAR}] B_ANDAND"),
            (JMP_IFNOT, "wait"),
            opcodes.encode(0xC8, 53248, 683, 0, 128, 125),   # the Hunt's announce blip
            opcodes.run_script_sync(DISPATCH_LEVEL, choice_slot, 3),
            opcodes.wait(12),                                # post-menu debounce ONLY
            (JMP, "top"),
            label("wait"),
            opcodes.wait(1),                                 # the stock poll cadence
            (JMP, "top"),
            opcodes.RETURN,
        ])

    def install(self, eb_bytes: bytes, compiled: CompiledBehavior | None = None,
                choice_slots: dict | None = None) -> bytes:
        """Install a compiled behavior into a BUILT field's `.eb` (the generalized
        `swarm_bench.patch_eb` shape): announce the player binding (the staged-latch
        existence source), replace each unit's tag-1 with its duty body,
        `add_function` the dispatch tags, seat + activate the ticker (the coop
        inject_hold entry pattern), prepend the Main_Init reset, and gate on an eblint
        BASELINE DIFF (pre-existing issues pass; a NEW error fails the install).

        ``choice_slots``: pool name -> the entry slot of that pool's PARKED hire
        [[choice]] region — required for every pool whose spec has ``button`` (the
        poller entry RunScriptSyncs the menu by slot)."""
        from .. import eblint
        from ..eb import edit as eb_edit
        from . import object as _object
        cb = compiled or self.compile()
        baseline = {str(p) for p in eblint.lint_eb(bytes(eb_bytes))}
        out = self._announce_player_bound(bytes(eb_bytes))
        for u in self.units.values():
            out = eb_edit.replace_function_body(out, u.entry, 1, cb.duty_bodies[u.name])
            for tag, body in cb.action_funcs[u.name]:
                out = eb_edit.add_function(out, u.entry, tag, body)
        ticker_entry = (bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + cb.ticker_body)
        out, slot = _object.seat_entry(out, ticker_entry)
        out = eb_edit.activate_block(out, opcodes.init_code(slot, 0))
        # buy-anywhere pollers (one seated entry per button pool)
        for pname, ps in self.pool_specs.items():
            if ps.button is None:
                continue
            cslot = (choice_slots or {}).get(pname)
            if cslot is None:
                raise BehaviorError(
                    f"pool {pname!r} has a hire button but no parked-choice slot was "
                    f"given — author a zone [[choice]] (parked far off-mesh) whose Hire "
                    f"row does set_flag = [{self.pool_flags[pname]}, 1], and pass its "
                    f"entry slot via choice_slots")
            pentry = (bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4)
                      + self._poller_body(ps.button, int(cslot)))
            out, pslot = _object.seat_entry(out, pentry)
            out = eb_edit.activate_block(out, opcodes.init_code(pslot, 0))
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
        if isinstance(a, Battle):
            latch = self.bb.flag(f"{u.name}.battled{aid}")
            return asm([
                _set_flag(latch, 1),                     # one-shot: set BEFORE the
                _set_byte(run, 255),                     # suspend, so a return can
                opcodes.encode(0x2A, 0, int(a.scene)),   # never re-fire it. Battle(0,
                _set_byte(run, 0),                       # scene) = 559's tread shape.
                opcodes.RETURN,
            ])
        if isinstance(a, Announce):
            return asm(head[:1] + [opcodes.window_async(a.window, 128, int(a.txid))]
                       + [label("loop"),
                          _stmt(f"Global.Byte[{sel}] const({aid}) B_EQ"),
                          (JMP_IFNOT, "out"),
                          opcodes.wait(1), (JMP, "loop"),
                          label("out"), _set_byte(run, 0), opcodes.RETURN])
        if isinstance(a, SwingAt):
            self._check_unit(a.target)
            if a.target == PLAYER:
                raise BehaviorError("SwingAt(player) is not a v1 action")
            t_hp = self.bb.byte(f"{a.target}.hp")
            t_act = self.bb.flag(f"{a.target}.active")
            timer = self.bb.byte(f"{u.name}.swing{aid}")
            if timer not in self._reset_bytes:
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
