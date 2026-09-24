"""Computed prop motion -- ``[[prop]] motion`` (the sine kit, studies/sine-kit, board entry #7).

A prop can ORBIT a point, SHUTTLE between two points, BOB up and down, SPIN or SWING its facing -- channels that
compose -- driven by ONE per-field daemon entry that re-places every mover each tick with ``MoveInstantXZYEx`` (0xAD)
and ``TurnInstantEx`` (0x87) from ``B_SIN2`` / ``B_COS2``. This module is the single owner of the math: the build
emits the daemon from it, and the report, the CLI, the tests and the in-game harness all read the same
:func:`pose`, which predicts every frame EXACTLY (rung 0 proved the engine's float32 ``rsin`` in-game, C1 + C7).

THE MECHANISM (engine-read, Memoria Assembly-CSharp; studies/sine-kit/PLAN.md):
  ``B_SIN2(v)`` = ``ff9.rsin(v)`` = ``(Int32)(Mathf.Sin(v / 4096f * 360f * 0.0174532924f) * 4096f)`` -- 4096 a turn,
  amplitude +-4096, single precision, truncated (EBin.cs:1087-1100, ff9.cs:2124-2138). ``B_DIV`` truncates toward
  zero; ``B_CONST`` is a sign-extended Int16; expression values decode as signed 26-bit (EBin.cs:1682).
  ``0xAD(uid, a, b, c)`` sets ``pos = (a, -b, c)`` after turning pathing OFF, and ``obj(uid).f[1]`` reads ``b`` back;
  ``0x87(uid, v)`` faces ``(Int16)(v << 4)`` -- the byte is ``v mod 256`` (0 south, 64 west, 128 north, 192 east).

THE LAWS (each enforced at a call site here; the tests kill each one's removal):
  NOVEL-FIELD  motion only where the engine's effective id is the field's own custom id (no fork, no donor) --
               0xAD / 0x87 carry per-field hotfix branches keyed on EffectiveFieldId, two of which dereference the
               null ``actor`` of a code entry. Custom ids never match a stock id: table-free.
  NULL-TARGET  0xAD has no null guard: every mover exists for the whole visit -- unconditional, unattached,
               single-part (no requires_flag, attach_to or composite).
  SLOT-MAP     the daemon moves exactly the objects the toml meant: each recorded slot's SetModel is its model.
  STRAIGHT-LINE INIT  every op of a mover's Init is in :data:`MOVER_INIT_OPS` (no yield), one SetModel before one
               CreateObject, ending in RETURN -- so the whole Init completes in the frame it first runs.
  ORDER        the daemon's InitCode sits in Main_Init after EVERY mover's InitObject on every path (proved by
               dominance over the FINAL bytes) -- objects first run the frame after creation, in creation order, so
               each mover's Init (SetModel + CreateObject) completes before the daemon's tick 0 writes pose(0). This
               replaces rung 0's latch: the daemon reads NOTHING outside its own locals, so there is nothing to
               latch on (and a movement latch would freeze props through every entry cutscene).
  64-STRIDE    a STARTSEQ (0x43) from entry S-64 creates a Seq at uid S and disposes what holds it: no mover or
               daemon slot may sit 64 above an entry that runs one (a ladder climb in the player entry does).
  ZERO SHARED STATE  the daemon's only state is its own Instance.Int16 clocks at byte offsets 0, 2, ..., 2K-2;
               its opcodes and tokens are audited on the emitted bytes (no obj() reads, no Global/Map, no sysvar).
  REDUCTION + ENVELOPE  every trig argument is masked into [0, 4095] (where float32 rsin == the exact truncated
               sine: the predictor is an integer table); radius/amp/half-extent <= EXPR_VALUE_MAX // 4096.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import NamedTuple

from .. import prop_archetypes as _prop_archetypes
from ..eb import EbScript, disasm as D, edit as eb_edit, exprasm, opcodes
from ..eb.labelasm import JMP, asm, label


class MotionError(ValueError):
    """A ``[[prop]] motion`` the kit refuses (the message names the prop and the law)."""


# ============================================================== the engine's arithmetic
def _f32(x: float) -> float:
    """Round to IEEE single precision (every C# ``float`` step)."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


_DEG2RAD_F = _f32(0.0174532924)


def _rtrig(fn, a: int) -> int:
    """``ff9.rsin`` / ``ff9.rcos`` (ff9.cs:2124-2138), step by step in single precision, the cast truncating.
    Products of two floats are exact in a double, so rounding each to float32 IS the float32 operation."""
    deg = _f32(_f32(a / 4096.0) * 360.0)
    rad = _f32(deg * _DEG2RAD_F)
    return int(_f32(_f32(fn(rad)) * 4096.0))


SIN = tuple(_rtrig(math.sin, a) for a in range(4096))
COS = tuple(_rtrig(math.cos, a) for a in range(4096))


def cdiv(a: int, b: int) -> int:
    """C# integer division (``B_DIV``): truncate toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


AMP_MAX = opcodes.EXPR_VALUE_MAX // 4096          # 8191: r * SIN (<= r * 4096) stays a legal 26-bit value
PERIOD_MAX = AMP_MAX + 1                          # 8192: the clock c <= P-1, so c * 4096 <= EXPR_VALUE_MAX
HEIGHT_MAX = 16383
SWING_MAX = 127                                   # facing bytes either side (127 ~ 179 degrees)
MOVERS_MAX = 16
CLOCKS_MAX = 8
SNAP_UNITS = 400                                  # the smoother stops interpolating above ~400 u ...
SNAP_BYTES = 32                                   # ... or ~45 degrees a tick (SmoothFrameUpdater_Field.cs:14-16)
TICKS_PER_SECOND = 30                             # at the default Memoria.ini [Graphics] FieldTPS = 30
PHASE_UNITS = 4096

MOVE_EX, TURN_EX = 0xAD, 0x87
# every op the kit's [[prop]] Init emitters produce (no yield among them): SET, SetModel, CreateObject,
# TurnInstant, the stand/walk/run/turn anim setters, SetObjectLogicalSize, SetAnimationStandSpeed,
# SetHeadFocusMask, EnableHeadFocus, SetObjectFlags, DisableShadow, SetShadowSize, SetShadowAmplifier, RETURN
MOVER_INIT_OPS = frozenset({0x05, 0x2F, 0x1D, 0x36, 0x33, 0x34, 0x35, 0x7A, 0x7B, 0x4B, 0x86, 0x8B, 0x47,
                            0x93, 0x80, 0x81, 0x85, 0x04})
DAEMON_OPS = frozenset({0x05, MOVE_EX, TURN_EX, 0x22, 0x01, 0x04})
_OP_SETMODEL, _OP_CREATE, _OP_INITCODE, _OP_INITOBJ, _OP_STARTSEQ = 0x2F, 0x1D, 0x07, 0x09, 0x43

_KEYS = ("radius", "to", "period", "phase", "reverse", "height", "bob", "turn", "swing")
_BOB_KEYS = ("amp", "period", "phase")
_TURNS = ("travel", "spin", "swing")


# ============================================================== the spec
@dataclass(frozen=True)
class MotionSpec:
    idx: int                   # the [[prop]] index in the toml
    label: str
    model: object              # the toml's prop / model value (the build binds the model id)
    pos: tuple                 # (x, z): the orbit centre, the shuttle start, the bob/spin spot
    path: str | None           # "orbit" | "shuttle" | None
    radius: int                # orbit
    mid: tuple                 # shuttle midpoint (mx, mz)
    half: tuple                # shuttle half extent (hx, hz): pos = mid - half at phase 0
    period: int                # the horizontal / turn cycle, ticks (0 = none)
    phase_u: int               # [0, 4096)
    reverse: bool
    height: int                # ABSOLUTE, up-positive (the 0xAD operand is -height)
    bob_amp: int
    bob_period: int
    bob_phase_u: int
    turn: str | None
    swing: int
    face: int                  # the [[prop]] face byte, ADDED to the computed facing

    @property
    def moves(self) -> bool:
        """Emits 0xAD: a path, a bob, or a height off the floor."""
        return self.path is not None or self.bob_amp > 0 or self.height != 0

    @property
    def turns(self) -> bool:
        return self.turn is not None

    @property
    def airborne(self) -> bool:
        return self.height != 0 or self.bob_amp > 0

    @property
    def periods(self) -> list:
        out = []
        if self.period:
            out.append(self.period)
        if self.bob_amp and self.bob_period not in out:
            out.append(self.bob_period)
        return out

    @property
    def cycle(self) -> int:
        ps = self.periods
        return math.lcm(*ps) if ps else 1

    @property
    def far_end(self) -> tuple | None:
        """The shuttle point farthest from ``pos`` that the path REACHES: ``to`` (1 short on an odd axis
        difference) when the period is even at phase 0; short of it otherwise -- the clock never lands on the half
        turn."""
        if self.path != "shuttle":
            return None
        far = max((pose(self, n) for n in range(self.period)),
                  key=lambda p: (p.x - self.pos[0]) ** 2 + (p.z - self.pos[1]) ** 2)
        return (far.x, far.z)


def _label(prop: dict, idx: int) -> str:
    return f"[[prop]] {prop.get('prop', prop.get('name', prop.get('model', '#' + str(idx))))!r}"


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _phase_units(v, where: str) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v < 1:
        raise MotionError(f"{where}: phase must be a number in [0, 1) of a cycle, got {v!r}")
    return int(round(v * PHASE_UNITS)) % PHASE_UNITS


def _period(v, where: str) -> int:
    if not _is_int(v) or not 2 <= v <= PERIOD_MAX:
        raise MotionError(f"{where}: period must be an integer 2..{PERIOD_MAX} ticks "
                          f"({TICKS_PER_SECOND} ticks = 1 s at the default FieldTPS), got {v!r}")
    return v


def parse(prop: dict, idx: int) -> MotionSpec | None:
    """The prop's motion, or None when it has none. Raises :class:`MotionError` on a key, type, range or
    prop-level co-rule violation (one text for validate, lint and build)."""
    m = prop.get("motion")
    if m is None:
        return None
    lab = _label(prop, idx)
    where = f"{lab} motion"
    if not isinstance(m, dict):
        raise MotionError(f"{where} must be a table, got {type(m).__name__}")
    unknown = sorted(set(m) - set(_KEYS))
    if unknown:
        raise MotionError(f"{where}: unknown key(s) {', '.join(unknown)} (have: {', '.join(_KEYS)})")
    if not m:
        raise MotionError(f"{where} is empty -- give at least one of radius, to, bob, turn")
    pos = prop.get("pos")
    if not isinstance(pos, (list, tuple)) or len(pos) < 2 or not (_is_int(pos[0]) and _is_int(pos[1])):
        raise MotionError(f"{where}: the prop needs an integer pos = [x, z] (the motion's anchor)")
    px, pz = int(pos[0]), int(pos[1])
    face0 = prop.get("face")
    if face0 is not None and not _is_int(face0):
        raise MotionError(f"{where}: face must be an integer facing byte (0 south, 64 west, 128 north, 192 east), "
                          f"got {face0!r}")

    radius = m.get("radius")
    to = m.get("to")
    if radius is not None and to is not None:
        raise MotionError(f"{where}: radius (orbit) and to (shuttle) are exclusive -- pick one path")
    path, r, mid, half = None, 0, (px, pz), (0, 0)
    if radius is not None:
        if not _is_int(radius) or not 1 <= radius <= AMP_MAX:
            raise MotionError(f"{where}: radius must be an integer 1..{AMP_MAX} world units, got {radius!r}")
        path, r = "orbit", radius
    if to is not None:
        if (not isinstance(to, (list, tuple)) or len(to) != 2 or not all(_is_int(v) for v in to)):
            raise MotionError(f"{where}: to must be [x, z] integers, got {to!r}")
        tx, tz = int(to[0]), int(to[1])
        if not (-32768 <= tx <= 32767 and -32768 <= tz <= 32767):
            raise MotionError(f"{where}: to {list(to)} is outside the signed 16-bit world range")
        if (tx, tz) == (px, pz):
            raise MotionError(f"{where}: to equals pos -- a shuttle needs two different points")
        if abs(tx - px) > 2 * AMP_MAX or abs(tz - pz) > 2 * AMP_MAX:
            raise MotionError(f"{where}: to is more than {2 * AMP_MAX} units from pos on an axis (the engine's "
                              f"26-bit expression envelope)")
        hx, hz = cdiv(tx - px, 2), cdiv(tz - pz, 2)
        path, half, mid = "shuttle", (hx, hz), (px + hx, pz + hz)

    period = m.get("period")
    turn = m.get("turn")
    if turn is not None and turn not in _TURNS:
        raise MotionError(f"{where}: turn must be one of {', '.join(_TURNS)}, got {turn!r}")
    if (path is not None or turn is not None) and period is None:
        raise MotionError(f"{where}: period (ticks for one full cycle) is required with "
                          f"{'radius' if path == 'orbit' else 'to' if path == 'shuttle' else 'turn'}")
    per = _period(period, where) if period is not None else 0
    if per and path is None and turn is None:
        bob0 = m.get("bob")
        if bob0 is None:
            raise MotionError(f"{where}: period without a channel -- add radius, to, turn or bob")
        if isinstance(bob0, dict) and "period" in bob0:
            raise MotionError(f"{where}: period drives nothing here -- the bob has its own period and there is no "
                              f"radius, to or turn; drop the motion period")

    phase_u = 0
    if "phase" in m:
        if path is None and turn is None:
            raise MotionError(f"{where}: phase needs a horizontal or turn channel (radius, to, turn); a bob "
                              f"takes its own phase inside bob = {{ ... }}")
        phase_u = _phase_units(m["phase"], where)

    reverse = m.get("reverse", False)
    if not isinstance(reverse, bool):
        raise MotionError(f"{where}: reverse must be true or false, got {reverse!r}")
    if reverse and not (path == "orbit" or turn == "spin"):
        raise MotionError(f"{where}: reverse applies only to an orbit (radius) or turn = \"spin\"")

    height = m.get("height", 0)
    if not _is_int(height) or abs(height) > HEIGHT_MAX:
        raise MotionError(f"{where}: height must be an integer within +-{HEIGHT_MAX} (ABSOLUTE, up-positive), "
                          f"got {height!r}")

    bob_amp = bob_period = bob_phase_u = 0
    bob = m.get("bob")
    if bob is not None:
        if not isinstance(bob, dict):
            raise MotionError(f"{where}: bob must be a table {{ amp, period, phase }}, got {bob!r}")
        bunk = sorted(set(bob) - set(_BOB_KEYS))
        if bunk:
            raise MotionError(f"{where}: bob has unknown key(s) {', '.join(bunk)} (have: amp, period, phase)")
        amp = bob.get("amp")
        if not _is_int(amp) or not 1 <= amp <= AMP_MAX:
            raise MotionError(f"{where}: bob amp must be an integer 1..{AMP_MAX}, got {amp!r}")
        bp = bob.get("period", per or None)
        if bp is None:
            raise MotionError(f"{where}: bob needs a period (its own, or the motion's)")
        bob_amp, bob_period = amp, _period(bp, where + " bob")
        if "phase" in bob:
            bob_phase_u = _phase_units(bob["phase"], where + " bob")

    swing = m.get("swing")
    if turn == "travel" and path != "orbit":
        raise MotionError(f"{where}: turn = \"travel\" faces along an orbit -- it needs radius")
    if turn == "spin" and path == "orbit":
        raise MotionError(f"{where}: turn = \"spin\" with radius -- an orbiter already turns once a lap; use "
                          f"turn = \"travel\" (plus face as an offset)")
    if turn == "swing":
        if not _is_int(swing) or not 1 <= swing <= SWING_MAX:
            raise MotionError(f"{where}: turn = \"swing\" needs swing = 1..{SWING_MAX} facing bytes "
                              f"(32 = 45 degrees either side), got {swing!r}")
    elif swing is not None:
        raise MotionError(f"{where}: swing is only for turn = \"swing\"")
    if path is None and bob is None and turn is None:
        raise MotionError(f"{where}: no channel -- give at least one of radius, to, bob, turn")

    spec = MotionSpec(idx=idx, label=lab, model=prop.get("prop", prop.get("model")), pos=(px, pz), path=path,
                      radius=r, mid=mid, half=half, period=per, phase_u=phase_u, reverse=reverse,
                      height=int(height), bob_amp=bob_amp, bob_period=bob_period, bob_phase_u=bob_phase_u,
                      turn=turn, swing=int(swing or 0), face=int(face0 or 0) & 0xFF)
    _co_rules(prop, spec)
    return spec


def _co_rules(prop: dict, spec: MotionSpec) -> None:
    lab = spec.label
    if spec.moves and prop.get("collision", True) is not False:
        raise MotionError(f"{lab} motion: a prop that moves must be walk-through -- set collision = false (the "
                          f"player push against an actor re-placed every tick is unproven)")
    if spec.airborne and prop.get("shadow") is not False:
        raise MotionError(f"{lab} motion: an airborne prop (height or bob) must set shadow = false (the engine "
                          f"draws its blob at the prop's own height -- a dark disc hanging in mid-air, never on "
                          f"the floor below)")
    for k in ("requires_flag", "requires_flag_clear", "attach_to"):
        if prop.get(k) is not None:
            raise MotionError(f"{lab} motion: a moving prop may not use {k} -- THE NULL-TARGET LAW: 0xAD has no "
                              f"null guard, so every mover must exist for the whole visit")
    name = prop.get("prop")
    if name is not None and _prop_archetypes.is_composite(name):
        raise MotionError(f"{lab} motion: {name!r} is a composite archetype (several parts) -- a mover is one "
                          f"model")


def any_motion(raw: dict) -> bool:
    return any(isinstance(p, dict) and p.get("motion") is not None for p in (raw.get("prop") or []))


def problems(raw: dict, *, donor=None) -> list:
    """Every refusal for ``raw`` -- the same texts validate, lint and build report. ``donor`` =
    ``build.donor_field_id(raw)`` (passed in: this module never imports build)."""
    out: list = []
    for i, n in enumerate(raw.get("npc") or []):
        if isinstance(n, dict) and n.get("motion") is not None:
            out.append(f"[[npc]] {n.get('name', '#' + str(i))!r} motion: motion is a [[prop]] key -- an NPC walks "
                       f"(the engine re-grounds walkers every frame, 0xBF), so it cannot ride a computed path")
    if not any_motion(raw):
        return out
    fork = []
    if raw.get("verbatim_eb") is not None:
        fork.append("[verbatim_eb]")
    if donor is not None:
        fork.append(f"a donor (field {donor})")
    if fork:
        out.append(f"[[prop]] motion: novel fields only -- this field has {' and '.join(fork)}. THE NOVEL-FIELD "
                   f"LAW: 0xAD/0x87 carry per-field hotfixes keyed on the effective (donor) id, two of which "
                   f"dereference a code entry's null actor; forks are rung 2")
    specs = []
    for i, p in enumerate(raw.get("prop") or []):
        if not isinstance(p, dict):
            continue
        try:
            s = parse(p, i)
        except MotionError as e:
            out.append(str(e))
            continue
        if s is not None:
            specs.append(s)
    if len([p for p in (raw.get("prop") or []) if isinstance(p, dict) and p.get("motion") is not None]) > MOVERS_MAX:
        out.append(f"[[prop]] motion: at most {MOVERS_MAX} moving props per field")
    if len(clocks(specs)) > CLOCKS_MAX:
        out.append(f"[[prop]] motion: at most {CLOCKS_MAX} distinct periods per field (bob periods count) -- "
                   f"got {len(clocks(specs))}; share periods")
    mcf = ((raw.get("field") or {}).get("mapconfig"))
    if mcf:
        air = [s.label for s in specs if s.airborne]
        if air:
            out.append(f"[[prop]] motion: {', '.join(air)} are airborne on a field that ships MapConfigData -- "
                       f"after a battle the engine rebuilds the actor and the MCF service shadows it again "
                       f"(shadow = false does not survive); keep airborne movers to fields without [field] "
                       f"mapconfig")
    return out


# ============================================================== the predictor
class Pose(NamedTuple):
    x: int
    b: int                     # the 0xAD height operand == obj(uid).f[1]; height = -b
    z: int
    face: int | None           # the facing byte, or None when the mover does not turn

    @property
    def height(self) -> int:
        return -self.b


def _base(n: int, period: int) -> int:
    return cdiv((n % period) * 4096, period)


def _angle(spec: MotionSpec, n: int) -> int:
    """The horizontal/turn channel's reduced angle in [0, 4095]."""
    a = _base(n, spec.period)
    if spec.reverse:
        return (8192 - spec.phase_u - a) & 4095
    return (a + spec.phase_u) & 4095 if spec.phase_u else a


def _bob_angle(spec: MotionSpec, n: int) -> int:
    a = _base(n, spec.bob_period)
    return (a + spec.bob_phase_u) & 4095 if spec.bob_phase_u else a


def _face_value(spec: MotionSpec, th: int) -> int:
    """The raw 0x87 operand (the engine takes it mod 256): always in [0, 702], never negative."""
    if spec.turn == "travel":
        return spec.face + (64 if spec.reverse else 192) + th // 16
    if spec.turn == "spin":
        return spec.face + th // 16
    return spec.face + 256 + cdiv(SIN[th] * spec.swing, 4096)          # swing: centred ON face


def pose(spec: MotionSpec, n: int) -> Pose:
    """What tick ``n`` (>= 0; tick 0 = the field's first frame) writes for this mover."""
    th = _angle(spec, n) if spec.period else 0
    if spec.path == "orbit":
        x = spec.pos[0] + cdiv(SIN[th] * spec.radius, 4096)
        z = spec.pos[1] + cdiv(COS[th] * spec.radius, 4096)
    elif spec.path == "shuttle":
        x = spec.mid[0] - cdiv(COS[th] * spec.half[0], 4096) if spec.half[0] else spec.pos[0]
        z = spec.mid[1] - cdiv(COS[th] * spec.half[1], 4096) if spec.half[1] else spec.pos[1]
    else:
        x, z = spec.pos
    b = -spec.height
    if spec.bob_amp:
        b -= cdiv(SIN[_bob_angle(spec, n)] * spec.bob_amp, 4096)
    face = (_face_value(spec, th) & 0xFF) if spec.turns else None
    return Pose(x, b, z, face)


def path(spec: MotionSpec, n0: int = 0, n1: int | None = None) -> list:
    """Poses for ticks n0..n1-1 (one cycle from n0 by default)."""
    if n1 is None:
        n1 = n0 + spec.cycle
    return [pose(spec, n) for n in range(n0, n1)]


def _circ(a: int, b: int) -> int:
    d = (a - b) % 256
    return min(d, 256 - d)


def bounds(spec: MotionSpec) -> dict:
    """x / z / height ranges, each over its OWN channel's period (never the lcm -- two coprime legal periods would
    otherwise iterate ~67 million ticks)."""
    hor = [pose(spec, n) for n in range(spec.period or 1)]
    xs, zs = [p.x for p in hor], [p.z for p in hor]
    if spec.bob_amp:
        hs = [spec.height + cdiv(SIN[_bob_angle(spec, n)] * spec.bob_amp, 4096) for n in range(spec.bob_period)]
    else:
        hs = [spec.height]
    return {"x": (min(xs), max(xs)), "z": (min(zs), max(zs)), "h": (min(hs), max(hs))}


STEP_EXACT_MAX = 16384                            # the joint cycle max_step walks tick by tick


def step_is_exact(spec: MotionSpec) -> bool:
    """True when :func:`max_step`'s 3-D step is the real largest step, False when it is an upper bound."""
    return spec.cycle <= STEP_EXACT_MAX


def max_step(spec: MotionSpec) -> tuple:
    """(the largest per-tick 3-D step in world units, the largest per-tick facing change in bytes -- circular).
    The facing is exact over the horizontal period (it depends on nothing else). The 3-D step is exact over the
    joint cycle when that is at most STEP_EXACT_MAX ticks; past it (e.g. two coprime periods, ~67 M ticks) it
    combines each channel's own maximum -- an UPPER BOUND (:func:`step_is_exact`)."""
    xz = fb = 0
    if spec.period:
        prev = pose(spec, 0)
        for n in range(1, spec.period + 1):
            p = pose(spec, n)
            xz = max(xz, math.hypot(p.x - prev.x, p.z - prev.z))
            if spec.turns:
                fb = max(fb, _circ(p.face, prev.face))
            prev = p
    if step_is_exact(spec):
        seq = [pose(spec, n) for n in range(spec.cycle + 1)]
        return max(math.dist((a.x, a.b, a.z), (c.x, c.b, c.z)) for a, c in zip(seq, seq[1:])), fb
    dh = 0
    if spec.bob_amp:
        hs = [cdiv(SIN[_bob_angle(spec, n)] * spec.bob_amp, 4096) for n in range(spec.bob_period + 1)]
        dh = max(abs(hs[i + 1] - hs[i]) for i in range(len(hs) - 1))
    return math.hypot(xz, dh), fb


SWING_PX = 0.5                                    # field px a track must move back before a reversal counts
BOB_SEEN_PX = 1.0                                 # a bob moving the prop less than this (field px) is not seen
BOB_FIX_DIVS = (3, 4, 6, 8, 12, 16)               # bob periods a note tries: the path's period / these


def _swings(vs, h: float = SWING_PX, *, cyclic: bool = True) -> int:
    """Direction reversals of a screen track. A reversal counts only once the track has moved back ``h`` px from its
    last extreme, so the fraction-of-a-px jitter of integer poses never counts. A CYCLIC track is walked twice (the
    first lap settles the direction, the second counts); a window cut from a longer cycle is walked once."""
    n = len(vs)
    if n < 2:
        return 0
    dirn, ext, count = 0, vs[0], 0
    for i, v in enumerate(list(vs) * 2 if cyclic else list(vs)):
        if dirn == 0:
            if abs(v - ext) >= h:
                dirn, ext = (1 if v > ext else -1), v
        elif (v - ext) * dirn > 0:
            ext = v
        elif abs(v - ext) >= h:
            dirn, ext = -dirn, v
            count += (i >= n) if cyclic else 1
    return count


class BobReading(NamedTuple):
    px: float                  # the largest on-screen offset the bob adds (field px)
    with_bob: int              # screen-vertical reversals over the window, with the bob
    without: int               # ... the path alone
    path_span: float           # the path's own screen-vertical travel over the window (field px)
    window: int                # ticks measured
    cyclic: bool               # the window is the whole joint cycle

    @property
    def reads(self) -> bool:
        """THE BOB-READING LAW: a bob reads as a bob when it moves the prop a visible amount AND either adds
        up-and-downs of its own (it is fast enough) or out-travels the path's own up-and-down (it is large enough --
        on a nearly flat track the bob IS the vertical motion, whatever its period)."""
        return self.px >= BOB_SEEN_PX and (self.with_bob > self.without or 2 * self.px >= self.path_span)


def bob_reading(spec: MotionSpec, project) -> BobReading | None:
    """How a mover's bob READS through ``project(x, height, z) -> (u, v)`` (field-canvas px, v down). None for a
    mover without a bob. Measured over the joint cycle when it is at most STEP_EXACT_MAX ticks; past that, over a
    window of eight of the slower channel's periods (capped at STEP_EXACT_MAX, which still holds two of the longest
    legal period) -- the same window for both tracks, so their reversal counts compare.

    Why: on a pitched camera a path toward or away from the camera already moves the prop up and down the screen,
    and a bob small and slow next to that folds into it -- bench 30946's cask (+-60 every 256 ticks on a 128-tick
    r 300 orbit) moved +-4.3 px against the orbit's 60, added no up-and-down of its own, and the owner saw no bob."""
    if not spec.bob_amp:
        return None
    cyclic = spec.cycle <= STEP_EXACT_MAX
    n = spec.cycle if cyclic else min(STEP_EXACT_MAX, 8 * max(spec.period, spec.bob_period))
    vw, vo, px = [], [], 0.0
    for k in range(n):
        p = pose(spec, k)
        w, o = project(p.x, p.height, p.z), project(p.x, spec.height, p.z)
        px = max(px, math.dist(w, o))
        vw.append(w[1])
        vo.append(o[1])
    return BobReading(px, _swings(vw, cyclic=cyclic), _swings(vo, cyclic=cyclic), max(vo) - min(vo), n, cyclic)


def _replace(spec: MotionSpec, **kw) -> MotionSpec:
    import dataclasses
    return dataclasses.replace(spec, **kw)


def bob_note(spec: MotionSpec, project, camera: str = "") -> str | None:
    """The lint advisory for a bob that will not read as one through ``project``, or None. Every fix it names is
    re-measured first: a bob period (same amp) and an amp (same period) that DO read on this camera."""
    r = bob_reading(spec, project)
    if r is None or r.reads:
        return None
    on = f" on {camera}" if camera else " on this camera"
    what = f"{spec.label} motion: its bob (+-{spec.bob_amp} every {spec.bob_period} ticks)"
    fixes = []
    if r.px < BOB_SEEN_PX or spec.path is None:
        amp = min(AMP_MAX, math.ceil(spec.bob_amp * BOB_SEEN_PX / r.px)) if r.px else AMP_MAX
        if (bob_reading(_replace(spec, bob_amp=amp), project) or r).reads:
            fixes.append(f"an amp of {amp}")
        return (f"{what} moves it at most {r.px:.1f} field px{on} -- too small to see"
                + (f"; try {fixes[0]}" if fixes else ""))
    if spec.period:
        for div in BOB_FIX_DIVS:
            bp = spec.period // div
            if bp < 4:                                   # a 2- or 3-tick sine is a flicker, never a bob
                break
            if bob_reading(_replace(spec, bob_period=bp), project).reads:
                fixes.append(f"a bob period of {bp} (same amp)")
                break
    amp = min(AMP_MAX, math.ceil(spec.bob_amp * r.path_span / (2 * r.px)) + 1)
    if bob_reading(_replace(spec, bob_amp=amp), project).reads:
        fixes.append(f"an amp of {amp} (same period)")
    window = "" if r.cyclic else f" (measured over {r.window} ticks of its {spec.cycle}-tick joint cycle)"
    return (f"{what} does not read as a bob{on}: it moves the prop at most {r.px:.1f} field px and adds no "
            f"up-and-down of its own to the path's {r.path_span:.0f} px, so it reads as a reshaped path{window}"
            + (f" -- try {' or '.join(fixes)}" if fixes else ""))


def clocks(specs) -> list:
    """The distinct periods, first-use order (the horizontal period, then the bob's, mover by mover)."""
    out: list = []
    for s in specs:
        for p in s.periods:
            if p not in out:
                out.append(p)
    return out


def csv_rows(spec: MotionSpec, ticks: int) -> list:
    return [(spec.idx, spec.label, n, p.x, p.height, p.z, "" if p.face is None else p.face)
            for n, p in enumerate(path(spec, 0, ticks))]


# ============================================================== the daemon
def _stmt(text: str) -> bytes:
    return opcodes.encode(0x05, exprasm.assemble(text + " B_EXPR_END"), arg_flags=0b1)


def _x(text: str) -> bytes:
    return exprasm.assemble(text + " B_EXPR_END")


def _clock_ref(k: int) -> str:
    return f"Instance.Int16[{2 * k}]"            # a BYTE offset: clock k lives at bytes 2k..2k+1


def _angle_rpn(spec: MotionSpec, cref: str) -> str:
    base = f"{cref} const(4096) B_MULT const({spec.period}) B_DIV"
    if spec.reverse:
        return f"const({8192 - spec.phase_u}) {base} B_MINUS const(4095) B_AND"
    return f"{base} const({spec.phase_u}) B_PLUS const(4095) B_AND" if spec.phase_u else base


def _bob_rpn(spec: MotionSpec, cref: str) -> str:
    base = f"{cref} const(4096) B_MULT const({spec.bob_period}) B_DIV"
    return f"{base} const({spec.bob_phase_u}) B_PLUS const(4095) B_AND" if spec.bob_phase_u else base


def mover_ops(spec: MotionSpec, uid: int, clock_of: dict) -> list:
    """The per-tick instructions for one mover (0xAD when it moves, 0x87 when it turns)."""
    ops = []
    th = _angle_rpn(spec, _clock_ref(clock_of[spec.period])) if spec.period else "const(0)"
    if spec.moves:
        if spec.path == "orbit":
            xs = f"const({spec.pos[0]}) {th} B_SIN2 const({spec.radius}) B_MULT const(4096) B_DIV B_PLUS"
            zs = f"const({spec.pos[1]}) {th} B_COS2 const({spec.radius}) B_MULT const(4096) B_DIV B_PLUS"
        elif spec.path == "shuttle":
            xs = (f"const({spec.mid[0]}) {th} B_COS2 const({spec.half[0]}) B_MULT const(4096) B_DIV B_MINUS"
                  if spec.half[0] else f"const({spec.pos[0]})")
            zs = (f"const({spec.mid[1]}) {th} B_COS2 const({spec.half[1]}) B_MULT const(4096) B_DIV B_MINUS"
                  if spec.half[1] else f"const({spec.pos[1]})")
        else:
            xs, zs = f"const({spec.pos[0]})", f"const({spec.pos[1]})"
        bs = f"const({-spec.height})"
        if spec.bob_amp:
            be = _bob_rpn(spec, _clock_ref(clock_of[spec.bob_period]))
            bs += f" {be} B_SIN2 const({spec.bob_amp}) B_MULT const(4096) B_DIV B_MINUS"
        ops.append(opcodes.encode(MOVE_EX, uid, _x(xs), _x(bs), _x(zs), arg_flags=0b1110))
    if spec.turns:
        if spec.turn == "travel":
            fs = f"const({spec.face + (64 if spec.reverse else 192)}) {th} const(16) B_DIV B_PLUS"
        elif spec.turn == "spin":
            fs = f"const({spec.face}) {th} const(16) B_DIV B_PLUS"
        else:
            fs = f"const({spec.face + 256}) {th} B_SIN2 const({spec.swing}) B_MULT const(4096) B_DIV B_PLUS"
        ops.append(opcodes.encode(TURN_EX, uid, _x(fs), arg_flags=0b10))
    return ops


def daemon_body(movers) -> bytes:
    """``movers`` = [(spec, uid)]: the prelude zeroes every clock, then each tick writes every mover's pose(n),
    advances every clock ``c = (c + 1) % P``, Wait(1), and loops -- write-then-advance, so tick n writes pose(n)."""
    specs = [s for s, _u in movers]
    ks = clocks(specs)
    clock_of = {p: k for k, p in enumerate(ks)}
    B: list = [_stmt(f"{_clock_ref(k)} const(0) B_LET") for k in range(len(ks))]
    B.append(label("top"))
    for spec, uid in movers:
        B += mover_ops(spec, uid, clock_of)
    for k, p in enumerate(ks):
        B.append(_stmt(f"{_clock_ref(k)} {_clock_ref(k)} const(1) B_PLUS const({p}) B_REM B_LET"))
    B += [opcodes.wait(1), (JMP, "top"), opcodes.RETURN]
    return asm(B)


_ALLOWED_TOKENS = {"B_LET", "B_PLUS", "B_MINUS", "B_MULT", "B_DIV", "B_REM", "B_AND", "B_SIN2", "B_COS2",
                   "B_EXPR_END"}


def audit_body(body: bytes, loc: int, uids) -> list:
    """ZERO SHARED STATE on the EMITTED bytes: the opcode allowlist, the token allowlist (const, the daemon's own
    clocks at exactly byte offsets 0, 2, ..., loc-2), exactly-one-value expressions, and 0xAD/0x87 aimed only at
    ``uids``. Returns the violations."""
    import re
    from ..eb import exprsem
    bad: list = []
    clock_offs = set()
    prelude_re = re.compile(r"Instance\.Int16\[(\d+)\] const\(0\) B_LET")
    advance_re = re.compile(r"Instance\.Int16\[(\d+)\] Instance\.Int16\[(\d+)\] const\(1\) B_PLUS "
                            r"const\((\d+)\) B_REM B_LET")
    preludes, advances, waits, jumps, movers_at, rets = {}, {}, [], [], [], []
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op == 0x05:
            txt = D.pretty_expr(body, ins.off + 1)[0].strip().strip("{}").strip()
            txt = txt[:-len(" B_EXPR_END")] if txt.endswith(" B_EXPR_END") else txt
            m1, m2 = prelude_re.fullmatch(txt), advance_re.fullmatch(txt)
            if m1:
                preludes.setdefault(int(m1.group(1)), []).append(ins.off)
            elif m2 and m2.group(1) == m2.group(2):
                advances.setdefault(int(m2.group(1)), []).append(ins.off)
            else:
                bad.append(f"SET at +{ins.off} is neither a clock prelude nor a clock advance -- only the clocks "
                           f"may be written ({txt[:60]!r})")
        elif ins.op in (MOVE_EX, TURN_EX):
            movers_at.append(ins.off)
        elif ins.op == 0x22:
            waits.append(ins)
        elif ins.op == 0x01:
            jumps.append(ins)
        elif ins.op == 0x04:
            rets.append(ins)
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op not in DAEMON_OPS:
            bad.append(f"op 0x{ins.op:02X} at +{ins.off} is not a motion-daemon op")
            continue
        exprs = []
        if ins.op == 0x05:
            exprs.append(D.pretty_expr(body, ins.off + 1)[0])
        elif ins.op in (MOVE_EX, TURN_EX):
            if body[ins.off + 2] not in uids:
                bad.append(f"0x{ins.op:02X} at +{ins.off} targets uid {body[ins.off + 2]}, not a mover")
            off = ins.off + 3
            while off < ins.end:
                txt, off = D.pretty_expr(body, off)
                exprs.append(txt)
        for txt in exprs:
            inner = txt.strip().strip("{}").strip()
            try:
                exprsem.analyze(inner if inner.endswith("B_EXPR_END") else inner + " B_EXPR_END")
            except Exception as e:                       # noqa: BLE001 -- the audit reports, it never crashes
                bad.append(f"expression {inner[:60]!r}: {e}")
            if ins.op in (MOVE_EX, TURN_EX) and "B_LET" in inner.split():
                bad.append(f"0x{ins.op:02X} at +{ins.off} writes inside an operand -- only the clock SETs write")
            for tok in inner.split():
                m = re.fullmatch(r"Instance\.Int16\[(\d+)\]", tok)
                if m:
                    clock_offs.add(int(m.group(1)))
                elif not (re.fullmatch(r"const\(\d+\)", tok) or tok in _ALLOWED_TOKENS):
                    bad.append(f"token {tok!r} is not allowed in the motion daemon (nothing shared, nothing read)")
    want = set(range(0, loc, 2))
    for k in sorted(want):
        if len(preludes.get(k, [])) != 1 or len(advances.get(k, [])) != 1:
            bad.append(f"clock at byte {k} needs exactly one prelude and one advance, found "
                       f"{len(preludes.get(k, []))} / {len(advances.get(k, []))}")
    if len(waits) != 1 or (waits and body[waits[0].off + 2] != 1):     # 0x22 [arg flags] [n]
        bad.append("the loop must yield with exactly one Wait(1) per tick")
    if len(jumps) != 1:
        bad.append(f"the loop must close with exactly one JMP, found {len(jumps)}")
    else:
        top = D.jump_target(jumps[0])
        first_pre = max((o for offs in preludes.values() for o in offs), default=-1)
        loop_ops = movers_at + [o for offs in advances.values() for o in offs]
        if top <= first_pre or any(o < top for o in loop_ops) or (waits and waits[0].off < top):
            bad.append("the loop's JMP must return to just after the clock preludes (the preludes run once, "
                       "every mover op and clock advance runs every tick)")
        end = jumps[0].off
        if any(o > end for o in loop_ops) or (waits and waits[0].off > end):
            bad.append("every mover op, clock advance and the Wait(1) must sit INSIDE the loop, before its JMP")
        if any(r.off < end for r in rets):
            bad.append("a RETURN inside the loop would stop the daemon -- only the unreachable tail may RETURN")
    if clock_offs != want:
        bad.append(f"the clocks sit at Instance byte offsets {sorted(clock_offs)}, not exactly {sorted(want)} "
                   f"(an Int16 index is a BYTE offset)")
    return bad


def entry_bytes(movers) -> tuple:
    """(the seated code entry -- type 0, ONE tag-0 function at fpos 4 -- , its loc = 2 bytes per clock),
    self-audited: raises :class:`MotionError` on any ZERO-SHARED-STATE violation."""
    body = daemon_body(movers)
    loc = 2 * len(clocks([s for s, _u in movers]))
    bad = audit_body(body, loc, {u for _s, u in movers})
    if bad:
        raise MotionError("the motion daemon failed its self-audit: " + "; ".join(bad[:4]))
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body, loc


# ============================================================== the laws on the built script
def init_problems(eb: bytes, slot: int, model: int) -> list:
    """THE SLOT-MAP + STRAIGHT-LINE INIT laws for the mover at ``slot``."""
    s = EbScript.from_bytes(eb)
    if not 0 <= slot < s.entry_count:
        return [f"slot {slot} does not exist"]
    e = s.entry(slot)
    f0 = e.func_by_tag(0) if e.size > 0 else None
    if f0 is None:
        return [f"slot {slot} has no Init"]
    ops = list(D.iter_code(eb, f0.abs_start, f0.abs_end))
    bad = [f"op 0x{i.op:02X}" for i in ops if i.op not in MOVER_INIT_OPS]
    out = []
    if bad:
        out.append(f"slot {slot}'s Init runs {', '.join(sorted(set(bad)))} -- not in MOVER_INIT_OPS (a possible "
                   f"yield before the daemon's tick 0: THE STRAIGHT-LINE INIT LAW)")
    sm = [i for i in ops if i.op == _OP_SETMODEL]
    cr = [i for i in ops if i.op == _OP_CREATE]
    if len(sm) != 1 or len(cr) != 1 or sm[0].off > cr[0].off:
        out.append(f"slot {slot}'s Init must run exactly one SetModel before exactly one CreateObject")
    elif struct.unpack_from("<H", eb, sm[0].off + 2)[0] != model:
        out.append(f"slot {slot}'s SetModel is model {struct.unpack_from('<H', eb, sm[0].off + 2)[0]}, not the "
                   f"mover's {model} (THE SLOT-MAP LAW)")
    if not ops or ops[-1].op != 0x04:
        out.append(f"slot {slot}'s Init does not end in RETURN")
    return out


def _stride_problems(eb: bytes, slot: int, what: str) -> list:
    s = EbScript.from_bytes(eb)
    lo = slot - 64
    if lo < 0 or lo >= s.entry_count:
        return []
    e = s.entry(lo)
    if e.size <= 0:
        return []
    for fn in e.funcs:
        if any(i.op == _OP_STARTSEQ for i in D.iter_code(eb, fn.abs_start, fn.abs_end)):
            return [f"the {what} at slot {slot} sits 64 above entry {lo}, which runs a STARTSEQ (0x43): its Seq "
                    f"takes uid {slot} and disposes the object there (THE 64-STRIDE LAW -- a ladder climb in "
                    f"the player entry is one)"]
    return []


def _calls(eb: bytes, op: int, slot: int) -> list:
    """Every (entry, tag, abs offset) where ``op`` (0x07 InitCode / 0x09 InitObject) names ``slot``."""
    s = EbScript.from_bytes(eb)
    out = []
    for e in s.entries:
        if e.size <= 0:
            continue
        for fn in e.funcs:
            for i in D.iter_code(eb, fn.abs_start, fn.abs_end):
                if i.op == op and eb[i.off + 1] == slot:
                    out.append((e.index, fn.tag, i.off))
    return out


def arming_problems(eb: bytes, daemon_slot: int, mover_slots) -> list:
    """THE ORDER LAW on the FINAL bytes: one InitCode(daemon), in Main_Init; one InitObject per mover, in
    Main_Init; every mover InitObject dominates the InitCode (earlier in the same block); the InitCode dominates
    every reachable exit of Main_Init."""
    from ..eb.cfg import CfgError, FuncFlow
    out = []
    ic = _calls(eb, _OP_INITCODE, daemon_slot)
    if len(ic) != 1 or ic[0][:2] != (0, 0):
        return [f"the daemon (slot {daemon_slot}) must be armed by exactly one InitCode in Main_Init, found {ic}"]
    objs = {}
    for m in mover_slots:
        c = _calls(eb, _OP_INITOBJ, m)
        if len(c) != 1 or c[0][:2] != (0, 0):
            out.append(f"mover slot {m} must be created by exactly one InitObject in Main_Init, found {c}")
        else:
            objs[m] = c[0][2]
    if out:
        return out
    main = EbScript.from_bytes(eb).entry(0).func_by_tag(0)
    try:
        flow = FuncFlow.build(eb, main.abs_start, main.abs_end)
    except CfgError as e:
        return [f"Main_Init's control flow could not be analysed ({e}) -- THE ORDER LAW cannot be proved"]
    bo = flow._block_of

    def dom(a: int, b: int) -> bool:                 # block a dominates block b
        return bool(flow._dom[b]) and bool((flow._dom[b] >> a) & 1)

    ci = bo.get(ic[0][2])
    if ci is None or not flow._dom[ci]:
        return ["the daemon's InitCode is unreachable in Main_Init"]
    for m, off in objs.items():
        mb = bo.get(off)
        if mb is None or not dom(mb, ci) or (mb == ci and off > ic[0][2]):
            out.append(f"the daemon is armed before mover slot {m}'s InitObject on some path -- THE ORDER LAW: "
                       f"tick 0 would move a prop that has not run its Init")
    exits = [b.index for b in flow.blocks if flow._dom[b.index] and not b.succs]
    for x in exits:
        if not dom(ci, x):
            out.append("the daemon's InitCode does not run on every path through Main_Init")
            break
    return out


def arm(eb: bytes, raw: dict, seats, *, donor=None) -> tuple:
    """Seat and arm the motion daemon. ``seats`` = [(prop dict, model id, slot)] recorded by the build's [[prop]]
    loop; ``donor`` = ``build.donor_field_id(raw)``. Re-runs :func:`problems` (so a direct build_script call cannot
    slip a fork, the caps or the MapConfigData rule past validate). Returns (bytes, daemon slot, report lines).
    Raises :class:`MotionError` on any law."""
    probs = problems(raw, donor=donor)
    if probs:
        raise MotionError(probs[0])
    props = raw.get("prop") or []
    specs = []
    for i, p in enumerate(props):
        if isinstance(p, dict):
            s = parse(p, i)
            if s is not None:
                specs.append((s, p))
    movers = []
    for s, p in specs:
        mine = [(mid, slot) for q, mid, slot in seats if q is p]
        if len(mine) != 1:
            raise MotionError(f"{s.label} motion: expected exactly one seated part, found {len(mine)}")
        mid, slot = mine[0]
        if not 1 <= slot <= 249:
            raise MotionError(f"{s.label} motion: slot {slot} is outside 1..249 (250-255 alias the player, the "
                              f"party and self; 0 is Main)")
        bad = init_problems(eb, slot, mid) + _stride_problems(eb, slot, "mover")
        if bad:
            raise MotionError(f"{s.label} motion: " + "; ".join(bad))
        movers.append((s, slot))
    entry, loc = entry_bytes(movers)
    from . import object as _object
    out, dslot = _object.seat_entry(eb, entry, loc=loc)
    if not 1 <= dslot <= 249:
        raise MotionError(f"[[prop]] motion: the daemon landed at slot {dslot}, outside 1..249")
    bad = _stride_problems(out, dslot, "motion daemon")
    if bad:
        raise MotionError("[[prop]] motion: " + "; ".join(bad))
    main = EbScript.from_bytes(out).entry(0).func_by_tag(0)
    lasts = []
    for _s, sl in movers:
        hits = [off for e, t, off in _calls(out, _OP_INITOBJ, sl) if (e, t) == (0, 0)]
        if len(hits) != 1:
            raise MotionError(f"[[prop]] motion: mover slot {sl} must be created by exactly one InitObject in "
                              f"Main_Init, found {len(hits)} (THE ORDER LAW)")
        lasts.append(hits[0])
    last = max(lasts)
    ins = next(i for i in D.iter_code(out, main.abs_start, main.abs_end) if i.off == last)
    out = eb_edit.insert_in_function(out, 0, 0, ins.end - main.abs_start, opcodes.init_code(dslot, 0))
    bad = arming_problems(out, dslot, [sl for _s, sl in movers])
    if bad:
        raise MotionError("[[prop]] motion: " + "; ".join(bad))
    return out, dslot, report_lines(movers, dslot, loc)


# ============================================================== the report
def _secs(ticks: int) -> str:
    return f"{ticks / TICKS_PER_SECOND:.2f} s"


def describe(spec: MotionSpec, uid: int | None = None) -> str:
    parts = []
    if spec.path == "orbit":
        parts.append(f"orbit r {spec.radius}{' reverse' if spec.reverse else ''} about {spec.pos}")
    elif spec.path == "shuttle":
        parts.append(f"shuttle {spec.pos} -> {spec.far_end}")
    else:
        parts.append(f"at {spec.pos}")
    parts.append(f"height {spec.height}")
    if spec.period:
        parts.append(f"period {spec.period} ({_secs(spec.period)}), phase {spec.phase_u / PHASE_UNITS:g}")
    if spec.bob_amp:
        bph = f", phase {spec.bob_phase_u / PHASE_UNITS:g}" if spec.bob_phase_u else ""
        parts.append(f"bob +-{spec.bob_amp} every {spec.bob_period} ({_secs(spec.bob_period)}){bph}")
    if len(spec.periods) > 1:
        parts.append(f"cycle {spec.cycle} ({_secs(spec.cycle)})")
    if spec.turn == "swing":
        parts.append(f"turn swing +-{spec.swing} about face {spec.face}")
    elif spec.turn:
        parts.append(f"turn {spec.turn}{f' +{spec.face}' if spec.face else ''}")
    b = bounds(spec)
    step, fb = max_step(spec)
    exact = step_is_exact(spec)
    first = " ".join(f"({p.x},{p.height},{p.z},{'-' if p.face is None else p.face})" for p in path(spec, 0, 4))
    snap = ""
    if fb >= SNAP_BYTES or (step >= SNAP_UNITS and exact):
        snap = " -- SNAPS: over the smoother's 400 u / 45 deg per tick"
    elif step >= SNAP_UNITS:
        snap = " -- MAY SNAP: its step bound is over the smoother's 400 u per tick"
    who = f"{spec.label} motion" + (f" uid {uid}" if uid is not None else "")
    def rng(lo_hi):
        return f"{lo_hi[0]}" if lo_hi[0] == lo_hi[1] else f"{lo_hi[0]}..{lo_hi[1]}"
    return (f"{who}: {'; '.join(parts)}; x {rng(b['x'])} z {rng(b['z'])} h {rng(b['h'])}; "
            f"max {'' if exact else '<= '}{step:.1f} u, {fb} bytes/tick; ticks 0-3 (x,h,z,face): {first}{snap}")


def report_lines(movers, daemon_slot=None, loc=None) -> list:
    specs = [s for s, _u in movers]
    ks = clocks(specs)
    head = (f"[[prop]] motion: {len(specs)} mover(s) on {len(ks)} clock(s) ({', '.join(map(str, ks))} ticks; "
            f"{TICKS_PER_SECOND} ticks = 1 s at the default FieldTPS)")
    if daemon_slot is not None:
        head += (f" -- daemon entry {daemon_slot} (loc {loc} B), armed in Main_Init after the last mover's "
                 f"InitObject (THE ORDER LAW); tick 0 = the field's first frame; state = the daemon's own locals")
    return [head] + [describe(s, u) for s, u in movers]


def lint_notes(raw: dict) -> list:
    """Advisories (never errors): a mover faster than the smoother interpolates."""
    out = []
    for i, p in enumerate(raw.get("prop") or []):
        if not isinstance(p, dict) or p.get("motion") is None:
            continue
        try:
            s = parse(p, i)
        except MotionError:
            continue                                   # the error is reported by problems()
        step, fb = max_step(s)
        if fb >= SNAP_BYTES or (step >= SNAP_UNITS and step_is_exact(s)):
            out.append(f"{s.label} motion moves {step:.0f} u / turns {fb} bytes in one tick -- over the smoother's "
                       f"{SNAP_UNITS} u / {SNAP_BYTES} bytes, so it will visibly SNAP (slow it: a longer period or "
                       f"a smaller radius)")
        elif step >= SNAP_UNITS:
            out.append(f"{s.label} motion may move up to {step:.0f} u in one tick (a bound: its periods' joint cycle "
                       f"is {s.cycle} ticks) -- over the smoother's {SNAP_UNITS} u, so it may visibly SNAP")
    return out
