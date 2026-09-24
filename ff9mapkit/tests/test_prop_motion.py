"""``[[prop]] motion`` -- the PURE tests (sine kit rung 1; the rung-1 spec's section 7, items 1-17;
studies/sine-kit/PLAN.md).

No install, no templates, no game, so this file NEVER skips. Every ``.eb`` here is synthetic: a hand-assembled
Main_Init with prop Inits, or the kit's own ``inject_prop`` over a synthetic blank. The daemon runs in
:class:`tests._ebengine.MotionEngine`, which applies the EBin rules: the 26-bit wrap, truncating ``B_DIV``, float32
``rsin``, and Instance BYTES that alias. The oracle is :func:`ff9mapkit.content.motion.pose`.

THE PREDICTOR IS THE ORACLE, so nothing here re-derives the motion math, with two exceptions:
  * rung 0's in-game-proven predictor (``studies/sine-kit/sine0_bench.py``, 15/15), IMPORTED, is the anchor the
    kit's reduced model must reproduce;
  * the two independent float32 ``rsin`` copies (rung 0's numpy one, ``_ebengine.ff9_rtrig``'s struct one) that
    the SIN/COS tables are checked against.

Each test names the mutation it kills in brackets.
"""
from __future__ import annotations

import ast
import dataclasses
import functools
import importlib.util
import math
import re
import struct
import time
from pathlib import Path

import pytest

from ff9mapkit import build
from ff9mapkit.content import motion as M
from ff9mapkit.content import object as _object
from ff9mapkit.content import prop as _prop_mod
from ff9mapkit.eb import EbScript, disasm as D, edit as eb_edit, exprasm, opcodes
from ff9mapkit.eb.labelasm import JMP_IFNOT, asm, label
from ff9mapkit.eb.model import pack_entry

from ._ebengine import MotionEngine, ff9_rtrig

_STUDY = Path(__file__).resolve().parents[2] / "studies" / "sine-kit"
C7_ANGLES = (6684, 10684, 13892)          # rung 0 C7: raw B_SIN2 at unreduced angles where float32 != float64


@functools.lru_cache(maxsize=None)
def _rung0():
    """``studies/sine-kit/sine0_bench.py``: rung 0's IN-GAME-PROVEN predictor (numpy float32 ``rsin`` on the
    UNREDUCED angles its daemon fed ``B_SIN``). Imported, never re-derived."""
    spec = importlib.util.spec_from_file_location("_sine0_bench_rung0", _STUDY / "sine0_bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ============================================================================ toml fixtures
def _prop(motion=None, **over) -> dict:
    """A ``[[prop]]`` table: a walk-through, shadowless balloon at (0, -800) unless ``over`` says otherwise
    (``key=None`` drops the key, i.e. the author did not write it)."""
    p = {"prop": "balloon", "pos": [0, -800], "collision": False, "shadow": False}
    p.update(over)
    if motion is not None:
        p["motion"] = motion
    return {k: v for k, v in p.items() if v is not None}


def _spec(motion, idx: int = 0, **over) -> M.MotionSpec:
    return M.parse(_prop(motion, **over), idx)


# the rung-1 bench movers (the spec's section 9). A and B are rung 0's A and B exactly
BENCH = {
    "A": _prop({"radius": 300, "period": 128, "height": 150, "turn": "travel"}),
    "B": _prop({"radius": 300, "period": 128, "phase": 0.5, "height": 150, "turn": "travel",
                "bob": {"amp": 60, "period": 256}}, prop="cask"),
    "C": _prop({"radius": 250, "period": 90, "reverse": True, "height": 80, "turn": "travel"},
               prop="letter", pos=[-750, -450], face=32),
    "D": _prop({"to": [-301, -1600], "period": 150}, prop="chest", pos=[-1000, -1600], shadow=None),
    "E": _prop({"turn": "spin", "period": 64, "reverse": True}, prop="sword", pos=[750, -350],
               collision=True, shadow=None),
    "F": _prop({"turn": "swing", "swing": 40, "period": 75, "phase": 0.25}, prop="fish", pos=[750, -1350],
               face=128, shadow=None),
    "G": _prop({"radius": 8191, "period": 64}, prop="hand_bell"),
}


def _bench_movers(names="ABCDEFG", uid0: int = 2) -> list:
    return [(M.parse(BENCH[k], i), uid0 + i) for i, k in enumerate(names)]


# ============================================================================ the engine run + its oracle
def _expect(movers, n: int) -> list:
    """What tick ``n`` must issue, from the predictor: 0xAD (x, b, z) for a mover that moves, then 0x87's
    facing BYTE for one that turns, mover by mover in toml order."""
    out = []
    for s, uid in movers:
        p = M.pose(s, n)
        if s.moves:
            out.append((M.MOVE_EX, uid, (p.x, p.b, p.z)))
        if s.turns:
            out.append((M.TURN_EX, uid, p.face))
    return out


def _seen(tick) -> list:
    """One captured tick, with 0x87's operand reduced to the byte the engine faces (``(Int16)(v << 4)``). The raw
    operand must be non-negative and <= 702 (spec section 2), so the shift cannot wrap."""
    out = []
    for op, uid, vals in tick:
        if op == M.TURN_EX:
            (v,) = vals
            assert 0 <= v <= 702, f"0x87 operand {v} for uid {uid} is outside [0, 702]"
            out.append((op, uid, v & 0xFF))
        else:
            out.append((op, uid, vals))
    return out


def _run(movers, n: int, *, strict: bool = True):
    """Run the EMITTED daemon (the entry's body, after its 6-byte header) ``n`` ticks. Returns (ticks, engine)."""
    entry, loc = M.entry_bytes(movers)
    eng = MotionEngine(loc, strict_reduced=strict)
    return eng.ticks(entry[6:], n), eng


def _clock_values(eng, k: int) -> list:
    """The K clocks, read back as signed Int16s at the Instance BYTE offsets 0, 2, ..., 2K-2."""
    return [struct.unpack_from("<h", eng.inst, 2 * i)[0] for i in range(k)]


# ============================================================================ synthetic .eb assembly
def _set(text: str) -> bytes:
    """A ``SET`` (0x05) expression statement."""
    return opcodes.encode(0x05, exprasm.assemble(text + " B_EXPR_END"), arg_flags=0b1)


COND = _set("Global.Bit[9000]")                 # an opaque story condition for a JMP_IFNOT to consume


def _eb(*entries) -> bytes:
    """A synthetic ``.eb``: the 0x80 header, one 8-byte table slot per entry, then the bodies (``None`` is an
    empty slot). The layout :class:`EbScript` parses, as in test_fork_walkmesh_lint's ``_minimal_eb``."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = len(entries)
    table, blob = bytearray(), bytearray()
    for e in entries:
        if e:
            table += struct.pack("<HHBBH", 8 * len(entries) + len(blob), len(e), 0, 0, 0)
            blob += e
        else:
            table += bytes(8)
    return bytes(head + table + blob)


def _main(*items) -> bytes:
    """Entry 0 with a Main_Init assembled from ``items`` (labelasm: bytes, labels, jumps) plus a closing RETURN."""
    return pack_entry(0, [(0, asm(list(items) + [opcodes.RETURN]))])


def _init(model: int = 226, *, before=b"", between=b"", after=b"", ret: bool = True) -> bytes:
    """A mover's tag-0 Init in the kit prop's straight-line shape: SetModel, CreateObject, TurnInstant,
    EnableHeadFocus(0), RETURN. ``before`` / ``between`` / ``after`` splice a doctored op in."""
    return (before + opcodes.set_model(model, 0) + between + opcodes.create_object(0, -800)
            + opcodes.turn_instant(64) + opcodes.encode(0x47, 0) + after + (opcodes.RETURN if ret else b""))


def _obj(body: bytes) -> bytes:
    return pack_entry(2, [(0, body)])


FILLER = pack_entry(0, [(0, opcodes.RETURN)])     # an occupied, inert code entry
MOVER_YIELDS = frozenset({0x00, 0x01, 0x02, 0x03, 0x22})     # NOP (a one-tick yield), the jumps, Wait
IO1, IO2, IC3 = opcodes.init_object(1, 0), opcodes.init_object(2, 0), opcodes.init_code(3, 0)


def _order_eb(*main_items, m1: bytes | None = None, m2: bytes | None = None, extra=()) -> bytes:
    """Main_Init from ``main_items``; movers at 1 (balloon 226) and 2 (cask 241); the daemon's code entry at 3."""
    return _eb(_main(*main_items), _obj(m1 or _init(226)), _obj(m2 or _init(241)), FILLER, *extra)


def _main_ops(eb: bytes) -> list:
    s = EbScript.from_bytes(eb)
    f = s.entry(0).func_by_tag(0)
    return [(i.op, eb[i.off + 1] if i.op in (0x07, 0x09) else None) for i in D.iter_code(eb, f.abs_start, f.abs_end)]


# ============================================================================ 1. parse refusals
_REFUSED = [
    # (id, motion, prop overrides, fragment the MotionError must carry)
    ("unknown_key", {"radius": 300, "period": 128, "raduis": 3}, {}, "unknown key(s) raduis"),
    ("bool_radius", {"radius": True, "period": 128}, {}, "radius must be an integer 1..8191"),
    ("bool_period", {"radius": 300, "period": True}, {}, "period must be an integer 2..8192"),
    ("radius_0", {"radius": 0, "period": 128}, {}, "radius must be an integer 1..8191"),
    ("radius_neg", {"radius": -1, "period": 128}, {}, "radius must be an integer 1..8191"),
    ("radius_8192", {"radius": 8192, "period": 128}, {}, "radius must be an integer 1..8191"),
    ("radius_float", {"radius": 300.0, "period": 128}, {}, "radius must be an integer 1..8191"),
    ("radius_and_to", {"radius": 300, "to": [100, -800], "period": 128}, {}, "are exclusive"),
    ("to_is_pos", {"to": [0, -800], "period": 128}, {}, "to equals pos"),
    ("to_far_x", {"to": [16383, -800], "period": 128}, {}, "more than 16382 units from pos"),
    ("to_far_z", {"to": [0, 15583], "period": 128}, {}, "more than 16382 units from pos"),
    ("to_int16", {"to": [32768, -800], "period": 128}, {}, "outside the signed 16-bit world range"),
    ("to_int16_neg", {"to": [0, -32769], "period": 128}, {}, "outside the signed 16-bit world range"),
    ("to_short", {"to": [100], "period": 128}, {}, "to must be [x, z] integers"),
    ("to_float", {"to": [100.5, -800], "period": 128}, {}, "to must be [x, z] integers"),
    ("to_bool", {"to": [True, -800], "period": 128}, {}, "to must be [x, z] integers"),
    ("period_1", {"radius": 300, "period": 1}, {}, "period must be an integer 2..8192"),
    ("period_8193", {"radius": 300, "period": 8193}, {}, "period must be an integer 2..8192"),
    ("period_float", {"radius": 300, "period": 2.5}, {}, "period must be an integer 2..8192"),
    ("period_missing_radius", {"radius": 300}, {}, "is required with radius"),
    ("period_missing_to", {"to": [100, -800]}, {}, "is required with to"),
    ("period_missing_turn", {"turn": "spin"}, {}, "is required with turn"),
    ("bob_amp_0", {"bob": {"amp": 0, "period": 100}}, {}, "bob amp must be an integer 1..8191"),
    ("bob_amp_8192", {"bob": {"amp": 8192, "period": 100}}, {}, "bob amp must be an integer 1..8191"),
    ("bob_amp_missing", {"bob": {"period": 100}}, {}, "bob amp must be an integer 1..8191"),
    ("bob_period_1", {"bob": {"amp": 60, "period": 1}}, {}, "bob: period must be an integer 2..8192"),
    ("bob_period_8193", {"bob": {"amp": 60, "period": 8193}}, {}, "bob: period must be an integer 2..8192"),
    ("bob_unknown", {"bob": {"amp": 60, "period": 100, "phaze": 0.5}}, {}, "bob has unknown key(s) phaze"),
    ("bob_no_period", {"bob": {"amp": 60}}, {}, "bob needs a period"),
    ("bob_not_table", {"bob": 60}, {}, "bob must be a table"),
    ("bob_phase_1", {"bob": {"amp": 60, "period": 100, "phase": 1.0}}, {}, "bob: phase must be a number in [0, 1)"),
    ("phase_1", {"radius": 300, "period": 128, "phase": 1.0}, {}, "phase must be a number in [0, 1)"),
    ("phase_neg", {"radius": 300, "period": 128, "phase": -0.1}, {}, "phase must be a number in [0, 1)"),
    ("phase_bool", {"radius": 300, "period": 128, "phase": True}, {}, "phase must be a number in [0, 1)"),
    ("phase_str", {"radius": 300, "period": 128, "phase": "0.5"}, {}, "phase must be a number in [0, 1)"),
    ("phase_bob_only", {"bob": {"amp": 60, "period": 100}, "phase": 0.5}, {},
     "phase needs a horizontal or turn channel"),
    ("height_16384", {"radius": 300, "period": 128, "height": 16384}, {}, "height must be an integer within +-16383"),
    ("height_neg", {"radius": 300, "period": 128, "height": -16384}, {}, "height must be an integer within +-16383"),
    ("height_float", {"radius": 300, "period": 128, "height": 1.5}, {}, "height must be an integer within +-16383"),
    ("turn_wobble", {"turn": "wobble", "period": 64}, {}, "turn must be one of travel, spin, swing"),
    ("travel_alone", {"turn": "travel", "period": 64}, {}, "it needs radius"),
    ("travel_shuttle", {"to": [100, -800], "turn": "travel", "period": 64}, {}, "it needs radius"),
    ("spin_orbit", {"radius": 300, "turn": "spin", "period": 64}, {}, 'turn = "spin" with radius'),
    ("swing_no_turn", {"radius": 300, "period": 128, "swing": 30}, {}, 'swing is only for turn = "swing"'),
    ("swing_missing", {"turn": "swing", "period": 64}, {}, "needs swing = 1..127"),
    ("swing_128", {"turn": "swing", "swing": 128, "period": 64}, {}, "needs swing = 1..127"),
    ("swing_0", {"turn": "swing", "swing": 0, "period": 64}, {}, "needs swing = 1..127"),
    ("swing_bool", {"turn": "swing", "swing": True, "period": 64}, {}, "needs swing = 1..127"),
    ("reverse_shuttle", {"to": [100, -800], "period": 64, "reverse": True}, {}, "reverse applies only"),
    ("reverse_swing", {"turn": "swing", "swing": 20, "period": 64, "reverse": True}, {}, "reverse applies only"),
    ("reverse_alone", {"reverse": True}, {}, "reverse applies only"),
    ("reverse_bob", {"bob": {"amp": 60, "period": 100}, "reverse": True}, {}, "reverse applies only"),
    ("reverse_not_bool", {"radius": 300, "period": 128, "reverse": 1}, {}, "reverse must be true or false"),
    ("period_no_channel", {"period": 100}, {}, "period without a channel"),
    ("height_no_channel", {"height": 100}, {}, "no channel"),
    ("empty", {}, {}, "is empty"),
    ("not_a_table", 5, {}, "must be a table"),
    ("a_list", [300, 128], {}, "must be a table"),
    ("pos_float", {"radius": 300, "period": 128}, {"pos": [0.5, -800]}, "needs an integer pos"),
    ("pos_missing", {"radius": 300, "period": 128}, {"pos": None}, "needs an integer pos"),
    # [review] a malformed PROP-level key parse() reads is a MotionError, never a bare TypeError / ValueError
    ("pos_scalar", {"radius": 300, "period": 128}, {"pos": 5}, "needs an integer pos"),
    ("pos_string", {"radius": 300, "period": 128}, {"pos": "ab"}, "needs an integer pos"),
    ("face_string", {"radius": 300, "period": 128, "turn": "travel"}, {"face": "north"}, "face must be an integer"),
    ("face_float", {"radius": 300, "period": 128, "turn": "travel"}, {"face": 1.5}, "face must be an integer"),
]


@pytest.mark.parametrize("motion, over, frag", [r[1:] for r in _REFUSED], ids=[r[0] for r in _REFUSED])
def test_parse_refuses(motion, over, frag):
    """[the removal of each individual key/type/range check] Every row raises MotionError, naming the prop and
    the rule broken."""
    with pytest.raises(M.MotionError) as ei:
        M.parse(_prop(motion, **over), 3)
    msg = str(ei.value)
    assert frag in msg
    assert msg.startswith("[[prop]] 'balloon' motion")


def test_parse_without_motion_is_none():
    assert M.parse(_prop(None), 0) is None
    assert M.any_motion({"prop": [_prop(None), _prop(None)]}) is False
    assert M.any_motion({"prop": [_prop(None), _prop({"turn": "spin", "period": 9})]}) is True


# ============================================================================ 2. the legal boundaries
_ACCEPTED = [
    ("radius_max", {"radius": 8191, "period": 64}, "radius", 8191),
    ("radius_min", {"radius": 1, "period": 64}, "radius", 1),
    ("period_2", {"radius": 300, "period": 2}, "period", 2),
    ("period_8192", {"radius": 300, "period": 8192}, "period", 8192),
    ("amp_max", {"bob": {"amp": 8191, "period": 100}}, "bob_amp", 8191),
    ("bob_period_2", {"bob": {"amp": 1, "period": 2}}, "bob_period", 2),
    ("bob_period_8192", {"bob": {"amp": 1, "period": 8192}}, "bob_period", 8192),
    ("bob_inherits_period", {"turn": "spin", "period": 90, "bob": {"amp": 10}}, "bob_period", 90),
    ("bob_rides_bare_period", {"period": 90, "bob": {"amp": 10}}, "bob_period", 90),
    ("swing_127", {"turn": "swing", "swing": 127, "period": 75}, "swing", 127),
    ("swing_1", {"turn": "swing", "swing": 1, "period": 75}, "swing", 1),
    ("height_max", {"radius": 300, "period": 64, "height": 16383}, "height", 16383),
    ("height_min", {"radius": 300, "period": 64, "height": -16383}, "height", -16383),
    ("phase_0999", {"radius": 300, "period": 64, "phase": 0.999}, "phase_u", 4092),
    ("phase_quarter", {"radius": 300, "period": 64, "phase": 0.25}, "phase_u", 1024),
    ("phase_int_0", {"radius": 300, "period": 64, "phase": 0}, "phase_u", 0),
    ("bob_phase", {"bob": {"amp": 5, "period": 64, "phase": 0.5}}, "bob_phase_u", 2048),
    ("to_x_16382", {"to": [16382, -800], "period": 64}, "half", (8191, 0)),
    ("to_both_16382", {"to": [-16382, 15582], "period": 64}, "half", (-8191, 8191)),
    ("to_odd", {"to": [-301, -1600], "period": 64}, "mid", (-150, -1200)),
]


@pytest.mark.parametrize("motion, field, want", [r[1:] for r in _ACCEPTED], ids=[r[0] for r in _ACCEPTED])
def test_parse_accepts_boundaries(motion, field, want):
    """[an over-tight cap] Every legal extreme parses, and to the value the predictor then uses."""
    s = M.parse(_prop(motion), 0)
    assert getattr(s, field) == want


def test_parse_face_is_the_init_byte():
    """``face`` is normalised exactly as ``prop_init_tail`` writes its TurnInstant (``int(face) & 0xFF``), so the
    predicted facing base IS the Init's byte."""
    assert _spec({"turn": "spin", "period": 64}, face=300).face == 300 & 0xFF == 44
    assert _spec({"turn": "spin", "period": 64}).face == 0
    tail = _prop_mod.prop_init_tail(300)
    assert tail[-1] == 44 and tail[-3] == 0x36                   # TurnInstant(44)
    # the face offset is additive, so 300 and 44 drive identical facings
    a = _spec({"radius": 300, "period": 128, "turn": "travel"}, face=300)
    b = _spec({"radius": 300, "period": 128, "turn": "travel"}, face=44)
    assert M.path(a) == M.path(b)


def test_parse_shuttle_far_end_is_one_short_on_an_odd_axis():
    s = M.parse(BENCH["D"], 0)
    assert (s.path, s.half, s.mid, s.far_end) == ("shuttle", (349, 0), (-651, -1600), (-302, -1600))
    assert M.pose(s, 0)[:3] == (-1000, 0, -1600)                  # th = 0 is exactly pos
    assert M.pose(s, 75)[:3] == (-302, 0, -1600)                  # the half cycle is the far end
    even = _spec({"to": [-300, -1000], "period": 150}, pos=[-1000, -1600], shadow=None)
    assert even.far_end == (-300, -1000) and M.pose(even, 75)[:3] == (-300, 0, -1000)


# ============================================================================ 3. the caps derive from the engine
def test_caps_derive_from_engine():
    """[a second hard-coded number, or a cap past the engine] The engine decodes an expression value as signed
    26-bit (EBin.cs:1682), and every cap is an expression of ``opcodes.EXPR_VALUE_MAX``: the tightest one that keeps
    ``r * SIN`` and ``c * 4096`` legal."""
    V = opcodes.EXPR_VALUE_MAX
    assert V == (1 << 25) - 1
    assert M.AMP_MAX * 4096 <= V < (M.AMP_MAX + 1) * 4096
    assert (M.PERIOD_MAX - 1) * 4096 <= V < M.PERIOD_MAX * 4096
    assert (M.AMP_MAX, M.PERIOD_MAX) == (8191, 8192)
    tree = ast.parse(Path(M.__file__).read_text(encoding="utf-8"))
    assigns = {t.id: ast.unparse(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Name)}
    assert "EXPR_VALUE_MAX" in assigns["AMP_MAX"]
    assert assigns["PERIOD_MAX"] == "AMP_MAX + 1"
    ints = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and type(n.value) is int}
    assert not ints & {8191, 8193, 16382, 33554431}, "a cap is hard-coded instead of derived"


# ============================================================================ 4. the trig table is the engine's
def test_trig_table_is_engine():
    """[a float64-round/floor or mis-scaled table] SIN/COS equal BOTH independent float32 ``rsin`` copies at all
    4096 angles, and those copies reproduce rung 0's in-game C7 reads."""
    R = _rung0()
    assert len(M.SIN) == len(M.COS) == 4096
    for a in range(4096):
        assert M.SIN[a] == ff9_rtrig(math.sin, a) == R.rsin(a), a
        assert M.COS[a] == ff9_rtrig(math.cos, a) == R.rcos(a), a
    # rung 0 C7, measured in-game: raw B_SIN2 at these UNREDUCED angles read the float32 values ...
    assert [R.rsin(a) for a in C7_ANGLES] == [-3017, -2579, 2579]
    assert [ff9_rtrig(math.sin, a) for a in C7_ANGLES] == [-3017, -2579, 2579]
    # ... one off the exact truncated sine, which is what the REDUCED table (all the kit ever reads) holds
    assert [M.SIN[a & 4095] for a in C7_ANGLES] == [-3018, -2578, 2578]
    # on [0, 4095] the table IS the truncated sine (the census: 0 of 8192 differ), so the path is float-model-free
    assert all(M.SIN[t] == int(4096 * math.sin(2 * math.pi * t / 4096)) for t in range(4096))
    assert all(M.COS[t] == int(4096 * math.cos(2 * math.pi * t / 4096)) for t in range(4096))
    assert (M.SIN[0], M.SIN[1024], M.SIN[3072], M.COS[0], M.COS[2048]) == (0, 4096, -4096, 4096, -4096)
    assert [M.cdiv(a, b) for a, b in ((7, 2), (-7, 2), (7, -2), (-7, -2), (0, 5))] == [3, -3, -3, 3, 0]


# ============================================================================ 5. the kit reproduces rung 0
def _rung0_pair(n: int) -> tuple:
    p = _rung0().predict(n)
    return (p["ax"], p["ay"], p["az"], p["ar"]), (p["bx"], p["by"], p["bz"], p["br"])


def test_pose_reproduces_rung0():
    """[floor division, phase units, the +192 tangent, the bob sign, operand order] For n in [0, 770] the kit's
    reduced model for A and B equals rung 0's in-game-proven, unreduced formula EXACTLY, facing mod 256 and the
    bob included."""
    A, B = M.parse(BENCH["A"], 0), M.parse(BENCH["B"], 1)
    for n in range(771):
        ra, rb = _rung0_pair(n)
        assert tuple(M.pose(A, n)) == ra, n
        assert tuple(M.pose(B, n)) == rb, n


def test_kit_diverges_from_rung0_unreduced_at_771():
    """Documented: n = 771 is where the two models first part. Rung 0's UNREDUCED B angle ``(2t + 128) << 4`` =
    26720 hits an ``rsin`` that differs from the reduced table's by one, and the divide no longer absorbs it. The
    kit is right by construction (THE REDUCTION LAW); rung 0 never ran that far unlatched."""
    A, B = M.parse(BENCH["A"], 0), M.parse(BENCH["B"], 1)
    ra, rb = _rung0_pair(771)
    assert tuple(M.pose(A, 771)) == ra                       # A still agrees
    kb = M.pose(B, 771)
    assert (kb.x, rb[0]) == (-44, -43)                       # B.x: kit -44, rung 0 -43
    assert (kb.b, kb.z, kb.face) == rb[1:]                   # everything else still agrees
    ang = (2 * 771 + 128) << 4
    assert (ang, _rung0().rsin(ang), M.SIN[ang & 4095]) == (26720, -600, -601)


# ============================================================================ 6 + 7. the daemon == pose
KINDS = {
    "orbit_forward": [_prop({"radius": 300, "period": 128, "height": 150})],
    "orbit_reverse": [_prop({"radius": 250, "period": 90, "reverse": True, "height": 80})],
    "orbit_phase": [_prop({"radius": 300, "period": 100, "phase": 0.3, "height": 40})],
    "orbit_reverse_phase_travel": [_prop({"radius": 200, "period": 60, "reverse": True, "phase": 0.7, "height": 10,
                                          "turn": "travel"})],
    "orbit_bob_rung0": [BENCH["A"], BENCH["B"]],
    "shuttle_even": [_prop({"to": [-300, -1000], "period": 150}, pos=[-1000, -1600], shadow=None)],
    "shuttle_odd": [BENCH["D"], _prop({"to": [0, -467], "period": 40}, prop="chest", shadow=None)],
    "shuttle_phase_bob": [_prop({"to": [500, -300], "period": 70, "phase": 0.4, "height": 60,
                                 "bob": {"amp": 25, "period": 35, "phase": 0.5}})],
    "bob_only": [_prop({"bob": {"amp": 60, "period": 256, "phase": 0.25}}),
                 _prop({"height": -120, "bob": {"amp": 30, "period": 50}}, prop="cask")],
    "spin_forward": [_prop({"turn": "spin", "period": 64}, prop="sword", collision=True, shadow=None)],
    "spin_reverse": [BENCH["E"]],
    "swing": [BENCH["F"], _prop({"turn": "swing", "swing": 127, "period": 4}, prop="fish", shadow=None)],
    "travel_face_offset": [BENCH["C"], _prop({"radius": 400, "period": 120, "turn": "travel"}, face=64)],
    "turn_only_ground": [_prop({"turn": "spin", "period": 50}, prop="sword", collision=True, shadow=True)],
    "turn_only_airborne": [_prop({"turn": "swing", "swing": 20, "period": 30, "height": 120}, prop="fish")],
    "shared_clock_3": [_prop({"radius": 200, "period": 64, "turn": "travel", "height": 30}),
                       _prop({"turn": "spin", "period": 64}, prop="sword", shadow=None),
                       _prop({"turn": "swing", "swing": 50, "period": 64, "phase": 0.5}, prop="fish", shadow=None)],
    "bench_7": [BENCH[k] for k in "ABCDEFG"],
}
TICK_CAP = 458                                  # past every kind's longest single period (256), so every clock wraps


def _kind(name: str) -> list:
    return [(M.parse(p, i), 2 + i) for i, p in enumerate(KINDS[name])]


@pytest.mark.parametrize("kind", list(KINDS))
def test_daemon_matches_pose(kind):
    """[a sin/cos swap, a missing prelude, advance-before-write, a B_REM off-by-one, a reverse sign, a dropped phase
    mask, the face constants, a uid mix-up] The EMITTED daemon, run in the EBin-rule engine for a full cycle (capped
    past every clock's wrap) plus 2, issues exactly ``pose(n)`` at tick n: every 0xAD / 0x87 operand, in order.
    The engine is strict, so every B_SIN2 / B_COS2 argument is also asserted in [0, 4095] (test 7)."""
    movers = _kind(kind)
    ks = M.clocks([s for s, _ in movers])
    n = min(math.lcm(*[s.cycle for s, _ in movers]), TICK_CAP) + 2
    assert n > max(ks), "the run must wrap every clock"
    ticks, eng = _run(movers, n)
    assert len(ticks) == n
    for t, tick in enumerate(ticks):
        assert _seen(tick) == _expect(movers, t), f"{kind} tick {t}"
    assert _clock_values(eng, len(ks)) == [n % p for p in ks]


def test_daemon_turn_only_at_height_0_never_moves():
    """A turn-only mover at height 0 issues 0x87 and never 0xAD (its Init's floor placement stands)."""
    ticks, _ = _run(_kind("turn_only_ground"), 60)
    assert {op for t in ticks for op, _u, _v in t} == {M.TURN_EX}
    ticks, _ = _run(_kind("turn_only_airborne"), 32)
    assert [op for op, _u, _v in ticks[0]] == [M.MOVE_EX, M.TURN_EX]
    assert all(t[0][2] == (0, -120, -800) for t in ticks)          # held at its height, never re-pathed


def test_trig_args_reduced(monkeypatch):
    """[a dropped ``& 4095``] test_daemon_matches_pose runs STRICT over every kind. This proves the strictness bites:
    each mask dropped from the emitter trips the engine's reduction assert."""
    orig_angle, orig_bob = M._angle_rpn, M._bob_rpn

    def unmasked(fn):
        return lambda spec, cref: fn(spec, cref).replace(" const(4095) B_AND", "")

    cases = [("_angle_rpn", orig_angle, [_prop({"radius": 300, "period": 100, "phase": 0.3, "height": 40})]),
             ("_angle_rpn", orig_angle, [_prop({"radius": 250, "period": 90, "reverse": True, "height": 80})]),
             ("_bob_rpn", orig_bob, [_prop({"bob": {"amp": 60, "period": 256, "phase": 0.25}})])]
    for attr, fn, props in cases:
        movers = [(M.parse(p, i), 2 + i) for i, p in enumerate(props)]
        _run(movers, 260)                                            # clean with the mask
        with monkeypatch.context() as mp:
            mp.setattr(M, attr, unmasked(fn))
            with pytest.raises(AssertionError, match="is not reduced to"):
                _run(movers, 260)


# ============================================================================ 8. the envelope at the max legal
def test_envelope_at_max_legal():
    """[a bigint interpreter that cannot fail; cap drift] Radius 8191, P 8192, amp 8191 and shuttle half 8191,
    through the engine's 26-bit wrap on EVERY operator for the whole period, equal ``pose``: nothing wraps. A doctored
    radius of 8192 (one past the cap) visibly does."""
    movers = [(_spec({"radius": 8191, "period": 8192, "turn": "travel"}, pos=[0, 0]), 2),
              (_spec({"bob": {"amp": 8191, "period": 8192}}, pos=[0, 0]), 3),
              (_spec({"to": [8191, 8191], "period": 8192}, pos=[-8191, -8191]), 4)]
    assert movers[2][0].half == (8191, 8191)
    assert M.clocks([s for s, _ in movers]) == [8192]
    ticks, eng = _run(movers, 8194)
    for t, tick in enumerate(ticks):
        assert _seen(tick) == _expect(movers, t), t
    assert _clock_values(eng, 1) == [8194 % 8192]
    # one past the cap: SIN[1024] * 8192 = 2^25 wraps to -2^25, so the far side lands on the near side
    bad = dataclasses.replace(_spec({"radius": 300, "period": 4}, pos=[0, 0]), radius=8192)
    assert M.SIN[M._angle(bad, 1)] == 4096 and M.pose(bad, 1).x == 8192
    ticks, _ = _run([(bad, 2)], 2)
    assert ticks[1][0][2][0] == -8192                                 # the engine: wrapped
    doctored_amp = dataclasses.replace(_spec({"bob": {"amp": 60, "period": 4}}, pos=[0, 0]), bob_amp=8192)
    ticks, _ = _run([(doctored_amp, 2)], 2)
    assert M.pose(doctored_amp, 1).b == -8192 and ticks[1][0][2][1] == 8192


# ============================================================================ 9. periods are exact
@pytest.mark.parametrize("P", [2, 75, 90, 128, 8192])
def test_period_exact(P):
    """[an unbounded clock] ``pose(n + cycle) == pose(n)`` exactly, for every channel, and the emitted daemon
    repeats with the same period."""
    specs = [_spec({"radius": 300, "period": P, "height": 20, "turn": "travel", "bob": {"amp": 40, "period": P}}),
             _spec({"to": [301, -500], "period": P, "phase": 0.3}, shadow=None),
             _spec({"turn": "spin", "period": P, "reverse": True}, shadow=None),
             _spec({"turn": "swing", "swing": 50, "period": P, "phase": 0.6}, shadow=None)]
    for s in specs:
        assert s.cycle == P
        for n in range(P):
            assert M.pose(s, n + P) == M.pose(s, n), (s, n)
    if P <= 128:
        movers = [(s, 2 + i) for i, s in enumerate(specs)]
        ticks, eng = _run(movers, 2 * P + 2)
        assert all(ticks[n] == ticks[n + P] for n in range(P + 2))
        assert _clock_values(eng, 1) == [(2 * P + 2) % P]


def test_mixed_periods_repeat_on_the_lcm():
    """A 90-tick orbit bobbing every 75 ticks repeats on lcm(90, 75) = 450, not 90."""
    s = _spec({"radius": 300, "period": 90, "height": 50, "bob": {"amp": 40, "period": 75}})
    assert s.cycle == 450
    assert all(M.pose(s, n + 450) == M.pose(s, n) for n in range(450))
    assert any(M.pose(s, n + 90) != M.pose(s, n) for n in range(90))


# ============================================================================ 10. the daemon's shape
def test_daemon_shape():
    """[always-emit, per-mover clocks, a wrong loc] Type 0, one tag-0 function at fpos 4. ``loc == 2K``. One prelude
    SET per clock at byte offsets 0, 2, ... The loop issues 0xAD only for position movers and 0x87 only for turners,
    at exactly the given uids, then advances every clock, Wait(1), JMP top, RETURN."""
    A, B, Dm, E = (M.parse(BENCH[k], i) for i, k in enumerate("ABDE"))
    movers = [(A, 7), (B, 8), (Dm, 9), (E, 10)]
    ks = M.clocks([A, B, Dm, E])
    assert ks == [128, 256, 150, 64]                         # A and B share 128; B's bob adds 256
    entry, loc = M.entry_bytes(movers)
    assert loc == 8 == 2 * len(ks)
    assert entry[:6] == bytes([0, 1]) + struct.pack("<HH", 0, 4)
    body = entry[6:]
    assert body == M.daemon_body(movers)
    ins = list(D.iter_code(body, 0, len(body)))
    K = len(ks)
    pre = [D.pretty_expr(body, i.off + 1)[0] for i in ins[:K]]
    assert [i.op for i in ins[:K]] == [0x05] * K
    assert pre == [f"{{Instance.Int16[{2 * k}] const(0) B_LET B_EXPR_END}}" for k in range(K)]
    loop = ins[K:]
    sig = [(i.op, body[i.off + 2]) for i in loop if i.op in (M.MOVE_EX, M.TURN_EX)]
    assert sig == [(0xAD, 7), (0x87, 7), (0xAD, 8), (0x87, 8), (0xAD, 9), (0x87, 10)]
    tail = loop[len(sig):]
    assert [i.op for i in tail] == [0x05] * K + [0x22, 0x01, 0x04]
    adv = [D.pretty_expr(body, i.off + 1)[0] for i in tail[:K]]
    assert adv == [f"{{Instance.Int16[{2 * k}] Instance.Int16[{2 * k}] const(1) B_PLUS const({p}) B_REM B_LET "
                   f"B_EXPR_END}}" for k, p in enumerate(ks)]
    wait, jmp = tail[K], tail[K + 1]
    assert wait.imm(0) == 1
    assert D.jump_target(jmp) == loop[0].off                 # JMP top: back past the prelude, never into it
    # A and B read the one shared clock; B's bob reads the second
    a_x = D.pretty_expr(body, loop[0].off + 3)[0]
    b_ops = [i for i in loop if i.op == M.MOVE_EX and body[i.off + 2] == 8][0]
    b_x, off = D.pretty_expr(body, b_ops.off + 3)
    b_b = D.pretty_expr(body, off)[0]
    assert "Instance.Int16[0]" in a_x and "Instance.Int16[0]" in b_x and "Instance.Int16[2]" in b_b
    assert M.audit_body(body, loc, {7, 8, 9, 10}) == []
    assert M.DAEMON_OPS == {0x05, 0xAD, 0x87, 0x22, 0x01, 0x04}


def test_daemon_shape_bench_and_one_clock():
    """The bench's 7 movers run on 6 clocks (loc 12, the spec's report). Three movers on one period share ONE
    clock (loc 2)."""
    specs = [s for s, _ in _bench_movers()]
    assert M.clocks(specs) == [128, 256, 90, 150, 64, 75]
    assert M.entry_bytes(_bench_movers())[1] == 12
    shared = _kind("shared_clock_3")
    assert M.clocks([s for s, _ in shared]) == [64] and M.entry_bytes(shared)[1] == 2


# ============================================================================ 11. the daemon's self-audit bites
def _good_body():
    A, B = M.parse(BENCH["A"], 0), M.parse(BENCH["B"], 1)
    return M.daemon_body([(A, 7), (B, 8)]), 4, {7, 8}


_DOCTORED = [
    # (id, a prepended doctored instruction, the audit fragment it must raise)
    ("global_mirror", _set("Global.Int16[1400] Instance.Int16[0] B_LET"), "token 'Global.Int16[1400]'"),
    ("map_mirror", _set("Map.Int16[10] Instance.Int16[0] B_LET"), "token 'Map.Int16[10]'"),
    ("obj_facing_read", _set("Instance.Int16[0] obj(uid=250).f[3] B_LET"), "token 'obj(uid=250).f[3]'"),
    ("sysvar_gate", _set("B_SYSVAR[2]"), "token 'B_SYSVAR[2]'"),
    ("byte_view", _set("Instance.Byte[0] const(0) B_LET"), "token 'Instance.Byte[0]'"),
    ("const4", _set("Instance.Int16[0] const4(70000) B_LET"), "token 'const4(70000)'"),
    ("index_past_loc", _set("Instance.Int16[4] const(0) B_LET"), "byte offsets [0, 2, 4], not exactly [0, 2]"),
    ("odd_offset", _set("Instance.Int16[1] const(0) B_LET"), "byte offsets [0, 1, 2], not exactly [0, 2]"),
    ("two_values", _set("const(1) const(2)"), "EXACTLY ONE value"),
    ("op_A1_move", opcodes.move_instant_xzy(0, -800, 0), "op 0xA1 at +0 is not a motion-daemon op"),
    ("op_37_self", opcodes.encode(0x37, 0, 0), "op 0x37 at +0 is not a motion-daemon op"),
    ("op_jmp_ifnot", bytes([0x02, 0x00, 0x00]), "op 0x02 at +0 is not a motion-daemon op"),
    ("foreign_uid_move", opcodes.encode(0xAD, 250, exprasm.assemble("const(0) B_EXPR_END"),
                                        exprasm.assemble("const(0) B_EXPR_END"),
                                        exprasm.assemble("const(0) B_EXPR_END"), arg_flags=0b1110),
     "0xAD at +0 targets uid 250, not a mover"),
    ("foreign_uid_turn", opcodes.encode(0x87, 9, exprasm.assemble("const(0) B_EXPR_END"), arg_flags=0b10),
     "0x87 at +0 targets uid 9, not a mover"),
]


@pytest.mark.parametrize("doctor, frag", [r[1:] for r in _DOCTORED], ids=[r[0] for r in _DOCTORED])
def test_daemon_audit_bites(doctor, frag, monkeypatch):
    """[the self-audit] Each doctored body fails ``audit_body``, and ``entry_bytes`` refuses to emit it. A prepend
    keeps every relative jump intact, so only the doctored op differs."""
    body, loc, uids = _good_body()
    assert M.audit_body(body, loc, uids) == []
    bad = M.audit_body(doctor + body, loc, uids)
    assert any(frag in b for b in bad), bad
    A, B = M.parse(BENCH["A"], 0), M.parse(BENCH["B"], 1)
    monkeypatch.setattr(M, "daemon_body", lambda movers: doctor + body)
    with pytest.raises(M.MotionError, match="failed its self-audit"):
        M.entry_bytes([(A, 7), (B, 8)])


def _shaped(order: str):
    """The daemon body for BENCH A+B, assembled from its real parts in ``order`` (labels keep every jump right)."""
    from ff9mapkit.eb.labelasm import JMP
    A, B = M.parse(BENCH["A"], 0), M.parse(BENCH["B"], 1)
    ks = M.clocks([A, B])
    clock_of = {p: k for k, p in enumerate(ks)}
    mv = [op for s, u in ((A, 7), (B, 8)) for op in M.mover_ops(s, u, clock_of)]
    parts = {
        "pre": [M._stmt(f"{M._clock_ref(k)} const(0) B_LET") for k in range(len(ks))],
        "top": [label("top")], "mv": mv, "mv-": mv[:-1], "mv1": mv[-1:],
        "adv": [M._stmt(f"{M._clock_ref(k)} {M._clock_ref(k)} const(1) B_PLUS const({p}) B_REM B_LET")
                for k, p in enumerate(ks)],
        "wait": [opcodes.wait(1)], "jmp": [(JMP, "top")], "ret": [opcodes.RETURN],
    }
    return asm([x for key in order.split() for x in parts[key]])


_LOOP_SHAPES = [
    # (id, order, the audit fragment) -- each was audit-CLEAN before the loop-shape law (review, refuted-but-real)
    ("wait_past_jmp", "pre top mv adv jmp wait ret", "must sit INSIDE the loop"),
    ("mover_past_jmp", "pre top mv- adv wait jmp mv1 ret", "must sit INSIDE the loop"),
    ("return_in_loop", "pre top mv adv wait ret jmp ret", "RETURN inside the loop"),
]


@pytest.mark.parametrize("order, frag", [r[1:] for r in _LOOP_SHAPES], ids=[r[0] for r in _LOOP_SHAPES])
def test_audit_refuses_a_broken_loop_shape(order, frag):
    """[the loop's shape] Nothing that must run every tick may sit past the JMP, and no RETURN may sit inside the
    loop -- either would stop the motion after tick 0 while the audit's other laws all pass."""
    good = _shaped("pre top mv adv wait jmp ret")
    A, B = M.parse(BENCH["A"], 0), M.parse(BENCH["B"], 1)
    assert good == M.daemon_body([(A, 7), (B, 8)])                 # the helper IS the emitter's shape
    assert M.audit_body(good, 4, {7, 8}) == []
    bad = M.audit_body(_shaped(order), 4, {7, 8})
    assert any(frag in b for b in bad), bad


def test_audit_catches_the_k_indexed_clock_emitter(monkeypatch):
    """[the platform-land regression: ``Instance.Int16[k]`` indexed by clock NUMBER] Clocks 0 and 1 then share byte
    1. The audit refuses it, and the engine shows why: the aliased clocks corrupt each other from tick 1."""
    movers = _kind("orbit_bob_rung0")
    monkeypatch.setattr(M, "_clock_ref", lambda k: f"Instance.Int16[{k}]")
    with pytest.raises(M.MotionError, match=r"byte offsets \[0, 1\], not exactly \[0, 2\]"):
        M.entry_bytes(movers)
    body = M.daemon_body(movers)

    def moves(ops):
        return [o for o in ops if o[0] == M.MOVE_EX]

    ticks = MotionEngine(4, strict_reduced=False).ticks(body, 3)
    assert _seen(ticks[0]) == _expect(movers, 0)                  # tick 0 is right (both clocks read 0) ...
    assert moves(ticks[2]) != moves(_expect(movers, 2))           # ... then clock 0's store eats clock 1's byte
    with pytest.raises(AssertionError, match="is not reduced to"):
        MotionEngine(4).ticks(body, 3)                            # clock 0 reads 257: its angle leaves [0, 4095]


def test_audit_refuses_a_write_outside_the_clock_sets():
    """[only the clock SETs write] A B_LET inside a 0xAD operand, a stray clock SET that is neither a prelude nor an
    advance, and a second advance of one clock are each refused."""
    body, loc, uids = _good_body()
    let_in_move = opcodes.encode(0xAD, 7, exprasm.assemble("Instance.Int16[0] const(5) B_LET B_EXPR_END"),
                                 exprasm.assemble("const(0) B_EXPR_END"), exprasm.assemble("const(0) B_EXPR_END"),
                                 arg_flags=0b1110)
    assert any("writes inside an operand" in b for b in M.audit_body(let_in_move + body, loc, uids))
    stray = M._stmt("Instance.Int16[0] const(7) B_LET")
    assert any("neither a clock prelude nor a clock advance" in b for b in M.audit_body(stray + body, loc, uids))
    again = M._stmt("Instance.Int16[0] Instance.Int16[0] const(1) B_PLUS const(128) B_REM B_LET")
    assert any("exactly one prelude and one advance" in b for b in M.audit_body(again + body, loc, uids))


# ============================================================================ 12. THE ORDER LAW
_ORDER_OK = [
    ("straight", (IO1, IO2, IC3)),
    ("fillers_after", (IO1, IO2, IC3, opcodes.wait(2), opcodes.wait(2))),
    ("branch_after_arming", (IO1, IO2, IC3, COND, (JMP_IFNOT, "x"), opcodes.wait(1), label("x"))),
    ("branch_rejoins_before_movers", (COND, (JMP_IFNOT, "x"), opcodes.wait(1), label("x"), IO1, IO2, IC3)),
]


@pytest.mark.parametrize("items", [r[1] for r in _ORDER_OK], ids=[r[0] for r in _ORDER_OK])
def test_order_law_accepts(items):
    assert M.arming_problems(_order_eb(*items), 3, [1, 2]) == []


_ORDER_BAD = [
    # (id, Main_Init, extra entries, fragments the problems must carry, fragments they must NOT carry)
    ("a_prepended", (IC3, IO1, IO2), (), ["before mover slot 1's", "before mover slot 2's"], []),
    ("a_between", (IO1, IC3, IO2), (), ["before mover slot 2's"], ["slot 1's"]),
    ("b_guarded_mover", (IO1, COND, (JMP_IFNOT, "x"), IO2, label("x"), IC3), (), ["before mover slot 2's"],
     ["slot 1's"]),
    ("c_jump_lands_before_initcode", (COND, (JMP_IFNOT, "x"), IO1, IO2, label("x"), IC3), (),
     ["before mover slot 1's", "before mover slot 2's"], []),
    ("d_skippable_initcode", (IO1, IO2, COND, (JMP_IFNOT, "x"), IC3, label("x")), (),
     ["does not run on every path"], ["before mover"]),
    ("e_duplicated_mover", (IO1, IO2, IO2, IC3), (), ["mover slot 2 must be created by exactly one InitObject"],
     ["slot 1 must"]),
    ("e_missing_mover", (IO1, IC3), (), ["mover slot 2 must be created by exactly one InitObject in Main_Init, "
                                         "found []"], []),
    ("e_mover_created_elsewhere", (IO1, IC3), (pack_entry(0, [(0, IO2 + opcodes.RETURN)]),),
     ["mover slot 2 must be created by exactly one InitObject in Main_Init, found [(4, 0,"], []),
    ("initcode_twice", (IO1, IO2, IC3, IC3), (), ["must be armed by exactly one InitCode in Main_Init"], []),
    ("initcode_elsewhere", (IO1, IO2), (pack_entry(0, [(0, IC3 + opcodes.RETURN)]),),
     ["must be armed by exactly one InitCode in Main_Init, found [(4, 0,"], []),
    ("initcode_missing", (IO1, IO2), (), ["must be armed by exactly one InitCode in Main_Init, found []"], []),
]


@pytest.mark.parametrize("items, extra, want, never", [r[1:] for r in _ORDER_BAD], ids=[r[0] for r in _ORDER_BAD])
def test_order_law_refuses(items, extra, want, never):
    """[each clause of THE ORDER LAW] Dominance on the final bytes, not offset order: each row names exactly the
    mover (or the path) it breaks."""
    probs = M.arming_problems(_order_eb(*items, extra=extra), 3, [1, 2])
    text = " | ".join(probs)
    for w in want:
        assert w in text, probs
    for n in never:
        assert n not in text, probs


def test_order_law_refuses_an_unanalysable_main_init():
    """A CfgError is a refusal, never a pass: a jump into the middle of the InitCode."""
    mid_jump = bytes([0x01]) + struct.pack("<h", 1)
    eb = _eb(pack_entry(0, [(0, IO1 + IO2 + mid_jump + IC3 + opcodes.RETURN)]), _obj(_init(226)), _obj(_init(241)),
             FILLER)
    probs = M.arming_problems(eb, 3, [1, 2])
    assert len(probs) == 1 and "could not be analysed" in probs[0]


_INIT_BAD = [
    # (id, mover Init body, fragment)
    ("f_wait_before_create", _init(226, between=opcodes.wait(1)), "runs op 0x22"),
    ("g_jmp", _init(226, between=bytes([0x01, 0x00, 0x00])), "runs op 0x01"),
    ("g_jmp_ifnot", _init(226, before=COND + bytes([0x02, 0x00, 0x00])), "runs op 0x02"),
    ("nop_yield", _init(226, after=bytes([0x00])), "runs op 0x00"),
    ("h_no_create", opcodes.set_model(226, 0) + opcodes.encode(0x47, 0) + opcodes.RETURN,
     "exactly one SetModel before exactly one CreateObject"),
    ("h_create_first", opcodes.create_object(0, 0) + opcodes.set_model(226, 0) + opcodes.RETURN,
     "exactly one SetModel before exactly one CreateObject"),
    ("h_two_setmodels", _init(226, before=opcodes.set_model(226, 0)),
     "exactly one SetModel before exactly one CreateObject"),
    ("no_return", _init(226, ret=False), "does not end in RETURN"),
]


@pytest.mark.parametrize("body, frag", [r[1:] for r in _INIT_BAD], ids=[r[0] for r in _INIT_BAD])
def test_mover_init_law_refuses(body, frag):
    """[THE STRAIGHT-LINE INIT LAW] An allowlist, not a yield denylist: any op outside MOVER_INIT_OPS, a missing
    or misordered SetModel / CreateObject, or no closing RETURN is refused."""
    eb = _order_eb(IO1, IO2, IC3, m1=body)
    assert M.init_problems(_order_eb(IO1, IO2, IC3), 1, 226) == []
    probs = M.init_problems(eb, 1, 226)
    assert any(frag in p for p in probs), probs


def test_mover_init_slot_map_law():
    """[THE SLOT-MAP LAW] The recorded slot's SetModel must be the recorded model, so the daemon never moves the
    wrong object. A missing slot or an empty one is refused too."""
    eb = _order_eb(IO1, IO2, IC3)
    assert M.init_problems(eb, 2, 241) == []
    probs = M.init_problems(eb, 1, 241)
    assert len(probs) == 1 and "SetModel is model 226, not the mover's 241" in probs[0] and "SLOT-MAP" in probs[0]
    assert M.init_problems(eb, 9, 226) == ["slot 9 does not exist"]
    assert M.init_problems(_eb(_main(IO1), None), 1, 226) == ["slot 1 has no Init"]
    assert MOVER_YIELDS.isdisjoint(M.MOVER_INIT_OPS)


# ------------------------------------------------------------------ arm(): the law applied, then re-proved
def _arm_base(main=(IO1, IO2, opcodes.wait(2))) -> bytes:
    return _eb(_main(*main), _obj(_init(226)), _obj(_init(241)))


def test_arm_seats_and_arms_after_the_last_mover():
    """``arm`` seats the self-audited daemon with loc = 2K, arms it right after the byte-last mover InitObject, and
    the result passes THE ORDER LAW. Its report IS ``report_lines``."""
    pa, pb = BENCH["A"], BENCH["B"]
    out, slot, lines = M.arm(_arm_base(), {"prop": [pa, pb]}, [(pa, 226, 1), (pb, 241, 2)])
    A, B = M.parse(pa, 0), M.parse(pb, 1)
    entry, loc = M.entry_bytes([(A, 1), (B, 2)])
    e = EbScript.from_bytes(out).entry(slot)
    assert slot == 3 and out[e.abs_start:e.abs_end] == entry and e.loc == loc == 4
    assert _main_ops(out) == [(0x09, 1), (0x09, 2), (0x07, 3), (0x22, None), (0x04, None)]
    assert M.arming_problems(out, slot, [1, 2]) == []
    assert lines == M.report_lines([(A, 1), (B, 2)], slot, loc)


def test_order_law_kills_the_activate_block_mutants():
    """[the activate_block arming path] ``activate_block`` PREPENDS, so the daemon would be created (and tick)
    before every mover. ``after_player`` is no better: the player's InitObject precedes the movers'."""
    pa, pb = BENCH["A"], BENCH["B"]
    A, B = M.parse(pa, 0), M.parse(pb, 1)
    entry, loc = M.entry_bytes([(A, 1), (B, 2)])
    seated, dslot = _object.seat_entry(_arm_base(), entry, loc=loc)
    mutant = eb_edit.activate_block(seated, opcodes.init_code(dslot, 0))
    probs = M.arming_problems(mutant, dslot, [1, 2])
    assert len(probs) == 2 and all("armed before mover slot" in p for p in probs)
    # after_player: a player entry (DefinePlayerCharacter in its Init) created FIRST, as the kit template does
    player = _obj(opcodes.encode(0x2C) + opcodes.RETURN)
    base = _eb(_main(opcodes.init_object(1, 0), opcodes.init_object(2, 0), opcodes.init_object(3, 0)), player,
               _obj(_init(226)), _obj(_init(241)))
    seated, dslot = _object.seat_entry(base, entry, loc=loc)
    mutant = eb_edit.activate_block(seated, opcodes.init_code(dslot, 0), after_player=True)
    assert _main_ops(mutant)[:2] == [(0x09, 1), (0x07, dslot)]
    probs = M.arming_problems(mutant, dslot, [2, 3])
    assert len(probs) == 2 and all("armed before mover slot" in p for p in probs)


def test_arm_reproves_the_law_on_its_own_insert():
    """[``arm`` trusting its insert] A mover created under a guard: arm's insert point (right after the byte-last
    InitObject) is the guard's jump TARGET, and ``insert_in_function`` keeps that jump aimed at the inserted
    InitCode rather than raising. The InitCode then sits AFTER every InitObject in offset order, yet the guarded
    path skips mover 2's. Only the dominance proof on the result sees it, and arm refuses."""
    pa, pb = BENCH["A"], BENCH["B"]
    eb = _arm_base(main=(IO1, COND, (JMP_IFNOT, "x"), IO2, label("x")))
    with pytest.raises(M.MotionError, match="armed before mover slot 2's InitObject on some path") as ei:
        M.arm(eb, {"prop": [pa, pb]}, [(pa, 226, 1), (pb, 241, 2)])
    assert "slot 1's" not in str(ei.value)


def test_arm_runs_the_init_laws():
    """[``arm`` skipping init_problems] A yielding mover Init and a slot-map mismatch are refused at arm, naming the
    prop."""
    pa, pb = BENCH["A"], BENCH["B"]
    eb = _eb(_main(IO1, IO2), _obj(_init(226, between=opcodes.wait(1))), _obj(_init(241)))
    with pytest.raises(M.MotionError, match=r"\[\[prop\]\] 'balloon' motion: .*runs op 0x22"):
        M.arm(eb, {"prop": [pa, pb]}, [(pa, 226, 1), (pb, 241, 2)])
    with pytest.raises(M.MotionError, match=r"\[\[prop\]\] 'cask' motion: .*SLOT-MAP"):
        M.arm(_arm_base(), {"prop": [pa, pb]}, [(pa, 226, 1), (pb, 999, 2)])


def test_arm_needs_exactly_one_seat_per_mover():
    """[THE NULL-TARGET LAW at arm] Each motion prop is seated exactly once: a composite's second part or a lost
    record is refused. Seats match the toml table by IDENTITY, not equality."""
    pa, pb = BENCH["A"], BENCH["B"]
    with pytest.raises(M.MotionError, match="'cask' motion: expected exactly one seated part, found 2"):
        M.arm(_arm_base(), {"prop": [pa, pb]}, [(pa, 226, 1), (pb, 241, 2), (pb, 241, 2)])
    with pytest.raises(M.MotionError, match="'cask' motion: expected exactly one seated part, found 0"):
        M.arm(_arm_base(), {"prop": [pa, pb]}, [(pa, 226, 1), (dict(pb), 241, 2)])


# ============================================================================ 13. the mover Init ops cover every emitter
def _blank() -> bytes:
    """A synthetic blank field: Main_Init = two Wait(2) fillers + RETURN, two empty slots."""
    return _eb(pack_entry(0, [(0, opcodes.wait(2) * 2 + opcodes.RETURN)]), None, None)


_EMITTERS = [
    ("plain", {}, set()),
    ("face", {"face": 64}, {0x36}),
    ("face_wraps", {"face": 300}, {0x36}),
    ("collision_false", {"collision": False}, {0x93}),
    ("shadow_true", {"shadow": True}, {0x81, 0x85}),
    ("shadow_false", {"shadow": False}, set()),
    ("shadow_table", {"shadow": {"size": 12, "intensity": 6}}, {0x81, 0x85}),
    ("mcf_shadow_false", {"mcf": True, "shadow": False}, {0x80}),
    ("mcf_shadow_true", {"mcf": True, "shadow": True}, set()),
    ("mcf_shadow_table", {"mcf": True, "shadow": {"size": 12}}, set()),
    ("everything", {"face": 32, "collision": False, "shadow": {"size": 9, "intensity": 4}}, {0x36, 0x93, 0x81, 0x85}),
]


@pytest.mark.parametrize("kw, must", [r[1:] for r in _EMITTERS], ids=[r[0] for r in _EMITTERS])
def test_mover_init_ops_cover_emitters(kw, must):
    """[a new emitter op slipping past the yield review] Every ``inject_prop`` variant's Init is a subset of
    MOVER_INIT_OPS and passes init_problems. Each variant really hits its emitter path (``must``)."""
    out = _prop_mod.inject_prop(_blank(), 0, -800, model=226, pose=3349, slot=1, **kw)
    f0 = EbScript.from_bytes(out).entry(1).func_by_tag(0)
    ops = [i.op for i in D.iter_code(out, f0.abs_start, f0.abs_end)]
    assert set(ops) <= M.MOVER_INIT_OPS, sorted(set(ops) - M.MOVER_INIT_OPS)
    assert must <= set(ops[ops.index(0x1D) + 2:])                     # the tail, after CreateObject + its TurnInstant
    assert M.init_problems(out, 1, 226) == []


# ============================================================================ 14. no mover or daemon on an alias uid
@pytest.mark.parametrize("slot", [0, 250, 251, 255])
def test_uid_alias_refused_for_a_mover(slot):
    """[a daemon that could move the player] 250-255 alias the player, the party and self (GetObjUID); 0 is Main."""
    pa = BENCH["A"]
    with pytest.raises(M.MotionError, match=f"slot {slot} is outside 1..249"):
        M.arm(_arm_base(), {"prop": [pa]}, [(pa, 226, slot)])


def test_uid_alias_refused_for_the_daemon():
    """A field whose 250 slots are all taken would seat the daemon at 250, the player alias: refused."""
    pa = BENCH["A"]
    eb = _eb(_main(IO1), _obj(_init(226)), *[FILLER] * 248)
    assert EbScript.from_bytes(eb).first_free_slot() == 250
    with pytest.raises(M.MotionError, match="the daemon landed at slot 250, outside 1..249"):
        M.arm(eb, {"prop": [pa]}, [(pa, 226, 1)])
    ok, slot, _lines = M.arm(_eb(_main(IO1), _obj(_init(226)), *[FILLER] * 247), {"prop": [pa]}, [(pa, 226, 1)])
    assert slot == 249 and M.arming_problems(ok, 249, [1]) == []


# ------------------------------------------------------------------ THE 64-STRIDE LAW
CLIMBER = pack_entry(2, [(0, opcodes.RETURN), (5, opcodes.run_shared_script(7) + opcodes.RETURN)])


def test_stride_problems_on_a_startseq_entry():
    """[THE 64-STRIDE LAW] A STARTSEQ (0x43) from entry S-64, in ANY of its functions (a faithful ladder climb
    lives in a player function, not its Init), makes slot S unsafe. The neighbours are not."""
    eb = _eb(_main(IO1), CLIMBER, _obj(_init(226)))
    (p,) = M._stride_problems(eb, 65, "mover")
    assert "mover at slot 65 sits 64 above entry 1" in p and "64-STRIDE" in p
    assert M._stride_problems(eb, 66, "mover") == []              # entry 2 runs no STARTSEQ
    assert M._stride_problems(eb, 64, "mover") == []              # entry 0 neither
    assert M._stride_problems(eb, 63, "mover") == []              # below the stride
    assert M._stride_problems(_eb(_main(IO1), _obj(opcodes.RETURN), FILLER), 65, "mover") == []


def test_stride_law_refuses_at_arm():
    """[``arm`` skipping the stride check] A mover at 65 and a daemon landing at 65 over a climbing entry 1 are
    both refused."""
    pa = BENCH["A"]
    eb = _eb(_main(opcodes.init_object(65, 0)), CLIMBER, *[FILLER] * 63, _obj(_init(226)))
    with pytest.raises(M.MotionError, match="'balloon' motion: the mover at slot 65 sits 64 above entry 1"):
        M.arm(eb, {"prop": [pa]}, [(pa, 226, 65)])
    eb = _eb(_main(opcodes.init_object(2, 0)), CLIMBER, _obj(_init(226)), *[FILLER] * 62)
    assert EbScript.from_bytes(eb).first_free_slot() == 65
    with pytest.raises(M.MotionError, match="the motion daemon at slot 65 sits 64 above entry 1"):
        M.arm(eb, {"prop": [pa]}, [(pa, 226, 2)])


# ============================================================================ 15. the scope rules (problems)
_MOVER = {"radius": 300, "period": 128, "height": 150, "turn": "travel"}
_SPIN = {"turn": "spin", "period": 64}


def _spins(n: int, periods) -> list:
    return [_prop({"turn": "spin", "period": periods[i % len(periods)]}, prop="sword", collision=None, shadow=None)
            for i in range(n)]


_SCOPE_BAD = [
    ("verbatim_eb", {"verbatim_eb": {"donor": 100}, "prop": [_prop(_MOVER)]}, "this field has [verbatim_eb]"),
    ("verbatim_eb_no_donor", {"verbatim_eb": {}, "prop": [_prop(_MOVER)]}, "this field has [verbatim_eb]"),
    ("source_field", {"field": {"id": 4100, "source_field": 100}, "prop": [_prop(_MOVER)]},
     "this field has a donor (field 100)"),
    ("borrow_field", {"field": {"id": 4100, "borrow_field": "250"}, "prop": [_prop(_MOVER)]},
     "this field has a donor (field 250)"),
    ("requires_flag", {"prop": [_prop(_MOVER, requires_flag=9000)]}, "may not use requires_flag"),
    ("requires_flag_clear", {"prop": [_prop(_MOVER, requires_flag_clear=9000)]}, "may not use requires_flag_clear"),
    ("attach_to", {"prop": [_prop(_MOVER, attach_to="vivi")]}, "may not use attach_to"),
    ("composite", {"prop": [_prop(_SPIN, prop="save_point", collision=None, shadow=None)]}, "composite archetype"),
    ("collision_absent", {"prop": [_prop({"to": [300, -800], "period": 100}, collision=None, shadow=None)]},
     "must be walk-through -- set collision = false"),
    ("collision_true", {"prop": [_prop({"to": [300, -800], "period": 100}, collision=True, shadow=None)]},
     "must be walk-through -- set collision = false"),
    ("collision_on_raised_spinner", {"prop": [_prop({"turn": "spin", "period": 64, "height": 50}, collision=True)]},
     "must be walk-through -- set collision = false"),
    ("shadow_absent", {"prop": [_prop(_MOVER, shadow=None)]}, "must set shadow = false"),
    ("shadow_true", {"prop": [_prop(_MOVER, shadow=True)]}, "must set shadow = false"),
    ("shadow_table_on_bob", {"prop": [_prop({"bob": {"amp": 60, "period": 90}}, shadow={"size": 9})]},
     "must set shadow = false"),
    ("17_movers", {"prop": _spins(17, [64])}, "at most 16 moving props per field"),
    ("9_clocks", {"prop": _spins(9, list(range(2, 11)))}, "at most 8 distinct periods per field"),
    ("bob_period_counts", {"prop": _spins(7, list(range(2, 9))) + [_prop({"turn": "spin", "period": 9,
                                                                            "bob": {"amp": 5, "period": 10}})]},
     "at most 8 distinct periods per field"),
    ("npc_motion", {"npc": [{"name": "vivi", "pos": [0, 0], "motion": _MOVER}]}, "motion is a [[prop]] key"),
    ("airborne_on_mapconfig", {"field": {"mapconfig": "mcf.bin"}, "prop": [_prop(_MOVER)]},
     "are airborne on a field that ships MapConfigData"),
    ("bob_on_mapconfig", {"field": {"mapconfig": "mcf.bin"}, "prop": [_prop({"bob": {"amp": 9, "period": 40}})]},
     "are airborne on a field that ships MapConfigData"),
]


@pytest.mark.parametrize("raw, frag", [r[1:] for r in _SCOPE_BAD], ids=[r[0] for r in _SCOPE_BAD])
def test_problems_scope_refused(raw, frag):
    """[each clause of the scope and co-rules] ``problems`` (what validate, lint and build report) carries the
    refusal. ``donor`` comes from build.donor_field_id, exactly as validate passes it."""
    probs = M.problems(raw, donor=build.donor_field_id(raw))
    assert sum(frag in p for p in probs) == 1, probs


_SCOPE_OK = [
    ("solid_turn_only", {"prop": [_prop(_SPIN, prop="sword", collision=True, shadow=None)]}),
    ("shadow_on_ground_mover", {"prop": [_prop({"to": [300, -800], "period": 100}, shadow=True)]}),
    ("default_shadow_ground_mover", {"prop": [BENCH["D"]]}),
    ("borrow_bg_only", {"field": {"id": 4100, "borrow_bg": 100}, "prop": [_prop(_MOVER)]}),
    ("ground_mover_on_mapconfig", {"field": {"mapconfig": "mcf.bin"},
                                   "prop": [_prop({"to": [300, -800], "period": 100}, shadow=None)]}),
    ("16_movers_8_clocks", {"prop": _spins(16, list(range(2, 10)))}),
    ("the_bench", {"prop": list(BENCH.values()) + [_prop(None, prop="scroll", pos=[-750, -1300], face=64)]}),
    ("static_props_on_a_fork", {"verbatim_eb": {"donor": 100}, "prop": [_prop(None), _prop(None, prop="cask")]}),
    ("npc_without_motion", {"npc": [{"name": "vivi", "pos": [0, 0]}], "prop": [_prop(_MOVER)]}),
]


@pytest.mark.parametrize("raw", [r[1] for r in _SCOPE_OK], ids=[r[0] for r in _SCOPE_OK])
def test_problems_scope_accepted(raw):
    """[an over-broad clause] A solid turn-only mover at height 0, a casting ground mover, a borrow_bg-only novel
    field, a ground mover on an MCF field, the caps exactly, the whole bench, and a fork with only STATIC props (no
    motion anywhere, so the novel-field law does not apply) are all clean."""
    assert M.problems(raw, donor=build.donor_field_id(raw)) == []


# ============================================================================ 16. the report IS the predictor
_TICKS_RE = re.compile(r"\((-?\d+),(-?\d+),(-?\d+),(-|\d+)\)")
# a constant range prints as one value ("h 150"), a varying one as lo..hi
_RANGE_RE = re.compile(r"x (-?\d+)(?:\.\.(-?\d+))? z (-?\d+)(?:\.\.(-?\d+))? h (-?\d+)(?:\.\.(-?\d+))?; "
                       r"max ([\d.]+) u, (\d+) bytes/tick")


def _parsed(line: str) -> tuple:
    m = _RANGE_RE.search(line)
    assert m, line
    g = m.groups()
    ranges = tuple(v for i in (0, 2, 4) for v in (int(g[i]), int(g[i + 1] if g[i + 1] is not None else g[i])))
    ticks = [(int(x), int(h), int(z), None if f == "-" else int(f))
             for x, h, z, f in _TICKS_RE.findall(line.split("ticks 0-3 (x,h,z,face):")[1])]
    return ranges, float(m.group(7)), int(m.group(8)), ticks


def test_report_lines():
    """[report drift from the predictor] The summary names every clock and the daemon. Each mover's line carries its
    period in ticks and seconds, ticks 0-3 == ``pose(0..3)``, bounds == min/max over ``path()``, the max step, the
    shuttle's far end, and SNAPS on (only) the over-fast G. Spot-pinned to the spec's printed numbers."""
    movers = _bench_movers()
    lines = M.report_lines(movers, 9, 12)
    assert len(lines) == 1 + len(movers)
    head = lines[0]
    assert head.startswith("[[prop]] motion: 7 mover(s) on 6 clock(s) (128, 256, 90, 150, 64, 75 ticks; "
                           "30 ticks = 1 s")
    assert "daemon entry 9 (loc 12 B)" in head and "THE ORDER LAW" in head
    for (s, uid), line in zip(movers, lines[1:]):
        assert line.startswith(f"{s.label} motion uid {uid}: ")
        assert f"period {s.period} ({s.period / 30:.2f} s)" in line
        if s.bob_amp:
            assert f"bob +-{s.bob_amp} every {s.bob_period} ({s.bob_period / 30:.2f} s)" in line
        ranges, step, fb, ticks = _parsed(line)
        assert ticks == [(p.x, p.height, p.z, p.face) for p in M.path(s, 0, 4)]
        full = M.path(s)                                     # one full cycle (all small on the bench)
        assert ranges == (min(p.x for p in full), max(p.x for p in full), min(p.z for p in full),
                          max(p.z for p in full), min(p.height for p in full), max(p.height for p in full))
        ms = M.max_step(s)
        assert (step, fb) == (round(ms[0], 1), ms[1])
        # the step is the real joint one on a small cycle (every bench mover); past the cap it is an upper bound
        seq = M.path(s, 0, s.cycle + 1)
        joint = max(math.dist((a.x, a.b, a.z), (b.x, b.b, b.z)) for a, b in zip(seq, seq[1:]))
        assert M.step_is_exact(s) and abs(joint - ms[0]) < 1e-9
        assert ("SNAPS" in line) == (s.label == "[[prop]] 'hand_bell'")
    by = {s.label: line for (s, _u), line in zip(movers, lines[1:])}
    # the spec's section 5 numbers, verbatim
    assert "x -300..300 z -1100..-500 h 150; max 15.3 u, 2 bytes/tick; ticks 0-3 (x,h,z,face): " \
           "(0,150,-500,192) (14,150,-501,194) (29,150,-502,196) (44,150,-504,198)" in by["[[prop]] 'balloon'"]
    assert by["[[prop]] 'cask'"].endswith("(0,150,-1100,64) (-14,151,-1099,66) (-29,152,-1098,68) (-44,154,-1096,70)")
    assert "orbit r 250 reverse about (-750, -450)" in by["[[prop]] 'letter'"]
    assert "turn travel +32" in by["[[prop]] 'letter'"]
    assert by["[[prop]] 'letter'"].endswith("(-750,80,-200,96) (-767,80,-201,93) (-784,80,-203,90) (-801,80,-206,87)")
    assert "shuttle (-1000, -1600) -> (-302, -1600)" in by["[[prop]] 'chest'"]
    assert by["[[prop]] 'chest'"].endswith("(-997,0,-1600,-)")                # no turn: no facing written
    assert "(750,0,-1350,168)" in by["[[prop]] 'fish'"]                        # phase .25: face + swing at tick 0
    assert "turn swing +-40 about face 128" in by["[[prop]] 'fish'"]            # said once, centred on face
    assert "cycle 256 (8.53 s)" in by["[[prop]] 'cask'"]                       # two periods: the joint cycle
    # without a daemon (the CLI's pure report): no slot, no uid
    bare = M.report_lines([(s, None) for s, _ in movers])
    assert "daemon entry" not in bare[0] and " uid " not in bare[1]


# the smoother's thresholds (400 u, 32 bytes a tick), both sides of each, and the circular facing wrap
_SNAP = [
    ("shuttle_400", _prop({"to": [400, 0], "period": 2}, pos=[0, 0], shadow=None), (400.0, 0), True),
    ("shuttle_diag_400", _prop({"to": [240, 320], "period": 2}, pos=[0, 0], shadow=None), (400.0, 0), True),
    ("shuttle_399", _prop({"to": [398, 30], "period": 2}, pos=[0, 0], shadow=None), (399.13, 0), False),
    ("shuttle_398", _prop({"to": [398, 0], "period": 2}, pos=[0, 0], shadow=None), (398.0, 0), False),
    ("bob_400", _prop({"bob": {"amp": 400, "period": 4}}), (400.0, 0), True),
    ("bob_399", _prop({"bob": {"amp": 399, "period": 4}}), (399.0, 0), False),
    ("swing_32_bytes", _prop({"turn": "swing", "swing": 19, "period": 3}, shadow=None), (0.0, 32), True),
    ("swing_31_bytes", _prop({"turn": "swing", "swing": 31, "period": 4}, shadow=None), (0.0, 31), False),
    ("spin_32_bytes", _prop({"turn": "spin", "period": 8}, shadow=None), (0.0, 32), True),
    ("spin_29_bytes", _prop({"turn": "spin", "period": 9}, shadow=None), (0.0, 29), False),
    ("travel_P128_wraps_255_to_0", _prop({"radius": 300, "period": 128, "turn": "travel"}), (15.3, 2), False),
    ("spin_P64_wraps_255_to_0", _prop({"turn": "spin", "period": 64}, shadow=None), (0.0, 4), False),
    ("spin_reverse_P64", _prop({"turn": "spin", "period": 64, "reverse": True}, shadow=None), (0.0, 4), False),
    ("hand_bell", BENCH["G"], (804.7, 0), True),
]


@pytest.mark.parametrize("p, step, snaps", [r[1:] for r in _SNAP], ids=[r[0] for r in _SNAP])
def test_report_snaps_exactly_at_the_thresholds(p, step, snaps):
    """[a threshold off by one or a strict comparison; a raw facing difference] SNAPS at >= 400 u or >= 32 bytes a
    tick, never below. The facing step is CIRCULAR: an orbiter's travel facing crosses 255 -> 0 every lap and a
    spinner's too, and neither is a 255-byte snap."""
    s = M.parse(p, 0)
    u, b = M.max_step(s)
    assert u == pytest.approx(step[0], abs=0.05) and b == step[1]
    line = M.describe(s, 5)
    assert ("SNAPS" in line) == snaps
    notes = M.lint_notes({"prop": [p]})                      # test 17: the lint advisory, the same threshold
    assert len(notes) == int(snaps)
    if snaps:
        assert notes[0].startswith(f"{s.label} motion moves ") and "SNAP" in notes[0]
    if s.turns and not snaps:                               # the wrap is really crossed, and a raw diff would flag it
        faces = [q.face for q in M.path(s)] + [M.pose(s, s.cycle).face]
        assert max(abs(x - y) for x, y in zip(faces, faces[1:])) >= 200


def test_lint_notes_skip_broken_and_still_props():
    """The advisory never duplicates an error (``problems`` reports a broken motion) and ignores props without
    motion."""
    raw = {"prop": [_prop({"radius": 0, "period": 2}), _prop(None), BENCH["A"], BENCH["G"]]}
    notes = M.lint_notes(raw)
    assert len(notes) == 1 and notes[0].startswith("[[prop]] 'hand_bell' motion moves 805 u")


# ------------------------------------------------------------------ the swing is centred on face
def test_swing_is_centred_on_face():
    """[the swing constant face + 128: centred 180 degrees away] At th = 0 a swing faces exactly ``face``. Over a
    period its signed (circular) offsets from ``face`` span exactly +-swing and are symmetric (P = 64 divides 4096,
    so the angles pair up exactly). ``face = 0`` crosses the 255 -> 0 wrap. The bench fish (phase 0.25) starts at
    ``face + swing``."""
    for face in (128, 0, 250):
        s = _spec({"turn": "swing", "swing": 40, "period": 64}, face=face, shadow=None)
        off = [((M.pose(s, n).face - face + 128) % 256) - 128 for n in range(64)]
        assert off[0] == 0 and M.pose(s, 0).face == face
        assert (max(off), min(off), sum(off)) == (40, -40, 0)
        assert sorted(off) == sorted(-o for o in off)
    s = _spec({"turn": "swing", "swing": 40, "period": 75}, face=128, shadow=None)
    off = [M.pose(s, n).face - 128 for n in range(75)]
    assert max(off) == -min(off) == 39                       # 75 does not divide 4096: +-39, still centred
    assert M.pose(M.parse(BENCH["F"], 0), 0).face == 168


# ------------------------------------------------------------------ coprime periods stay cheap
def test_coprime_periods_report_fast():
    """[bounds / max_step walking the lcm] Two legal coprime periods have a ~67-million-tick cycle. The report, the
    bounds, the max step and the lint are per channel over each channel's own period, so they stay fast."""
    p = _prop({"radius": 300, "period": 8191, "height": 150, "turn": "travel", "bob": {"amp": 60, "period": 8192}})
    s = M.parse(p, 0)
    assert s.cycle == 8191 * 8192
    t0 = time.perf_counter()
    lines = M.report_lines([(s, 5)], 9, 4)
    notes = M.lint_notes({"prop": [p]})
    b = M.bounds(s)
    assert time.perf_counter() - t0 < 2.0
    assert b == {"x": (-300, 300), "z": (-1100, -500), "h": (90, 210)}
    assert notes == [] and "x -300..300 z -1100..-500 h 90..210" in lines[1]


# ------------------------------------------------------------------ review: the report says what the path does
def test_shuttle_far_end_is_the_point_reached():
    """[review: far end = mid + half] With an odd period the clock never lands on the half turn, so the prop turns
    back short of mid + half; the far end the report prints is the farthest pose the path REACHES."""
    for period in (151, 3):
        s = _spec({"to": [-301, -1600], "period": period}, pos=[-1000, -1600], shadow=None)
        reached = max(M.path(s, 0, period), key=lambda p: abs(p.x + 1000))
        assert s.far_end == (reached.x, reached.z)
        assert s.far_end[0] == M.bounds(s)["x"][1] < -302           # short of mid + half (-302)
        assert f"-> {s.far_end}" in M.describe(s)
    assert _spec({"to": [-301, -1600], "period": 3}, pos=[-1000, -1600], shadow=None).far_end[0] < -450


def test_max_step_is_exact_over_a_small_joint_cycle():
    """[review: the combined channel maxima flagged a SNAP that never happens] A shuttle + a bob whose maxima fall
    on different ticks: the real largest step is under 400 u, so no SNAPS, no lint advisory."""
    m = {"to": [3800, -800], "period": 32, "height": 1200, "bob": {"amp": 1000}}
    s = _spec(m)
    assert M.step_is_exact(s)
    step, _fb = M.max_step(s)
    seq = M.path(s, 0, s.cycle + 1)
    assert step == max(math.dist((a.x, a.b, a.z), (c.x, c.b, c.z)) for a, c in zip(seq, seq[1:])) < 400
    assert "SNAP" not in M.describe(s) and M.lint_notes({"prop": [_prop(m)]}) == []


def test_max_step_past_the_exact_cap_is_named_a_bound():
    """A joint cycle over STEP_EXACT_MAX ticks keeps the per-channel bound, and the report and lint say so."""
    m = {"radius": 8191, "period": 129, "bob": {"amp": 8191, "period": 128}}
    s = _spec(m)
    assert s.cycle == 129 * 128 > M.STEP_EXACT_MAX and not M.step_is_exact(s)
    line = M.describe(s)
    assert "max <= " in line and line.endswith("MAY SNAP: its step bound is over the smoother's 400 u per tick")
    notes = M.lint_notes({"prop": [_prop(m)]})
    assert len(notes) == 1 and "may move up to" in notes[0] and "a bound" in notes[0]


def test_reverse_orbit_swings_counter_clockwise_first():
    """[review: FORMAT's compass] reverse on an orbit reverses the one shared angle, swing included (documented)."""
    fwd = _spec({"radius": 200, "period": 64, "turn": "swing", "swing": 40}, face=128)
    rev = _spec({"radius": 200, "period": 64, "reverse": True, "turn": "swing", "swing": 40}, face=128)
    assert M.pose(fwd, 0).face == M.pose(rev, 0).face == 128
    assert M.pose(fwd, 1).face > 128 > M.pose(rev, 1).face


# ------------------------------------------------------------------ a bob that READS (owner: "no cask bob")
def _pitched(x, h, z):
    """A pitched camera's field-canvas map, linearised: 1 u of height moves a prop 0.069 px up the screen, 1 u of
    depth (away, +z) 0.100 px -- the bench camera's measured gains (pitch 48). v grows DOWN."""
    return (0.1 * x, -0.069 * h - 0.100 * z)


def test_swings_count_reversals_not_integer_jitter():
    lap = [10 * math.sin(2 * math.pi * n / 64) for n in range(64)]
    assert M._swings(lap) == 2                                   # one up, one down a cycle
    assert M._swings([v + (0.2 if n % 2 else -0.2) for n, v in enumerate(lap)]) == 2   # sub-0.5 px jitter ignored
    assert M._swings([3.0] * 20) == 0 and M._swings([1.0]) == 0
    assert M._swings(lap * 3, cyclic=False) == 6                 # a cut window: every turn once the direction settles


def test_a_small_slow_bob_folds_into_the_orbit():
    """[bench 30946's cask, owner-observed] +-60 every 256 ticks on a 128-tick r 300 orbit moves the prop ~4 px on
    a pitched camera, adds no up-and-down of its own and is far smaller than the orbit's own ~60 px: no read. The
    default bob period (the orbit's own) and a 4x faster +-60 bob fold too -- amp matters, not only speed."""
    cask = M.parse(BENCH["B"], 1)
    r = M.bob_reading(cask, _pitched)
    assert (r.with_bob, r.cyclic) == (r.without, True) and 3.5 < r.px < 5.0 and not r.reads
    assert "adds no up-and-down of its own" in M.bob_note(cask, _pitched)
    same = _spec({"radius": 300, "period": 128, "height": 150, "turn": "travel", "bob": {"amp": 60}})
    assert same.bob_period == 128 and M.bob_note(same, _pitched) is not None
    assert M.bob_note(_spec({"radius": 300, "period": 128, "height": 150, "bob": {"amp": 60, "period": 32}}),
                      _pitched) is not None


_READS = [
    # (id, motion, pos) -- each READS as a bob; the old reversal-only rule flagged every one but the first two
    ("demo_4x_faster", {"radius": 200, "period": 128, "height": 150, "turn": "travel",
                        "bob": {"amp": 120, "period": 32}}, [0, -1500]),
    ("bob_only", {"height": 150, "bob": {"amp": 150, "period": 60}}, [0, -800]),
    ("sideways_slow", {"to": [600, -800], "period": 120, "height": 150, "bob": {"amp": 60, "period": 240}}, [-600, -800]),
    ("shuttle_depth_drift", {"to": [900, -990], "period": 128, "height": 150, "bob": {"amp": 100}}, [300, -1000]),
    ("small_orbit_big_bob", {"radius": 40, "period": 120, "height": 200, "bob": {"amp": 150}}, [0, -800]),
    ("bob_swallows_reversals", {"radius": 50, "period": 64, "height": 400, "bob": {"amp": 400, "period": 128}}, [0, -800]),
]


@pytest.mark.parametrize("motion, pos", [r[1:] for r in _READS], ids=[r[0] for r in _READS])
def test_a_bob_that_moves_or_outtravels_its_path_reads(motion, pos):
    """[review: the reversal-only rule] A bob reads when it adds up-and-downs of its own OR out-travels the path's own
    up-and-down: a bob on a nearly flat track (sideways, a small orbit, a slight depth drift) IS the vertical motion,
    whatever its period -- and a sub-px depth change cannot flip the verdict."""
    s = _spec(motion, prop="cask", pos=pos)
    r = M.bob_reading(s, _pitched)
    assert r.reads and M.bob_note(s, _pitched) is None, r


def test_a_long_joint_cycle_is_measured_not_skipped():
    """[review: past STEP_EXACT_MAX the check went silent] The owner's +-60 bob at period 257 (lcm 32896 with the
    128-tick orbit) folds exactly like period 256: it is measured over a window and flagged, and the note says so."""
    s = _spec({"radius": 300, "period": 128, "phase": 0.5, "height": 150, "bob": {"amp": 60, "period": 257}})
    r = M.bob_reading(s, _pitched)
    assert s.cycle > M.STEP_EXACT_MAX and not r.cyclic and r.window == 8 * 257 and not r.reads
    assert "measured over 2056 ticks of its 32896-tick joint cycle" in M.bob_note(s, _pitched)


def test_a_pathless_bob_too_small_to_see_gets_the_amp_advice():
    """[review: a spin/swing prop got the path advice] Any mover without radius/to -- bob-only, spin or swing -- whose
    bob moves it under a field px is told its amp, never a bob period (it has no path to outpace)."""
    for m in ({"height": 300, "bob": {"amp": 1, "period": 60}},
              {"turn": "spin", "period": 64, "height": 150, "bob": {"amp": 2, "period": 60}},
              {"turn": "swing", "swing": 20, "period": 64, "height": 150, "bob": {"amp": 3, "period": 60}}):
        note = M.bob_note(_spec(m, shadow=False), _pitched)
        assert "too small to see; try an amp of" in note and "bob period" not in note, note
    assert M.bob_reading(_spec({"radius": 300, "period": 128}), _pitched) is None          # no bob, no reading


_FIX_RE = re.compile(r"a bob period of (\d+) \(same amp\)|an amp of (\d+)")


@pytest.mark.parametrize("motion", [
    {"radius": 300, "period": 128, "phase": 0.5, "height": 150, "bob": {"amp": 60, "period": 256}},
    {"radius": 300, "period": 128, "height": 150, "bob": {"amp": 60, "period": 40}},
    {"radius": 300, "period": 300, "height": 150, "bob": {"amp": 60, "period": 256}},
    {"height": 300, "bob": {"amp": 1, "period": 60}},
], ids=["cask", "cask_40", "long_cycle", "tiny"])
def test_every_fix_a_note_names_really_reads(motion):
    """[review: the advice could not clear the note] A note names only fixes it has re-measured: applying each named
    bob period or amp to the same mover gives a bob that reads on the same camera."""
    s = _spec(motion)
    note = M.bob_note(s, _pitched)
    fixes = _FIX_RE.findall(note)
    assert fixes, note
    for bp, amp in fixes:
        fixed = dataclasses.replace(s, bob_period=int(bp)) if bp else dataclasses.replace(s, bob_amp=int(amp))
        assert M.bob_reading(fixed, _pitched).reads, (note, bp, amp)
