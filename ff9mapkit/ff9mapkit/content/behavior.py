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
from dataclasses import dataclass, field as _dc_field

from ..eb import exprasm, opcodes
from ..eb.labelasm import JMP, JMP_IF, JMP_IFNOT, _measure, asm, label
from ..flags import (BEHAVIOR_BYTE_BASE, BEHAVIOR_BYTE_END, BEHAVIOR_FLAG_BASE,
                     BEHAVIOR_FLAG_END, NAMEPLATE_EXPLORED_FLOOR)
from .chest import RUN_SOUND_CODE3, SFX_BANK, SFX_PARAMS   # the in-game-proven SFX triple (chest owns it)

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
# The byte band's ceiling (flags.BEHAVIOR_BYTE_END, byte 1989): below the UNRESERVED
# modal-result home (bytes 1990-2005, the [[qte]]/[[numeric_input]] `result` landing),
# which itself sits flush below the reserved top of the gEventGlobal heap -- the
# nameplate explored words (NAMEPLATE_EXPLORED_FLOOR, save-persistent), then the
# [[qte]] scratch, the netsync co-op cells (engine-written every frame under co-op),
# and the choice mask. flags.BIT_REGIONS is the truth; a byte past this line is live state.
BYTE_END_DEFAULT = BEHAVIOR_BYTE_END                        # byte 1989

# The WIDE standalone band: the historical bytes 1220-1989 (770 bytes) for content the campaign-safe
# default can't hold (condor-scale sieges, 40-unit swarms). It OVERLAPS the campaign per-member flag
# windows (members ~65+ of a FIRST_SAFE_FLAG-based campaign): a wide-band field's Main_Init clears
# its allocations there, wiping those members' once-flags -- NEVER deploy wide-band behavior content
# onto a save that also plays a campaign. Opt in via [behavior] byte_band = "wide" (behaviortoml) or
# Blackboard(byte_base=WIDE_BYTE_BASE); [siege] generates the wide band (it cannot fit otherwise).
# The wide band carries its own FLAG window too, seated DIRECTLY BELOW the byte band (bytes
# 1190-1219 = bits 9520-9759, 240 flags): the safe partition's 96-flag Blackboard window is boxed
# in by the siege-request and kit-world sub-bands and cannot grow, and a condor-scale siege's
# event-once latch+request lanes exhaust it (the shipped REDOUBT needs ~120 under the v1 ticker).
# The window sits in the campaign lane exactly as the byte band itself does — the SAME
# standalone-only contract covers both — and the byte band keeps its full measured 770 bytes
# (the 40-unit swarm wall is pinned by test at that width).
WIDE_FLAG_BASE = 9520                # bit of byte 1190
WIDE_FLAG_END = 9759                 # 240 flags, flush under the byte band
WIDE_BYTE_BASE = 1220


class Blackboard:
    """Named GLOB allocation over the safe band — compiled, never hand-assigned.

    Defaults live in the KIT-STANDING LANE of the safe-band partition (``flags.py``:
    flags ``BEHAVIOR_FLAG_BASE``-``BEHAVIOR_FLAG_END``, bytes from ``BEHAVIOR_BYTE_BASE``)
    — above the campaign per-member window space, so a campaign playthrough and a
    behavior field can never alias state. (The pre-partition defaults, flags 8860-9080 +
    bytes 1220+, sat INSIDE the opening campaign's windows; the fort-condor bench's hand
    map at bytes 1102-1214 / flags 8800-8853 still does — bench-grade exposure until
    rebuilt.) The byte band tops out flush BELOW the reserved heap top (nameplate
    explored words / [[qte]] scratch / co-op cells / choice mask —
    :data:`BYTE_END_DEFAULT`); every allocation is cleared/preset by the emitted
    Main_Init prepend, so nothing leaks into saves. ``report()`` is the ~ Flags
    debugging map."""

    def __init__(self, *, byte_base: int = BEHAVIOR_BYTE_BASE, byte_end: int = BYTE_END_DEFAULT,
                 flag_base: int = BEHAVIOR_FLAG_BASE, flag_end: int = BEHAVIOR_FLAG_END):
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
    anim: int | None = None          # SwingAt's theater, same damage-tick timing
    hit_sfx: int | None = None

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
    minus death policy — death is a TREE branch, e.g. Cond(hp==0) -> Do(Die())).

    THEATER (both optional, fired on the DAMAGE tick — the swing lands with its
    own clip and sound, never per-frame): ``anim`` = a one-shot clip id played on
    the swinger (``RunAnimation`` in its own object context), ``hit_sfx`` = the
    impact cue. ``anim`` must be a clip of the unit model's OWN family — the TOML
    layer resolves a gesture NAME against that model and refuses a foreign one
    (the own-clip law); a raw id passes through."""
    target: str
    interval: int = 30
    damage: int = 1
    anim: int | None = None
    hit_sfx: int | None = None

    def __post_init__(self):
        for f in ("anim", "hit_sfx"):
            v = getattr(self, f)
            if v is not None and not 0 <= int(v) <= 0xFFFF:
                raise BehaviorError(f"SwingAt {f} must be 0..65535")


OP_RUN_ANIMATION = 0x40             # ANIM — one-shot clip on the running object
OP_WAIT_ANIMATION = 0x41            # WAITANIM — block until it finishes
OP_SET_STAND_ANIM = 0x33            # the object's IDLE clip (what it reverts to)
OP_SET_WALK_ANIM = 0x34             # ... and its WALK clip (what a blocked walk drives)
OP_SET_ANIM_FLAGS = 0x3F            # AMODE(mode, repeats) — mode 1 = FREEZE AT END
ANIM_HOLD = 1                       # (engine: flag<<3 & afHold|afLoop|afPalindrome;
                                    #  1 freeze-at-end, 2 loop, 3 palindrome) — the
                                    #  chest's own `SetAnimationFlags(1, 0)` idiom


@dataclass
class Die(Action):
    """Clear my active flag (mirrors stop — the dead-uid firewall), then TerminateEntry.
    ``count``: bump that counter by 1 first — the dispatch body runs exactly once
    (the entry terminates), so the bump is edge-safe for free (the kill-counter
    idiom: every attacker dies with ``count="kills"``, a win branch gates on
    ``counter_ge``).

    THE DEATH BEAT (``anim`` / ``linger``): without them the unit VANISHES the
    tick it dies — the fort-condor "instant vanish" complaint. ``anim`` fires a
    one-shot clip (bare ``RunAnimation`` — see the body for why NOT
    ``WaitAnimation``) and ``linger`` holds the corpse N frames while it plays,
    so linger IS the visible beat: size it to the clip.
    The active flag drops FIRST either way, so the dying unit stops being a
    target the same tick it starts falling — the corpse is already inert."""
    count: str | None = None
    anim: int | None = None
    linger: int = 0

    def __post_init__(self):
        if self.anim is not None and not 0 <= int(self.anim) <= 0xFFFF:
            raise BehaviorError("Die anim must be 0..65535")
        if not 0 <= int(self.linger) <= 255:
            raise BehaviorError("Die linger must be 0..255 frames")


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
    a once-ever announcement.
    ``delay``: hold the dispatch level SILENTLY for N frames before opening — the
    staged-text primitive (the previous line's reading time; queued requests wait).
    ``sustain``: hold for N frames AFTER opening — for a line that must ring before a
    queued Battle takes the screen (Sfx's sustain, same law: order ≠ duration)."""
    txid: int
    window: int = 0
    delay: int = 0
    sustain: int = 0

    def __post_init__(self):
        if not 0 <= int(self.delay) <= 255 or not 0 <= int(self.sustain) <= 255:
            raise BehaviorError("Announce delay/sustain must be 0..255 frames")


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


@dataclass
class ShopSynth(Action):
    """Add or remove a SYNTHESIS recipe in a shop — Memoria's extended
    ``AddShopSynthesis`` (0x116), ``ShopStock``'s sibling with the mutation
    INVERTED: it adds the SHOP to the RECIPE's ``Shops`` list (the engine guard is
    on the recipe — an unknown synth id silently no-ops). ``synth``: a raw recipe
    id (int — a vanilla 0..base-max row), or a RESULT item name (str) matched
    against this project's own ``[[synthesis]]`` recipes and resolved at compile
    to the id the CSV emitter mints (the deterministic base-max+1 allocator; a
    string selector therefore needs a reachable install at build). Same session
    semantics as ShopStock (a static process table; never saved; relaunch
    resets), same event-Once + remove-then-add discipline. The target shop must
    open as a SYNTHESIS shop — i.e. be ABSENT from ShopItems.csv (a [[shop]] buy
    id or vanilla 0-31 can never render recipes; validate refuses them)."""
    shop: int
    synth: object                    # recipe id (int) or a [[synthesis]] result name (str)
    add: bool = True

    def __post_init__(self):
        if not 0 <= int(self.shop) <= 255:
            raise BehaviorError("ShopSynth shop id must be 0..255 (the Menu byte)")


@dataclass
class Sfx(Action):
    """Play ONE sound-effect cue — ``RunSoundCode3`` (0xC8) with the chest's proven
    bank + pan/volume triple (content.chest; in-game on fields 200/407 and the kit's
    own chests). Once-wrapped it rides the event-Once lane (fire-and-release — the
    purse-fanfare shape); bare, it plays at dispatch then idles while selected
    (Announce's shape: no re-fire until the tree deselects and re-selects it).
    ``sustain``: hold the dispatch level for N frames AFTER the play, so queued
    one-shots (a Battle, an announce) cannot stomp the cue — the event-once lane
    guarantees ORDER, not DURATION (rung-C round-1 playtest: a loss sting got one
    ~33ms frame of air before the boss battle took the audio)."""
    sound: int
    bank: int = SFX_BANK
    sustain: int = 0

    def __post_init__(self):
        if not 0 <= int(self.sound) <= 0xFFFF:
            raise BehaviorError("Sfx sound id must be 0..65535 (`ff9mapkit sfx-list`)")
        if not 0 <= int(self.bank) <= 0xFFFF:
            raise BehaviorError("Sfx bank must be 0..65535 (default 53248 = 0xD000)")
        if not 0 <= int(self.sustain) <= 255:
            raise BehaviorError("Sfx sustain must be 0..255 frames")


OP_RUN_TIMER = 0x7D                 # RunTimer(0|1) — the countdown's own pause switch


@dataclass
class StopTimer(Action):
    """PAUSE the field countdown — ``RunTimer(0)``, the stop half of the Hunt's
    start triplet the ticker already emits (ChangeTimerTime/ShowTimer/RunTimer).
    The clock FREEZES at its current reading and stays on screen.

    ⚠ THE CLOCK-COUPLED BATTLE LAW (REDOUBT rung-D playtest): ``B_SYSVAR[17]``
    IS ``TimerUI.Time``, and real battle AI reads it — the Festival of the Hunt
    scenes (e.g. 35, the ``LB_E080x`` family) end themselves the instant the
    countdown reads 0 (``B_SYSVAR[17] B_NOT`` → ``RunBattleCode`` end). So a
    timed minigame whose ENDING runs any theater before firing a battle must
    stop its clock first, or the clock hits 0:00 during the aftermath and the
    battle dies the moment combat starts. Stopping keeps the reading nonzero."""
    pass


FLASH_OUT_FRAMES = 24               # the stock white-out: FadeFilter(0, 24, x, colour) —
FLASH_IN_FRAMES = 16                # — released by FadeFilter(1, 16, x, black); field
                                    # 682's exact pair (21 / 11 uses across the 817
                                    # exports; stock Waits 25 = out + 1 before moving on)
FLASH_PAUSE_FRAMES = 20              # the beat held AT the colour between out and release
                                    # (stock does its scene work there; we just hold)


@dataclass
class Flash(Action):
    """ONE screen wash — stock's ADD-channel ``FadeFilter`` (0xEC) flash pair:
    ``CalculateScreenPosition(player)`` + mode-0 out to the colour over 24 frames,
    ``Wait(25)`` (stock's out+1), a held beat at the colour, then the mode-1
    release to black over 16 (field 682's exact idiom, twice in that field).
    ⚠ NOT modes 6/7 — bit 1 selects the SUB channel, and SUB toward white is the
    stock warp fade to BLACK (the REDOUBT round-2 playtest lesson; the correct
    lore was already in content.event.WARP_FADE's comment). Same two stances as
    Sfx: Once-wrapped = event-Once fire-and-release (the win-flash lane); bare =
    play at dispatch, idle while selected. The body holds the dispatch level
    ~out+hold+in frames — queued one-shots fire when it releases."""
    rgb: tuple = (255, 255, 255)
    pause: int = FLASH_PAUSE_FRAMES  # TOML key `pause` — `hold` is taken (the feed verb)

    def __post_init__(self):
        self.rgb = tuple(int(c) for c in self.rgb)
        if len(self.rgb) != 3 or not all(0 <= c <= 255 for c in self.rgb):
            raise BehaviorError("Flash rgb must be three ints 0..255")
        if not 0 <= int(self.pause) <= 255:
            raise BehaviorError("Flash pause must be 0..255 frames")


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


@dataclass
class ClassSpec:
    """ONE SHARED BRAIN for N same-tree units — the per-CLASS variant of the
    brains backend (the ticker cross-product kill). Every member's tag-1 head
    RunSharedScripts the SAME seated brain entry; each spawn is its own Seq
    whose gCur = the spawning member every tick (THE CALLER-CONTEXT LAW), so
    the one compiled tree drives whichever unit spawned it. Per-member state
    is STRIDED: uid-indexed gScriptVector cells replace the per-unit GLOBs,
    and the brain indexes them by THE IDENTITY CHANNEL — ``obj(uid=255).f[5]``
    (B_OBJSPECA resolves uid 255 through GetObjUID → gCur, and getvobj field
    5 IS ``obj.uid``: EBin.cs:1216/1674/1815, EventEngine.cs:948) — while the
    member-side bodies (duty walk, dispatch tags) read the same cells at
    their own CONSTANT uid. Members keep their individual names for other
    trees to target; the class name is a pseudo-unit valid only as the SELF
    of its own tree."""
    name: str
    members: tuple
    tree: Node | None = None


# THE IDENTITY CHANNEL (engine-grounded, O(1), player-free): inside a Seq brain
# this expression reads THE CALLING UNIT'S UID — GetObjUID(255) returns gCur
# directly (never a list walk), and object-var field 5 is `obj.uid` with no
# cid guard. Alive-safe by THE ORPHAN-BRAIN LAW: a brain never ticks after its
# unit is disposed (die bodies StopSharedScript first).
MYUID = "obj(uid=255).f[5]"

# THE FREE-GATE (rung 5): the calling unit's SCRIPT LEVEL (getvobj case 6 =
# obj.level, same B_OBJSPECA path as the uid read). `MYLEVEL > 4` IS the
# engine's requestAcceptable(unit, 4) — READ instead of probed: an idle or
# duty-walking unit sits at 7 (a running tag-1 main = cEventLevelN-1), a
# kit body holds 4, an engine talk holds lower. An inline one-shot behind
# this gate skips-and-retries while the unit is engine-held, exactly like
# the REQ it replaces used to drop-and-retry.
MYLEVEL = "obj(uid=255).f[6]"

# per-unit state slots: GLOB home for unclassed units (kind, blackboard name) —
# the classed home is the same slot in a uid-indexed class table (see _uref)
_SLOT_GLOB = {
    "active": ("flag", "{u}.active"),
    "selected": ("byte", "{u}.selected"), "running": ("byte", "{u}.running"),
    "spd": ("byte", "{u}.spd"), "spdap": ("byte", "{u}.spdap"),
    "wp": ("byte", "{u}.wp"), "wtimer": ("byte", "{u}.wtimer"),
    "ctgt": ("byte", "{u}.ctgt"),
    "mx": ("int16", "{u}.mx"), "mz": ("int16", "{u}.mz"),
    "tx": ("int16", "{u}.tx"), "tz": ("int16", "{u}.tz"),
    "px": ("int16", "{u}.px"), "pz": ("int16", "{u}.pz"),
    "wtx": ("int16", "{u}.wtx"), "wtz": ("int16", "{u}.wtz"),
}
# the slots every class allocates up front (shared family tables, uid-indexed);
# wp/wtx/wtz/wtimer/ctgt and decorator latches are PER-CLASS tables, lazy
_CLS_CORE = {"active": "cls.act", "selected": "cls.sel", "running": "cls.run",
             "spd": "cls.spd", "spdap": "cls.spdap",
             "mx": "cls.mx", "mz": "cls.mz", "tx": "cls.tx", "tz": "cls.tz",
             "px": "cls.px", "pz": "cls.pz"}
# the PAYOUT actions a class tree refuses (rung 2 lifted the rest of the
# one-shot family with ONCE-PER-MEMBER latches — but a payout firing once per
# member is N payouts, almost never the intent: Award/shop verbs stay on
# single-npc rows)
_CLS_FORBIDDEN_ACTIONS = ("Award", "ShopStock", "ShopSynth")


# ------------------------------------------------------------------ the compiler
def check_64_stride(occupied, units) -> None:
    """THE 64-STRIDE LAW (brains mode): a brain Seq's runtime uid is its unit's
    uid + 64 (a Byte), and STARTSEQ DISPOSES whatever object already holds that
    uid. Kit objects take uid == entry slot, so refuse any layout where a unit's
    slot + 64 lands on an occupied slot (or past the Byte)."""
    occupied = set(occupied)
    for u in units:
        bu = u.entry + 64
        if bu > 0xFF:
            raise BehaviorError(
                f"64-STRIDE: unit {u.name!r} at slot {u.entry} puts its brain "
                f"uid at {bu} > 255 (uid is a Byte) — reseat the unit lower")
        if bu in occupied:
            raise BehaviorError(
                f"64-STRIDE: unit {u.name!r} at slot {u.entry} puts its brain "
                f"uid at {bu}, which is an OCCUPIED entry slot — STARTSEQ would "
                f"DISPOSE that object; reseat so no entry sits at unit slot + 64")


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
    brain_bodies: dict = _dc_field(default_factory=dict)  # brains mode: unit -> Seq body
    brain_locs: dict = _dc_field(default_factory=dict)    # owner -> instance bytes (varn)

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
        brain_total = sum(len(b) for b in self.brain_bodies.values())
        islands = len(self.ticker_body) - s["ticker_content"]
        new_total = (len(self.ticker_body) + len(self.main_init)
                     + duty_total + disp_total + brain_total)
        out = [f"byte histogram -- new bytes this build: {new_total}B "
               f"(ticker {len(self.ticker_body)}B"
               + (f" = {s['ticker_content']}B + {islands}B islands" if islands else "")
               + f", main_init {len(self.main_init)}B, duty {duty_total}B, "
                 f"dispatch bodies {disp_total}B"
               + (f", brains {brain_total}B" if self.brain_bodies else "") + ")"]
        if self.brain_bodies:
            out.append("  brains (per-unit Seq bodies): " + ", ".join(
                f"{n} {len(b)}B" for n, b in sorted(
                    self.brain_bodies.items(), key=lambda kv: -len(kv[1]))))
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
        for name in sorted(self.brain_bodies):
            h.update(self.brain_bodies[name])
        return h.hexdigest()[:16]


class FieldBehavior:
    """The per-field behavior compilation unit: a roster of units + one tree each."""

    def __init__(self, units: list[UnitSpec], *, blackboard: Blackboard | None = None,
                 tick: int = 1, warmup: int = 45, pools: list[PoolSpec] | tuple = (),
                 timer: int | None = None, tables: list[TableSpec] | tuple = (),
                 counters: tuple = (), brains: bool = False,
                 classes: list[ClassSpec] | tuple = ()):
        """``warmup``: frames after the player is staged before ANY unit activates —
        the field loads dead-still (no walking, no pathing) while the engine settles
        the camera (rung-1 playtest: five actors pathing during entry-settle dragged
        the framerate and stretched the settle to ~5-6s).

        ``brains``: the PER-UNIT-BRAIN backend (the SEQBRAIN bench's architecture,
        all five composites in-game proven 2026-07-27). Each unit's tree segment —
        the SAME bytes the central ticker would carry — compiles into its own
        one-function entry instead, spawned as a shared-script coroutine from the
        unit's tag-1 head (``RunSharedScript``; gCur = the unit for the Seq's whole
        life, so dispatches target uid 255). The residual ticker keeps every
        field-level lane (warm-up, mirrors, clocks, scans, pools, HUDs). Semantics
        are v1's by construction — same conditions, same blackboard, same bodies —
        while no single body ever approaches the ±32K ticker-span wall. Die bodies
        gain ``StopSharedScript`` before ``TerminateEntry`` (THE ORPHAN-BRAIN LAW:
        a disposed unit's live brain NREs the engine on its next tick).

        ``classes``: :class:`ClassSpec` rows — PER-CLASS BRAIN SHARING (needs
        ``brains``). Members of a class carry NO per-unit GLOB protocol state:
        their active/sel/run/spd/mirror/target slots live in uid-indexed
        gScriptVector cells (seeded like every kit table), the ONE class brain
        indexes them by the caller's own uid (:data:`MYUID`), and member-side
        bodies read the same cells at their constant uid. The class name is the
        tree's SELF; assign the tree on ``fb.classes[name].tree``."""
        self.brains = bool(brains)
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
        # ---- classes (per-class brain sharing): validated BEFORE the per-unit
        # allocation loop — classed members take no GLOB protocol slots
        self.classes: dict[str, ClassSpec] = {}
        self._clsof: dict[str, str] = {}                 # member name -> class name
        for cs in classes:
            if not self.brains:
                raise BehaviorError(
                    f"class {cs.name!r}: classes need brains=True (a shared brain "
                    f"IS a Seq coroutine — the central ticker has no caller context)")
            if not re.fullmatch(r"[a-z][a-z0-9_]*", cs.name or ""):
                raise BehaviorError(f"class name {cs.name!r} must be [a-z][a-z0-9_]*")
            if cs.name in self.classes or cs.name in self.units or cs.name == PLAYER:
                raise BehaviorError(f"class name {cs.name!r} collides with a "
                                    f"unit/class/reserved name")
            members = tuple(str(m) for m in cs.members)
            if not members:
                raise BehaviorError(f"class {cs.name!r}: needs at least one member")
            if len(set(members)) != len(members):
                raise BehaviorError(f"class {cs.name!r}: duplicate members")
            for m in members:
                if m not in self.units:
                    raise BehaviorError(f"class {cs.name!r}: unknown member {m!r}")
                if m in self._clsof:
                    raise BehaviorError(f"class {cs.name!r}: {m!r} is already in "
                                        f"class {self._clsof[m]!r}")
                if self.units[m].tree is not None:
                    raise BehaviorError(f"class {cs.name!r}: member {m!r} carries "
                                        f"its own tree — the CLASS owns the tree")
                self._clsof[m] = cs.name
            cs.members = members
            self.classes[cs.name] = cs
        # every strided table is uid-indexed; kit uids == entry slots
        self._cls_len = (max(self.units[m].entry for m in self._clsof) + 1
                         if self._clsof else 0)
        self._cls_tids: dict[str, int] = {}              # table name -> vector id
        self._cls_values: dict[str, dict[int, int]] = {}  # table name -> {cell: preset}
        self.tick = int(tick)
        self._cooldowns: list[tuple[str, int]] = []      # v1: (timer name, frames)
        # THE INSTANCE BLOCK (brains backends): brain-PRIVATE state — sticky
        # once/cooldown latches+timers, the areq/breq request flags, patrol
        # progress, wander state, the acquire scratch — lives in each Seq's own
        # instance vars (the entry's varn block; P3-proven, zeroed at spawn =
        # reset for free, one copy PER SEQ = per-member for free under a
        # class). Only state something OUTSIDE the brain touches (body-written
        # latches, the sel/run protocol, mirrors, targets) stays addressable.
        self._inst_next: dict[str, int] = {}             # owner -> next free byte
        self._inst_slots: dict[tuple, tuple] = {}        # (owner, key) -> (kind, off)
        self._brain_cooldowns: dict[str, list] = {}      # owner -> [timer ref text]
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
            classed = u.name in self._clsof
            if not classed:                              # a classed member's protocol
                self.bb.flag(f"{u.name}.active")         # state is STRIDED cells — no
                self.bb.byte(f"{u.name}.selected")       # GLOB slots (the band relief)
                self.bb.byte(f"{u.name}.running")
                self.bb.byte(f"{u.name}.spd")            # desired walk speed (per-action)
                self.bb.byte(f"{u.name}.spdap")          # applied speed (the nudge shadow)
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
                if not classed:
                    self.bb.int16(f"{u.name}.px")        # the placement post (press-time pos)
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
        self.synth_mints: dict[str, int] = {}            # [[synthesis]] result name -> minted
                                                         # recipe id (the TOML lane fills it —
                                                         # ShopSynth string selectors resolve here)
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
        if self.classes:
            # the shared strided-state families (uid-indexed; one set per FIELD,
            # shared by every class) — allocated after user tables + counters so
            # a class-free build's table ids never move
            for tname in dict.fromkeys(_CLS_CORE.values()):
                self._cls_tids[tname] = _auto_tid()
            for cname, cs in self.classes.items():
                # every member's cells preset: speed = walk_speed; posts = spawn
                # (HoldPost's + the pooled overwrite target); active/sel/run stay
                # zero-filled (the seed law's free reset)
                for m in cs.members:
                    mu = self.units[m]
                    self._cls_preset("cls.spd", mu.entry, int(mu.walk_speed))
                    self._cls_preset("cls.spdap", mu.entry, int(mu.walk_speed))
                    self._cls_preset("cls.px", mu.entry, int(mu.spawn[0]))
                    self._cls_preset("cls.pz", mu.entry, int(mu.spawn[1]))

    # ---------------- the strided-state ref layer (per-class brain sharing)
    def _cls_preset(self, tname: str, cell: int, value: int) -> None:
        """A non-zero seed value for a strided cell — lands in the table's
        Main_Init seed (the zero cells ride the engine's grow-fill for free)."""
        if value:
            self._cls_values.setdefault(tname, {})[int(cell)] = int(value)

    def _cls_tid_for(self, cls: str, slot: str) -> int:
        """The vector id holding ``slot`` for class members: a CORE family table
        (shared by every class) or a lazily-allocated per-class table
        (feed/decorator state). Lazy allocation order = emission order =
        deterministic (the allocation contract)."""
        tname = _CLS_CORE.get(slot) or f"cls.{cls}.{slot}"
        tid = self._cls_tids.get(tname)
        if tid is None:
            tid = self._cls_tids[tname] = self._alloc_tid()
        return tid

    def _uref(self, owner: str, slot: str) -> str:
        """The lvalue/rvalue RPN text for per-unit state ``slot`` of ``owner``:
        an unclassed unit reads its Global home (byte-for-byte the v1 text); a
        classed MEMBER reads its uid-indexed class cell at a constant index
        (member-side bodies + ticker lanes); a CLASS name reads the strided
        self cell indexed by the caller's own uid — valid only inside that
        class's brain (:data:`MYUID`)."""
        kind, pat = _SLOT_GLOB[slot]
        if owner in self.classes:                        # the strided self (brain)
            return f"{_cnum(self._cls_tid_for(owner, slot))} {MYUID} B_VECTOR"
        cls = self._clsof.get(owner)
        if cls is not None:                              # a concrete member cell
            return (f"{_cnum(self._cls_tid_for(cls, slot))} "
                    f"{_cnum(self.units[owner].entry)} B_VECTOR")
        idx = getattr(self.bb, kind)(pat.format(u=owner))
        t = {"flag": "Bit", "byte": "Byte", "int16": "Int16"}[kind]
        return f"Global.{t}[{idx}]"

    def _uset(self, owner: str, slot: str, value) -> bytes:
        """Assign ``value`` (an int, or RPN text) into ``owner``'s ``slot``."""
        v = value if isinstance(value, str) else _cnum(int(value))
        return _stmt(f"{self._uref(owner, slot)} {v} B_LET")

    # ---------------- perception / condition helpers (mirror-safe by construction)
    def _mx(self, unit: str) -> str:
        return self._uref(unit, "mx")

    def _mz(self, unit: str) -> str:
        return self._uref(unit, "mz")

    def _check_unit(self, unit: str, *, self_pos: bool = False):
        if unit in self.classes:
            if not self_pos:
                raise BehaviorError(
                    f"{unit!r} is a CLASS — a class cannot be a TARGET (its N "
                    f"members have N positions); name a member, or engage a group")
            return
        if unit != PLAYER and unit not in self.units:
            raise BehaviorError(f"unknown unit {unit!r}")

    def near(self, a: str, b: str, r: int) -> Cond:
        self._check_unit(a, self_pos=True)               # a = the tree's self — a
        self._check_unit(b)                              # class name strides here
        return Cond(_box(self._mx(a), self._mz(a), self._mx(b), self._mz(b), r),
                    _trusted=True)

    def near_point(self, unit: str, point: tuple, r: int) -> Cond:
        self._check_unit(unit, self_pos=True)
        x, z = point
        return Cond(_box(self._mx(unit), self._mz(unit), int(x), int(z), r), _trusted=True)

    def active(self, unit: str) -> Cond:
        if unit == PLAYER:
            return Cond(f"Global.Bit[{self._staged}]", _trusted=True)
        self._check_unit(unit)                           # a class is refused: its own
        return Cond(self._uref(unit, "active"), _trusted=True)   # seg is already gated

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
        used.update(self._cls_tids.values())             # the strided-state tables
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
        """The RPN fragment for a unit's hit points — a Global byte, a roster
        member's group CELL, a classed member's ``cls.hp`` cell, or (for a CLASS
        name = the tree's self) the STRIDED read: all-members-in-one-group goes
        through the seeded uid→roster-index table into the group's hp cells;
        no-member-grouped reads ``cls.hp`` at the caller's uid. Mixed homes have
        no single expressible text — refused."""
        if unit in self.classes:
            cs = self.classes[unit]
            homes = {self._member.get(m, (None,))[0] for m in cs.members}
            if len(homes) != 1:
                raise BehaviorError(
                    f"class {unit!r}: self-hp needs ONE home — every member in "
                    f"the SAME group, or none grouped (found {sorted(map(str, homes))})")
            gname = next(iter(homes))
            if gname is None:
                for m in cs.members:
                    if self.units[m].hp is None:
                        raise BehaviorError(f"class {unit!r}: member {m!r} has no hp=")
                return f"{_cnum(self._cls_hp_tid(unit))} {MYUID} B_VECTOR"
            # uid -> roster index, seeded static data (THE ORD TABLE); the group
            # hp cells stay the ONE home every attacker already targets
            g = self._groups[gname]
            otid = self._cls_tids.get(f"cls.{unit}.ord")
            if otid is None:
                otid = self._cls_tids[f"cls.{unit}.ord"] = self._alloc_tid()
                for m in cs.members:
                    self._cls_preset(f"cls.{unit}.ord",
                                     self.units[m].entry, self._member[m][1])
            return (f"{_cnum(g.hp_tid)} {_cnum(otid)} {MYUID} B_VECTOR B_VECTOR")
        m = self._member.get(unit)
        if m is not None:
            g = self._groups[m[0]]
            return f"{_cnum(g.hp_tid)} {_cnum(m[1])} B_VECTOR"
        cls = self._clsof.get(unit)
        if cls is not None:                              # classed, ungrouped: cls.hp cell
            if self.units[unit].hp is None:
                raise BehaviorError(f"{unit!r} has no hp=")
            return (f"{_cnum(self._cls_hp_tid(cls))} "
                    f"{_cnum(self.units[unit].entry)} B_VECTOR")
        return f"Global.Byte[{self.bb.byte(f'{unit}.hp')}]"

    def _cls_spd0_tid(self, cls: str) -> int:
        """The per-class DEFAULT-SPEED table (cells preset to each member's
        walk_speed) — the strided fallback for a class feed with no speed=."""
        fresh = f"cls.{cls}.spd0" not in self._cls_tids
        tid = self._cls_tid_for(cls, "spd0")
        if fresh:
            for m in self.classes[cls].members:
                mu = self.units[m]
                self._cls_preset(f"cls.{cls}.spd0", mu.entry, int(mu.walk_speed))
        return tid

    def _cls_hp_tid(self, cls: str) -> int:
        """The per-class hp table for UNGROUPED classed members — allocation
        registers every member's hp preset (the cells ARE their hit points)."""
        fresh = f"cls.{cls}.hp" not in self._cls_tids
        tid = self._cls_tid_for(cls, "hp")
        if fresh:
            for m in self.classes[cls].members:
                mu = self.units[m]
                if mu.hp is not None and m not in self._member:
                    self._cls_preset(f"cls.{cls}.hp", mu.entry, int(mu.hp))
        return tid

    def engage_node(self, unit: str, e: Engage) -> Node:
        """Compile-side surface for the ``engage`` verb: registers the owner's
        acquire loop + target register and returns the two-phase subtree
        (contact -> the strike dispatch; else -> the pursue feed), built
        entirely from the standard node vocabulary. ``unit`` may be a CLASS
        name (the tree's self): the target register strides per member."""
        if unit not in self.units and unit not in self.classes:
            raise BehaviorError(f"engage: unknown unit {unit!r}")
        if e.group not in self._groups:
            raise BehaviorError(f"engage: unknown group {e.group!r} "
                                f"(declare it with group())")
        g = self._groups[e.group]
        selves = (self.classes[unit].members if unit in self.classes else (unit,))
        for s in selves:
            if s in g.units:
                raise BehaviorError(f"engage: {s!r} cannot engage its OWN group "
                                    f"{e.group!r}")
        if unit in self._engages:
            raise BehaviorError(f"engage: {unit!r} already has an engage "
                                f"(one target register per unit in v2 rung 1)")
        self._engages[unit] = e
        ctgt_r = self._uref(unit, "ctgt")
        pxc = f"{_cnum(g.px_tid)} {ctgt_r} B_VECTOR"
        pzc = f"{_cnum(g.pz_tid)} {ctgt_r} B_VECTOR"
        return Selector(
            Sequence(Cond(f"{ctgt_r} const(255) B_LT", _trusted=True),
                     Cond(_box(self._mx(unit), self._mz(unit), pxc, pzc,
                               int(e.contact)), _trusted=True),
                     Do(e._swing)),
            Sequence(Cond(f"{ctgt_r} const(255) B_LT", _trusted=True),
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
    def _collect_tree_actions(self, tree: Node | None) -> list[Action]:
        out: list[Action] = []

        def walk(n: Node):
            if isinstance(n, (Selector, Sequence)):
                for c in n.children:
                    walk(c)
            elif isinstance(n, (Once, Cooldown)):
                walk(n.child)
            elif isinstance(n, Do):
                out.append(n.action)
        walk(tree)
        return out

    def _collect_actions(self, unit: UnitSpec) -> list[Action]:
        return self._collect_tree_actions(unit.tree)

    def _check_class_tree(self, cs: ClassSpec) -> None:
        """Class-tree restrictions (rung 2): the one-shot family (Battle,
        Announce, Sfx, Flash, StopTimer) is IN with ONCE-PER-MEMBER latches
        (strided cells — each member fires its own one-shot once; class-wide
        once = the raise_flags + not_flag idiom). Only the PAYOUT actions stay
        out: once-per-member on an Award/shop mutation means N payouts —
        they belong on a single-npc row (a herald, a referee)."""
        for a in self._collect_tree_actions(cs.tree):
            if type(a).__name__ in _CLS_FORBIDDEN_ACTIONS:
                raise BehaviorError(
                    f"class {cs.name!r}: {type(a).__name__} fires once PER "
                    f"MEMBER under a class — {len(cs.members)} payouts; put it "
                    f"on a normal single-npc [[behavior.unit]]")

    def _fallback_feed_tree(self, owner: str, tree: Node) -> Action:
        """The tree's unconditional fallback must be a STATIC feed (WalkTo/Hold/Patrol)
        so Main_Init can preset the duty target — enforced, per the charter."""
        node = tree
        while True:
            if isinstance(n := node, Selector):
                node = n.children[-1]
            elif isinstance(node, Sequence):
                # a fallback Sequence must be condition-free to be unconditional
                if any(isinstance(c, (Cond, Invert)) for c in node.children):
                    raise BehaviorError(
                        f"{owner}: the tree's last branch must be UNCONDITIONAL — "
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
                    f"{owner}: the fallback action must be a static feed "
                    f"(WalkTo/Hold/Patrol/March/Flee/Wander/HoldPost), not {type(a).__name__}")
            else:
                raise BehaviorError(
                    f"{owner}: the tree needs an unconditional Do fallback "
                    f"(got {type(node).__name__})")

    def _fallback_feed(self, unit: UnitSpec) -> Action:
        return self._fallback_feed_tree(unit.name, unit.tree)

    def _once_announce_map(self, owner: str, tree: Node, ids: dict) -> dict:
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
                if leaf is not None and isinstance(leaf.action, (Announce, Award, ShopStock, ShopSynth, Sfx, Flash, StopTimer)):
                    aid = ids[id(leaf.action)]
                    if aid in onced and onced[aid] != n.name:
                        raise BehaviorError(
                            f"{owner}: the same {type(leaf.action).__name__} object "
                            f"sits under two Once decorators ({onced[aid]!r}, "
                            f"{n.name!r}) — one latch cannot serve two gates; give "
                            f"each its own instance")
                    onced[aid] = n.name
                else:
                    walk(n.child)
            elif isinstance(n, Do) and isinstance(n.action, (Announce, Award, ShopStock, ShopSynth, Sfx, Flash, StopTimer)):
                bare.add(ids[id(n.action)])
                if isinstance(n.action, (Award, ShopStock, ShopSynth)):
                    bare_awards.add(ids[id(n.action)])
        walk(tree)
        if bare_awards:
            raise BehaviorError(
                f"{owner}: an Award / shop-stock action must be wrapped in Once "
                f"(exactly-once BY that machinery — a bare one would re-fire "
                f"every selection)")
        clash = set(onced) & bare
        if clash:
            raise BehaviorError(
                f"{owner}: an Announce/Sfx object is shared between a Once-wrapped site "
                f"and a bare site — give each site its own instance")
        return onced

    def has_battle_actions(self) -> bool:
        """True when any tree fires a :class:`Battle` — the build must then
        ensure the entry-0 tag-10 Main_Reinit (the after-battle resume law).
        Class trees count: the engine's park/restore/suspend/resume is uid-
        keyed and cid-blind (EventContext.copy + EnterBattleEnd + the state0
        wake), so Seq brains ride a battle round-trip like any stock object."""
        trees = [u.tree for u in self.units.values() if u.tree is not None]
        trees += [cs.tree for cs in self.classes.values() if cs.tree is not None]
        return any(isinstance(a, Battle)
                   for t in trees for a in self._collect_tree_actions(t))

    def compile(self) -> CompiledBehavior:
        for u in self.units.values():
            if u.tree is None and u.name not in self._clsof:
                raise BehaviorError(f"unit {u.name!r} has no tree")
        for cs in self.classes.values():
            if cs.tree is None:
                raise BehaviorError(f"class {cs.name!r} has no tree")
            self._check_class_tree(cs)

        duty_bodies: dict[str, bytes] = {}
        action_funcs: dict[str, list] = {}
        brain_bodies: dict[str, bytes] = {}              # brains mode: unit -> Seq body
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
            ticker.append(self._uset(u.name, "active", 1))
        # THE WAKE-PUBLICATION LAW (brains backends): the wake pass must FALL
        # THROUGH into the run path, so activation and the first mirror/scan/
        # counter publication land in ONE ticker slice (no Wait between = atomic
        # against every other object). A brain is its own Seq: with the v1-style
        # jump-to-wait it can tick between "active set" and "counters published"
        # and read a counter at its SEED — the BTCLASS boot misfire ("the Mus
        # are wiped out!" before the brawl: alive-counts seed 0, and
        # counter_eq 0 is armed AT the seed). v1 keeps the jump byte-for-byte:
        # its tree segments run inside this same body AFTER the scan blocks, so
        # the gap is structurally unobservable there (and those bytes are
        # in-game proven).
        ticker += ([] if self.brains else [(JMP, "wait")]) + [label("run")]
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
                _stmt(self._uref(u.name, "active")),
                (JMP_IFNOT, f"m_{u.name}_skip"),
                _stmt(f"{self._uref(u.name, 'mx')} obj(uid={u.entry}).f[0] B_LET"),
                _stmt(f"{self._uref(u.name, 'mz')} obj(uid={u.entry}).f[2] B_LET"),
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

        # TREE OWNERS: every unclassed unit owns its own tree (v1 / per-unit
        # brains — the proven paths, byte-identical); every CLASS owns ONE tree
        # emitted ONCE, driving all its members through the strided cells + the
        # caller-context dispatch (uid 255)
        owners: list[tuple[str, "Node", list[UnitSpec]]] = \
            [(u.name, u.tree, [u]) for u in self.units.values()
             if u.name not in self._clsof] \
            + [(cs.name, cs.tree, [self.units[m] for m in cs.members])
               for cs in self.classes.values()]
        for owner, tree, members in owners:
            is_cls = owner in self.classes
            actions = self._collect_tree_actions(tree)
            if not actions:
                raise BehaviorError(f"{owner}: tree selects no actions")
            ids: dict[int, int] = {}                     # id(action) -> action id
            for a in actions:
                ids.setdefault(id(a), len(ids) + 1)
            fallback = self._fallback_feed_tree(owner, tree)

            # ---- main_init: units start INACTIVE (the ticker's warm-up wakes
            # them), reset protocol state, preset the duty target. A classed
            # member's protocol state lives in seeded cells — active/sel/run
            # ride the zero-fill, presets become seed VALUES, no statements.
            for u in members:
                if isinstance(fallback, (Patrol, March, Flee)):
                    px, pz = fallback.points[0]
                elif isinstance(fallback, Wander):
                    px, pz = fallback.center
                elif isinstance(fallback, HoldPost):
                    px, pz = u.spawn
                else:
                    px, pz = fallback.point
                if is_cls:
                    cls = self._clsof[u.name]
                    self._cls_tid_for(cls, "tx")         # materialize the families
                    self._cls_tid_for(cls, "tz")         # (zero cells need no value)
                    self._cls_preset("cls.tx", u.entry, int(px))
                    self._cls_preset("cls.tz", u.entry, int(pz))
                    if u.hp is not None and u.name not in self._member:
                        self._cls_hp_tid(cls)            # cells = the hp home
                    if owner in self._engages:
                        # the target register: 255 = none (0 is a VALID roster
                        # index — the preset must never ride the zero-fill)
                        self._cls_preset(f"cls.{cls}.ctgt", u.entry, 255)
                    if u.pooled:
                        main_init += _set_flag(self.bb.flag(f"{u.name}.spawned"), 0)
                    continue
                main_init += self._uset(u.name, "active", 0)
                main_init += self._uset(u.name, "selected", 0)
                main_init += self._uset(u.name, "running", 0)
                main_init += self._uset(u.name, "spd", u.walk_speed)
                main_init += self._uset(u.name, "spdap", u.walk_speed)
                main_init += self._uset(u.name, "tx", int(px))
                main_init += self._uset(u.name, "tz", int(pz))
                if u.hp is not None and u.name not in self._member:
                    # a roster member's ONLY hp home is its group cell (table-seeded)
                    main_init += _set_byte(self.bb.byte(f"{u.name}.hp"), int(u.hp))
                if owner in self._engages:
                    # the target register: 255 = none (0 is a VALID roster index,
                    # so this preset must never ride the zero-reset list)
                    main_init += self._uset(u.name, "ctgt", 255)
                if u.pooled or any(isinstance(a, HoldPost) for a in actions):
                    # the placement post: presets to the unit's own spawn; a pooled
                    # activation overwrites it with the press-time position
                    main_init += self._uset(u.name, "px", int(u.spawn[0]))
                    main_init += self._uset(u.name, "pz", int(u.spawn[1]))
                if u.pooled:
                    main_init += _set_flag(self.bb.flag(f"{u.name}.spawned"), 0)

            # ---- per-member duty bodies (universal blocked walk on the target
            # slots; a classed member reads its cells at its CONSTANT uid — the
            # engine re-evaluates walk args every frame, cells included)
            for u in members:
                spd_r = self._uref(u.name, "spd")
                duty_bodies[u.name] = asm([
                    label("top"),
                    opcodes.encode(OP_SET_OBJECT_FLAGS, 7)
                    + opcodes.encode(0x26, exprasm.assemble(f"{spd_r} B_EXPR_END"),
                                     arg_flags=0b1)
                    + opcodes.set_pathing(1)
                    + opcodes.set_walk_turn_speed(255),
                    _stmt(self._uref(u.name, "active")),
                    (JMP_IFNOT, "wait"),
                    opcodes.init_walk()
                    + opcodes.encode(OP_WALK,
                                     exprasm.assemble(f"{self._uref(u.name, 'tx')} B_EXPR_END"),
                                     exprasm.assemble(f"{self._uref(u.name, 'tz')} B_EXPR_END"),
                                     arg_flags=0b11),
                    label("wait"),
                    opcodes.wait(1),
                    (JMP, "top"),
                    opcodes.RETURN,
                ])

            # ---- dispatch-action bodies (tags 15+), per member — every member
            # gets the same tag numbering (the shared brain REQs by tag)
            once_ann = self._once_announce_map(owner, tree, ids)  # aid -> Once name
            dispatch_tag: dict[int, int] = {}
            oneshot_latch: dict[int, int] = {}           # aid -> latch slot KEY
            oneshot_req: dict[int, int] = {}             # aid -> EDGE-latched req KEY
            oneshot_action: dict[int, Action] = {}       # aid -> the action (rung 5)
            die_aids: set[int] = set()                   # transition-critical aids
            for a in actions:
                aid = ids[id(a)]
                if a.feed or aid in dispatch_tag:        # same object in 2+ Do sites
                    continue
                dispatch_tag[aid] = FIRST_ACTION_TAG + len(dispatch_tag)
                if isinstance(a, Die):
                    die_aids.add(aid)
                if isinstance(a, Battle):
                    lk, rk = f"battled{aid}", f"breq{aid}"
                elif isinstance(a, (Announce, Award, ShopStock, ShopSynth, Sfx, Flash, StopTimer)) and aid in once_ann:
                    lk, rk = f"once.{once_ann[aid]}", f"areq{aid}"
                else:
                    lk = rk = None
                if lk is not None:
                    oneshot_latch[aid] = lk
                    oneshot_req[aid] = rk
                    oneshot_action[aid] = a
                    # registration: the LATCH is body-written (GLOB / strided —
                    # once-per-member; class-wide once = raise_flags+not_flag);
                    # the REQUEST is brain-private (Instance under brains).
                    # v1 keeps the latch-then-request reset order byte-for-byte.
                    self._sticky_flag(owner, lk)
                    if self.brains:
                        self._inst_ref(owner, rk)
                    else:
                        self._sticky_flag(owner, rk)
            nudge_tag = FIRST_ACTION_TAG + len(dispatch_tag)
            for u in members:
                funcs: list = []
                for a in actions:
                    aid = ids[id(a)]
                    tag = dispatch_tag.get(aid)
                    if a.feed or tag is None or any(t == tag for t, _b in funcs):
                        continue
                    if self.brains and aid in oneshot_req:
                        continue    # rung 5: INLINE in the brain — no member body
                    latch_arg = (oneshot_latch.get(aid)
                                 if not isinstance(a, Battle) else None)
                    body = self._dispatch_body(owner, u, a, aid,
                                               oneshot_latch=latch_arg)
                    funcs.append((tag, body))
                    disp_sizes.setdefault(u.name, []).append(
                        (tag, f"{type(a).__name__}#{aid}", len(body)))
                # the SPEED NUDGE (always the last tag): MSPEED from the speed
                # slot, then record it applied. Straight-line at level 4 —
                # preempts a mid-flight blocked walk, which resumes at the new
                # speed (actor.speed is re-read every walk frame).
                nudge_body = asm([
                    self._uset(u.name, "running", 255),
                    opcodes.encode(0x26,
                                   exprasm.assemble(f"{self._uref(u.name, 'spd')} B_EXPR_END"),
                                   arg_flags=0b1),
                    _stmt(f"{self._uref(u.name, 'spdap')} "
                          f"{self._uref(u.name, 'spd')} B_LET"),
                    self._uset(u.name, "running", 0),
                    opcodes.RETURN,
                ])
                funcs.append((nudge_tag, nudge_body))
                disp_sizes.setdefault(u.name, []).append(
                    (nudge_tag, "nudge", len(nudge_body)))
                action_funcs[u.name] = funcs

            # the per-owner segment: identical emission for every backend — in v1
            # it rides the central ticker (dispatch targets the unit's ENTRY);
            # under `brains` it becomes the unit's own Seq body (gCur = the unit,
            # so every dispatch targets uid 255 — the SEQBRAIN caller-context
            # law); for a CLASS the one seg serves every member (self state is
            # strided by the caller's uid — THE IDENTITY CHANNEL)
            tgt = 255 if self.brains else members[0].entry
            sel_r = self._uref(owner, "selected")
            run_r = self._uref(owner, "running")
            seg: list = [
                _stmt(self._uref(owner, "active")),
                (JMP_IFNOT, f"t_{owner}_done"),
            ]
            if self.brains:
                # the tree compiles FIRST: it discovers this owner's
                # SEQ-PRIVATE cooldown timers, whose decrement blocks must sit
                # ahead of it in the same pass (the central clock's position,
                # brain-local). v1 keeps its original emission order below —
                # its blackboard allocation sequence is part of its bytes.
                tree_body = self._compile_tree(owner, tree, ids,
                                               fail=f"t_{owner}_fellthrough")
                for ci, t_r in enumerate(self._brain_cooldowns.get(owner, ())):
                    sk = f"t_{owner}_bcd{ci}"
                    seg += [
                        _stmt(f"{t_r} const(0) B_GT"), (JMP_IFNOT, sk),
                        _stmt(f"{t_r} {t_r} const(1) B_MINUS B_LET"),
                        label(sk),
                    ]
                if owner in self._engages:
                    seg += self._acquire_block(owner, self._engages[owner])
                seg += tree_body
            else:
                if owner in self._engages:
                    seg += self._acquire_block(owner, self._engages[owner])
                seg += self._compile_tree(owner, tree, ids,
                                          fail=f"t_{owner}_fellthrough")
            seg += [
                label(f"t_{owner}_fellthrough"),         # unreachable (fallback is
                label(f"t_{owner}_selected"),            # unconditional) — lint safety
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
            disp_end = f"t_{owner}_dend"
            for aid, rk in oneshot_req.items():
                bl = f"t_{owner}_b{aid}"
                req_r = (self._inst_ref(owner, rk) if self.brains
                         else self._sticky_flag(owner, rk))
                seg += [
                    _stmt(req_r), (JMP_IFNOT, bl),
                    _stmt(self._sticky_flag(owner, oneshot_latch[aid])), (JMP_IF, bl),
                    _stmt(f"{run_r} const(0) B_EQ"), (JMP_IFNOT, bl),
                ]
                if self.brains:
                    # RUNG 5 — THE INLINE ONE-SHOT: the body's work is global
                    # by audit (_oneshot_work), so it runs HERE in the brain
                    # Seq instead of being REQ'd onto a per-member function —
                    # the per-member copies are gone. THE FREE-GATE replaces
                    # the REQ's acceptance check (requestAcceptable READ, not
                    # probed): while the unit is engine-held (an open talk
                    # dialogue) the lane skips and retries next pass, exactly
                    # the old drop-and-retry. Latch FIRST (Battle's shape — a
                    # battle suspend can never re-fire), run wraps the work at
                    # MYUID (the same cells the member body wrote).
                    seg += [
                        _stmt(f"{MYLEVEL} const({DISPATCH_LEVEL}) B_GT"),
                        (JMP_IFNOT, bl),
                        _stmt(f"{self._sticky_flag(owner, oneshot_latch[aid])} "
                              f"const(1) B_LET"),
                        self._uset(owner, "running", 255),
                    ] + self._oneshot_work(oneshot_action[aid], owner) + [
                        self._uset(owner, "running", 0),
                        (JMP, disp_end),
                        label(bl),
                    ]
                else:
                    seg += [
                        opcodes.run_script_async(DISPATCH_LEVEL, tgt,
                                                 dispatch_tag[aid]),
                        (JMP, disp_end),
                        label(bl),
                    ]
            for aid, tag in dispatch_tag.items():        # the normal sel-gated tail
                if aid in oneshot_req:                   # one-shots ride the request lane
                    continue
                # THE MUST-LAND DISPATCH LAW (seqbrain P4 round 2): a routine
                # dispatch WANTS drop-while-busy — that IS the run-gate — but a
                # transition-critical one (Die: the unit must actually die) uses
                # REQSW 0x12: the Seq STAYS on the instruction while the unit's
                # level is held (an open talk dialogue, a blocked walk), then
                # binds. Brains only — each Seq blocks only ITSELF, and no
                # deadlock is reachable: the tree wrote sel=<die aid> before
                # this tail, so a looping kit body exits its sel check and
                # frees the level. The v1 TICKER MUST NEVER BLOCK (one busy
                # unit would stall every brain in the field), so v1 keeps
                # REQ + its per-tick re-REQ retry — byte-identical and correct.
                disp = (opcodes.run_script(DISPATCH_LEVEL, tgt, tag)
                        if self.brains and aid in die_aids
                        else opcodes.run_script_async(DISPATCH_LEVEL, tgt, tag))
                seg += [
                    _stmt(f"{sel_r} const({aid}) B_EQ"),
                    (JMP_IFNOT, f"t_{owner}_d{aid}"),
                    _stmt(f"{run_r} const(0) B_EQ"),
                    (JMP_IFNOT, f"t_{owner}_d{aid}"),
                    disp,
                    label(f"t_{owner}_d{aid}"),
                ]
            seg += [label(disp_end)]
            # the nudge dispatch: only when level 4 is free AND a FEED is selected
            # (a selected dispatch action owns the level-4 REQ this tick — mutual
            # exclusion by construction, never two REQs on one unit per tick)
            nl = f"t_{owner}_nudge"
            seg += [
                _stmt(f"{run_r} const(0) B_EQ"), (JMP_IFNOT, nl),
                _stmt(f"{self._uref(owner, 'spd')} "
                      f"{self._uref(owner, 'spdap')} B_EQ"), (JMP_IF, nl),
            ]
            for aid in dispatch_tag:
                seg += [_stmt(f"{sel_r} const({aid}) B_EQ"), (JMP_IF, nl)]
            seg += [opcodes.run_script_async(DISPATCH_LEVEL, tgt, nudge_tag),
                    label(nl)]
            seg += [label(f"t_{owner}_done")]
            if self.brains:
                # the brain: the SAME segment, self-scheduled at the ticker cadence.
                # The active gate idles it (pooled units' brains spawn on activation,
                # since a dormant entry's tag-1 first runs then). No __seg markers —
                # brains report whole-body sizes, the histogram stays ticker-only.
                # A CLASS emits this body ONCE; every member's tag-1 spawns it.
                brain_bodies[owner] = asm(
                    [label("__brain_top")] + seg
                    + [opcodes.wait(self.tick), (JMP, "__brain_top"), opcodes.RETURN])
            else:
                ticker += [label(f"__seg unit {owner}")] + seg

            acts = ", ".join(dict.fromkeys(          # dedupe shared-object Do sites
                f"{ids[id(a)]}={type(a).__name__}" for a in actions))
            if is_cls:
                report.append(
                    f"  class {owner}: ONE shared brain, members "
                    f"[{', '.join(m.name for m in members)}] (entries "
                    f"{', '.join(str(m.entry) for m in members)}); per-member "
                    f"state = uid-indexed cells (see the cls.* tables); "
                    f"actions[{acts}]")
            else:
                u = members[0]
                report.append(f"  {owner}: entry {u.entry}, "
                              f"selected@{self.bb.byte(f'{owner}.selected')} "
                              f"running@{self.bb.byte(f'{owner}.running')} "
                              f"spd@{self.bb.byte(f'{owner}.spd')} actions[{acts}]")

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
        # (brains-backend cooldown timers are SEQ-PRIVATE and tick inside each
        # brain's own loop — the central clock carries only v1's GLOB timers)
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
                cd_blocks += [
                    _stmt(f"{_cnum(g.px_tid)} {_cnum(i)} B_VECTOR "
                          f"{self._uref(un, 'mx')} B_LET"),
                    _stmt(f"{_cnum(g.pz_tid)} {_cnum(i)} B_VECTOR "
                          f"{self._uref(un, 'mz')} B_LET"),
                    _stmt(f"{_cnum(g.act_tid)} {_cnum(i)} B_VECTOR "
                          f"{self._uref(un, 'active')} B_LET"),
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
                    cd_blocks.append(_stmt(f"{_cnum(sc.px_tid)} {_cnum(i)} B_VECTOR "
                                           f"{self._uref(un, 'mx')} B_LET"))
                    cd_blocks.append(_stmt(f"{_cnum(sc.pz_tid)} {_cnum(i)} B_VECTOR "
                                           f"{self._uref(un, 'mz')} B_LET"))
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
                upx = self._uref(un, "px")
                upz = self._uref(un, "pz")
                nxt = f"pl_{pname}_t{i + 1}" if i + 1 < len(unames) else f"pl_{pname}_done"
                cd_blocks += [
                    _stmt(f"Global.Bit[{spawned}]"), (JMP_IF, nxt),
                ] + ([opcodes.remove_gil(int(price))] if price else []) \
                  + ([opcodes.remove_item(int(item), 1)] if item is not None else []) + [
                    # the placement post = the press-time player position
                    _stmt(f"{upx} {pmx} B_LET"),
                    _stmt(f"{upz} {pmz} B_LET"),
                    opcodes.init_object(pu.entry, 0),
                    opcodes.wait(2),                     # let the pooled Init complete
                    opcodes.move_instant_ex(
                        pu.entry,
                        exprasm.assemble(f"{upx} B_EXPR_END"),
                        exprasm.assemble(f"{upz} B_EXPR_END")),
                    # seed the unit's mirrors (its tree ticks THIS pass) + wake it
                    _stmt(f"{self._uref(un, 'mx')} {upx} B_LET"),
                    _stmt(f"{self._uref(un, 'mz')} {upz} B_LET"),
                    _set_flag(spawned, 1),
                    self._uset(un, "active", 1),
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
                # the sentinel rides a u16 operand: clamp, don't wrap. A 6-digit slot's naive
                # 999999 used to mask down to 16959 (a NARROWER strip than asked). 65535 is the
                # widest value the opcode can ever carry, so it is the true max-width sentinel.
                cd_blocks.append(opcodes.encode(0x66, i, min(10 ** int(d) - 1, 0xFFFF)))
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
        # THE STRIDED-STATE SEEDS (classes): the same size-wipe/grow/non-zero-cell
        # idiom as every kit table — active/sel/run/latches ride the zero-fill
        # (reset for free on ~ Reload), presets (speed, posts, targets, hp, the
        # ord map, ctgt=255) are seed VALUES. Emitted last: nothing else in
        # Main_Init reads a table, and every allocation is final by now.
        for tname, tid in self._cls_tids.items():
            main_init += _stmt(f"{_cnum(tid)} B_VECTOR_SIZE const(0) B_LET")
            main_init += _stmt(f"{_cnum(tid)} B_VECTOR_SIZE "
                               f"{_cnum(self._cls_len)} B_LET")
            for cell, v in sorted(self._cls_values.get(tname, {}).items()):
                main_init += _stmt(f"{_cnum(tid)} {_cnum(cell)} B_VECTOR "
                                   f"{_cnum(v)} B_LET")

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
        if self._cls_tids:
            report.append("strided class-state tables (gScriptVector, uid-indexed; "
                          f"{self._cls_len} cells each):")
            report.append("  " + ", ".join(
                f"{n}={tid}" for n, tid in self._cls_tids.items()))
        if self._inst_slots:
            report.append("brain instance blocks (Seq-private vars — zeroed at "
                          "spawn; NOT visible in ~ Flags):")
            for o in sorted({ow for ow, _k in self._inst_slots}):
                slots = ", ".join(
                    f"{k}@{off}{'w' if kind == 'int16' else ''}"
                    for (ow, k), (kind, off) in sorted(self._inst_slots.items(),
                                                       key=lambda kv: kv[1][1])
                    if ow == o)
                report.append(f"  {o}: {self._inst_next.get(o, 0)}B [{slots}]")
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
                if un in self.classes:
                    reg = (f"cells cls.{un}.ctgt (id "
                           f"{self._cls_tids[f'cls.{un}.ctgt']}, uid-indexed)")
                else:
                    reg = f"byte {self.bb.byte(f'{un}.ctgt')}"
                tl.append(f"  engage {un} -> group '{e.group}': target register "
                          f"{reg} (255=none, watch in "
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
                   "brains": {n: len(b) for n, b in brain_bodies.items()},
                   "main_init": len(main_init)},
            brain_bodies=brain_bodies,
            brain_locs={o: self._inst_next.get(o, 0) for o in brain_bodies},
        )

    # ---------------- tree → ticker blocks
    def _inst_ref(self, owner: str, key: str, kind: str = "byte") -> str:
        """A BRAIN-PRIVATE slot as a Seq Instance var (brains backends only):
        allocated once per (owner, key) from the owner's varn block — install
        seats the brain entry with ``loc =`` the block size. Int16 slots are
        2-aligned. Flags are whole BYTES (the SEQBRAIN-proven shape; the
        private block is not the band, bytes are free there)."""
        width = 2 if kind == "int16" else 1
        slot = self._inst_slots.get((owner, key))
        if slot is None:
            off = self._inst_next.get(owner, 0)
            if width == 2 and off % 2:
                off += 1
            if off + width > 255:
                raise BehaviorError(
                    f"{owner}: brain instance block exceeds 255 bytes (the "
                    f"entry-table varn is a Byte) — split the tree")
            slot = (kind, off)
            self._inst_slots[(owner, key)] = slot
            self._inst_next[owner] = off + width
        k, off = slot
        return f"Instance.{'Int16' if k == 'int16' else 'Byte'}[{off}]"

    def _sticky_flag(self, owner: str, key: str) -> str:
        """A sticky-decorator latch ref: a reset-listed GLOB flag for a unit
        owner (the v1 text); for a CLASS, a zero-seeded strided cell — one latch
        per MEMBER for free (reset = the table seed)."""
        if owner in self.classes:
            return f"{_cnum(self._cls_tid_for(owner, key))} {MYUID} B_VECTOR"
        idx = self.bb.flag(f"{owner}.{key}")
        if idx not in self._reset_flags:
            self._reset_flags.append(idx)
        return f"Global.Bit[{idx}]"

    def _compile_tree(self, owner: str, node: Node, ids: dict, fail: str,
                      _ctr=None, on_select: list | None = None) -> list:
        if _ctr is None:
            _ctr = [0]
        _ctr[0] += 1
        me = f"t_{owner}_n{_ctr[0]}"
        out: list = []
        if isinstance(node, Selector):
            for i, c in enumerate(node.children):
                nxt = f"{me}_alt{i}" if i + 1 < len(node.children) else fail
                out += self._compile_tree(owner, c, ids, nxt, _ctr, on_select)
                if i + 1 < len(node.children):
                    out.append(label(nxt))
            return out
        if isinstance(node, Sequence):
            for i, c in enumerate(node.children):
                if isinstance(c, Do) and i + 1 != len(node.children):
                    raise BehaviorError(
                        f"{owner}: v1 is reactive — a Do must be the LAST child of its "
                        f"Sequence (no action-result plumbing yet)")
                out += self._compile_tree(owner, c, ids, fail, _ctr, on_select)
            return out
        if isinstance(node, Cond):
            return [_stmt(node.text), (JMP_IFNOT, fail)]
        if isinstance(node, Invert):
            return [_stmt(node.child.text), (JMP_IF, fail)]
        if isinstance(node, Once):
            leaf = _terminal_do(node.child)
            if leaf is not None and isinstance(leaf.action, (Announce, Award, ShopStock, ShopSynth, Sfx, Flash, StopTimer)):
                # THE EVENT ONCE (BTTABLE round-2 law): over an Announce/Award,
                # "once" means fire-and-release — the sticky form over a MONOTONIC
                # cond (a kill tally, a spent wave counter) would hold the selection
                # forever and STARVE every branch below it. Selection edge-latches
                # the request; the one-shot lane fires it when the level frees;
                # the dispatch body sets THIS latch itself, releasing the branch.
                # The LATCH is body-written — it must stay outside-addressable
                # (GLOB / strided cell); the REQUEST is brain-private and rides
                # the Instance block under brains. Once-per-member either way.
                aid = ids[id(leaf.action)]
                latch_r = self._sticky_flag(owner, f"once.{node.name}")
                req_r = (self._inst_ref(owner, f"areq{aid}") if self.brains
                         else self._sticky_flag(owner, f"areq{aid}"))
                extra = (on_select or []) + [_stmt(f"{req_r} const(1) B_LET")]
                return ([_stmt(latch_r), (JMP_IF, fail)]
                        + self._compile_tree(owner, node.child, ids, fail, _ctr, extra))
            # STICKY semantics (rung-1 design fix), for FEED behaviors: a reactive
            # ticker re-selects every tick, so a select-time latch would fire for
            # ONE tick. Instead: selecting the child ENGAGES; while engaged the gate
            # is bypassed (the child's own conditions keep deciding); the first
            # child-FAIL while engaged disengages and latches — "chase me while I'm
            # near, never again once I escape". Under brains the latch pair is
            # SEQ-PRIVATE (Instance vars — per member for free, zeroed at
            # spawn); v1 keeps the reset-listed GLOBs byte-for-byte.
            if self.brains:
                latch_r = self._inst_ref(owner, f"once.{node.name}")
                eng_r = self._inst_ref(owner, f"onceeng.{node.name}")
            else:
                latch_r = self._sticky_flag(owner, f"once.{node.name}")
                eng_r = self._sticky_flag(owner, f"onceeng.{node.name}")
            myfail = f"{me}_dfail"
            ff = f"{me}_dff"
            extra = (on_select or []) + [_stmt(f"{eng_r} const(1) B_LET")]
            return ([_stmt(latch_r), (JMP_IF, myfail)]
                    + self._compile_tree(owner, node.child, ids, myfail, _ctr, extra)
                    + [label(myfail),
                       _stmt(eng_r), (JMP_IFNOT, ff),
                       _stmt(f"{eng_r} const(0) B_LET"),
                       _stmt(f"{latch_r} const(1) B_LET"),
                       label(ff), (JMP, fail)])
        if isinstance(node, Cooldown):
            # sticky like Once: engage on select, and start the TIMER at DISENGAGE
            # (the child failing while engaged), so the cooldown measures time since
            # the behavior ENDED, not since it began. Under brains the timer is
            # SEQ-PRIVATE and the BRAIN decrements it (same Wait(tick) cadence
            # as the central clock; it holds while the unit is inactive — a
            # dead unit's cooldown freezing is unobservable, dead units select
            # nothing). v1 keeps the central-clock GLOB byte-for-byte.
            if self.brains:
                t_r = self._inst_ref(owner, f"cd{_ctr[0]}")
                bc = self._brain_cooldowns.setdefault(owner, [])
                if t_r not in bc:                        # compile() may re-run
                    bc.append(t_r)
                eng_r = self._inst_ref(owner, f"cdeng{_ctr[0]}")
            else:
                name = f"{owner}.cd{_ctr[0]}"
                t = self.bb.byte(name)
                if name not in [n for n, _f in self._cooldowns]:
                    self._cooldowns.append((name, node.frames))
                t_r = f"Global.Byte[{t}]"
                eng_r = self._sticky_flag(owner, f"cdeng{_ctr[0]}")
            myfail = f"{me}_dfail"
            ff = f"{me}_dff"
            extra = (on_select or []) + [_stmt(f"{eng_r} const(1) B_LET")]
            return ([_stmt(f"{t_r} const(0) B_EQ {eng_r} B_OROR"),
                     (JMP_IFNOT, fail)]
                    + self._compile_tree(owner, node.child, ids, myfail, _ctr, extra)
                    + [label(myfail),
                       _stmt(eng_r), (JMP_IFNOT, ff),
                       _stmt(f"{eng_r} const(0) B_LET"),
                       _stmt(f"{t_r} const({int(node.frames)}) B_LET"),
                       label(ff), (JMP, fail)])
        if isinstance(node, Do):
            aid = ids[id(node.action)]
            out = list(on_select or [])
            out.append(self._uset(owner, "selected", aid))
            if isinstance(node.action, Battle):
                # EDGE-LATCH the request at selection — the branch may be outranked
                # next tick by its own raise_flags (the siege round-1 clobber); the
                # dispatch tail's request lane fires it when level 4 frees.
                # Brain-private: Instance under brains.
                breq_r = (self._inst_ref(owner, f"breq{aid}") if self.brains
                          else self._sticky_flag(owner, f"breq{aid}"))
                out.append(_stmt(f"{breq_r} const(1) B_LET"))
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
                if node.action.speed is not None:
                    spd_v = int(node.action.speed)
                    if not 1 <= spd_v <= 255:
                        raise BehaviorError(f"{owner}: action speed must be 1..255")
                    out.append(self._uset(owner, "spd", spd_v))
                elif owner in self.classes:
                    # no per-action speed -> each member falls back to its OWN
                    # default: a seeded per-member cell read (members of one
                    # class may carry different walk_speeds)
                    spd0 = f"{_cnum(self._cls_spd0_tid(owner))} {MYUID} B_VECTOR"
                    out.append(_stmt(f"{self._uref(owner, 'spd')} {spd0} B_LET"))
                else:
                    spd_v = int(self.units[owner].walk_speed)
                    out.append(self._uset(owner, "spd", spd_v))
                out += self._feed_effect(owner, node.action)
            else:
                # selecting a DISPATCH action HALTS the duty walk the same tick (feed
                # own mirror) — otherwise the stale target keeps pulling the unit for
                # the tick(s) until the body preempts (rung-1 playtest: duelists
                # carried momentum into near-overlap)
                out += [_stmt(f"{self._uref(owner, 'tx')} {self._mx(owner)} B_LET"),
                        _stmt(f"{self._uref(owner, 'tz')} {self._mz(owner)} B_LET")]
            out.append((JMP, f"t_{owner}_selected"))
            return out
        raise BehaviorError(f"unknown node {type(node).__name__}")

    def _acquire_block(self, owner: str, e: Engage) -> list:
        """THE ACQUIRE LOOP (per engage owner, inside its active gate, before the
        tree): keep a STILL-VALID target (alive, active, within radius — the
        sticky fast path most ticks take), else scan the roster FIRST-IN-RANGE
        in roster order (v1 pair-branch parity: roster order is the priority
        list). All reads index the group tables by a live byte — the rung-0
        composition doing per-unit perception. For a CLASS owner the target
        register strides (one per member); the loop byte stays ONE shared GLOB
        scratch — Seqs execute sequentially and the loop never crosses a Wait."""
        g = self._groups[e.group]
        n = len(g.units)
        ctgt_r = self._uref(owner, "ctgt")
        li = self.bb.byte(f"{owner}.gscan")
        pxc = f"{_cnum(g.px_tid)} {ctgt_r} B_VECTOR"
        pzc = f"{_cnum(g.pz_tid)} {ctgt_r} B_VECTOR"
        pxl = f"{_cnum(g.px_tid)} Global.Byte[{li}] B_VECTOR"
        pzl = f"{_cnum(g.pz_tid)} Global.Byte[{li}] B_VECTOR"
        A = f"t_{owner}_aq"
        return [
            _stmt(f"{ctgt_r} const(255) B_LT"), (JMP_IFNOT, f"{A}_scan"),
            _stmt(f"{_cnum(g.act_tid)} {ctgt_r} B_VECTOR const(1) B_EQ"),
            (JMP_IFNOT, f"{A}_drop"),
            _stmt(f"{_cnum(g.hp_tid)} {ctgt_r} B_VECTOR const(0) B_GT"),
            (JMP_IFNOT, f"{A}_drop"),
            _stmt(_box(self._mx(owner), self._mz(owner), pxc, pzc, int(e.radius))),
            (JMP_IF, f"{A}_end"),
            label(f"{A}_drop"),
            _stmt(f"{ctgt_r} const(255) B_LET"),
            label(f"{A}_scan"),
        ] + (self._acquire_scan_nearest(owner, e, g, n, ctgt_r, li, pxl, pzl, A)
             if e.nearest else [
            _set_byte(li, 0),
            label(f"{A}_top"),
            _stmt(f"{_cnum(g.act_tid)} Global.Byte[{li}] B_VECTOR const(1) B_EQ"),
            (JMP_IFNOT, f"{A}_nxt"),
            _stmt(f"{_cnum(g.hp_tid)} Global.Byte[{li}] B_VECTOR const(0) B_GT"),
            (JMP_IFNOT, f"{A}_nxt"),
            _stmt(_box(self._mx(owner), self._mz(owner), pxl, pzl, int(e.radius))),
            (JMP_IFNOT, f"{A}_nxt"),
            _stmt(f"{ctgt_r} Global.Byte[{li}] B_LET"),
            (JMP, f"{A}_end"),
            label(f"{A}_nxt"),
            _stmt(f"Global.Byte[{li}] Global.Byte[{li}] const(1) B_PLUS B_LET"),
            _stmt(f"Global.Byte[{li}] const({n}) B_LT"),
            (JMP_IF, f"{A}_top"),
            _stmt(f"{ctgt_r} const(255) B_LET"),
        ]) + [
            label(f"{A}_end"),
        ]

    def _acquire_scan_nearest(self, owner: str, e: Engage, g: GroupSpec, n: int,
                              ctgt_r: str, li: int, pxl: str, pzl: str, A: str) -> list:
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
            _stmt(f"Global.Int16[{dx}] {pxl} {self._mx(owner)} B_MINUS B_LET"),
            _stmt(f"Global.Int16[{dx}] const(0) B_LT"),
            (JMP_IFNOT, f"{A}_nax"),
            _stmt(f"Global.Int16[{dx}] const(0) Global.Int16[{dx}] B_MINUS B_LET"),
            label(f"{A}_nax"),
            _stmt(f"Global.Int16[{dz}] {pzl} {self._mz(owner)} B_MINUS B_LET"),
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
            _stmt(f"{ctgt_r} Global.Byte[{idx}] B_LET"),
        ]

    def _wp_ref(self, owner: str) -> str:
        """The Patrol/March waypoint-progress slot: SEQ-PRIVATE under brains
        (each member/brain walks the shared route at its OWN progress, zeroed
        at spawn); a reset-listed GLOB byte in v1."""
        if self.brains:                                  # classes imply brains
            return self._inst_ref(owner, "wp")
        idx = self.bb.byte(f"{owner}.wp")
        if idx not in self._reset_bytes:                 # out-of-range wp resets to 0
            self._reset_bytes.append(idx)
        return f"Global.Byte[{idx}]"

    def _feed_effect(self, owner: str, a: Action) -> list:
        tx_r = self._uref(owner, "tx")
        tz_r = self._uref(owner, "tz")
        if isinstance(a, (WalkTo, Hold)):
            x, z = a.point
            return [_stmt(f"{tx_r} const({int(x)}) B_LET"),
                    _stmt(f"{tz_r} const({int(z)}) B_LET")]
        if isinstance(a, HoldPost):
            return [_stmt(f"{tx_r} {self._uref(owner, 'px')} B_LET"),
                    _stmt(f"{tz_r} {self._uref(owner, 'pz')} B_LET")]
        if isinstance(a, _GroupPursue):
            e = a.engage
            g = self._groups[e.group]
            ctgt_r = self._uref(owner, "ctgt")
            pxc = f"{_cnum(g.px_tid)} {ctgt_r} B_VECTOR"
            pzc = f"{_cnum(g.pz_tid)} {ctgt_r} B_VECTOR"
            self._label_ctr += 1
            L = f"t_{owner}_gp{self._label_ctr}"
            # walk toward the target's TABLE position (live retarget — the
            # mirrors refresh the cells each pass). In contact the swing branch
            # outranks this one, and its dispatch-halt feeds the own mirror, so
            # no standoff clause is needed here. Belt: no target -> hold ground
            # (the engage subtree's valid-cond makes this unreachable).
            return [_stmt(f"{ctgt_r} const(255) B_LT"),
                    (JMP_IFNOT, f"{L}_own"),
                    _stmt(f"{tx_r} {pxc} B_LET"),
                    _stmt(f"{tz_r} {pzc} B_LET"),
                    (JMP, f"{L}_end"),
                    label(f"{L}_own"),
                    _stmt(f"{tx_r} {self._mx(owner)} B_LET"),
                    _stmt(f"{tz_r} {self._mz(owner)} B_LET"),
                    label(f"{L}_end")]
        if isinstance(a, Chase):
            self._check_unit(a.target)
            gate = (f"Global.Bit[{self._staged}]" if a.target == PLAYER
                    else self._uref(a.target, "active"))
            self._label_ctr += 1
            skip = f"t_{owner}_ch{self._label_ctr}"
            near_lbl = f"t_{owner}_chs{self._label_ctr}"
            return [_stmt(gate), (JMP_IFNOT, skip),
                    # inside standoff: hold ground (feed own mirror) — pursuers must
                    # never occupy the target's tile (rung-1 playtest: phasing)
                    _stmt(_box(self._mx(owner), self._mz(owner),
                               self._mx(a.target), self._mz(a.target), int(a.standoff))),
                    (JMP_IFNOT, near_lbl),
                    _stmt(f"{tx_r} {self._mx(owner)} B_LET"),
                    _stmt(f"{tz_r} {self._mz(owner)} B_LET"),
                    (JMP, skip),
                    label(near_lbl),
                    _stmt(f"{tx_r} {self._mx(a.target)} B_LET"),
                    _stmt(f"{tz_r} {self._mz(a.target)} B_LET"),
                    label(skip)]
        if isinstance(a, Flee):
            self._check_unit(a.threat)
            gate = (f"Global.Bit[{self._staged}]" if a.threat == PLAYER
                    else self._uref(a.threat, "active"))
            self._label_ctr += 1
            L = f"t_{owner}_fl{self._label_ctr}"
            p0x, p0z = a.points[0]
            out = [_stmt(gate), (JMP_IFNOT, f"{L}_ng")]  # threat gone -> primary refuge
            for i, (px, pz) in enumerate(a.points[:-1]):
                out += [_stmt(_box(self._mx(a.threat), self._mz(a.threat),
                                   int(px), int(pz), int(a.avoid_r))),
                        (JMP_IF, f"{L}_n{i}"),           # threat camps it -> next refuge
                        _stmt(f"{tx_r} const({int(px)}) B_LET"),
                        _stmt(f"{tz_r} const({int(pz)}) B_LET"),
                        (JMP, f"{L}_end"),
                        label(f"{L}_n{i}")]
            lx, lz = a.points[-1]
            out += [_stmt(f"{tx_r} const({int(lx)}) B_LET"),
                    _stmt(f"{tz_r} const({int(lz)}) B_LET"), (JMP, f"{L}_end"),
                    label(f"{L}_ng"),
                    _stmt(f"{tx_r} const({int(p0x)}) B_LET"),
                    _stmt(f"{tz_r} const({int(p0z)}) B_LET"),
                    label(f"{L}_end")]
            return out
        if isinstance(a, Wander):
            cx, cz = int(a.center[0]), int(a.center[1])
            if self.brains:
                # SEQ-PRIVATE wander state (classes imply brains): the zeroed
                # timer means the FIRST selection rolls a fresh target before
                # the feed reads it — the center preset the v1 GLOBs carry is
                # a belt this path never needs
                wtx_r = self._inst_ref(owner, "wtx", "int16")
                wtz_r = self._inst_ref(owner, "wtz", "int16")
                wt_r = self._inst_ref(owner, "wtimer")
            else:
                wtx_r = self._uref(owner, "wtx")
                wtz_r = self._uref(owner, "wtz")
                wt_r = self._uref(owner, "wtimer")
                wt = self.bb.byte(f"{owner}.wtimer")
                if wt not in self._reset_bytes:          # 0 -> fresh roll on first select
                    self._reset_bytes.append(wt)
                self._preset16.setdefault(self.bb.int16(f"{owner}.wtx"), cx)
                self._preset16.setdefault(self.bb.int16(f"{owner}.wtz"), cz)
            self._label_ctr += 1
            L = f"t_{owner}_wn{self._label_ctr}"
            roll = (f"const(128) B_MINUS const({int(a.radius)}) B_MULT "
                    f"const(128) B_DIV B_PLUS B_LET")
            return [
                _stmt(f"{wt_r} const(0) B_GT"), (JMP_IFNOT, f"{L}_roll"),
                _stmt(f"{wt_r} {wt_r} const(1) B_MINUS B_LET"),
                (JMP, f"{L}_feed"),
                label(f"{L}_roll"),
                _stmt(f"{wt_r} const({int(a.hold)}) B_LET"),
                _stmt(f"{wtx_r} const({cx}) B_SYSVAR[0] {roll}"),
                _stmt(f"{wtz_r} const({cz}) B_SYSVAR[0] {roll}"),
                label(f"{L}_feed"),
                _stmt(f"{tx_r} {wtx_r} B_LET"),
                _stmt(f"{tz_r} {wtz_r} B_LET"),
            ]
        if isinstance(a, March):
            wp_r = self._wp_ref(owner)               # shared with Patrol
            self._label_ctr += 1
            p = f"t_{owner}_m{self._label_ctr}"
            out: list = []
            n = len(a.points)
            for i, (px, pz) in enumerate(a.points):
                out += [_stmt(f"{wp_r} const({i}) B_EQ"),
                        (JMP_IFNOT, f"{p}_w{i}")]
                if i < n - 1:                        # advance on arrival, except last
                    out += [_stmt(_box(self._mx(owner), self._mz(owner),
                                       int(px), int(pz), a.arrive_r)),
                            (JMP_IFNOT, f"{p}_f{i}"),
                            _stmt(f"{wp_r} const({i + 1}) B_LET"),
                            (JMP, f"{p}_end"),
                            label(f"{p}_f{i}")]
                out += [_stmt(f"{tx_r} const({int(px)}) B_LET"),
                        _stmt(f"{tz_r} const({int(pz)}) B_LET"),
                        (JMP, f"{p}_end"),
                        label(f"{p}_w{i}")]
            out += [_stmt(f"{wp_r} const(0) B_LET"), label(f"{p}_end")]
            return out
        if isinstance(a, Patrol):
            wp_r = self._wp_ref(owner)
            self._label_ctr += 1
            p = f"t_{owner}_p{self._label_ctr}"
            out: list = []
            n = len(a.points)
            for i, (px, pz) in enumerate(a.points):
                out += [_stmt(f"{wp_r} const({i}) B_EQ"), (JMP_IFNOT, f"{p}_w{i}")]
                out += [_stmt(_box(self._mx(owner), self._mz(owner),
                                   int(px), int(pz), a.arrive_r)),
                        (JMP_IFNOT, f"{p}_f{i}"),
                        _stmt(f"{wp_r} const({(i + 1) % n}) B_LET"),
                        (JMP, f"{p}_end")]
                out += [label(f"{p}_f{i}"),
                        _stmt(f"{tx_r} const({int(px)}) B_LET"),
                        _stmt(f"{tz_r} const({int(pz)}) B_LET"),
                        (JMP, f"{p}_end"),
                        label(f"{p}_w{i}")]
            out += [_stmt(f"{wp_r} const(0) B_LET"), label(f"{p}_end")]
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
        from ..eb.model import EbScript
        from . import object as _object
        cb = compiled or self.compile()
        baseline = {str(p) for p in eblint.lint_eb(bytes(eb_bytes))}
        out = self._announce_player_bound(bytes(eb_bytes))
        brain_slots: dict[str, int] = {}
        for name, body in cb.brain_bodies.items():
            # a brain is a dormant one-function code entry (never InitObject'd):
            # it exists only as the STARTSEQ target for its unit's tag-1 head.
            # A CLASS seats ONE entry here — every member STARTSEQs the same
            # slot, each spawn its own Seq with its own caller (P3's shape).
            # ``loc`` sizes the entry's varn = EACH Seq's private Instance
            # block (the brain-private latches/timers/wander state).
            bentry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
            out, brain_slots[name] = _object.seat_entry(
                out, bentry, loc=int(cb.brain_locs.get(name, 0)))
        for u in self.units.values():
            duty = cb.duty_bodies[u.name]
            if cb.brain_bodies:
                # tag-1 head spawns the brain ONCE (tag-1 starts once per object
                # life; a pooled re-activation re-runs it, and STARTSEQ replacing
                # the prior Seq is exactly the reset wanted)
                duty = opcodes.run_shared_script(
                    brain_slots[self._clsof.get(u.name, u.name)]) + duty
            out = eb_edit.replace_function_body(out, u.entry, 1, duty)
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
        if cb.brain_bodies:
            occupied = {e.index for e in EbScript.from_bytes(out).entries if e.size > 0}
            check_64_stride(occupied, self.units.values())
        fresh = [p for p in eblint.lint_eb(out)
                 if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
        if fresh:
            raise BehaviorError("install produced NEW lint errors:\n"
                                + "\n".join(map(str, fresh)))
        return out

    def _oneshot_ref(self, owner: str, member: str, key: str) -> str:
        """A one-shot latch/request ref in MEMBER context (dispatch bodies run
        ON the member): the class table's cell at the member's CONSTANT uid —
        the same cell the brain reads strided — or the owner's GLOB flag
        (owner == member for a unit owner)."""
        if owner in self.classes:
            return (f"{_cnum(self._cls_tid_for(owner, key))} "
                    f"{_cnum(self.units[member].entry)} B_VECTOR")
        return f"Global.Bit[{self.bb.flag(f'{owner}.{key}')}]"

    def _oneshot_work(self, a: Action, who: str) -> list:
        """The GLOBAL work of a one-shot action — the ops between the latch/
        run(255) prologue and the run(0) epilogue, shared verbatim by the
        member-body path (v1 + looping variants) and the rung-5 INLINE path.
        Every op here is context-free by audit: a battle id, a window, a
        sound, a screen fade, the timer, gil/item/shop — global or
        explicitly-uid'd, never a bare actor op (which binds gCur/gExec and
        therefore CANNOT move between a member body and the brain Seq)."""
        if isinstance(a, Battle):
            return [opcodes.encode(0x2A, 0, int(a.scene))]  # Battle(0, scene) =
        if isinstance(a, Award):                            # 559's tread shape
            from . import event as _event
            pay: list = []
            if int(a.gil):
                pay.append(opcodes.add_gil(int(a.gil)))
            if a.item is not None:
                pay.append(_event.give_item(a.item, int(a.count)))
            return pay
        if isinstance(a, ShopStock):
            from .. import items as _items
            iid = _items.resolve(a.item)
            ops = [opcodes.encode(0x115, int(a.shop), iid, 0)]   # remove first —
            if a.add:                                            # List.Add dupes,
                ops.append(opcodes.encode(0x115, int(a.shop), iid, 1))  # so idempotent
            return ops
        if isinstance(a, ShopSynth):
            if isinstance(a.synth, str):
                from .. import items as _items
                sid = self.synth_mints.get(_items.resolve(a.synth))
                if sid is None:
                    raise BehaviorError(
                        f"{who}: shop_synth recipe {a.synth!r} did not resolve — "
                        f"string selectors match this project's [[synthesis]] result "
                        f"names and need a reachable install at build (the minted-id "
                        f"floor comes from the base Synthesis.csv); a vanilla row "
                        f"takes its int id instead")
            else:
                sid = int(a.synth)
            ops = [opcodes.encode(0x116, int(a.shop), sid, 0)]   # remove-then-add:
            if a.add:                                            # same List dupe
                ops.append(opcodes.encode(0x116, int(a.shop), sid, 1))
            return ops
        if isinstance(a, Announce):
            return (([opcodes.wait(int(a.delay))] if a.delay else [])
                    + [opcodes.window_async(a.window, 128, int(a.txid))]
                    + ([opcodes.wait(int(a.sustain))] if a.sustain else []))
        if isinstance(a, StopTimer):
            return [opcodes.encode(OP_RUN_TIMER, 0)]
        if isinstance(a, Flash):
            r, g, bl = a.rgb
            return [
                opcodes.encode(0xA9, PLAYER_UID),        # stock runs CalcScreenPos
                opcodes.encode(0xEC, 0, FLASH_OUT_FRAMES, 255, r, g, bl),
                opcodes.wait(FLASH_OUT_FRAMES + 1),      # before EACH FadeFilter;
            ] + ([opcodes.wait(int(a.pause))] if a.pause else []) + [
                opcodes.encode(0xA9, PLAYER_UID),        # Wait(25) = field 682's
                opcodes.encode(0xEC, 1, FLASH_IN_FRAMES, 255, 0, 0, 0),  # out + 1
                opcodes.wait(FLASH_IN_FRAMES),
            ]
        if isinstance(a, Sfx):
            play = opcodes.encode(RUN_SOUND_CODE3, int(a.bank), int(a.sound),
                                  *SFX_PARAMS)
            if a.sustain:
                play += opcodes.wait(int(a.sustain))     # hold: queued one-shots
            return [play]                                # wait their turn
        raise BehaviorError(f"no one-shot work for {type(a).__name__}")

    def _dispatch_body(self, owner: str, u: UnitSpec, a: Action, aid: int,
                       oneshot_latch: str | None = None) -> bytes:
        """One dispatch-action body for MEMBER ``u`` of tree-owner ``owner``
        (owner == u.name for an unclassed unit). Bodies always run ON the
        member, so every protocol ref is the member's own — a classed member
        reads its cells at its CONSTANT uid. ``oneshot_latch`` is a latch slot
        KEY (event-Once actions); the body resolves it in member context."""
        sel_r = self._uref(u.name, "selected")
        run_r = self._uref(u.name, "running")
        latch_ref = (self._oneshot_ref(owner, u.name, oneshot_latch)
                     if oneshot_latch is not None else None)

        def set_run(v: int) -> bytes:
            return self._uset(u.name, "running", v)
        head: list = [set_run(aid), label("loop"),
                      _stmt(f"{sel_r} const({aid}) B_EQ"),
                      (JMP_IFNOT, "out")]
        tail: list = [label("wait"), opcodes.wait(1), (JMP, "loop"),
                      label("out"), set_run(0), opcodes.RETURN]
        if isinstance(a, Die):
            bump: list = []
            if a.count is not None:
                # the body runs once ever (the entry terminates) — edge-safe free
                cell = self._counter_ref(a.count)
                bump = [_stmt(f"{cell} {cell} const(1) B_PLUS B_LET")]
            # THE DEATH BEAT: the corpse plays its clip and lingers BEFORE the
            # entry terminates. active=0 already ran, so it is inert while it
            # falls (nothing targets it, its mirror stops) — the body holds the
            # dispatch level throughout, which is exactly what we want: a dying
            # unit does nothing else.
            # THE DEATH POSE (rung-E round 3 → 4, both halves playtest-driven):
            #   * NO WaitAnimation — blocking the level-4 body in WAITANIM
            #     rendered nothing at all (round 2). Fire-and-forget renders.
            #   * RunAnimation ALONE is not enough either. A one-shot ENDS, and
            #     the object then reverts to its STAND clip — round 3's soldier
            #     knelt, stood back up, and only then vanished. And a unit that
            #     dies mid-march is still driven by a blocked Walk, whose WALK
            #     clip overrode the one-shot entirely — round 3's raiders showed
            #     no clip at all. So the death clip is installed as the object's
            #     stand AND walk animation first (the same 0x33/0x34 setters the
            #     NPC Init uses for its movement slots): whatever the engine
            #     drives next, it drives THIS clip, and the pose holds until the
            #     corpse is removed.
            #   * and it must FREEZE AT END, or the corpse replays its death
            #     over and over for the whole linger (round 4: "loop their death
            #     animation 3 times") — a STAND clip loops by definition.
            #     SetAnimationFlags(1, 0) is the engine's freeze-at-end mode and
            #     the exact idiom content.chest uses before its lid clip.
            fall: list = []
            if a.anim is not None:
                fall += [
                    opcodes.encode(OP_SET_STAND_ANIM, int(a.anim)),
                    opcodes.encode(OP_SET_WALK_ANIM, int(a.anim)),
                    opcodes.encode(OP_SET_ANIM_FLAGS, ANIM_HOLD, 0),
                    opcodes.encode(OP_RUN_ANIMATION, int(a.anim)),
                ]
            if a.linger:
                fall.append(opcodes.wait(int(a.linger)))
            return asm([
                self._uset(u.name, "active", 0),         # mirrors stop first
                # HOLD THE LEVEL for the whole death beat and NEVER release it: a
                # dead unit must never dispatch again. Without this the ticker sees
                # run==0 while the corpse falls and keeps dispatching the unit's
                # OTHER bodies — the rung-E playtest's "soldiers still swing after
                # the death anim starts" (harmless when the body was instantaneous,
                # a real bug the moment it blocks).
                set_run(255),
            ] + bump + fall + [
                # THE ORPHAN-BRAIN LAW (brains mode): TerminateEntry(255) DISPOSES
                # this unit, and DisposeObj does NOT cascade to its brain Seq at
                # uid+64 — the orphan NREs the engine on its next tick (DoEventCode
                # derefs gCur unconditionally). StopSharedScript keys off gExec =
                # this unit, so it kills exactly OUR brain. Stock emits 0x45 as a
                # single bare byte (field 450, three grammars agreeing).
            ] + ([opcodes.encode(0x45)] if self.brains else []) + [
                opcodes.terminate_entry(255),
                opcodes.RETURN,
            ])
        if isinstance(a, Battle):
            blatch = self._oneshot_ref(owner, u.name, f"battled{aid}")
            return asm([
                _stmt(f"{blatch} const(1) B_LET"),       # one-shot: set BEFORE the
                set_run(255),                     # suspend, so a return can
            ] + self._oneshot_work(a, u.name) + [        # never re-fire it
                set_run(0),
                opcodes.RETURN,
            ])
        if isinstance(a, HoldGround):
            return asm(head + tail)                       # pure pin: idle while selected
        if isinstance(a, (Award, ShopStock, ShopSynth)):
            if oneshot_latch is None:                     # unreachable (the map
                raise BehaviorError(                      # refused it) — belt+braces
                    f"{u.name}: {type(a).__name__} must be Once-wrapped")
            return asm([
                _stmt(f"{latch_ref} const(1) B_LET"),              # latch FIRST — pay once ever
                set_run(255),
            ] + self._oneshot_work(a, u.name) + [
                set_run(0),
                opcodes.RETURN,
            ])
        if isinstance(a, (Announce, StopTimer, Flash, Sfx)):
            work = self._oneshot_work(a, u.name)
            if oneshot_latch is not None:
                # the EVENT-Once variant: latch FIRST (Battle's one-shot shape —
                # a re-request can never re-fire), do the work (an announce
                # window is async — it persists on screen without a body
                # idling), release the level. delay/sustain hold the level
                # around the open — queued one-shots (the NEXT staged line, a
                # Battle) fire when it drops.
                return asm([
                    _stmt(f"{latch_ref} const(1) B_LET"),
                    set_run(255),
                ] + work + [
                    set_run(0),
                    opcodes.RETURN,
                ])
            return asm(head[:1] + work
                       + [label("loop"),
                          _stmt(f"{sel_r} const({aid}) B_EQ"),
                          (JMP_IFNOT, "out"),
                          opcodes.wait(1), (JMP, "loop"),
                          label("out"), set_run(0), opcodes.RETURN])
        if isinstance(a, SwingAt):
            self._check_unit(a.target)
            if a.target == PLAYER:
                raise BehaviorError("SwingAt(player) is not a v1 action")
            t_hp = self._hp_ref(a.target)      # Global byte, or a roster/class hp CELL
            t_act = self._uref(a.target, "active")
            timer = self.bb.byte(f"{u.name}.swing{aid}")
            if timer not in self._reset_bytes:
                self._reset_bytes.append(timer)
            work: list = [
                _stmt(t_act), (JMP_IFNOT, "out"),
                _stmt(f"{t_hp} const(0) B_GT"), (JMP_IFNOT, "out"),
                _stmt(f"Global.Byte[{timer}] Global.Byte[{timer}] const(1) B_PLUS B_LET"),
                _stmt(f"Global.Byte[{timer}] const({a.interval}) B_LT"),
                (JMP_IF, "wait"),
                _set_byte(timer, 0),
                opcodes.turn_toward_object(self.units[a.target].entry, 16),
                _stmt(f"{t_hp} {t_hp} const({a.damage}) B_MINUS B_LET"),
            ] + self._swing_theater(a.anim, a.hit_sfx)
            return asm(head + work + tail)
        if isinstance(a, _GroupSwing):
            e = a.engage
            g = self._groups[e.group]
            ctgt_r = self._uref(u.name, "ctgt")          # the MEMBER's register
            timer = self.bb.byte(f"{u.name}.gswing")
            if timer not in self._reset_bytes:
                self._reset_bytes.append(timer)
            actc = f"{_cnum(g.act_tid)} {ctgt_r} B_VECTOR"
            hpc = f"{_cnum(g.hp_tid)} {ctgt_r} B_VECTOR"
            pxc = f"{_cnum(g.px_tid)} {ctgt_r} B_VECTOR"
            pzc = f"{_cnum(g.pz_tid)} {ctgt_r} B_VECTOR"
            # the SwingAt body generalized by the target REGISTER: every read
            # and the damage write index the roster tables through ctgt. Facing
            # is TurnTowardPosition on the target's TABLE position — pure data,
            # no uid, the player-ref law never enters.
            work = [
                _stmt(f"{ctgt_r} const(255) B_LT"), (JMP_IFNOT, "out"),
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
            ] + self._swing_theater(e.anim, e.hit_sfx)
            return asm(head + work + tail)
        raise BehaviorError(f"no dispatch body for {type(a).__name__}")

    @staticmethod
    def _swing_theater(anim, hit_sfx) -> list:
        """The strike's clip + impact cue, emitted on the DAMAGE tick (inside the
        interval gate — never per frame). The clip is FIRE-AND-FORGET: no
        ``WaitAnimation``, so the swing loop keeps ticking its sel-check and the
        unit can still be retargeted or preempted mid-clip (a blocked wait here
        would make every strike an uninterruptible commitment, and a LOOPING
        clip would wedge the body outright)."""
        out: list = []
        if anim is not None:
            out.append(opcodes.encode(OP_RUN_ANIMATION, int(anim)))
        if hit_sfx is not None:
            out.append(opcodes.encode(RUN_SOUND_CODE3, SFX_BANK, int(hit_sfx),
                                      *SFX_PARAMS))
        return out
