"""Map-variable layout: an Int16 var index is a BYTE OFFSET, so two live Int16s must not share a byte.

``EventContext.mapvar`` is ``Byte[80]`` (Memoria EventContext.cs:9). The Map source hands the token's
index straight to ``GetVariableValueInternal`` as ``ofs`` (EBin.cs:1631), which reads an Int16 as
``buffer[ofs] | (sbyte)buffer[ofs+1] << 8`` (EBin.cs:1868). So ``MAP.I16[3]`` and ``MAP.I16[4]`` share
byte 4. ``[[platform]]`` once held its ride state at 3/4/5/6: capturing x, then z, then selfY left the
boarding x holding selfY's high byte and z's low byte (-600 read back as 28672), and the land ride threw
the player ~11000 units sideways on its first frame. The cutscene signal guard sat at 3, straddling the
ladder's 2-3 and the Init position scratch.

Three layers: the declared constants, every emitter's own bytes, and a whole built field. The last
test RUNS the land ride on a byte-offset model of mapvar, so it checks what the ride reads back.
"""
from __future__ import annotations

import itertools

import pytest

from ff9mapkit.build import FieldProject, build_script, collect_text, validate
from ff9mapkit.content import cutscene as _cutscene
from ff9mapkit.content import ladder as _ladder
from ff9mapkit.content import platform as _platform
from ff9mapkit.content import region as _region
from ff9mapkit.eb import EbScript
from ff9mapkit.eb import disasm as D

MAP_SRC = 1                                    # VariableSource.Map
T_INT16, T_UINT16 = 6, 7                       # VariableType.Int16 / UInt16
_WIDTH = {0: 0, 1: 0, 2: 3, 3: 3, 4: 1, 5: 1, 6: 2, 7: 2}   # by VariableType; 0 = a bit index
INIT_POS_SCRATCH = (0, 2, 4, 6)                # stock D9 x/y/z/face scratch every object Init writes


def _map_accesses(raw: bytes, start: int = 0, end: int | None = None) -> list:
    """Every Map var token in ``raw[start:end]`` as ``(first_byte, width, vtype, index)``."""
    out = []
    for ins in D.iter_code(raw, start, len(raw) if end is None else end):
        for toks in D.instr_expr_tokens(raw, ins):
            for op, arg in toks or ():
                if op < 0xC0 or op == 0xD3 or (op & 3) != MAP_SRC:
                    continue
                vtype = (op >> 2) & 7
                w = _WIDTH[vtype]
                out.append((arg >> 3, 1, vtype, arg) if w == 0 else (arg, w, vtype, arg))
    return out


def _int16_offsets(accesses) -> set:
    return {a[0] for a in accesses if a[2] in (T_INT16, T_UINT16)}


def _partial_overlaps(offsets) -> list:
    """Pairs of Int16 byte offsets that share a byte without being the same slot."""
    return [(a, b) for a, b in itertools.combinations(sorted(set(offsets)), 2) if b - a < 2]


# --- the detector itself ------------------------------------------------------------------------

def test_the_detector_flags_the_old_platform_layout():
    assert _partial_overlaps([3, 4, 5, 6]) == [(3, 4), (4, 5), (5, 6)]
    assert _partial_overlaps([2, 3]) == [(2, 3)]                      # the old signal guard vs the ladder
    assert _partial_overlaps([0, 2, 4, 6]) == []                      # stock's own stride-2 Init scratch
    assert _partial_overlaps([2, 2]) == []                            # one slot shared is not an overlap


# --- the declared allocations -------------------------------------------------------------------

def _declared() -> dict:
    return {
        "platform scratch": _platform.PLATFORM_SCRATCH,
        "platform start": _platform.PLATFORM_START,
        "platform start x": _platform.PLATFORM_START_X,
        "platform start z": _platform.PLATFORM_START_Z,
        "cutscene signal guard": _cutscene.SIGNAL_GUARD_IDX,
        "ladder climb scratch": _ladder.CLIMB_SCRATCH,
    }


def test_declared_int16_slots_fit_mapvar():
    for name, ofs in _declared().items():
        assert 0 <= ofs and ofs + 2 <= _region.MAPVAR_BYTES, name


def test_declared_int16_slots_do_not_overlap_each_other():
    assert _partial_overlaps(_declared().values()) == []
    assert len(set(_declared().values())) == len(_declared())           # and none is shared outright


def test_ride_and_guard_slots_are_clear_of_the_init_position_scratch():
    # the ladder sharing I16[2] with the Init y is stock 706's own layout; nothing else may join them
    held = [v for k, v in _declared().items() if k != "ladder climb scratch"]
    busy = {b for o in INIT_POS_SCRATCH for b in (o, o + 1)}
    assert not busy & {b for o in held for b in (o, o + 1)}


# --- each emitter's own bytes -------------------------------------------------------------------

_BIT = _platform.platform_ride_bit(0)
EMITTERS = {
    "land": lambda: _platform.carry_body(land=(600, -400, 200)),
    "land+model+warp": lambda: _platform.carry_body(land=(600, -400, 200), ride_bit=_BIT, warp_to=30001),
    "rise": lambda: _platform.carry_body(rise=300),
    "rise down+model": lambda: _platform.carry_body(rise=-300, ride_bit=_BIT),
    "entry rise": lambda: _platform.entry_rise_body(land=(0, 0, 300), rise=600, ride_bit=_BIT),
    "wait_signal": lambda: _cutscene.wait_signal(2),
    "ladder climb": lambda: _ladder.navigable_climb_body((600, -500, 0), (600, -700, 400)),
}


@pytest.mark.parametrize("name", sorted(EMITTERS))
def test_emitter_int16_offsets_do_not_overlap(name):
    acc = _map_accesses(EMITTERS[name]())
    assert _partial_overlaps(_int16_offsets(acc)) == [], name
    assert all(first + width <= _region.MAPVAR_BYTES for first, width, _, _ in acc), name


def test_land_ride_actually_uses_all_four_slots():
    # guards the emitter scan against going vacuous: the land ride must read/write every ride slot
    held = {_platform.PLATFORM_SCRATCH, _platform.PLATFORM_START,
            _platform.PLATFORM_START_X, _platform.PLATFORM_START_Z}
    assert _int16_offsets(_map_accesses(EMITTERS["land"]())) == held


# --- a whole built field ------------------------------------------------------------------------

COMPOSITE = """
[field]
id = 30603
name = "MAPLAY"
area = 11

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[[npc]]
name = "zorn"
preset = "vivi"
pos = [-300, -800]
dialogue = "..."

[[npc]]
name = "thorn"
preset = "vivi"
pos = [300, -800]
dialogue = "..."

[[cutscene]]
actors = ["zorn", "thorn"]
steps = [
  { set_signal = 0 },
  { actor = "zorn",  open = "A!", speaker = "Zorn",  window = 2, signal = "+", hold = true },
  { actor = "thorn", open = "B!", speaker = "Thorn", window = 3, signal = "+", hold = true },
  { wait_signal = 2 },
  { close = 2 },
  { close = 3 },
]

[[ladder]]
navigable = true
bottom = [600, -500, 0]
top = [600, -700, 400]

[[platform]]
zone = [[-900, -150], [-700, -150], [-700, -350], [-900, -350]]
land = [-800, -900, 200]
prop = "cask"

[[platform]]
zone = [[-500, -150], [-300, -150], [-300, -350], [-500, -350]]
rise = 200
"""


@pytest.fixture(scope="module")
def composite_eb(tmp_path_factory) -> bytes:
    p = tmp_path_factory.mktemp("maplay") / "f.field.toml"
    p.write_text(COMPOSITE, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []
    _mes, npc_txids, _ev, cs_txids, *_ = collect_text(proj)
    return build_script(proj, "us", npc_txids, cutscene_txids=cs_txids)


def _all_accesses(eb: bytes) -> list:
    s = EbScript.from_bytes(eb)
    return [a for e in s.entries for f in e.funcs for a in _map_accesses(eb, f.abs_start, f.abs_end)]


def test_built_field_int16_offsets_do_not_overlap(composite_eb):
    acc = _all_accesses(composite_eb)
    offs = _int16_offsets(acc)
    # un-vacuous: the ride, the guard and the ladder all made it into the scanned bytes
    assert {_platform.PLATFORM_START_X, _cutscene.SIGNAL_GUARD_IDX, _ladder.CLIMB_SCRATCH} <= offs
    assert _partial_overlaps(offs) == []
    assert all(first + width <= _region.MAPVAR_BYTES for first, width, _, _ in acc)


def test_built_field_leaves_the_ride_and_guard_bytes_to_their_owners(composite_eb):
    owners = {_platform.PLATFORM_SCRATCH, _platform.PLATFORM_START, _platform.PLATFORM_START_X,
              _platform.PLATFORM_START_Z, _cutscene.SIGNAL_GUARD_IDX}
    reserved = {b for o in owners for b in (o, o + 1)}
    for first, width, vtype, idx in _all_accesses(composite_eb):
        if reserved & set(range(first, first + width)):
            assert vtype in (T_INT16, T_UINT16) and first in owners, (first, width, vtype, idx)


# --- the ride, run on a byte-offset model of mapvar ----------------------------------------------

class _Ride:
    """Just enough of EBin to run a land ride: Map Int16 by byte offset (EBin.cs:1868), obj fields
    0/1/2 = x / -pos[1] / z (EBin.getvobj), MoveInstantXZY(a1, a2, a3) -> x, selfY, z, Int26 results,
    truncating division. Anything else in the stream fails loudly rather than being skipped."""

    def __init__(self, x, selfy, z):
        self.mapvar = bytearray(_region.MAPVAR_BYTES)
        self.pos = [x, selfy, z]
        self.frames = []

    def _get(self, v):
        if isinstance(v, int):
            return v
        kind, a = v
        if kind == "obj":
            assert a[0] == _ladder.SELF
            return self.pos[a[1]]
        lo, hi = self.mapvar[a], self.mapvar[a + 1]
        return lo | ((hi - 256 if hi & 0x80 else hi) << 8)

    def _eval(self, toks):
        st = []
        for op, arg in toks:
            if op == _region.T_END:
                break
            if op == _region.T_CONST:
                st.append(arg)
            elif op == _region.MAP_INT16:
                st.append(("map", arg))
            elif op == _region.T_OBJVAR:
                st.append(("obj", arg))
            elif op == _region.T_ASSIGN:
                v, (kind, ofs) = self._get(st.pop()), st.pop()
                assert kind == "map"
                self.mapvar[ofs], self.mapvar[ofs + 1] = v & 0xFF, (v >> 8) & 0xFF
                st.append(v)
            else:
                b, a = self._get(st.pop()), self._get(st.pop())
                r = {_region.T_PLUS: lambda: a + b, _region.T_MINUS: lambda: a - b,
                     _region.T_MULT: lambda: a * b, _region.T_DIV: lambda: int(a / b) if b else 0,
                     _region.T_EQ: lambda: int(a == b), _region.T_GT: lambda: int(a > b),
                     _region.T_LT: lambda: int(a < b)}[op]()
                r &= (1 << 26) - 1
                st.append(r - (1 << 26) if r & (1 << 25) else r)
        (top,) = st
        return self._get(top)

    def run(self, body: bytes):
        code = {ins.off: ins for ins in D.iter_code(body, 0, len(body))}
        pc, last = 0, 0
        for _ in range(10000):
            ins = code[pc]
            if ins.op == 0x04:                                            # RETURN
                return self
            nxt = ins.end
            if ins.op == 0x05:
                last = self._eval(D.instr_expr_tokens(body, ins)[0])
            elif ins.op == 0xA1:
                self.pos = [self._eval(t) for t in D.instr_expr_tokens(body, ins)]
            elif ins.op == 0x22:                                          # Wait -> one ride frame
                self.frames.append(tuple(self.pos))
            elif ins.op == _region.JMP_TRUE and last:
                nxt = D.jump_target(ins)
            pc = nxt
        raise AssertionError("the ride never returned")


@pytest.mark.parametrize("board, land", [
    ((-600, 0, -400), (600, -400, 200)),        # 1200 east, 200 up
    ((250, -120, 800), (-900, 1500, 460)),      # boarding off the ground floor; west + north
])
def test_land_ride_interpolates_from_the_captured_boarding_point(board, land):
    bx, bsy, bz = board
    lx, lz, ly = land
    ride = _Ride(bx, bsy, bz).run(_platform.carry_body(land=land, speed=30))
    # what the ride captured reads back intact after the whole ride has run
    assert ride._get(("map", _platform.PLATFORM_START_X)) == bx
    assert ride._get(("map", _platform.PLATFORM_START_Z)) == bz
    assert ride._get(("map", _platform.PLATFORM_START)) == bsy
    # every frame is on the straight line from the boarding point to the landing, within rounding
    assert len(ride.frames) >= 3
    span = -ly - bsy
    for x, sy, z in ride.frames:
        t = (sy - bsy) / span
        assert 0 < t <= 1 + 30 / abs(span)                                # the last step may overshoot

        assert abs(x - (bx + (lx - bx) * t)) <= 1 and abs(z - (bz + (lz - bz) * t)) <= 1, (x, sy, z)
    assert ride.pos == [lx, -ly, lz]                                      # the exact landing snap
