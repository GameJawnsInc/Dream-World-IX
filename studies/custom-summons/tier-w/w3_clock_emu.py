r"""TIER W rung 3 / B0 -- an offline emulator of ``ef227:c0`` state 0's clock-coupled arithmetic.

    py w3_clock_emu.py                       # the full B0 proof (stock vs patched vs mis-retime)
    py w3_clock_emu.py --blob <ef227.bytes>  # ... against an explicit container copy
    py w3_clock_emu.py --table               # per-tick dump of every signal, both timelines

WHY THIS EXISTS
---------------
W3 stretches ``ef227:c0`` state 0 from 70 ticks to 118 by moving one ``slti`` immediate.  A2 found
that the phase length is ALSO baked into two magic reciprocals whose products are consumed
**unclamped**, so the one-immediate edit leaves the phase's internal motion normalising against the
old length: ramps that were authored to arrive exactly at the phase end instead sail past it, go
negative, and invert the geometry they drive.  The full edit set is
:mod:`w3_program_edits`; this module is the proof that the set is right, and complete.

It is a LIBRARY.  ``B2``'s gates import :func:`audit` and assert on its result; the ``__main__``
path runs the same audit and prints it.

WHAT IT MODELS -- and what it deliberately does not
---------------------------------------------------
Every arithmetic expression in s0's body (image ``0x0B6C .. 0x1384``) whose value depends on the
phase clock, bit-exact: 32-bit wraparound, MIPS ``mult`` as a SIGNED 32x32 with ``mfhi`` taking the
high half, arithmetic ``sra``, and the two magic-division idioms (with and without the add-back).
Every constant is READ FROM THE CONTAINER at run time -- no stock byte is embedded in this file.

It does **not** model ``rsin``/``rcos`` (HLE ops 15/14), the HLE draw calls, or the host.  It does
not need to: the trig functions are pure, so proving that the *argument* handed to ``rsin`` on the
patched phase's last tick equals the argument on the stock phase's last tick proves the resulting
pose is identical **without knowing what rsin returns**.  That is stronger than modelling it.

THE SIGNAL NAMES (B0 section 3 has the dataflow map)
----------------------------------------------------
``progress``   the /69 ramp at image 0x0B6C, stored to ``320($sp)``, read six times.  0 -> 4096.
``arrival``    the /45 ramp at image 0x0C54, kept in ``$s1``.  0 at clock 24 -> 4096 at the end.
``eff_scale``  effect-model scale, piecewise in ``progress``.  8192 -> 16384.
``eff_tilt``   effect-model rotation X = ``progress >> 4``.  0 -> 256.
``eff_spin``   effect-model rotation Y = ``clock * 7``.  A RATE, not a progress ramp -- not retuned.
``eff_rgb``    effect-model RGB bias.  -64 -> 0.
``shake_env``  the camera-shake decay envelope ``4096 - progress``, multiplied by ``rand(160)``.
``cre_radius`` the creature's fly-in radius.  1224 -> 24.
``cre_scale``  the creature's scale.  6144 (held) -> 2048.
``cre_theta``  the argument handed to ``rsin`` for the creature's spiral angle.  0 -> 3072.
``cre_yarg``   the argument handed to ``rsin`` for the creature's vertical curve, plus its branch.
``trail``      ``328($sp)``: 0 below clock 45, a saturated 4096 at and above it.
``beam_cd``    the light column's 150 -> 0 countdown, gated ``clock < 46`` (self-contained /46).
``beam_ang``   ``progress >> 2``, handed to ``rcos`` inside that same ``clock < 46`` block.
``beams``      which of the 9 wrapping beam elements are drawn this tick.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import w3_program_edits as E                                          # noqa: E402

#: sha256 of the stock container this audit was derived against -- the same constant
#: ``rescore.EXPECTED_STOCK_SHA[227]`` registers.  Hash only; no stock bytes.
EXPECTED_STOCK_SHA256 = "fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167"

IMAGE_BASE = E.IMAGE_BASE                                             # 0x2D000


class ClockEmuError(RuntimeError):
    pass


# =============================================================== (0) exact MIPS semantics
M32 = 0xFFFFFFFF


def s32(v: int) -> int:
    """Reinterpret the low 32 bits as a signed word."""
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def sra(v: int, n: int) -> int:
    """MIPS ``sra`` -- arithmetic right shift of the 32-bit value."""
    return s32(v) >> n


def srl(v: int, n: int) -> int:
    """MIPS ``srl`` -- logical right shift of the 32-bit value."""
    return (v & M32) >> n


def sll(v: int, n: int) -> int:
    return s32((v << n) & M32)


def addu(a: int, b: int) -> int:
    return s32((a + b) & M32)


def subu(a: int, b: int) -> int:
    return s32((a - b) & M32)


def mult_hi(a: int, b: int) -> int:
    """MIPS ``mult`` + ``mfhi``: the high word of a SIGNED 32x32 -> 64 product."""
    return s32(((s32(a) * s32(b)) >> 32) & M32)


def magic_div(x: int, magic: int, shift: int, addback: bool) -> int:
    """The image's own reciprocal idiom, instruction for instruction.

    without add-back   ``mfhi``            -> ``sra shift`` -> ``subu (x >> 31)``
    with    add-back   ``mfhi`` + ``addu x`` -> ``sra shift`` -> ``subu (x >> 31)``
    """
    hi = mult_hi(x, magic)
    v = addu(hi, x) if addback else hi
    return subu(sra(v, shift), sra(x, 31))


# =============================================================== (1) read the constants
def _u16(blob: bytes, img: int) -> int:
    return struct.unpack_from("<H", blob, IMAGE_BASE + img)[0]


def _word(blob: bytes, img: int) -> int:
    return struct.unpack_from("<I", blob, IMAGE_BASE + img)[0]


def _shamt(blob: bytes, img: int) -> int:
    return (_word(blob, img) >> 6) & 0x1F


def _simm(blob: bytes, img: int) -> int:
    v = _u16(blob, img)
    return v - 0x10000 if v & 0x8000 else v


@dataclass(frozen=True)
class Consts:
    """Every clock-coupled constant in s0's body, read out of the container."""
    threshold: int                       # slti @0x1278 -- the phase boundary
    # the phase-progress reciprocal @0x0B6C/0x0B70, shift @0x0B84, no add-back
    prog_magic: int
    prog_shift: int
    # the arrival reciprocal @0x0C54/0x0C58, shift @0x0C70, add-back @0x0C6C
    arr_magic: int
    arr_shift: int
    arr_magic_delay: int                 # the DUPLICATE lui @0x0C04
    arr_origin: int                      # addiu @0x0C5C -- the -24 the arrival ramp starts from
    # the intro reciprocal @0x0B98/0x0B9C, shift @0x0BB4, no add-back (gated clock < 12)
    intro_magic: int
    intro_shift: int
    # the light-column reciprocal @0x1190/0x1194, shift @0x11C8, add-back (gated clock < 46)
    beam_magic: int
    beam_shift: int
    # the vertical curve's /3 @0x0CD4/0x0CD8, shift 0, no add-back -- a Q-DOMAIN reciprocal, so it
    # rebases with the arrival ramp for free and is not part of E1
    ycurve_magic: int
    # the gates and one-shots
    g_intro: int                         # slti @0x0B8C  = 12
    g_creature: int                      # slti @0x0BF0  = 24
    g_motion: int                        # addiu @0x0BFC = 24  (equality one-shot)
    g_latch: int                         # addiu @0x0E48 = 44  (equality one-shot)
    g_trail: int                         # slti @0x0E50  = 45
    g_parity_odd: int                    # slti @0x0FA4  = 35
    g_parity_even: int                   # slti @0x0FB0  = 35
    g_beam: int                          # slti @0x1188  = 46
    trail_value: int                     # addiu @0x0E68 = 4096 (the saturated write to 328($sp))

    @property
    def prog_divisor(self) -> int:
        """The divisor the progress magic actually implements, recovered by probing it."""
        return _recover_divisor(self.prog_magic, self.prog_shift, False)

    @property
    def arr_divisor(self) -> int:
        return _recover_divisor(self.arr_magic, self.arr_shift, True)

    @property
    def ycurve_divisor(self) -> int:
        """The vertical curve's Q-domain reciprocal -- 3, and nothing to do with the clock."""
        return _recover_divisor(self.ycurve_magic, 0, False)

    @property
    def beam_divisor(self) -> int:
        """The light column's own reciprocal -- self-contained, and NOT the phase length."""
        return _recover_divisor(self.beam_magic, self.beam_shift, True)

    @property
    def intro_divisor(self) -> int:
        """The intro fade's own reciprocal -- gated ``clock < 12``, also not the phase length."""
        return _recover_divisor(self.intro_magic, self.intro_shift, False)


def _recover_divisor(magic: int, shift: int, addback: bool) -> int:
    """What does this (magic, shift, add-back) triple divide by?  Probed, not assumed."""
    x = 1 << 20
    q = magic_div(x, magic, shift, addback)
    if q <= 0:
        raise ClockEmuError("magic 0x%08X shift %d does not look like a reciprocal" % (magic, shift))
    d = round(x / q)
    for cand in (d - 1, d, d + 1):
        if cand > 0 and all(magic_div(t, magic, shift, addback) == t // cand
                            for t in range(0, 1 << 21, 4093)):
            return cand
    raise ClockEmuError("magic 0x%08X shift %d is not an exact reciprocal" % (magic, shift))


def read_consts(blob: bytes) -> Consts:
    """Decode s0's constants straight out of the container -- nothing here is hard-coded."""
    return Consts(
        threshold=_simm(blob, 0x1278),
        prog_magic=(_u16(blob, 0x0B6C) << 16) | _u16(blob, 0x0B70),
        prog_shift=_shamt(blob, 0x0B84),
        arr_magic=(_u16(blob, 0x0C54) << 16) | _u16(blob, 0x0C58),
        arr_shift=_shamt(blob, 0x0C70),
        arr_magic_delay=(_u16(blob, 0x0C04) << 16) | _u16(blob, 0x0C58),
        arr_origin=_simm(blob, 0x0C5C),
        intro_magic=(_u16(blob, 0x0B98) << 16) | _u16(blob, 0x0B9C),
        intro_shift=_shamt(blob, 0x0BB4),
        beam_magic=(_u16(blob, 0x1190) << 16) | _u16(blob, 0x1194),
        beam_shift=_shamt(blob, 0x11C8),
        ycurve_magic=(_u16(blob, 0x0CD4) << 16) | _u16(blob, 0x0CD8),
        g_intro=_simm(blob, 0x0B8C),
        g_creature=_simm(blob, 0x0BF0),
        g_motion=_simm(blob, 0x0BFC),
        g_latch=_simm(blob, 0x0E48),
        g_trail=_simm(blob, 0x0E50),
        g_parity_odd=_simm(blob, 0x0FA4),
        g_parity_even=_simm(blob, 0x0FB0),
        g_beam=_simm(blob, 0x1188),
        trail_value=_simm(blob, 0x0E68),
    )


# =============================================================== (2) one tick of s0's body
@dataclass
class Tick:
    clock: int
    progress: int
    # the intro block (clock < 12)
    intro_ran: bool
    intro_ang: Optional[int]
    # the creature half (clock >= 24)
    creature_ran: bool
    arrival: Optional[int]
    cre_theta: Optional[int]
    cre_radius: Optional[int]
    cre_scale: Optional[int]
    cre_yarg: Optional[int]
    cre_ybranch: Optional[str]
    motion_oneshot: bool
    latch_oneshot: bool
    trail: int
    # the 9 wrapping beam elements
    beams: Tuple[int, ...]
    # the particle spawner
    spawner_ran: bool
    # the always-on effect model
    eff_scale: int
    eff_tilt: int
    eff_spin: int
    eff_rgb: int
    shake_env: int
    # the light-column sub-phase (clock < 46)
    column_ran: bool
    beam_cd: Optional[int]
    beam_ang: Optional[int]
    # the transition
    transitions: bool


def tick(c: Consts, clock: int) -> Tick:
    """Replay every clock-coupled expression in ``0x0B6C .. 0x1384`` for one value of the clock."""
    # ---- head: the progress ramp, stored to 320($sp) unconditionally (delay slot @0x0B94)
    progress = magic_div(sll(clock, 12), c.prog_magic, c.prog_shift, False)

    # ---- the intro fade, gated clock < 12 (self-contained /12, image 0x0B98)
    intro_ran = clock < c.g_intro
    intro_ang = magic_div(sll(clock, 10), c.intro_magic, c.intro_shift, False) if intro_ran else None

    # ---- the creature half, gated clock >= 24
    creature_ran = clock >= c.g_creature
    arrival = cre_theta = cre_radius = cre_scale = cre_yarg = None
    cre_ybranch = None
    motion_oneshot = latch_oneshot = False
    trail = 0                                        # 328($sp) is zeroed every tick @0x0B2C
    if creature_ran:
        motion_oneshot = (clock == c.g_motion)       # SetSummonMotion + SetSummonMotFrame(0)
        # the arrival ramp.  NOTE: the lui is emitted twice (0x0C04 in the bne's delay slot, 0x0C54
        # on the equal path).  Both must agree or the ramp is wrong on the clock == 24 tick only.
        magic = c.arr_magic if motion_oneshot else c.arr_magic_delay
        x = sll(addu(clock, c.arr_origin), 12)
        arrival = magic_div(x, magic, c.arr_shift, True)
        # spiral angle: (3 * (q >> 1) + srl(3 * (q >> 1), 31)) >> 1  -- the rsin ARGUMENT
        h = sra(arrival, 1)
        a = addu(sll(h, 1), h)
        cre_theta = sra(addu(a, srl(a, 31)), 1)
        # radius: ((4096 - q) * 1200 >> 12) + 24
        r = subu(4096, arrival)
        v = addu(sll(r, 2), r)                       # r * 5
        v = subu(sll(v, 4), v)                       # r * 75
        cre_radius = addu(sra(sll(v, 4), 12), 24)    # (r * 1200) >> 12, + 24
        # vertical curve + scale: two segments joined at q == 3072 (continuous in stock)
        if arrival < 3072:
            cre_ybranch = "A"
            cre_yarg = magic_div(arrival, c.ycurve_magic, 0, False)      # q // 3
            cre_scale = 6144
        else:
            cre_ybranch = "B"
            w = subu(arrival, 3072)
            cre_yarg = w
            cre_scale = subu(6144, sll(w, 2))
        latch_oneshot = (clock == c.g_latch)
        if not latch_oneshot and clock >= c.g_trail:
            trail = c.trail_value                    # the SATURATED write to 328($sp)

    # ---- the 9 wrapping beam elements (image 0x0E74 .. 0x0F98).  Each carries a phase
    # ``clock * 245 + i * 455`` reduced modulo 4096 by a loop that can subtract AT MOST TWICE, so an
    # element whose phase passes 3 * 4096 can never be reduced into range again and stops drawing.
    base = addu(sll(addu(sll(subu(sll(clock, 4), clock), 2), clock), 2), clock)   # clock * 245
    drawn: List[int] = []
    for i in range(9):
        s1 = addu(base, 455 * i)
        if not (s1 < 4096):                          # 0x0EAC slti / 0x0EB0 bne
            v1 = 2                                   # 0x0EB8
            while v1 > 0:                            # 0x0EBC blez
                s1 = subu(s1, 4096)                  # 0x0EC4
                if s1 < 4096:                        # 0x0EC8 slti / 0x0ECC beq
                    break
                v1 -= 1                              # 0x0ED0 (the beq's delay slot)
        if s1 < 4097:                                # 0x0ED4 slti / 0x0ED8 beq -> skip the draw
            drawn.append(i)

    # ---- the particle spawner: every odd tick, and every tick from 35
    spawner_ran = bool(clock & 1) or clock >= c.g_parity_even

    # ---- the effect model, driven by the progress ramp (image 0x102C .. 0x1150)
    eff_scale = (addu(progress, 8192) if progress < 3072
                 else addu(addu(sll(subu(progress, 3072), 2), subu(progress, 3072)), 11264))
    eff_tilt = sra(progress, 4)
    eff_spin = subu(sll(clock, 3), clock)            # clock * 7 -- a RATE, not a progress ramp
    eff_rgb = subu(sra(addu(sra(progress, 1), 2048), 5), 128)
    shake_env = subu(4096, progress)

    # ---- the light column, gated clock < 46 (self-contained /46, image 0x1190)
    column_ran = clock < c.g_beam
    beam_cd = beam_ang = None
    if column_ran:
        y = sll(subu(sll(addu(sll(clock, 2), clock), 4), addu(sll(clock, 2), clock)), 1)  # clock*150
        beam_cd = subu(150, magic_div(y, c.beam_magic, c.beam_shift, True))
        beam_ang = sra(progress, 2)

    return Tick(clock=clock, progress=progress, intro_ran=intro_ran, intro_ang=intro_ang,
                creature_ran=creature_ran, arrival=arrival, cre_theta=cre_theta,
                cre_radius=cre_radius, cre_scale=cre_scale, cre_yarg=cre_yarg,
                cre_ybranch=cre_ybranch, motion_oneshot=motion_oneshot,
                latch_oneshot=latch_oneshot, trail=trail, beams=tuple(drawn),
                spawner_ran=spawner_ran, eff_scale=eff_scale, eff_tilt=eff_tilt,
                eff_spin=eff_spin, eff_rgb=eff_rgb, shake_env=shake_env,
                column_ran=column_ran, beam_cd=beam_cd, beam_ang=beam_ang,
                transitions=not (clock < c.threshold))


def run(c: Consts, hi: Optional[int] = None) -> List[Tick]:
    """Every tick of the phase, 0 .. threshold inclusive (the transition fires on the last one)."""
    hi = c.threshold if hi is None else hi
    return [tick(c, k) for k in range(0, hi + 1)]


# =============================================================== (3) the invariants
#: the trig-free scalars that must land on their stock terminal value at the new last tick.
#: ``(name, accessor, first tick it is defined on)``
RAMPS: Tuple[Tuple[str, str, str], ...] = (
    ("progress", "progress", "head"),
    ("arrival", "arrival", "creature"),
    ("eff_scale", "eff_scale", "head"),
    ("eff_tilt", "eff_tilt", "head"),
    ("eff_rgb", "eff_rgb", "head"),
    ("shake_env", "shake_env", "head"),
    ("cre_radius", "cre_radius", "creature"),
    ("cre_scale", "cre_scale", "creature"),
    ("cre_theta", "cre_theta", "creature"),
)

#: the gate immediates the locked policy leaves alone
GATE_FIELDS = ("g_intro", "g_creature", "g_motion", "g_latch", "g_trail",
               "g_parity_odd", "g_parity_even", "g_beam", "trail_value")

#: the per-tick booleans/one-shots that must be identical over the whole STOCK window
DISCRETE_FIELDS = ("intro_ran", "creature_ran", "motion_oneshot", "latch_oneshot", "trail",
                   "beams", "spawner_ran", "column_ran", "beam_cd", "eff_spin")


@dataclass
class Finding:
    ok: bool
    tag: str
    detail: str

    def __str__(self) -> str:
        return "  [%s] %-34s %s" % ("PASS" if self.ok else "FAIL", self.tag, self.detail)


def _mono(vals: Sequence[int]) -> Optional[str]:
    up = all(b >= a for a, b in zip(vals, vals[1:]))
    down = all(b <= a for a, b in zip(vals, vals[1:]))
    if up or down:
        return None
    for i, (a, b) in enumerate(zip(vals, vals[1:])):
        if (up and b < a) or (not up and b > a):
            return "not monotone at index %d (%d -> %d)" % (i, a, b)
    return "not monotone"


def check_stock_endpoints(c: Consts) -> List[Finding]:
    """(a) The stock machine reproduces the endpoints A2/R3 measured independently."""
    out: List[Finding] = []
    ts = {t.clock: t for t in run(c)}
    end = c.threshold

    def want(tag, got, exp):
        out.append(Finding(got == exp, tag, "got %r, expected %r" % (got, exp)))

    want("stock progress(0)", ts[0].progress, 0)
    want("stock progress(end)", ts[end].progress, 4096)
    want("stock progress(end-1)", ts[end - 1].progress, ((end - 1) << 12) // end)
    want("stock arrival(24)", ts[c.g_creature].arrival, 0)
    want("stock arrival(end)", ts[end].arrival, 4096)
    want("stock shake_env(end)", ts[end].shake_env, 0)
    want("stock eff_rgb(0..end)", (ts[0].eff_rgb, ts[end].eff_rgb), (-64, 0))
    want("stock eff_scale(0..end)", (ts[0].eff_scale, ts[end].eff_scale), (8192, 16384))
    want("stock eff_tilt(end)", ts[end].eff_tilt, 256)
    want("stock cre_radius(24..end)", (ts[c.g_creature].cre_radius, ts[end].cre_radius), (1224, 24))
    want("stock cre_scale(24..end)", (ts[c.g_creature].cre_scale, ts[end].cre_scale), (6144, 2048))
    want("stock cre_theta(end)", ts[end].cre_theta, 3072)
    want("stock cre_y(end)", (ts[end].cre_ybranch, ts[end].cre_yarg), ("B", 1024))
    want("stock trail step 44/45", (ts[44].trail, ts[45].trail), (0, c.trail_value))
    want("stock beam_cd(0)", ts[0].beam_cd, 150)
    want("stock column off at 46", ts[46].column_ran, False)
    # the 9 beam elements retract and stay gone, well before the stock phase end
    last_beam = max((t.clock for t in ts.values() if t.beams), default=-1)
    out.append(Finding(last_beam < end - 15, "stock beams retract early",
                       "last tick with any beam drawn = %d (phase ends at %d)" % (last_beam, end)))
    out.append(Finding(all(not ts[k].beams for k in range(last_beam + 1, end + 1)),
                       "stock beams stay gone", "no element returns after tick %d" % last_beam))
    return out


def check_retime(stock: Consts, patched: Consts, n: int) -> List[Finding]:
    """(b) + (c): the patched ramps land, hold and never invert; the discrete beats do not move."""
    out: List[Finding] = []
    s = {t.clock: t for t in run(stock)}
    p = {t.clock: t for t in run(patched)}
    s_end, p_end = stock.threshold, patched.threshold

    out.append(Finding(p_end - s_end == n, "threshold moved by N",
                       "%d -> %d (N = %+d)" % (s_end, p_end, p_end - s_end)))

    # -- (b1) terminal identity: the patched last tick reproduces the stock last tick, exactly
    for name, attr, _dom in RAMPS:
        a, b = getattr(s[s_end], attr), getattr(p[p_end], attr)
        out.append(Finding(a == b, "terminal %s" % name,
                           "stock@%d = %r, patched@%d = %r" % (s_end, a, p_end, b)))
    a = (s[s_end].cre_ybranch, s[s_end].cre_yarg)
    b = (p[p_end].cre_ybranch, p[p_end].cre_yarg)
    out.append(Finding(a == b, "terminal cre_y (rsin arg)",
                       "stock %r == patched %r -- so the rsin OUTPUT is identical without "
                       "modelling rsin" % (a, b)))

    # -- (b2) start identity
    for name, attr, dom in RAMPS:
        k = 0 if dom == "head" else stock.g_creature
        a, b = getattr(s[k], attr), getattr(p[k], attr)
        out.append(Finding(a == b, "start %s @%d" % (name, k), "%r == %r" % (a, b)))

    # -- (b3) monotone, in range, never negative-where-stock-is-not
    for name, attr, dom in RAMPS:
        lo = 0 if dom == "head" else patched.g_creature
        vals = [getattr(p[k], attr) for k in range(lo, p_end + 1)]
        bad = _mono(vals)
        out.append(Finding(bad is None, "patched %s monotone" % name, bad or "over %d ticks"
                           % len(vals)))
        s_lo, s_hi = sorted((getattr(s[lo if dom == 'head' else stock.g_creature], attr),
                             getattr(s[s_end], attr)))
        inside = [v for v in vals if not (s_lo <= v <= s_hi)]
        out.append(Finding(not inside, "patched %s in stock range" % name,
                           "[%d, %d]; %d excursions" % (s_lo, s_hi, len(inside))))
        s_min = min(getattr(s[k], attr) for k in range(lo if dom == "head" else stock.g_creature,
                                                       s_end + 1))
        out.append(Finding(min(vals) >= min(0, s_min), "patched %s not negative" % name,
                           "min = %d (stock min %d)" % (min(vals), s_min)))

    # -- (b4) the two normalised ramps never exceed 4096
    for name in ("progress", "arrival"):
        vals = [getattr(p[k], name) for k in range(0, p_end + 1)
                if getattr(p[k], name) is not None]
        out.append(Finding(max(vals) <= 4096 and min(vals) >= 0, "patched %s in [0, 4096]" % name,
                           "min %d max %d" % (min(vals), max(vals))))

    # -- (c1) the gate immediates are byte-identical
    for f in GATE_FIELDS:
        a, b = getattr(stock, f), getattr(patched, f)
        out.append(Finding(a == b, "gate %s unchanged" % f, "%r == %r" % (a, b)))
    out.append(Finding(stock.arr_origin == patched.arr_origin, "arrival origin unchanged",
                       "%d == %d" % (stock.arr_origin, patched.arr_origin)))
    out.append(Finding(stock.intro_magic == patched.intro_magic
                       and stock.intro_shift == patched.intro_shift,
                       "intro /12 reciprocal untouched", "gated clock < %d" % stock.g_intro))
    out.append(Finding(stock.beam_magic == patched.beam_magic
                       and stock.beam_shift == patched.beam_shift,
                       "column /46 reciprocal untouched", "gated clock < %d" % stock.g_beam))
    out.append(Finding(patched.arr_magic == patched.arr_magic_delay,
                       "both arrival lui copies agree",
                       "0x%08X (0x0C04 delay-slot) == 0x%08X (0x0C54 equal-path)"
                       % (patched.arr_magic_delay, patched.arr_magic)))

    # -- (c2) every discrete beat fires on the same tick over the stock window
    for f in DISCRETE_FIELDS:
        diffs = [k for k in range(0, s_end + 1) if getattr(s[k], f) != getattr(p[k], f)]
        out.append(Finding(not diffs, "beat %s unmoved 0..%d" % (f, s_end),
                           "identical" if not diffs else "differs at %r" % diffs[:6]))

    # -- (c3) and it behaves over the EXTENSION as the audit predicts
    ext = range(s_end + 1, p_end + 1)
    out.append(Finding(all(p[k].trail == patched.trail_value for k in ext),
                       "extension: trail stays saturated", "328($sp) == %d on ticks %d..%d"
                       % (patched.trail_value, s_end + 1, p_end)))
    out.append(Finding(all(not p[k].beams for k in ext), "extension: no beam returns",
                       "all 9 elements stay retracted"))
    out.append(Finding(all(not p[k].column_ran for k in ext), "extension: column stays off",
                       "the clock < %d block is skipped throughout" % patched.g_beam))
    out.append(Finding(all(p[k].spawner_ran for k in ext), "extension: spawner at full rate",
                       "the clock >= %d parity arm holds" % patched.g_parity_even))
    out.append(Finding(all(not p[k].motion_oneshot and not p[k].latch_oneshot for k in ext),
                       "extension: no one-shot re-fires", "ticks %d..%d" % (s_end + 1, p_end)))
    out.append(Finding(sum(1 for k in range(p_end + 1) if p[k].transitions) == 1,
                       "exactly one transition tick", "clock %d" % p_end))
    return out


def check_half_patch(blob: bytes) -> List[Finding]:
    """Why E1d and E1e are peers: the arrival ``lui`` is emitted twice, on two different paths.

    ``0x0C04`` sits in the delay slot of the ``clock == 24`` ``bne`` and is therefore the constant
    every tick EXCEPT 24 uses; ``0x0C54`` is the equal-path copy and is live only on tick 24.  A
    retimer that patches one and not the other produces a build that is arithmetically wrong in a
    way no single-tick spot check would catch -- so this proves which half is load-bearing rather
    than asserting it.
    """
    out: List[Finding] = []
    by_img = {off - IMAGE_BASE: (off, ln, nb, why) for off, ln, nb, why in E.PROGRAM_EDITS}
    common = [by_img[i] for i in (0x1278, 0x0B6C, 0x0B70, 0x0C58, 0x0C70)]
    only_delay = E.apply_edits(blob, common + [by_img[0x0C04]])
    only_equal = E.apply_edits(blob, common + [by_img[0x0C54]])
    end = read_consts(only_delay).threshold

    d_last = tick(read_consts(only_delay), end)
    e_last = tick(read_consts(only_equal), end)
    out.append(Finding(d_last.arrival == 4096, "half-patch: 0x0C04 alone still lands",
                       "the delay-slot copy is the live one on every tick but 24 -- arrival(%d) "
                       "= %d" % (end, d_last.arrival)))
    out.append(Finding(e_last.arrival != 4096, "half-patch: 0x0C54 alone does NOT land",
                       "the equal-path copy is live only on tick 24, so every other tick runs the "
                       "spliced-together magic 0x%08X, which is not an exact reciprocal of "
                       "anything: arrival(%d) = %d, i.e. the creature sails %+d/4096 past its "
                       "mark.  Small enough to pass a glance -- which is exactly why both copies "
                       "are peers in the edit set."
                       % (read_consts(only_equal).arr_magic_delay, end, e_last.arrival,
                          e_last.arrival - 4096)))
    out.append(Finding(tick(read_consts(only_delay), 24).arrival
                       == tick(read_consts(only_equal), 24).arrival == 0,
                       "half-patch: tick 24 is blind to the split",
                       "arrival(24) = 0 for any magic, which is why the split hides"))
    return out


def check_mis_retime(stock: Consts, n: int) -> List[Finding]:
    """The MIS-RETIME artifact's offline signature: E1 omitted, so the ramps sail past 4096."""
    out: List[Finding] = []
    end = stock.threshold + n
    ts = [tick(stock, k) for k in range(end + 1)]
    last = ts[-1]
    out.append(Finding(last.progress > 4096, "mis-retime: progress overshoots",
                       "%d at clock %d (stock endpoint 4096)" % (last.progress, end)))
    out.append(Finding(last.arrival > 4096, "mis-retime: arrival overshoots",
                       "%d at clock %d" % (last.arrival, end)))
    out.append(Finding(last.shake_env < 0, "mis-retime: shake envelope inverts",
                       "4096 - progress = %d -- the camera jitter grows the wrong way"
                       % last.shake_env))
    out.append(Finding(last.cre_radius < 0, "mis-retime: creature radius goes negative",
                       "%d -- the creature overshoots its mark and flies out the far side"
                       % last.cre_radius))
    out.append(Finding(last.cre_scale < 0, "mis-retime: creature scale goes negative",
                       "%d -- the model inverts" % last.cre_scale))
    out.append(Finding(last.eff_rgb > 0, "mis-retime: effect RGB overbrightens",
                       "%d (stock endpoint 0)" % last.eff_rgb))
    return out


def residuals(stock: Consts, patched: Consts) -> List[str]:
    """What the edit set CHANGES that is neither an endpoint nor a beat -- stated, not hidden.

    Every item here is a deliberate consequence of the locked policy (discrete beats keep their
    stock ticks, progress ramps are retuned), not a defect.  ``B0-CLOCK-AUDIT.md`` section 6 argues
    each one; this function keeps the numbers honest by re-deriving them from the container.
    """
    s = {t.clock: t for t in run(stock)}
    p = {t.clock: t for t in run(patched)}
    out: List[str] = []
    out.append(
        "eff_spin (rotation Y = clock*7) is a RATE, not a progress ramp, and is NOT retuned: it "
        "reaches %d at the stock end and %d at the new end (+%d units = %.1f degrees on the "
        "4096-unit circle).  Retuning it would slow a continuous spin, which is the wrong "
        "behaviour for a longer entrance."
        % (s[stock.threshold].eff_spin, p[patched.threshold].eff_spin,
           p[patched.threshold].eff_spin - s[stock.threshold].eff_spin,
           (p[patched.threshold].eff_spin - s[stock.threshold].eff_spin) * 360.0 / 4096))
    lo = max(k for k in s if s[k].column_ran)
    out.append(
        "the light column (gated clock < %d, own /%d countdown) keeps its stock schedule -- its "
        "countdown is identical tick for tick (%d at clock %d, both) -- but the rcos angle it "
        "reads from the progress ramp is now %d instead of %d on its last tick, because that ramp "
        "is slower everywhere.  The column therefore ends its own sub-phase %.0f%% of the way "
        "through the progress ramp instead of %.0f%%."
        % (stock.g_beam, stock.beam_divisor, s[lo].beam_cd, lo,
           p[lo].beam_ang, s[lo].beam_ang,
           100.0 * p[lo].progress / 4096, 100.0 * s[lo].progress / 4096))
    out.append(
        "the particle spawner runs at full rate for %d extra ticks (clock %d..%d) and the bone "
        "trail stays lit for the same %d, both because their gates are absolute ticks the policy "
        "deliberately does not move."
        % (patched.threshold - stock.threshold, stock.threshold + 1, patched.threshold,
           patched.threshold - stock.threshold))
    out.append(
        "the float clip keeps looping through the extension.  N = +%d is exactly two 24-frame "
        "loops, so the clip frame at the new phase end is the same one stock ends on."
        % (patched.threshold - stock.threshold))
    return out


# =============================================================== (4) the same-length proof
def _decode(word: int) -> Dict[str, int]:
    return dict(op=word >> 26, rs=(word >> 21) & 31, rt=(word >> 16) & 31,
                rd=(word >> 11) & 31, sa=(word >> 6) & 31, funct=word & 63,
                imm=word & 0xFFFF)


def check_same_length(stock_blob: bytes, patched_blob: bytes) -> List[Finding]:
    """(d) No instruction was added, removed, lengthened or re-typed."""
    out: List[Finding] = []
    out.append(Finding(len(stock_blob) == len(patched_blob), "container length unchanged",
                       "%d == %d bytes" % (len(stock_blob), len(patched_blob))))
    n_instr = (len(stock_blob) - IMAGE_BASE) // 4
    out.append(Finding((len(patched_blob) - IMAGE_BASE) // 4 == n_instr,
                       "instruction count unchanged", "%d words after the image base" % n_instr))

    touched = {}
    for off, old_len, new_bytes, _why in E.PROGRAM_EDITS:
        out.append(Finding(len(new_bytes) == old_len, "edit @0x%X same-length" % off,
                           "%d == %d" % (len(new_bytes), old_len)))
        img = off - IMAGE_BASE
        word_img = img & ~3
        out.append(Finding((img - word_img) + old_len <= 4, "edit @0x%X inside one word" % off,
                           "image 0x%04X, word 0x%04X" % (img, word_img)))
        touched.setdefault(word_img, []).append(off)

    diff = [i for i in range(len(stock_blob)) if stock_blob[i] != patched_blob[i]]
    words = sorted({(d - IMAGE_BASE) & ~3 for d in diff})
    out.append(Finding(set(words) <= set(touched), "no byte changed outside the declared words",
                       "%d bytes changed in %d words: %s"
                       % (len(diff), len(words), ", ".join("0x%04X" % w for w in words))))

    # An I-type word HAS no rd/sa/funct -- those bits are part of the imm16 -- so the structural
    # comparison must be taken over the fields the instruction's OWN format defines.  Which format
    # that is comes from the opcode, not from a hand-written table.
    for word_img in sorted(touched):
        a = _decode(struct.unpack_from("<I", stock_blob, IMAGE_BASE + word_img)[0])
        b = _decode(struct.unpack_from("<I", patched_blob, IMAGE_BASE + word_img)[0])
        if a["op"] == 0:                                   # R-type: only the shamt may move
            structural, moved_field = ("op", "rs", "rt", "rd", "funct"), "sa"
        else:                                              # I-type: only the imm16 may move
            structural, moved_field = ("op", "rs", "rt"), "imm"
        same = all(a[k] == b[k] for k in structural)
        only = a[moved_field] != b[moved_field]
        out.append(Finding(same and only, "word 0x%04X keeps its shape" % word_img,
                           "%s preserved; %s %s -> %s"
                           % ("/".join(structural), moved_field, a[moved_field], b[moved_field])))
    return out


# =============================================================== (5) the container
def load_container(path: Optional[str] = None, ef_id: int = 227) -> Tuple[bytes, str]:
    """The stock container, from the user's own install, with the registered drift guard applied.

    Resolution order: an explicit ``path`` / ``$FF9_W3_EF227`` -> ``rescore.read_stock_effect``
    (``resources.assets``, the authoritative source) -> the SCRATCH corpus copy.  Whatever the
    source, the sha256 must match :data:`EXPECTED_STOCK_SHA256`.
    """
    src = path or os.environ.get("FF9_W3_EF227")
    blob = None
    if src and os.path.exists(src):
        blob = open(src, "rb").read()
        where = src
    if blob is None:
        try:
            import rescore                                             # noqa: F401
            blob, where = rescore.read_stock_effect(ef_id)
        except Exception as exc:                                       # pragma: no cover
            fallback = os.path.join(r"C:\gd\SCRATCH\summon-format", "ef%03d.bytes" % ef_id)
            if not os.path.exists(fallback):
                raise ClockEmuError(
                    "could not read the stock container (%s) and no corpus copy at %s"
                    % (exc, fallback))
            blob, where = open(fallback, "rb").read(), fallback
    got = hashlib.sha256(blob).hexdigest()
    if got != EXPECTED_STOCK_SHA256:
        raise ClockEmuError(
            "ef%03d drift: %s has sha256 %s, expected %s.  Re-run the B0 audit before trusting any "
            "offset in w3_program_edits." % (ef_id, where, got, EXPECTED_STOCK_SHA256))
    return blob, where


# =============================================================== (6) the audit
@dataclass
class Audit:
    source: str
    stock: Consts
    patched: Consts
    findings: List[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(f.ok for f in self.findings)

    @property
    def failures(self) -> List[Finding]:
        return [f for f in self.findings if not f.ok]


def audit(path: Optional[str] = None, n: int = E.N_TICKS) -> Audit:
    """The whole B0 proof.  ``B2``'s gates call this and assert ``a.ok``."""
    blob, where = load_container(path)
    E.verify_stock(blob)
    patched_blob = E.apply_edits(blob)
    sc, pc = read_consts(blob), read_consts(patched_blob)

    # the frozen table must equal its own derivation
    d = E.recompute(n)
    f: List[Finding] = [
        Finding(pc.threshold == d["threshold"], "table matches its derivation",
                "threshold %d, /%d magic 0x%08X shift %d, /%d magic 0x%08X shift %d"
                % (d["threshold"], d["progress_divisor"], d["progress_magic"], d["progress_shift"],
                   d["arrival_divisor"], d["arrival_magic"], d["arrival_shift"])),
        Finding(sc.prog_divisor == sc.threshold, "stock progress ramp divides by the threshold",
                "/%d" % sc.prog_divisor),
        Finding(sc.arr_divisor == sc.threshold - sc.g_creature,
                "stock arrival ramp divides by threshold-24", "/%d" % sc.arr_divisor),
        Finding(sc.beam_divisor == sc.g_beam and sc.intro_divisor == sc.g_intro,
                "the other two reciprocals encode GATES, not the phase length",
                "light column /%d matches its own clock<%d gate; intro /%d matches clock<%d; the "
                "vertical curve's /%d is Q-domain -- none depends on the threshold, so none is "
                "retuned" % (sc.beam_divisor, sc.g_beam, sc.intro_divisor, sc.g_intro,
                             sc.ycurve_divisor)),
        Finding(pc.prog_divisor == pc.threshold, "patched progress ramp divides by the threshold",
                "/%d" % pc.prog_divisor),
        Finding(pc.arr_divisor == pc.threshold - pc.g_creature,
                "patched arrival ramp divides by threshold-24", "/%d" % pc.arr_divisor),
    ]
    # THE IDENTITY CHECK.  Run the same derivation at N = 0 and splice it in: if the recipe is a
    # faithful reading of the compiler's idiom rather than a rationalisation, it must reproduce the
    # SHIPPING BYTES exactly.  It does -- 0 bytes differ.  This is the strongest single piece of
    # evidence that the two new reciprocals are the constants the original author would have emitted.
    zero = E.apply_edits(blob, E.build_edits(0))
    n_zero = sum(1 for a, b in zip(blob, zero) if a != b)
    f.append(Finding(n_zero == 0, "N = 0 reproduces the stock bytes",
                     "%d bytes differ -- the derivation is a no-op at zero stretch, so its /69 and "
                     "/45 magics ARE the shipping ones" % n_zero))

    f += check_stock_endpoints(sc)
    f += check_retime(sc, pc, n)
    f += check_half_patch(blob)
    f += check_mis_retime(sc, n)
    f += check_same_length(blob, patched_blob)
    f.append(Finding(E.changed_byte_count(blob) == 12, "E1 changes 12 bytes",
                     "%d bytes differ across 7 sites (14 written)" % E.changed_byte_count(blob)))
    return Audit(source=where, stock=sc, patched=pc, findings=f)


def _print_table(sc: Consts, pc: Consts) -> None:
    hdr = ("clk", "prog", "arriv", "radius", "cscale", "theta", "yarg", "escale", "tilt",
           "spin", "rgb", "shake", "trail", "cd", "beams")
    print("  " + " ".join("%7s" % h for h in hdr))
    for label, c in (("STOCK", sc), ("PATCHED", pc)):
        print("  --- %s (threshold %d) ---" % (label, c.threshold))
        for t in run(c):
            if not (t.clock <= 2 or t.clock in (11, 12, 23, 24, 25, 34, 35, 43, 44, 45, 46, 50, 51)
                    or t.clock >= c.threshold - 2 or t.clock % 12 == 0):
                continue
            print("  " + " ".join("%7s" % v for v in (
                t.clock, t.progress, t.arrival, t.cre_radius, t.cre_scale, t.cre_theta,
                "%s%s" % (t.cre_ybranch or "-", t.cre_yarg if t.cre_yarg is not None else ""),
                t.eff_scale, t.eff_tilt, t.eff_spin, t.eff_rgb, t.shake_env, t.trail,
                t.beam_cd, len(t.beams))))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--blob", help="an explicit stock ef227 container (default: the user's install)")
    ap.add_argument("--table", action="store_true", help="also dump the per-tick signal table")
    ap.add_argument("-n", type=int, default=E.N_TICKS, help="ticks to stretch by (default 48)")
    a = ap.parse_args(argv)

    res = audit(a.blob, a.n)
    print("W3 / B0 -- ef227:c0 state 0 clock audit")
    print("  source            %s" % res.source)
    print("  stock             threshold %d, /%d progress (shift %d), /%d arrival (shift %d, "
          "add-back)" % (res.stock.threshold, res.stock.prog_divisor, res.stock.prog_shift,
                         res.stock.arr_divisor, res.stock.arr_shift))
    print("  patched           threshold %d, /%d progress (shift %d), /%d arrival (shift %d, "
          "add-back)" % (res.patched.threshold, res.patched.prog_divisor, res.patched.prog_shift,
                         res.patched.arr_divisor, res.patched.arr_shift))
    print()
    for f in res.findings:
        print(f)
    print("\n  %d checks, %d failures." % (len(res.findings), len(res.failures)))
    print("\n  RESIDUALS (deliberate consequences of the locked policy, not defects):")
    for i, r in enumerate(residuals(res.stock, res.patched), 1):
        print("   %d. %s" % (i, r))
    if a.table:
        print()
        _print_table(res.stock, res.patched)
    return 0 if res.ok else 1


if __name__ == "__main__":               # pragma: no cover
    raise SystemExit(_main())
