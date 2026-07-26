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
from ..eb.labelasm import JMP, JMP_IF, JMP_IFNOT, _measure, asm, label

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
class Engage(Action):
    """THE GROUP LOOP (v2): fight whichever member of ``group`` the acquire loop
    holds in my target register — ONE branch and ONE dispatch body regardless of
    roster size, replacing the unrolled per-pair machinery (the three-walls
    economics: ~130B of ticker + ~108B of body + a band byte PER PAIR collapse
    to a fixed ~700B per unit). Two-phase by construction: within ``contact``
    the strike body runs (target-indexed damage + facing); otherwise the pursue
    feed walks toward the target's table position (live retarget, sync-walk
    law). Acquisition is FIRST-IN-RANGE in roster order (v1 pair-branch parity
    — roster order IS the priority list) and STICKY: a valid target is kept
    until it dies, deactivates, or leaves ``radius``."""
    group: str
    radius: int = 900
    contact: int = 170
    damage: int = 1
    interval: int = 25
    speed: int | None = None
    nearest: bool = False            # argmin acquire (Chebyshev) vs roster order

    def __post_init__(self):
        if not 1 <= int(self.radius) <= 30000:
            raise BehaviorError("Engage radius must be 1..30000")
        if not 1 <= int(self.contact) < int(self.radius):
            raise BehaviorError("Engage contact must be 1..radius-1")
        if not 1 <= int(self.damage) <= 99:
            raise BehaviorError("Engage damage must be 1..99")
        if not 1 <= int(self.interval) <= 255:
            raise BehaviorError("Engage interval must be 1..255 (a GLOB byte timer)")
        self._swing = _GroupSwing(self)
        self._pursue = _GroupPursue(self)


@dataclass
class _GroupSwing(Action):
    """Engage's strike half (internal): the target-indexed dispatch body."""
    engage: "Engage"


@dataclass
class _GroupPursue(Action):
    """Engage's approach half (internal): the table-fed chase feed."""
    engage: "Engage"
    feed = True

    @property
    def speed(self):
        return self.engage.speed


@dataclass
class HoldGround(Action):
    """Stand and take the fight: a dispatch action whose SELECTION halts the duty
    walk (the dispatch-halt clause feeds the unit its own mirror) and whose body
    just idles while selected — THE PIN. A marcher gated on
    ``any_near(interceptors)`` stops mid-route while engaged instead of jogging
    away from its attackers (the condor round-1 feedback), and resumes its march
    at the current waypoint when the branch deselects."""


@dataclass
class SwingAt(Action):
    """Melee ticks against another unit's HP byte (the proven fight-body shape,
    minus death policy — death is a TREE branch, e.g. Cond(hp==0) -> Do(Die()))."""
    target: str
    interval: int = 30
    damage: int = 1


@dataclass
class Die(Action):
    """Clear my active flag (mirrors stop — the dead-uid firewall), then TerminateEntry.
    ``count``: bump that counter by 1 first — the dispatch body runs exactly once
    (the entry terminates), so the bump is edge-safe for free (the kill-counter
    idiom: every attacker dies with ``count="kills"``, a win branch gates on
    ``counter_ge``)."""
    count: str | None = None


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


@dataclass
class Award(Action):
    """Pay the player — gil and/or an item (the minigame win-reward lane). MUST be
    wrapped in Once: it compiles on the EVENT-Once machinery (edge-latched request
    lane, latch-FIRST body), which is what makes the payout exactly-once even if
    the win condition holds forever. Pair with a separate Announce branch for the
    fanfare text."""
    gil: int = 0
    item: object = None              # item name ("Ether") or numeric id
    count: int = 1

    def __post_init__(self):
        if not 0 <= int(self.gil) <= 0xFFFFFF:
            raise BehaviorError("Award gil must be 0..16777215 (24-bit)")
        if not 1 <= int(self.count) <= 99:
            raise BehaviorError("Award count must be 1..99")
        if not int(self.gil) and self.item is None:
            raise BehaviorError("Award needs gil and/or an item")


@dataclass
class ShopStock(Action):
    """Add or remove one item in a shop's BUY list at runtime — Memoria's extended
    ``AddShopItem`` (0x115: ``shopId, itemId, add`` — used by ZERO shipping fields;
    the wave-unlock armoury lever). Engine facts that shape the emission: the shop
    must already exist in ``ShopItems.csv`` (the engine silently no-ops otherwise —
    validate refuses an unknown shop id); the list mutation is SESSION-global
    in-memory state (survives field transitions, resets at relaunch, never saved);
    and the engine's ``List.Add`` DUPLICATES — so an add emits remove-then-add,
    idempotent per fire. MUST be Once-wrapped (the event-Once lane, Award's
    machinery): the once-latch resets per field entry, so each session re-asserts
    the unlock when its condition holds — the seed law for shop state."""
    shop: int
    item: object                     # item name ("Elixir") or numeric id
    add: bool = True

    def __post_init__(self):
        if not 0 <= int(self.shop) <= 255:
            raise BehaviorError("ShopStock shop id must be 0..255 (the Menu byte)")


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
    # THE ITEM POOL (the shop-as-hire-menu bridge): the pool's currency is an ITEM —
    # each ticker pass, holding >= 1 of ``item`` converts one contract into one spawn
    # (B_HAVE_ITEM gate + RemoveItem at the spawn site; the native Menu(2,id) shop is
    # the entire hire UX — it hard-pauses the ticker while open, so contracts convert
    # the tick after it closes). Exclusive with price/button/request_flag: the item IS
    # the request, no flag lane exists. An exhausted pool consumes NOTHING (contracts
    # are real inventory). ``item`` is a RESOLVED id; ``item_name`` for reports.
    item: int | None = None
    item_name: str = ""


# ---------------------------------------------------------------- data tables
TABLE_ID_BASE = 1000                     # kit auto-allocation band for gScriptVector ids
TABLE_MAX_LEN = 64                       # keeps the Main_Init seed block bounded
TABLE_VALUE_MIN = -(1 << 25)             # CalcStack values are 26-bit signed — a const4
TABLE_VALUE_MAX = (1 << 25) - 1          # is masked to 26 bits at evaluation


@dataclass
class HudSpec:
    """A LIVE COUNTER STRIP — the stock substrate every PC minigame HUD uses
    (the hunt points, the auction bid, the jump-rope count): SetTextVariable
    (0x66) feeds ``[NUMB=n]`` slots and a re-issued transparent WindowAsync
    (0x20, flags 16) replaces the same window; the ticker redraws only when a
    value changed (the hunt's dirty-mirror shape). ``values`` are COUNTER
    names, slot i drives ``[NUMB=i]`` in ``text``; the ``.mes`` line is minted
    by the build like an announce (``[IMME]`` is prepended if absent so the
    strip never types in)."""
    text: str
    values: tuple                    # value SOURCES (counter / gil / timer / hp:unit)
    window: int = 6
    txid: int | None = None
    digits: tuple = ()               # per-slot width reserve (open-pass sentinels)


@dataclass
class GroupSpec:
    """A ROSTER whose per-member state lives in gScriptVector tables — the v2
    substrate: px/pz (position mirrors, copied per tick), act (the active bit,
    copied per tick), hp (THE ONLY home of a member's hit points — seeded from
    UnitSpec.hp at Main_Init, damaged by computed-index writes, read by the
    rerouted hp conds). Rosters are what Engage loops over."""
    name: str
    units: tuple
    px_tid: int = 0
    pz_tid: int = 0
    act_tid: int = 0
    hp_tid: int = 0


@dataclass
class ScanSpec:
    """THE VECTOR LOOP (rung 0 of the v2 vector substrate): each ticker pass,
    the roster's mirrors are copied into position tables and a bounded loop
    walks them by a LIVE index — reads AND writes vector cells through the loop
    variable — deriving how many units sit inside a Chebyshev box around
    ``point``, published into counter ``count``. The count flows THROUGH a
    computed-index write then read-back of the per-unit flag cells, so any
    indexing fault breaks the number rather than passing silently."""
    name: str
    units: tuple
    point: tuple | None
    radius: int | None
    count: str
    flags: str | None
    px_tid: int = 0
    pz_tid: int = 0
    flag_tid: int = 0
    li: int = 0
    acc: int = 0
    group: str | None = None         # group form: loop the roster's own tables
    alive_only: bool = False         # gate each cell on act && hp>0 (group form)
    act_tid: int = 0                 # group form only
    hp_tid: int = 0


@dataclass
class TableSpec:
    """A named per-field DATA TABLE backed by Memoria's ``gScriptVector`` (the 0xD3
    VECTOR lane — real computed array indexing in ``.eb``, on the protected stock
    baseline since 2023).

    RE-SEEDED at every Main_Init (field entry AND ~ Reload): size is forced to 0
    then to ``len(values)`` (the engine zero-fills a grow), then non-zero cells are
    written — so a table is deterministic FIELD-SESSION state, and a redeploy can
    never leave a stale tail behind in the save (gScriptVector is save-serialized;
    the id namespace is save-GLOBAL, which the re-seed makes harmless: every field
    rebuilds its own tables before reading them). ``id``: an explicit gScriptVector
    id; default = allocated from :data:`TABLE_ID_BASE` in declaration order."""
    name: str
    values: tuple
    id: int | None = None


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


def _terminal_do(node) -> "Do | None":
    """The subtree's terminal Do — a bare Do, or a Sequence ending in one (the
    only shapes v1 emits). None for anything else."""
    if isinstance(node, Do):
        return node
    if isinstance(node, Sequence) and node.children and isinstance(node.children[-1], Do):
        return node.children[-1]
    return None


def _cnum(v: int) -> str:
    """The correct literal token for ``v``: ``const()`` is a SIGNED Int16 at
    runtime (the engine reads getShortIP signed — 32768..65535 would come out
    negative), anything outside ±32767 rides ``const4()`` (engine-masked to the
    26-bit CalcStack domain, which TABLE_VALUE_MIN/MAX already bound)."""
    v = int(v)
    return f"const({v})" if -0x8000 <= v <= 0x7FFF else f"const4({v})"


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
    sizes: dict | None = None        # the byte histogram (see size_report)

    def size_report(self) -> str:
        """THE BYTE HISTOGRAM — where the compiled bytes go, unit by unit, against
        the engine's real walls: the ticker relaxes past ±32K via jump islands,
        but the whole FILE stays u16-addressed (~64KB entry-table reach), so this
        is the budget sheet for roster/pairing decisions."""
        if not self.sizes:
            return "size report unavailable"
        s = self.sizes
        disp_total = sum(n for fns in s["dispatch"].values() for _, _, n in fns)
        duty_total = sum(s["duty"].values())
        islands = len(self.ticker_body) - s["ticker_content"]
        new_total = (len(self.ticker_body) + len(self.main_init)
                     + duty_total + disp_total)
        out = [f"byte histogram -- new bytes this build: {new_total}B "
               f"(ticker {len(self.ticker_body)}B"
               + (f" = {s['ticker_content']}B + {islands}B islands" if islands else "")
               + f", main_init {len(self.main_init)}B, duty {duty_total}B, "
                 f"dispatch bodies {disp_total}B)"]
        shared = [(nm, n) for nm, n in s["ticker_segments"]
                  if not nm.startswith("unit ")]
        out.append("  shared ticker: " + ", ".join(f"{nm} {n}B" for nm, n in shared))
        per_unit = []
        for nm, n in s["ticker_segments"]:
            if not nm.startswith("unit "):
                continue
            u = nm[5:]
            fns = s["dispatch"].get(u, [])
            per_unit.append((n + s["duty"].get(u, 0) + sum(x for _, _, x in fns),
                             u, n, fns))
        for tot, u, tick_n, fns in sorted(per_unit, reverse=True):
            body_txt = ", ".join(f"{kind} {x}B" for _, kind, x in fns)
            out.append(f"  {u}: {tot}B  (ticker {tick_n}B, duty "
                       f"{s['duty'].get(u, 0)}B; {body_txt})")
        return "\n".join(out)

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
                 timer: int | None = None, tables: list[TableSpec] | tuple = (),
                 counters: tuple = ()):
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
            if ps.item is not None:
                if not 0 <= int(ps.item) <= 254:          # 255 = NoItem
                    raise BehaviorError(f"pool {ps.name!r}: item must be a regular item id 0..254")
                if ps.price is not None or ps.button is not None or ps.request_flag is not None:
                    raise BehaviorError(f"pool {ps.name!r}: item is exclusive with price/"
                                        f"button/request_flag — the item IS the request "
                                        f"(the shop is the menu; no flag lane exists)")
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
            if ps is not None and ps.item is not None:
                continue                                  # an item pool has no request lane
            if ps is not None and ps.request_flag is not None:
                idx = int(ps.request_flag)
            else:
                idx = self.bb.flag(f"pool.{pname}.spawn")
            self.pool_flags[pname] = idx
            self._reset_flags.append(idx)
        # THE HIREABLE FLAG (per pool, PUBLISHED): hireable = (gil >= price, when
        # priced) AND not-exhausted — refreshed every run pass by the ticker. Wire a
        # hire [[choice]] row's `requires_flag` to it (and a refusal row's
        # `requires_flag_clear`) and the menu can never say "Deployed!" to a hire
        # the activation block will refuse. Presets to 1 in Main_Init (gil is
        # unknowable at build; the first run pass corrects within a tick).
        self.pool_hireable: dict[str, int] = {}
        for pname in self._pools:
            self.pool_hireable[pname] = self.bb.flag(f"pool.{pname}.hireable")
        # DATA TABLES + COUNTERS (the 0xD3 VECTOR lane): explicit ids claim first,
        # autos fill the lowest free ids from TABLE_ID_BASE in declaration order,
        # and the internal counter table takes the LAST auto slot — all
        # deterministic from the ctor arguments alone (the allocation contract).
        self.tables: dict[str, tuple[int, tuple]] = {}   # name -> (vector id, values)
        self._counters: dict[str, int] = {}              # name -> cell index
        self._schedules: list[tuple[str, str]] = []      # (counter, table)
        self._scans: list[ScanSpec] = []                 # the vector-loop probes
        self._groups: dict[str, GroupSpec] = {}          # the engage rosters
        self._member: dict[str, tuple[str, int]] = {}    # unit -> (group, index)
        self._engages: dict[str, Engage] = {}            # unit -> its one Engage
        self._huds: list[HudSpec] = []                   # live counter strips
        self._item_mirrors: dict[int, int] = {}          # item id -> snapshot byte (have_item)
        taken: set[int] = set()
        for ts in tables:
            if ts.id is not None:
                tid = int(ts.id)
                if not 0 <= tid <= TABLE_VALUE_MAX:
                    raise BehaviorError(f"table {ts.name!r}: id must be 0..{TABLE_VALUE_MAX}")
                if tid in taken:
                    raise BehaviorError(f"table {ts.name!r}: id {tid} used twice")
                taken.add(tid)
        self._next_tid = TABLE_ID_BASE

        def _auto_tid() -> int:
            while self._next_tid in taken:
                self._next_tid += 1
            taken.add(self._next_tid)
            return self._next_tid

        for ts in tables:
            if not re.fullmatch(r"[A-Za-z0-9_]+", ts.name or ""):
                raise BehaviorError(f"table name {ts.name!r} must be [A-Za-z0-9_]+")
            if ts.name in self.tables:
                raise BehaviorError(f"duplicate table {ts.name!r}")
            vals = tuple(int(v) for v in ts.values)
            if not 1 <= len(vals) <= TABLE_MAX_LEN:
                raise BehaviorError(f"table {ts.name!r}: 1..{TABLE_MAX_LEN} values "
                                    f"(got {len(vals)})")
            for v in vals:
                if not TABLE_VALUE_MIN <= v <= TABLE_VALUE_MAX:
                    raise BehaviorError(f"table {ts.name!r}: value {v} outside the "
                                        f"26-bit CalcStack domain "
                                        f"({TABLE_VALUE_MIN}..{TABLE_VALUE_MAX})")
            self.tables[ts.name] = (int(ts.id) if ts.id is not None else _auto_tid(),
                                    vals)
        for cn in counters:
            cn = str(cn)
            if not re.fullmatch(r"[A-Za-z0-9_]+", cn):
                raise BehaviorError(f"counter name {cn!r} must be [A-Za-z0-9_]+")
            if cn in self._counters:
                raise BehaviorError(f"duplicate counter {cn!r}")
            if cn in self.tables:
                raise BehaviorError(f"counter {cn!r} collides with a table name")
            self._counters[cn] = len(self._counters)
        self._ctr_tid: int | None = _auto_tid() if self._counters else None

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
        return Cond(f"{self._hp_ref(unit)} const({n}) B_GT", _trusted=True)

    def hp_le(self, unit: str, n: int) -> Cond:
        return Cond(f"{self._hp_ref(unit)} const({n}) B_LE", _trusted=True)

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

    def have_item(self, item_id: int, n: int = 1) -> Cond:
        """True while the party holds >= ``n`` of item ``item_id`` — via a
        TOP-OF-TICK SNAPSHOT of ``B_HAVE_ITEM`` (0x64, GetItemCount), NOT the live
        read. THE ARMOURY ROUND-2 LESSON (owner-diagnosed): pool activation runs
        BEFORE the tree blocks (a fresh spawn must tick the same pass), so an item
        pool consuming the same item ate one contract before a live cond could
        count it — ``have_item >= 3`` needed FOUR held. The snapshot (written with
        the mirrors, before any pool consumes) is the system's perception law
        applied to inventory: every cond in a pass judges the count as the player
        left it. The POOL's own gate stays live — it is the consumer."""
        if not 0 <= int(item_id) <= 254:                  # 255 = NoItem
            raise BehaviorError("have_item: item id must be 0..254")
        if not 1 <= int(n) <= 99:
            raise BehaviorError("have_item: count must be 1..99 (the inventory cap)")
        m = self.bb.byte(f"item.{int(item_id)}.held")     # one mirror per distinct item
        self._item_mirrors[int(item_id)] = m
        return Cond(f"Global.Byte[{m}] const({int(n)}) B_GE", _trusted=True)

    # ---------------- data tables + counters (the 0xD3 VECTOR lane)
    def _counter_ref(self, name: str) -> str:
        """The RPN fragment pushing counter ``name``'s cell — usable as a read
        operand OR as a B_LET assignment target (the VECTOR token is an lvalue)."""
        if name not in self._counters:
            raise BehaviorError(f"unknown counter {name!r} (declare it in counters=)")
        return f"{_cnum(self._ctr_tid)} {_cnum(self._counters[name])} B_VECTOR"

    def _table_ref(self, name: str, idx) -> str:
        """The RPN fragment pushing ``table[name][idx]``. ``idx``: an int (bounds-
        checked at compile time) or a COUNTER name — the computed-index form: the
        index is READ FROM the counter cell at runtime (nested VECTOR reads compose;
        the engine keys sub-operands by CalcStack depth). A runtime index past the
        end fails soft to 0 by engine design."""
        if name not in self.tables:
            raise BehaviorError(f"unknown table {name!r} (declare it in tables=)")
        tid, values = self.tables[name]
        if isinstance(idx, str):
            return f"{_cnum(tid)} {self._counter_ref(idx)} B_VECTOR"
        if not 0 <= int(idx) < len(values):
            raise BehaviorError(f"table {name!r} index {idx} out of range "
                                f"0..{len(values) - 1}")
        return f"{_cnum(tid)} {_cnum(int(idx))} B_VECTOR"

    def _check_cmp_value(self, n: int) -> int:
        if not TABLE_VALUE_MIN <= int(n) <= TABLE_VALUE_MAX:
            raise BehaviorError(f"comparison value {n} outside the 26-bit CalcStack "
                                f"domain ({TABLE_VALUE_MIN}..{TABLE_VALUE_MAX})")
        return int(n)

    def counter_ge(self, name: str, n: int) -> Cond:
        return Cond(f"{self._counter_ref(name)} {_cnum(self._check_cmp_value(n))} B_GE",
                    _trusted=True)

    def counter_le(self, name: str, n: int) -> Cond:
        return Cond(f"{self._counter_ref(name)} {_cnum(self._check_cmp_value(n))} B_LE",
                    _trusted=True)

    def counter_eq(self, name: str, n: int) -> Cond:
        return Cond(f"{self._counter_ref(name)} {_cnum(self._check_cmp_value(n))} B_EQ",
                    _trusted=True)

    def table_ge(self, name: str, idx, n: int) -> Cond:
        return Cond(f"{self._table_ref(name, idx)} {_cnum(self._check_cmp_value(n))} B_GE",
                    _trusted=True)

    def table_le(self, name: str, idx, n: int) -> Cond:
        return Cond(f"{self._table_ref(name, idx)} {_cnum(self._check_cmp_value(n))} B_LE",
                    _trusted=True)

    def table_eq(self, name: str, idx, n: int) -> Cond:
        return Cond(f"{self._table_ref(name, idx)} {_cnum(self._check_cmp_value(n))} B_EQ",
                    _trusted=True)

    def schedule(self, counter: str, table: str):
        """THE WAVE CLOCK: each ticker pass (after warm-up), if the countdown HUD
        has dropped below ``table[counter]``, the counter advances by 1 — one
        generic engine instead of N unrolled time bands, and the schedule is DATA
        (a rebalance edits the table, not the trees). Self-limiting by
        construction: once the counter walks off the table's end the read fails
        soft to 0 and ``timer < 0`` never holds (the OOB terminator — no latch
        flag needed). Units gate their waves on ``counter_ge``/``counter_eq``.
        Needs ``timer=`` on the field."""
        if self.timer is None:
            raise BehaviorError("schedule() needs timer= on the field (the countdown "
                                "HUD is the clock it reads)")
        self._counter_ref(counter)                        # existence checks
        self._table_ref(table, 0)
        if any(c == counter for c, _t in self._schedules):
            raise BehaviorError(f"counter {counter!r} already has a schedule")
        self._schedules.append((counter, table))

    def _alloc_tid(self) -> int:
        """A deterministic auto table id AFTER construction (scan registration):
        continue from the ctor's high-water mark, skipping anything taken."""
        used = {tid for tid, _v in self.tables.values()}
        if self._ctr_tid is not None:
            used.add(self._ctr_tid)
        while self._next_tid in used:
            self._next_tid += 1
        tid = self._next_tid
        self._next_tid += 1
        return tid

    def group(self, name: str, units) -> GroupSpec:
        """Declare a ROSTER (see :class:`GroupSpec`): allocates the px/pz/act/hp
        tables and moves every member's hit points INTO the hp table (the hp
        conds and every SwingAt damage write reroute to the cell — one home,
        no drift). Members must carry ``hp=`` and may belong to one group.
        DECLARE GROUPS BEFORE BUILDING TREES: ``hp_gt``/``hp_le`` bake the hp
        home into their Cond text at call time (the TOML lane orders this
        correctly by construction)."""
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name or ""):
            raise BehaviorError(f"group name {name!r} must be [a-z][a-z0-9_]*")
        if name in self._groups:
            raise BehaviorError(f"group {name!r} already registered")
        units = tuple(str(u) for u in units)
        if not units:
            raise BehaviorError(f"group {name!r}: needs at least one unit")
        if len(units) > TABLE_MAX_LEN:
            raise BehaviorError(f"group {name!r}: {len(units)} units > the "
                                f"{TABLE_MAX_LEN}-cell table cap")
        if len(set(units)) != len(units):
            raise BehaviorError(f"group {name!r}: duplicate units")
        for u in units:
            if u not in self.units:
                raise BehaviorError(f"group {name!r}: unknown unit {u!r}")
            if self.units[u].hp is None:
                raise BehaviorError(f"group {name!r}: member {u!r} has no hp= "
                                    f"(the roster hp table is a member's ONLY "
                                    f"hit-point home)")
            if u in self._member:
                raise BehaviorError(f"group {name!r}: {u!r} is already in group "
                                    f"{self._member[u][0]!r}")
        for tname in (f"group.{name}.px", f"group.{name}.pz",
                      f"group.{name}.act", f"group.{name}.hp"):
            if tname in self.tables:
                raise BehaviorError(f"group {name!r}: table name {tname!r} is taken")
        zeros = (0,) * len(units)
        g = GroupSpec(name, units,
                      px_tid=self._alloc_tid(), pz_tid=self._alloc_tid(),
                      act_tid=self._alloc_tid(), hp_tid=self._alloc_tid())
        self.tables[f"group.{name}.px"] = (g.px_tid, zeros)
        self.tables[f"group.{name}.pz"] = (g.pz_tid, zeros)
        self.tables[f"group.{name}.act"] = (g.act_tid, zeros)
        self.tables[f"group.{name}.hp"] = (
            g.hp_tid, tuple(int(self.units[u].hp) for u in units))
        self._groups[name] = g
        for i, u in enumerate(units):
            self._member[u] = (name, i)
        return g

    def _hp_ref(self, unit: str) -> str:
        """The RPN fragment for a unit's hit points — a Global byte, or (for a
        roster member) its hp CELL: usable as read operand or B_LET target."""
        m = self._member.get(unit)
        if m is not None:
            g = self._groups[m[0]]
            return f"{_cnum(g.hp_tid)} {_cnum(m[1])} B_VECTOR"
        return f"Global.Byte[{self.bb.byte(f'{unit}.hp')}]"

    def engage_node(self, unit: str, e: Engage) -> Node:
        """Compile-side surface for the ``engage`` verb: registers the unit's
        acquire loop + target register and returns the two-phase subtree
        (contact -> the strike dispatch; else -> the pursue feed), built
        entirely from the standard node vocabulary."""
        if unit not in self.units:
            raise BehaviorError(f"engage: unknown unit {unit!r}")
        if e.group not in self._groups:
            raise BehaviorError(f"engage: unknown group {e.group!r} "
                                f"(declare it with group())")
        g = self._groups[e.group]
        if unit in g.units:
            raise BehaviorError(f"engage: {unit!r} cannot engage its OWN group "
                                f"{e.group!r}")
        if unit in self._engages:
            raise BehaviorError(f"engage: {unit!r} already has an engage "
                                f"(one target register per unit in v2 rung 1)")
        self._engages[unit] = e
        ctgt = self.bb.byte(f"{unit}.ctgt")
        pxc = f"{_cnum(g.px_tid)} Global.Byte[{ctgt}] B_VECTOR"
        pzc = f"{_cnum(g.pz_tid)} Global.Byte[{ctgt}] B_VECTOR"
        return Selector(
            Sequence(Cond(f"Global.Byte[{ctgt}] const(255) B_LT", _trusted=True),
                     Cond(_box(self._mx(unit), self._mz(unit), pxc, pzc,
                               int(e.contact)), _trusted=True),
                     Do(e._swing)),
            Sequence(Cond(f"Global.Byte[{ctgt}] const(255) B_LT", _trusted=True),
                     Do(e._pursue)),
        )

    def scan(self, name: str, units=None, point=None, radius: int | None = None,
             count: str = "", flags: str | None = None, group: str | None = None,
             alive_only: bool = False):
        """THE VECTOR LOOP (v2 rung 0 — the group-scan primitive): each run
        pass, copy the roster's position mirrors into px/pz tables (constant-
        index vector writes, the proven seed shape), then LOOP an index byte
        over the roster: write each unit's inside-the-box flag into the flags
        table BY THE LOOP VARIABLE (the computed-index WRITE), read it back and
        accumulate (the computed-index READ), and publish the total into
        counter ``count`` — trees gate on ``counter_ge`` as usual. The count is
        derived THROUGH the flag round-trip on purpose: a mis-indexed write or
        read breaks the number instead of passing silently.

        TWO FORMS. Units form (``units=`` + ``point``/``radius`` required): the
        scan owns px/pz tables and copies the mirrors in — the rung-0 shape;
        mirrors freeze on deactivation, so a dead unit still standing in the
        box keeps counting. Group form (``group=``): loop the GROUP'S OWN
        tables (no copies — the group mirror block owns them), ``point`` is
        OPTIONAL (absent = no box: a pure roster headcount), and
        ``alive_only=True`` gates every cell on act && hp>0 — the team-wipe /
        alive-count primitive (``counter_eq = ["mus_alive", 0]`` = wiped)."""
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name or ""):
            raise BehaviorError(f"scan name {name!r} must be [a-z][a-z0-9_]*")
        if any(s.name == name for s in self._scans):
            raise BehaviorError(f"scan {name!r} already registered")
        if (group is None) == (units is None):
            raise BehaviorError(f"scan {name!r}: give exactly one of units= / group=")
        if (point is None) != (radius is None):
            raise BehaviorError(f"scan {name!r}: point and radius come together")
        if flags is not None and point is None:
            raise BehaviorError(f"scan {name!r}: flags need a point/radius box "
                                f"(a boxless scan has no per-unit near result)")
        gspec = None
        if group is not None:
            if group not in self._groups:
                raise BehaviorError(f"scan {name!r}: unknown group {group!r}")
            gspec = self._groups[group]
            units = gspec.units
        else:
            if alive_only:
                raise BehaviorError(f"scan {name!r}: alive_only needs group= "
                                    f"(only a roster carries act/hp tables)")
            if point is None:
                raise BehaviorError(f"scan {name!r}: the units form needs "
                                    f"point/radius (rosterless headcounts are "
                                    f"static — use group=)")
            units = tuple(str(u) for u in units)
        if not units:
            raise BehaviorError(f"scan {name!r}: needs at least one unit")
        if len(units) > TABLE_MAX_LEN:
            raise BehaviorError(f"scan {name!r}: {len(units)} units > the "
                                f"{TABLE_MAX_LEN}-cell table cap")
        for u in units:
            if u not in self.units:
                raise BehaviorError(f"scan {name!r}: unknown unit {u!r}")
        if len(set(units)) != len(units):
            raise BehaviorError(f"scan {name!r}: duplicate units")
        if radius is not None and not 1 <= int(radius) <= 30000:
            raise BehaviorError(f"scan {name!r}: radius must be 1..30000")
        self._counter_ref(count)                          # existence check
        fname = flags if flags is not None else (f"scan.{name}.near" if point else None)
        own_tables = group is None
        check = ([f"scan.{name}.px", f"scan.{name}.pz"] if own_tables else [])
        if fname:
            check.append(fname)
        for tname in check:
            if tname in self.tables:
                raise BehaviorError(f"scan {name!r}: table name {tname!r} is taken")
        zeros = (0,) * len(units)
        sc = ScanSpec(name, tuple(units),
                      (int(point[0]), int(point[1])) if point else None,
                      int(radius) if radius is not None else None,
                      str(count), fname,
                      px_tid=(self._alloc_tid() if own_tables else gspec.px_tid),
                      pz_tid=(self._alloc_tid() if own_tables else gspec.pz_tid),
                      flag_tid=(self._alloc_tid() if fname else 0),
                      li=self.bb.byte(f"scan.{name}.i"),
                      acc=self.bb.byte(f"scan.{name}.n"),
                      group=group, alive_only=bool(alive_only),
                      act_tid=(gspec.act_tid if gspec else 0),
                      hp_tid=(gspec.hp_tid if gspec else 0))
        # registering the tables makes Main_Init seed them (size wipe + grow)
        # and, for the user-named flags table, exposes it to the table_* conds
        if own_tables:
            self.tables[f"scan.{name}.px"] = (sc.px_tid, zeros)
            self.tables[f"scan.{name}.pz"] = (sc.pz_tid, zeros)
        if fname:
            self.tables[fname] = (sc.flag_tid, zeros)
        self._scans.append(sc)
        return sc

    def _hud_ref(self, src: str) -> str:
        """Resolve a hud VALUE SOURCE to an RPN fragment: a counter name, the
        live ``gil`` / ``timer`` sysvars, ``hp:<unit>`` (a unit's hit points —
        the group cell for a roster member), or ``item:<id>`` (the live held
        count via ``B_HAVE_ITEM`` — the TOML lane resolves an item NAME to the
        id before registration)."""
        src = str(src)
        if src == "gil":
            return "B_SYSVAR[6]"
        if src == "timer":
            return "B_SYSVAR[17]"
        if src.startswith("item:"):
            try:
                iid = int(src[5:])
            except ValueError:
                raise BehaviorError(f"hud value {src!r}: item: takes a resolved item "
                                    f"ID (the TOML lane resolves names)")
            if not 0 <= iid <= 254:
                raise BehaviorError(f"hud value {src!r}: item id must be 0..254")
            return f"const({iid}) B_HAVE_ITEM"
        if src.startswith("hp:"):
            unit = src[3:]
            if unit not in self.units:
                raise BehaviorError(f"hud value {src!r}: unknown unit {unit!r}")
            if self.units[unit].hp is None and unit not in self._member:
                raise BehaviorError(f"hud value {src!r}: unit {unit!r} has no hp=")
            return self._hp_ref(unit)
        return self._counter_ref(src)                     # raises if unknown

    def hud(self, text: str, values, window: int = 6,
            txid: int | None = None, digits=2) -> HudSpec:
        """Register a live strip (see :class:`HudSpec`). ``values``: 1..8 value
        SOURCES — a counter name, ``"gil"``, ``"timer"``, or ``"hp:<unit>"`` —
        slot i driving ``[NUMB=i]`` in ``text``. The TOML lane wires the minted
        txid; Python callers pass one explicitly.

        ``digits``: the widest value a slot will ever show — one int for every
        slot, or a per-slot list (a gil readout wants 6, a headcount 2). The
        engine bakes a dialog's width ONCE, at open, from the text as it
        renders THEN (``Dialog.AutomaticSize``; a variable change only
        re-parses, never re-sizes), so a strip opened at "0" clips when a value
        reaches two digits (playtest 2). The open pass therefore feeds each
        slot a max-width sentinel (``10**digits - 1``) so the bake reserves
        room."""
        values = tuple(str(v) for v in values)
        if not 1 <= len(values) <= 8:
            raise BehaviorError("hud: 1..8 values (the engine has 8 gMesValue slots)")
        for v in values:
            self._hud_ref(v)                              # existence check
        digs = ((int(digits),) * len(values) if isinstance(digits, int)
                else tuple(int(d) for d in digits))
        if len(digs) != len(values):
            raise BehaviorError(f"hud: digits list has {len(digs)} entries for "
                                f"{len(values)} values")
        if any(not 1 <= d <= 7 for d in digs):
            raise BehaviorError("hud: digits must be 1..7 (the width reserve)")
        if not str(text).strip():
            raise BehaviorError("hud: text must be non-empty")
        for m in re.finditer(r"\[NUMB=(\d+)", str(text)):
            if int(m.group(1)) >= len(values):
                raise BehaviorError(f"hud: [NUMB={m.group(1)}] has no value "
                                    f"(only {len(values)} given)")
        if not 0 <= int(window) <= 7:
            raise BehaviorError("hud: window must be 0..7 (Dialog.WindowID)")
        if any(h.window == int(window) for h in self._huds):
            raise BehaviorError(f"hud: window {window} already carries a strip")
        h = HudSpec(str(text), values, int(window), txid, digs)
        self._huds.append(h)
        return h

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

    def _once_announce_map(self, u: UnitSpec, ids: dict) -> dict:
        """aid -> Once name for every ``Once`` whose subtree is a simple branch
        ending in an ``Announce`` or ``Award`` — THE EVENT ONCE (the BTTABLE
        round-2 law: a sticky Once over a MONOTONIC condition — a kill tally, a
        spent wave counter — holds the selection FOREVER and starves every
        branch below it). Over these one-shot actions, "once" means an EVENT:
        fire and release. The fire rides the same edge-latched request lane as
        Battle (a one-tick selection can be clobbered by a body still holding
        the level — the siege round-1 lesson), and the dispatch body sets the
        Once latch itself, so the branch releases the moment it delivers.
        An Award OUTSIDE a Once is refused — a payout must be exactly-once."""
        onced: dict = {}
        bare: set = set()
        bare_awards: set = set()

        def walk(n):
            if isinstance(n, (Selector, Sequence)):
                for c in n.children:
                    walk(c)
            elif isinstance(n, Cooldown):
                walk(n.child)
            elif isinstance(n, Once):
                leaf = _terminal_do(n.child)
                if leaf is not None and isinstance(leaf.action, (Announce, Award, ShopStock)):
                    aid = ids[id(leaf.action)]
                    if aid in onced and onced[aid] != n.name:
                        raise BehaviorError(
                            f"{u.name}: the same {type(leaf.action).__name__} object "
                            f"sits under two Once decorators ({onced[aid]!r}, "
                            f"{n.name!r}) — one latch cannot serve two gates; give "
                            f"each its own instance")
                    onced[aid] = n.name
                else:
                    walk(n.child)
            elif isinstance(n, Do) and isinstance(n.action, (Announce, Award, ShopStock)):
                bare.add(ids[id(n.action)])
                if isinstance(n.action, (Award, ShopStock)):
                    bare_awards.add(ids[id(n.action)])
        walk(u.tree)
        if bare_awards:
            raise BehaviorError(
                f"{u.name}: an Award / shop-stock action must be wrapped in Once "
                f"(exactly-once BY that machinery — a bare one would re-fire "
                f"every selection)")
        clash = set(onced) & bare
        if clash:
            raise BehaviorError(
                f"{u.name}: an Announce object is shared between a Once-wrapped site "
                f"and a bare site — give each site its own Announce instance")
        return onced

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
        disp_sizes: dict[str, list] = {}                 # unit -> [(tag, kind, bytes)]
        wu = self.bb.byte("warmup")
        # "__seg " labels are zero-width byte-histogram markers: they emit nothing
        # (byte-identity holds) and are never placed between an expression statement
        # and its conditional jump (the island-legality stance is untouched)
        ticker: list = [label("__seg head"), label("top"),
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
            label("__seg mirrors"),
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
        # THE TABLE SEED: size←0 wipes whatever the save holds (stale tails from an
        # older deploy included), size←n zero-fills fresh (the engine's grow path),
        # then only NON-zero cells need writes. Counters are all-zero by definition
        # — their table seeds in exactly two statements.
        for _tname, (tid, values) in self.tables.items():
            main_init += _stmt(f"{_cnum(tid)} B_VECTOR_SIZE const(0) B_LET")
            main_init += _stmt(f"{_cnum(tid)} B_VECTOR_SIZE {_cnum(len(values))} B_LET")
            for i, v in enumerate(values):
                if v:
                    main_init += _stmt(f"{_cnum(tid)} {_cnum(i)} B_VECTOR "
                                       f"{_cnum(v)} B_LET")
        if self._counters:
            main_init += _stmt(f"{_cnum(self._ctr_tid)} B_VECTOR_SIZE const(0) B_LET")
            main_init += _stmt(f"{_cnum(self._ctr_tid)} B_VECTOR_SIZE "
                               f"{_cnum(len(self._counters))} B_LET")
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
            if u.hp is not None and u.name not in self._member:
                # a roster member's ONLY hp home is its group cell (table-seeded)
                main_init += _set_byte(self.bb.byte(f"{u.name}.hp"), int(u.hp))
            if u.name in self._engages:
                # the target register: 255 = none (0 is a VALID roster index,
                # so this preset must never ride the zero-reset list)
                main_init += _set_byte(self.bb.byte(f"{u.name}.ctgt"), 255)
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
            once_ann = self._once_announce_map(u, ids)   # aid -> Once name (EVENT Once)
            funcs: list = []
            dispatch_tag: dict[int, int] = {}
            oneshot_latch: dict[int, int] = {}           # aid -> one-shot latch flag
            oneshot_req: dict[int, int] = {}             # aid -> EDGE-latched request
            for a in actions:
                aid = ids[id(a)]
                if a.feed or aid in dispatch_tag:        # same object in 2+ Do sites
                    continue
                tag = FIRST_ACTION_TAG + len(funcs)
                dispatch_tag[aid] = tag
                latch_arg = None
                if isinstance(a, Battle):
                    li = self.bb.flag(f"{u.name}.battled{aid}")
                    ri = self.bb.flag(f"{u.name}.breq{aid}")
                elif isinstance(a, (Announce, Award, ShopStock)) and aid in once_ann:
                    li = self.bb.flag(f"{u.name}.once.{once_ann[aid]}")
                    ri = self.bb.flag(f"{u.name}.areq{aid}")
                    latch_arg = li
                else:
                    li = ri = None
                if li is not None:
                    oneshot_latch[aid] = li
                    oneshot_req[aid] = ri
                    for fi in (li, ri):
                        if fi not in self._reset_flags:
                            self._reset_flags.append(fi)
                body = self._dispatch_body(u, a, aid, sel, run,
                                           oneshot_latch=latch_arg)
                funcs.append((tag, body))
                disp_sizes.setdefault(u.name, []).append(
                    (tag, f"{type(a).__name__}#{aid}", len(body)))
            # the SPEED NUDGE (always the last tag): MSPEED from the speed GLOB, then
            # record it applied. Straight-line at level 4 — preempts a mid-flight
            # blocked walk, which resumes at the new speed (actor.speed is re-read
            # every walk frame). Same running-protocol shape as action bodies.
            nudge_tag = FIRST_ACTION_TAG + len(funcs)
            nudge_body = asm([
                _set_byte(run, 255),
                opcodes.encode(0x26, exprasm.assemble(f"Global.Byte[{spd}] B_EXPR_END"),
                               arg_flags=0b1),
                _stmt(f"Global.Byte[{spdap}] Global.Byte[{spd}] B_LET"),
                _set_byte(run, 0),
                opcodes.RETURN,
            ])
            funcs.append((nudge_tag, nudge_body))
            disp_sizes.setdefault(u.name, []).append(
                (nudge_tag, "nudge", len(nudge_body)))
            action_funcs[u.name] = funcs

            ticker += [
                label(f"__seg unit {u.name}"),
                _stmt(f"Global.Bit[{act_flag}]"),
                (JMP_IFNOT, f"t_{u.name}_done"),
            ]
            if u.name in self._engages:
                ticker += self._acquire_block(u, self._engages[u.name])
            ticker += self._compile_tree(u, u.tree, ids, fail=f"t_{u.name}_fellthrough")
            ticker += [
                label(f"t_{u.name}_fellthrough"),        # unreachable (fallback is
                label(f"t_{u.name}_selected"),           # unconditional) — lint safety
            ]
            # THE ONE-SHOT REQUEST LANE runs FIRST and is EDGE-LATCHED: a Battle (or
            # event-Once Announce) branch is typically outranked or released ONE
            # TICK after it selects (its own raise_flags — e.g. "lost" — promotes an
            # aftermath branch above it), and if another body still holds `running`
            # during that single tick the sel-gated dispatch never fires (the siege
            # round-1 clobber: the gatecry announce ate the window). So selection
            # SETS the request flag, and the dispatch fires on req && !latch &&
            # running==0 whenever level 4 frees — independent of what the tree
            # selects meanwhile. A successful REQ jumps past the rest of the tail
            # (one REQ per unit per tick, still by construction).
            disp_end = f"t_{u.name}_dend"
            for aid, ri in oneshot_req.items():
                bl = f"t_{u.name}_b{aid}"
                ticker += [
                    _stmt(f"Global.Bit[{ri}]"), (JMP_IFNOT, bl),
                    _stmt(f"Global.Bit[{oneshot_latch[aid]}]"), (JMP_IF, bl),
                    _stmt(f"Global.Byte[{run}] const(0) B_EQ"), (JMP_IFNOT, bl),
                    opcodes.run_script_async(DISPATCH_LEVEL, u.entry, dispatch_tag[aid]),
                    (JMP, disp_end),
                    label(bl),
                ]
            for aid, tag in dispatch_tag.items():        # the normal sel-gated tail
                if aid in oneshot_req:                   # one-shots ride the request lane
                    continue
                ticker += [
                    _stmt(f"Global.Byte[{sel}] const({aid}) B_EQ"),
                    (JMP_IFNOT, f"t_{u.name}_d{aid}"),
                    _stmt(f"Global.Byte[{run}] const(0) B_EQ"),
                    (JMP_IFNOT, f"t_{u.name}_d{aid}"),
                    opcodes.run_script_async(DISPATCH_LEVEL, u.entry, tag),
                    label(f"t_{u.name}_d{aid}"),
                ]
            ticker += [label(disp_end)]
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
        cd_blocks: list = [label("__seg clocks")]
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
        # schedule clocks (the wave engine): counter += 1 while the countdown HUD
        # sits below table[counter] — the read's INDEX is the counter cell itself,
        # the computed-array-indexing lane doing the work it was taken for. Runs on
        # the run path only (holds during warm-up, like every cd block).
        for si, (cname, tname) in enumerate(self._schedules):
            cell = self._counter_ref(cname)
            cd_blocks += [
                _stmt(f"B_SYSVAR[17] {self._table_ref(tname, cname)} B_LT"),
                (JMP_IFNOT, f"sch_{si}"),
                _stmt(f"{cell} {cell} const(1) B_PLUS B_LET"),
                label(f"sch_{si}"),
            ]
        # GROUP MIRRORS first (scans in group form read them same-pass): px/pz/
        # act into the roster tables once per group per pass — the same
        # constant-index write shape as the scan copies. hp needs no mirror:
        # the cells ARE the home.
        for g in self._groups.values():
            cd_blocks.append(label(f"__seg group {g.name}"))
            for i, un in enumerate(g.units):
                mx = self.bb.int16(f"{un}.mx")
                mz = self.bb.int16(f"{un}.mz")
                act = self.bb.flag(f"{un}.active")
                cd_blocks += [
                    _stmt(f"{_cnum(g.px_tid)} {_cnum(i)} B_VECTOR "
                          f"Global.Int16[{mx}] B_LET"),
                    _stmt(f"{_cnum(g.pz_tid)} {_cnum(i)} B_VECTOR "
                          f"Global.Int16[{mz}] B_LET"),
                    _stmt(f"{_cnum(g.act_tid)} {_cnum(i)} B_VECTOR "
                          f"Global.Bit[{act}] B_LET"),
                ]
        # THE VECTOR LOOPS (scan): a bounded backward-jump loop whose reads AND
        # writes index cells by the LIVE loop byte — the v2 rung-0 composition,
        # in-game proven. The per-cell TEST composes from the enabled parts
        # (alive gates and/or the Chebyshev box) into ONE jumpless statement.
        # Pure table/GLOB math (the player-ref eval law never enters); the loop
        # bound is a compile-time constant (always terminates).
        for sc in self._scans:
            n = len(sc.units)
            cd_blocks.append(label(f"__seg scan {sc.name}"))
            if sc.group is None:                     # units form: own copies
                for i, un in enumerate(sc.units):
                    mx = self.bb.int16(f"{un}.mx")
                    mz = self.bb.int16(f"{un}.mz")
                    cd_blocks.append(_stmt(f"{_cnum(sc.px_tid)} {_cnum(i)} B_VECTOR "
                                           f"Global.Int16[{mx}] B_LET"))
                    cd_blocks.append(_stmt(f"{_cnum(sc.pz_tid)} {_cnum(i)} B_VECTOR "
                                           f"Global.Int16[{mz}] B_LET"))
            parts = []
            if sc.alive_only:
                parts.append(f"{_cnum(sc.act_tid)} Global.Byte[{sc.li}] B_VECTOR "
                             f"const(1) B_EQ")
                parts.append(f"{_cnum(sc.hp_tid)} Global.Byte[{sc.li}] B_VECTOR "
                             f"const(0) B_GT")
            if sc.point is not None:
                px = f"{_cnum(sc.px_tid)} Global.Byte[{sc.li}] B_VECTOR"
                pz = f"{_cnum(sc.pz_tid)} Global.Byte[{sc.li}] B_VECTOR"
                x, z, r = sc.point[0], sc.point[1], sc.radius
                parts.append(f"{px} {_cnum(x - r)} B_GT {px} {_cnum(x + r)} B_LT "
                             f"B_ANDAND {pz} {_cnum(z - r)} B_GT B_ANDAND "
                             f"{pz} {_cnum(z + r)} B_LT B_ANDAND")
            test = (parts[0] + "".join(f" {p} B_ANDAND" for p in parts[1:])
                    if parts else "const(1)")
            if sc.flags:
                body = [_stmt(f"{_cnum(sc.flag_tid)} Global.Byte[{sc.li}] B_VECTOR "
                              f"{test} B_LET"),
                        _stmt(f"Global.Byte[{sc.acc}] Global.Byte[{sc.acc}] "
                              f"{_cnum(sc.flag_tid)} Global.Byte[{sc.li}] B_VECTOR "
                              f"B_PLUS B_LET")]
            else:
                body = [_stmt(f"Global.Byte[{sc.acc}] Global.Byte[{sc.acc}] "
                              f"{test} B_PLUS B_LET")]
            cd_blocks += ([_set_byte(sc.li, 0), _set_byte(sc.acc, 0),
                           label(f"scn_{sc.name}_top")]
                          + body
                          + [_stmt(f"Global.Byte[{sc.li}] Global.Byte[{sc.li}] "
                                   f"const(1) B_PLUS B_LET"),
                             _stmt(f"Global.Byte[{sc.li}] const({n}) B_LT"),
                             (JMP_IF, f"scn_{sc.name}_top"),
                             _stmt(f"{self._counter_ref(sc.count)} "
                                   f"Global.Byte[{sc.acc}] B_LET")])
        # ITEM SNAPSHOTS first — every have_item cond reads its item's count as it
        # stood BEFORE any pool consumed this pass (the perception law for
        # inventory; the ARMOURY round-2 skew: activation ran first and ate one
        # contract, so a live `have_item >= 3` needed FOUR held)
        if self._item_mirrors:
            cd_blocks.append(label("__seg item mirrors"))
            for iid, m in sorted(self._item_mirrors.items()):
                cd_blocks.append(_stmt(f"Global.Byte[{m}] const({iid}) "
                                       f"B_HAVE_ITEM B_LET"))
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
            price = getattr(self.pool_specs.get(pname), "price", None)
            item = getattr(self.pool_specs.get(pname), "item", None)
            if item is not None:
                # THE ITEM POOL: no request flag — holding a contract IS the request.
                # Polled every run pass; one convert per tick (natural stagger), and
                # RemoveItem sits at the SPAWN site so an exhausted pool consumes
                # NOTHING (contracts are real inventory, keep them honest).
                cd_blocks += [label(f"__seg pool {pname}"),
                              _stmt(f"const({int(item)}) B_HAVE_ITEM const(0) B_GT"),
                              (JMP_IFNOT, f"pl_{pname}_end")]
            else:
                req = self.pool_flags[pname]
                cd_blocks += [label(f"__seg pool {pname}"),
                              _stmt(f"Global.Bit[{req}]"), (JMP_IFNOT, f"pl_{pname}_end")]
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
                ] + ([opcodes.remove_gil(int(price))] if price else []) \
                  + ([opcodes.remove_item(int(item), 1)] if item is not None else []) + [
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
            if item is not None:
                cd_blocks += [label(f"pl_{pname}_done"),  # exhausted: keep the contracts
                              label(f"pl_{pname}_end")]
            else:
                cd_blocks += [label(f"pl_{pname}_done"),  # exhausted pool falls through
                              _set_flag(req, 0),          # here too: consume the request
                              label(f"pl_{pname}_end")]
        # hireable refresh — AFTER the activation blocks, so the tick that spawns a
        # pool's last unit flips it un-hireable the same pass
        if self._pools:
            cd_blocks.append(label("__seg hireable"))
        for pname, unames in self._pools.items():
            hidx = self.pool_hireable[pname]
            price = getattr(self.pool_specs.get(pname), "price", None)
            item = getattr(self.pool_specs.get(pname), "item", None)
            if item is not None:
                afford = f"const({int(item)}) B_HAVE_ITEM const(0) B_GT"
            else:
                afford = f"B_SYSVAR[6] {_cnum(int(price))} B_GE" if price else "const(1)"
            sp = [f"Global.Bit[{self.bb.flag(f'{un}.spawned')}]" for un in unames]
            allsp = sp[0] + "".join(f" {s} B_ANDAND" for s in sp[1:])
            cd_blocks.append(_stmt(f"Global.Bit[{hidx}] {afford} {allsp} B_NOT "
                                   f"B_ANDAND B_LET"))
        # HUD STRIPS last (freshest counters — the scans above already ran this
        # pass). THE WINDOW OPENS EXACTLY ONCE (the `shown` latch): the engine
        # re-renders a live dialog's [NUMB] variables in place every frame they
        # change (Dialog.Update -> UpdateMessageValue, CompleteAnimation +
        # HasMessageValueChanged), so a running strip only needs its variables
        # written. RE-ISSUING WindowAsync would DISPOSE and recreate the window
        # (ETb.DisposWindowByID) — its open animation replaying on every change
        # is exactly the flicker the first build showed. Dirty-mirror gating
        # stays: it keeps the writes (and the engine's re-parse) off the quiet
        # frames.
        for hi, h in enumerate(self._huds):
            if h.txid is None:
                raise BehaviorError(
                    f"hud #{hi}: no txid — the TOML build mints the .mes line "
                    f"(collect_text); Python callers must pass txid=")
            shown = self.bb.flag(f"hud{hi}.shown")
            if shown not in self._reset_flags:            # ~ Reload re-opens it
                self._reset_flags.append(shown)
            cd_blocks.append(label(f"__seg hud {hi}"))
            # THE OPEN PASS (once): feed each slot its max-width SENTINEL so
            # AutomaticSize bakes a strip wide enough for the widest value that
            # slot will ever show, then open. The values land on the next pass.
            cd_blocks += [_stmt(f"Global.Bit[{shown}]"), (JMP_IF, f"hud_{hi}_live")]
            for i, d in enumerate(h.digits):
                cd_blocks.append(opcodes.encode(0x66, i, 10 ** int(d) - 1))
            cd_blocks += [
                opcodes.window_async(h.window, 16, int(h.txid)),
                _set_flag(shown, 1),
                (JMP, f"hud_{hi}_skip"),
                label(f"hud_{hi}_live"),
            ]
            # THE LIVE PASS: write every slot from its source, unconditionally.
            # No dirty mirrors: the ENGINE already re-renders only when a value
            # actually changed (HasMessageValueChanged), a gMesValue write is a
            # bare array store, and a mirror would cap a gil readout at Int16.
            for i, v in enumerate(h.values):
                cd_blocks.append(opcodes.encode(
                    0x66, i,
                    exprasm.assemble(f"{self._hud_ref(v)} B_EXPR_END"),
                    arg_flags=0b10))
            cd_blocks.append(label(f"hud_{hi}_skip"))
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
        for pname in self._pools:                         # hireable: optimistic preset,
            main_init += _set_flag(self.pool_hireable[pname], 1)   # first pass corrects

        ticker += [label("__seg tail"), label("wait"), opcodes.wait(self.tick),
                   (JMP, "top"), opcodes.RETURN]
        pools_txt = ""
        if self._pools:
            def _pdesc(p):
                ps = self.pool_specs.get(p)
                extra = ""
                if ps is not None and ps.price:
                    extra += f", price {ps.price} gil"
                if ps is not None and ps.button is not None:
                    extra += f", hire button mask 0x{ps.button:X}"
                if ps is not None and ps.item is not None:
                    label = ps.item_name or f"item {ps.item}"
                    return (f"  {p}: ITEM POOL (one {label} converts to one spawn per "
                            f"tick), hireable flag {self.pool_hireable[p]}{extra}, "
                            f"units [{', '.join(self._pools[p])}]")
                return (f"  {p}: spawn-request flag {self.pool_flags[p]}, hireable "
                        f"flag {self.pool_hireable[p]}{extra}, "
                        f"units [{', '.join(self._pools[p])}]")
            pools_txt = "\npools (set the spawn flag from a [[choice]] row to activate):\n" \
                + "\n".join(_pdesc(p) for p in self._pools)
        tables_txt = ""
        if self.tables or self._counters:
            tl = ["tables (gScriptVector ids — re-seeded every field entry):"]
            for tname, (tid, values) in self.tables.items():
                tl.append(f"  {tname}: id {tid}, {len(values)} cell(s) = {list(values)}")
            if self._counters:
                tl.append(f"  counters: id {self._ctr_tid} — " + ", ".join(
                    f"{n}=cell {i}" for n, i in self._counters.items()))
            for cname, tname in self._schedules:
                tl.append(f"  schedule: {cname} += 1 while timer < {tname}[{cname}]")
            for sc in self._scans:
                src = f"group '{sc.group}'" if sc.group else f"px={sc.px_tid} pz={sc.pz_tid}"
                box = (f"box ({sc.point[0]},{sc.point[1]}) r={sc.radius}"
                       if sc.point else "no box (headcount)")
                extra = (" ALIVE-ONLY" if sc.alive_only else "") + (
                    f"; near={sc.flag_tid} ('{sc.flags}')" if sc.flags else "")
                tl.append(f"  scan {sc.name}: {len(sc.units)} unit(s) -> counter "
                          f"'{sc.count}' (acc byte {sc.acc}, loop byte {sc.li}); "
                          f"{box}; {src}{extra}")
            for g in self._groups.values():
                tl.append(f"  group {g.name}: [{', '.join(g.units)}] — tables "
                          f"px={g.px_tid} pz={g.pz_tid} act={g.act_tid} "
                          f"hp={g.hp_tid} (hp cells ARE the members' hit points)")
            for un, e in self._engages.items():
                tl.append(f"  engage {un} -> group '{e.group}': target register "
                          f"byte {self.bb.byte(f'{un}.ctgt')} (255=none, watch in "
                          f"~ Flags), r={e.radius} contact={e.contact} "
                          f"dmg={e.damage} ivl={e.interval}"
                          + (" NEAREST" if e.nearest else ""))
            for hi, h in enumerate(self._huds):
                tl.append(f"  hud #{hi}: window {h.window}, txid {h.txid}, values "
                          + ", ".join(f"[NUMB={i}]='{v}'({d}d)"
                                      for i, (v, d) in enumerate(zip(h.values,
                                                                     h.digits))))
            tables_txt = "\n" + "\n".join(tl)
        # the byte histogram: segment sizes from the PRE-relaxation measure (the
        # content bytes; the asm() length difference is pure island overhead)
        _slabels, _, _stotal = _measure(ticker)
        _marks = [(n[len("__seg "):], p) for n, p in _slabels.items()
                  if n.startswith("__seg ")]
        ticker_segments = []
        for i, (nm, p) in enumerate(_marks):
            end = _marks[i + 1][1] if i + 1 < len(_marks) else _stotal
            if end - p:
                ticker_segments.append((nm, end - p))
        return CompiledBehavior(
            ticker_body=asm(ticker),
            duty_bodies=duty_bodies,
            action_funcs=action_funcs,
            main_init=bytes(main_init),
            report=self.bb.report() + "\nunits:\n" + "\n".join(report) + pools_txt
            + tables_txt,
            sizes={"ticker_content": _stotal,
                   "ticker_segments": ticker_segments,
                   "duty": {n: len(b) for n, b in duty_bodies.items()},
                   "dispatch": disp_sizes,
                   "main_init": len(main_init)},
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
            leaf = _terminal_do(node.child)
            if leaf is not None and isinstance(leaf.action, (Announce, Award, ShopStock)):
                # THE EVENT ONCE (BTTABLE round-2 law): over an Announce/Award,
                # "once" means fire-and-release — the sticky form over a MONOTONIC
                # cond (a kill tally, a spent wave counter) would hold the selection
                # forever and STARVE every branch below it. Selection edge-latches
                # the request; the one-shot lane fires it when the level frees;
                # the dispatch body sets THIS latch itself, releasing the branch.
                aid = ids[id(leaf.action)]
                latch = self.bb.flag(f"{u.name}.once.{node.name}")
                req = self.bb.flag(f"{u.name}.areq{aid}")
                extra = (on_select or []) + [_set_flag(req, 1)]
                return ([_stmt(f"Global.Bit[{latch}]"), (JMP_IF, fail)]
                        + self._compile_tree(u, node.child, ids, fail, _ctr, extra))
            # STICKY semantics (rung-1 design fix), for FEED behaviors: a reactive
            # ticker re-selects every tick, so a select-time latch would fire for
            # ONE tick. Instead: selecting the child ENGAGES; while engaged the gate
            # is bypassed (the child's own conditions keep deciding); the first
            # child-FAIL while engaged disengages and latches — "chase me while I'm
            # near, never again once I escape".
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
            if isinstance(node.action, Battle):
                # EDGE-LATCH the request at selection — the branch may be outranked
                # next tick by its own raise_flags (the siege round-1 clobber); the
                # dispatch tail's request lane fires it when level 4 frees
                out.append(_set_flag(self.bb.flag(f"{u.name}.breq{aid}"), 1))
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

    def _acquire_block(self, u: UnitSpec, e: Engage) -> list:
        """THE ACQUIRE LOOP (per engage unit, inside its active gate, before the
        tree): keep a STILL-VALID target (alive, active, within radius — the
        sticky fast path most ticks take), else scan the roster FIRST-IN-RANGE
        in roster order (v1 pair-branch parity: roster order is the priority
        list). All reads index the group tables by a live byte — the rung-0
        composition doing per-unit perception."""
        g = self._groups[e.group]
        n = len(g.units)
        ctgt = self.bb.byte(f"{u.name}.ctgt")
        li = self.bb.byte(f"{u.name}.gscan")
        pxc = f"{_cnum(g.px_tid)} Global.Byte[{ctgt}] B_VECTOR"
        pzc = f"{_cnum(g.pz_tid)} Global.Byte[{ctgt}] B_VECTOR"
        pxl = f"{_cnum(g.px_tid)} Global.Byte[{li}] B_VECTOR"
        pzl = f"{_cnum(g.pz_tid)} Global.Byte[{li}] B_VECTOR"
        A = f"t_{u.name}_aq"
        return [
            _stmt(f"Global.Byte[{ctgt}] const(255) B_LT"), (JMP_IFNOT, f"{A}_scan"),
            _stmt(f"{_cnum(g.act_tid)} Global.Byte[{ctgt}] B_VECTOR const(1) B_EQ"),
            (JMP_IFNOT, f"{A}_drop"),
            _stmt(f"{_cnum(g.hp_tid)} Global.Byte[{ctgt}] B_VECTOR const(0) B_GT"),
            (JMP_IFNOT, f"{A}_drop"),
            _stmt(_box(self._mx(u.name), self._mz(u.name), pxc, pzc, int(e.radius))),
            (JMP_IF, f"{A}_end"),
            label(f"{A}_drop"),
            _set_byte(ctgt, 255),
            label(f"{A}_scan"),
        ] + (self._acquire_scan_nearest(u, e, g, n, ctgt, li, pxl, pzl, A)
             if e.nearest else [
            _set_byte(li, 0),
            label(f"{A}_top"),
            _stmt(f"{_cnum(g.act_tid)} Global.Byte[{li}] B_VECTOR const(1) B_EQ"),
            (JMP_IFNOT, f"{A}_nxt"),
            _stmt(f"{_cnum(g.hp_tid)} Global.Byte[{li}] B_VECTOR const(0) B_GT"),
            (JMP_IFNOT, f"{A}_nxt"),
            _stmt(_box(self._mx(u.name), self._mz(u.name), pxl, pzl, int(e.radius))),
            (JMP_IFNOT, f"{A}_nxt"),
            _stmt(f"Global.Byte[{ctgt}] Global.Byte[{li}] B_LET"),
            (JMP, f"{A}_end"),
            label(f"{A}_nxt"),
            _stmt(f"Global.Byte[{li}] Global.Byte[{li}] const(1) B_PLUS B_LET"),
            _stmt(f"Global.Byte[{li}] const({n}) B_LT"),
            (JMP_IF, f"{A}_top"),
            _set_byte(ctgt, 255),
        ]) + [
            label(f"{A}_end"),
        ]

    def _acquire_scan_nearest(self, u: UnitSpec, e: Engage, g: GroupSpec, n: int,
                              ctgt: int, li: int, pxl: str, pzl: str, A: str) -> list:
        """The argmin scan (``nearest=True``): track the smallest Chebyshev
        distance ≤ radius over the roster and take its index. Scratch is
        SHARED across every nearest engage (the ticker is sequential — one
        dx/dz/best/idx set serves all units, band-cheap). |d| via conditional
        negate (RPN has no abs); max(dx,dz) via conditional copy — the same
        no-squares Int24 stance as every kit distance."""
        s = getattr(self, "_nscratch", None)
        if s is None:
            s = self._nscratch = {
                "dx": self.bb.int16("engage.scratch.dx"),
                "dz": self.bb.int16("engage.scratch.dz"),
                "best": self.bb.int16("engage.scratch.best"),
                "idx": self.bb.byte("engage.scratch.idx"),
            }
        dx, dz, best, idx = s["dx"], s["dz"], s["best"], s["idx"]
        return [
            _set_byte(li, 0),
            _set_int16(best, int(e.radius) + 1),
            _set_byte(idx, 255),
            label(f"{A}_ntop"),
            _stmt(f"{_cnum(g.act_tid)} Global.Byte[{li}] B_VECTOR const(1) B_EQ"),
            (JMP_IFNOT, f"{A}_nnxt"),
            _stmt(f"{_cnum(g.hp_tid)} Global.Byte[{li}] B_VECTOR const(0) B_GT"),
            (JMP_IFNOT, f"{A}_nnxt"),
            _stmt(f"Global.Int16[{dx}] {pxl} {self._mx(u.name)} B_MINUS B_LET"),
            _stmt(f"Global.Int16[{dx}] const(0) B_LT"),
            (JMP_IFNOT, f"{A}_nax"),
            _stmt(f"Global.Int16[{dx}] const(0) Global.Int16[{dx}] B_MINUS B_LET"),
            label(f"{A}_nax"),
            _stmt(f"Global.Int16[{dz}] {pzl} {self._mz(u.name)} B_MINUS B_LET"),
            _stmt(f"Global.Int16[{dz}] const(0) B_LT"),
            (JMP_IFNOT, f"{A}_naz"),
            _stmt(f"Global.Int16[{dz}] const(0) Global.Int16[{dz}] B_MINUS B_LET"),
            label(f"{A}_naz"),
            _stmt(f"Global.Int16[{dx}] Global.Int16[{dz}] B_LT"),
            (JMP_IFNOT, f"{A}_nmx"),
            _stmt(f"Global.Int16[{dx}] Global.Int16[{dz}] B_LET"),
            label(f"{A}_nmx"),                        # dx = Chebyshev distance
            _stmt(f"Global.Int16[{dx}] Global.Int16[{best}] B_LT"),
            (JMP_IFNOT, f"{A}_nnxt"),
            _stmt(f"Global.Int16[{best}] Global.Int16[{dx}] B_LET"),
            _stmt(f"Global.Byte[{idx}] Global.Byte[{li}] B_LET"),
            label(f"{A}_nnxt"),
            _stmt(f"Global.Byte[{li}] Global.Byte[{li}] const(1) B_PLUS B_LET"),
            _stmt(f"Global.Byte[{li}] const({n}) B_LT"),
            (JMP_IF, f"{A}_ntop"),
            _stmt(f"Global.Byte[{ctgt}] Global.Byte[{idx}] B_LET"),
        ]

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
        if isinstance(a, _GroupPursue):
            e = a.engage
            g = self._groups[e.group]
            ctgt = self.bb.byte(f"{u.name}.ctgt")
            pxc = f"{_cnum(g.px_tid)} Global.Byte[{ctgt}] B_VECTOR"
            pzc = f"{_cnum(g.pz_tid)} Global.Byte[{ctgt}] B_VECTOR"
            self._label_ctr += 1
            L = f"t_{u.name}_gp{self._label_ctr}"
            # walk toward the target's TABLE position (live retarget — the
            # mirrors refresh the cells each pass). In contact the swing branch
            # outranks this one, and its dispatch-halt feeds the own mirror, so
            # no standoff clause is needed here. Belt: no target -> hold ground
            # (the engage subtree's valid-cond makes this unreachable).
            return [_stmt(f"Global.Byte[{ctgt}] const(255) B_LT"),
                    (JMP_IFNOT, f"{L}_own"),
                    _stmt(f"Global.Int16[{tx}] {pxc} B_LET"),
                    _stmt(f"Global.Int16[{tz}] {pzc} B_LET"),
                    (JMP, f"{L}_end"),
                    label(f"{L}_own"),
                    _stmt(f"Global.Int16[{tx}] {self._mx(u.name)} B_LET"),
                    _stmt(f"Global.Int16[{tz}] {self._mz(u.name)} B_LET"),
                    label(f"{L}_end")]
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

    def _dispatch_body(self, u: UnitSpec, a: Action, aid: int, sel: int, run: int,
                       oneshot_latch: int | None = None) -> bytes:
        head: list = [_set_byte(run, aid), label("loop"),
                      _stmt(f"Global.Byte[{sel}] const({aid}) B_EQ"),
                      (JMP_IFNOT, "out")]
        tail: list = [label("wait"), opcodes.wait(1), (JMP, "loop"),
                      label("out"), _set_byte(run, 0), opcodes.RETURN]
        if isinstance(a, Die):
            bump: list = []
            if a.count is not None:
                # the body runs once ever (the entry terminates) — edge-safe free
                cell = self._counter_ref(a.count)
                bump = [_stmt(f"{cell} {cell} const(1) B_PLUS B_LET")]
            return asm([
                _set_flag(self.bb.flag(f"{u.name}.active"), 0),   # mirrors stop first
            ] + bump + [
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
        if isinstance(a, HoldGround):
            return asm(head + tail)                       # pure pin: idle while selected
        if isinstance(a, Award):
            if oneshot_latch is None:                     # unreachable (the map
                raise BehaviorError(                      # refused it) — belt+braces
                    f"{u.name}: Award must be Once-wrapped")
            from . import event as _event
            pay: list = []
            if int(a.gil):
                pay.append(opcodes.add_gil(int(a.gil)))
            if a.item is not None:
                pay.append(_event.give_item(a.item, int(a.count)))
            return asm([
                _set_flag(oneshot_latch, 1),              # latch FIRST — pay once ever
                _set_byte(run, 255),
            ] + pay + [
                _set_byte(run, 0),
                opcodes.RETURN,
            ])
        if isinstance(a, ShopStock):
            if oneshot_latch is None:
                raise BehaviorError(
                    f"{u.name}: add/remove_shop_item must be Once-wrapped")
            from .. import items as _items
            iid = _items.resolve(a.item)
            ops = [opcodes.encode(0x115, int(a.shop), iid, 0)]   # remove first —
            if a.add:                                            # List.Add dupes,
                ops.append(opcodes.encode(0x115, int(a.shop), iid, 1))  # so idempotent
            return asm([
                _set_flag(oneshot_latch, 1),              # latch FIRST (Battle's shape)
                _set_byte(run, 255),
            ] + ops + [
                _set_byte(run, 0),
                opcodes.RETURN,
            ])
        if isinstance(a, Announce):
            if oneshot_latch is not None:
                # the EVENT-Once variant: latch FIRST (Battle's one-shot shape —
                # a re-request can never re-fire), show the window (async — it
                # persists on screen without a body idling), release the level.
                return asm([
                    _set_flag(oneshot_latch, 1),
                    _set_byte(run, 255),
                    opcodes.window_async(a.window, 128, int(a.txid)),
                    _set_byte(run, 0),
                    opcodes.RETURN,
                ])
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
            t_hp = self._hp_ref(a.target)      # Global byte, or a roster hp CELL
            t_act = self.bb.flag(f"{a.target}.active")
            timer = self.bb.byte(f"{u.name}.swing{aid}")
            if timer not in self._reset_bytes:
                self._reset_bytes.append(timer)
            work: list = [
                _stmt(f"Global.Bit[{t_act}]"), (JMP_IFNOT, "out"),
                _stmt(f"{t_hp} const(0) B_GT"), (JMP_IFNOT, "out"),
                _stmt(f"Global.Byte[{timer}] Global.Byte[{timer}] const(1) B_PLUS B_LET"),
                _stmt(f"Global.Byte[{timer}] const({a.interval}) B_LT"),
                (JMP_IF, "wait"),
                _set_byte(timer, 0),
                opcodes.turn_toward_object(self.units[a.target].entry, 16),
                _stmt(f"{t_hp} {t_hp} const({a.damage}) B_MINUS B_LET"),
            ]
            return asm(head + work + tail)
        if isinstance(a, _GroupSwing):
            e = a.engage
            g = self._groups[e.group]
            ctgt = self.bb.byte(f"{u.name}.ctgt")
            timer = self.bb.byte(f"{u.name}.gswing")
            if timer not in self._reset_bytes:
                self._reset_bytes.append(timer)
            actc = f"{_cnum(g.act_tid)} Global.Byte[{ctgt}] B_VECTOR"
            hpc = f"{_cnum(g.hp_tid)} Global.Byte[{ctgt}] B_VECTOR"
            pxc = f"{_cnum(g.px_tid)} Global.Byte[{ctgt}] B_VECTOR"
            pzc = f"{_cnum(g.pz_tid)} Global.Byte[{ctgt}] B_VECTOR"
            # the SwingAt body generalized by the target REGISTER: every read
            # and the damage write index the roster tables through ctgt. Facing
            # is TurnTowardPosition on the target's TABLE position — pure data,
            # no uid, the player-ref law never enters.
            work = [
                _stmt(f"Global.Byte[{ctgt}] const(255) B_LT"), (JMP_IFNOT, "out"),
                _stmt(f"{actc} const(1) B_EQ"), (JMP_IFNOT, "out"),
                _stmt(f"{hpc} const(0) B_GT"), (JMP_IFNOT, "out"),
                _stmt(f"Global.Byte[{timer}] Global.Byte[{timer}] const(1) B_PLUS B_LET"),
                _stmt(f"Global.Byte[{timer}] const({e.interval}) B_LT"),
                (JMP_IF, "wait"),
                _set_byte(timer, 0),
                opcodes.encode(0x9B,
                               exprasm.assemble(f"{pxc} B_EXPR_END"),
                               exprasm.assemble(f"{pzc} B_EXPR_END"),
                               arg_flags=0b11),
                _stmt(f"{hpc} {hpc} const({e.damage}) B_MINUS B_LET"),
            ]
            return asm(head + work + tail)
        raise BehaviorError(f"no dispatch body for {type(a).__name__}")
