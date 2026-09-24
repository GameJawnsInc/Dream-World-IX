"""A tiny EBin-rule interpreter for tests: run emitted ``.eb`` bodies and assert on what they DO.

:class:`Engine` ports just enough of ``EBin`` for field bodies (the vector store's own write rules --
``EBin.cs:1639-1658, :1917-1958`` -- Global/Map scalars, ``0x01``/``0x02`` jumps), calibrated in
``test_behavior_persist`` against the in-game-proven ordinary seed. :class:`BattleEngine` adds the battle
read tokens a ``[scene.ledger]`` fragment uses (``B_SYSLIST[n]``, ``B_SYSVAR[n]``, ``B_MEMBER(n) B_PICK``,
``B_COUNT``) and stops at ``RET``; ``test_battle_ledger`` calibrates it against rung 0's measured cells."""
import re

from ff9mapkit.eb import disasm as D


def _wrap26(v: int) -> int:
    """Every operator result is pushed through ``EBin.expr_Push_v0_Int24`` (EBin.cs:1270-1274) and read
    back sign-extended from bit 25 (:1682-1684): an overflow WRAPS mod 2^26 (measured in-game,
    studies/roll-stream rung 0: 2^25 - 1 + 1 reads back -2^25)."""
    return ((v + (1 << 25)) % (1 << 26)) - (1 << 25)


def _ctrunc_div(a: int, b: int) -> int:
    """C# ``/`` on Int32: truncation toward zero; a zero divisor pushes the NUMERATOR (EBin.cs:653-667)."""
    if b == 0:
        return a
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _ctrunc_rem(a: int, b: int) -> int:
    """C# ``%`` on Int32: the sign of the dividend; a zero divisor pushes the NUMERATOR (EBin.cs:668-682)."""
    return a if b == 0 else a - b * _ctrunc_div(a, b)


_ARITH = {"B_PLUS": lambda a, b: a + b, "B_MINUS": lambda a, b: a - b, "B_MULT": lambda a, b: a * b,
          "B_DIV": _ctrunc_div, "B_REM": _ctrunc_rem}


class Engine:
    """Just enough of EBin to run Main_Init / adjust bodies: 0x05 expression statements, the 0x01 /
    0x02 jumps, the vector store with the ENGINE's write rules (index == Count APPENDS; index 0 on a
    missing id CREATES; anything else on a missing/short vector is DROPPED), size writes (grow
    zero-fills, shrink truncates, negative ignored, missing id creates), and Global/Map scalars.
    Every other opcode is a no-op. const() is signed 16-bit, const4() is 26-bit sign-extended."""

    def __init__(self, vectors=None):
        self.vec = {k: list(v) for k, v in (vectors or {}).items()}
        self.scalars: dict = {}

    # -- references -----------------------------------------------------------------------------
    def _read(self, x):
        if isinstance(x, int):
            return x
        kind = x[0]
        if kind == "cell":
            v = self.vec.get(x[1])
            return v[x[2]] if v is not None and 0 <= x[2] < len(v) else 0
        if kind == "size":
            return len(self.vec[x[1]]) if x[1] in self.vec else 0
        return self.scalars.get(x[1], 0)

    def _write(self, ref, val):
        kind = ref[0]
        if kind == "cell":
            tid, idx = ref[1], ref[2]
            v = self.vec.get(tid)
            if v is not None:
                if idx == len(v):
                    v.append(val)
                elif 0 <= idx < len(v):
                    v[idx] = val
            elif idx == 0:
                self.vec[tid] = [val]
        elif kind == "size":
            tid = ref[1]
            if val < 0:
                return
            v = self.vec.get(tid)
            if v is None:
                self.vec[tid] = [0] * val
            elif val > len(v):
                v.extend([0] * (val - len(v)))
            else:
                del v[val:]
        else:
            self.scalars[ref[1]] = val

    # -- expressions ----------------------------------------------------------------------------
    def eval(self, text: str) -> int:
        toks = text.strip("{} ").split()
        st: list = []
        for tok in toks:
            if tok == "B_EXPR_END":
                break
            m = re.fullmatch(r"const4?\((-?\d+)\)", tok)
            if m:
                v = int(m.group(1))
                if tok.startswith("const4"):
                    v &= 0x3FFFFFF
                    v = v - (1 << 26) if v & (1 << 25) else v
                elif v > 0x7FFF:
                    v -= 0x10000
                st.append(v)
            elif re.fullmatch(r"(Global|Map)\.\w+\[\d+\]", tok):
                st.append(("scalar", tok))
            elif tok == "B_VECTOR":
                idx, tid = self._read(st.pop()), self._read(st.pop())
                st.append(("cell", tid, idx))
            elif tok == "B_VECTOR_SIZE":
                st.append(("size", self._read(st.pop())))
            elif tok == "B_LET":
                val, ref = self._read(st.pop()), st.pop()
                self._write(ref, val)
                st.append(val)
            else:
                b, a = self._read(st.pop()), self._read(st.pop())
                if tok in _ARITH:
                    st.append(_wrap26(_ARITH[tok](a, b)))
                    continue
                ops = {"B_LT": int(a < b), "B_GT": int(a > b),
                       "B_LE": int(a <= b), "B_GE": int(a >= b), "B_EQ": int(a == b),
                       "B_NE": int(a != b), "B_ANDAND": int(bool(a) and bool(b)),
                       "B_OROR": int(bool(a) or bool(b))}
                if tok not in ops:
                    raise AssertionError(f"interpreter has no rule for {tok!r} in {text!r}")
                st.append(ops[tok])
        return self._read(st[-1]) if st else 0

    def run(self, body: bytes) -> "Engine":
        ins_at = {i.off: i for i in D.iter_code(body, 0, len(body))}
        pc, last, steps = 0, 0, 0
        while pc < len(body):
            steps += 1
            assert steps < 100000, "runaway body"
            ins = ins_at[pc]
            if ins.op == 0x05:
                last = self.eval(D.pretty_expr(body, ins.off + 1)[0])
            elif ins.op == 0x01:
                pc = D.jump_target(ins)
                continue
            elif ins.op == 0x02:                     # JMP_IFNOT: beq -- jump when the value is 0
                if last == 0:
                    pc = D.jump_target(ins)
                    continue
            pc = ins.end
        return self


class BattleEngine(Engine):
    """:class:`Engine` + a battle context: ``syslist`` {n: bits}, ``sysvar`` {n: value}, ``units`` {bit: {member:
    value}}. ``<bits> B_MEMBER(n) B_PICK`` reads member ``n`` of the unit whose bit is the LOWEST set in ``bits``
    (``EventEngine.OperatorPick``); ``B_COUNT`` is a popcount; ``RET`` (0x04) ends the body."""

    def __init__(self, vectors=None, *, syslist=None, sysvar=None, units=None):
        super().__init__(vectors)
        self.syslist, self.sysvar = dict(syslist or {}), dict(sysvar or {})
        self.units = {k: dict(v) for k, v in (units or {}).items()}

    def eval(self, text: str) -> int:
        out = []
        for tok in text.strip("{} ").split():
            m = re.fullmatch(r"B_SYS(LIST|VAR)\[(\d+)\]", tok)
            if m:
                src = self.syslist if m.group(1) == "LIST" else self.sysvar
                out.append(f"const4({src.get(int(m.group(2)), 0)})")
            else:
                out.append(tok)
        st: list = []                                # resolve the battle-only tokens to literals first
        for tok in out:
            m = re.fullmatch(r"B_MEMBER\((\d+)\)", tok)
            if m:
                st.append(("member", int(m.group(1))))
            elif tok == "B_PICK":
                mem, bits = st.pop(), st.pop()
                v = int(re.fullmatch(r"const4?\((-?\d+)\)", bits).group(1))
                st.append(f"const4({self.units.get(v & -v, {}).get(mem[1], 0)})")
            elif tok == "B_COUNT":
                v = int(re.fullmatch(r"const4?\((-?\d+)\)", st.pop()).group(1))
                st.append(f"const({bin(v & 0xFFFF).count('1')})")
            else:
                st.append(tok)
        assert all(isinstance(x, str) for x in st), f"a B_MEMBER without B_PICK in {text!r}"
        return super().eval(" ".join(st))

    def run(self, body: bytes) -> "BattleEngine":
        ins_at = {i.off: i for i in D.iter_code(body, 0, len(body))}
        pc, last, steps = 0, 0, 0
        while pc < len(body):
            steps += 1
            assert steps < 100000, "runaway body"
            ins = ins_at[pc]
            if ins.op == 0x04:                       # RET ends an added function
                break
            if ins.op == 0x05:
                last = self.eval(D.pretty_expr(body, ins.off + 1)[0])
            elif ins.op == 0x01:
                pc = D.jump_target(ins)
                continue
            elif ins.op == 0x02:                     # JMP_IFNOT: jump when the value is 0
                if last == 0:
                    pc = D.jump_target(ins)
                    continue
            pc = ins.end
        return self


# ================================================================================ the motion daemon's engine
def _f32(x: float) -> float:
    import struct
    return struct.unpack("<f", struct.pack("<f", x))[0]


def ff9_rtrig(fn, a: int) -> int:
    """``ff9.rsin`` / ``ff9.rcos`` (ff9.cs:2124-2138) -- an INDEPENDENT copy of ``content.motion``'s table
    arithmetic (single precision each step, the cast truncating), so the two cross-check each other. The float32
    model itself is proven in-game (studies/sine-kit rung 0, C7)."""
    import math                                      # noqa: F401 -- fn is math.sin / math.cos
    deg = _f32(_f32(a / 4096.0) * 360.0)
    rad = _f32(deg * _f32(0.0174532924))
    return int(_f32(_f32(fn(rad)) * 4096.0))


class MotionEngine(Engine):
    """:class:`Engine` + what the ``[[prop]] motion`` daemon runs: its OWN Instance locals as a ``loc``-byte
    little-endian block (``Instance.Int16[k]`` = bytes k..k+1, a store WRAPS to 16 bits, and Int16/Byte views
    ALIAS -- the platform-land lesson: an index is a BYTE offset), the unary trig tokens (``B_SIN2``/``B_COS2``
    raw 4096 a turn, ``B_SIN``/``B_COS`` ``v << 4``), ``B_AND``, and a tick runner that captures every 0xAD / 0x87
    operand. ``strict_reduced`` asserts every B_SIN2/B_COS2 argument lies in [0, 4095] (THE REDUCTION LAW)."""

    def __init__(self, loc: int, *, strict_reduced: bool = True):
        super().__init__()
        self.inst = bytearray(loc)
        self.strict_reduced = strict_reduced

    def _inst_ref(self, tok: str):
        m = re.fullmatch(r"Instance\.(Int16|Byte)\[(\d+)\]", tok)
        return ("inst", m.group(1), int(m.group(2))) if m else None

    def _read(self, x):
        if isinstance(x, tuple) and x[0] == "inst":
            _k, typ, off = x
            if typ == "Byte":
                return self.inst[off]
            v = self.inst[off] | (self.inst[off + 1] << 8)
            return v - 0x10000 if v & 0x8000 else v
        return super()._read(x)

    def _write(self, ref, val):
        if isinstance(ref, tuple) and ref[0] == "inst":
            _k, typ, off = ref
            if typ == "Byte":
                self.inst[off] = val & 0xFF
            else:
                self.inst[off] = val & 0xFF
                self.inst[off + 1] = (val >> 8) & 0xFF
            return
        super()._write(ref, val)

    def eval(self, text: str) -> int:
        import math
        st: list = []
        for tok in text.strip("{} ").split():
            if tok == "B_EXPR_END":
                break
            ref = self._inst_ref(tok)
            m = re.fullmatch(r"const4?\((-?\d+)\)", tok)
            if ref is not None:
                st.append(ref)
            elif m:
                v = int(m.group(1))
                if tok.startswith("const4"):
                    v &= 0x3FFFFFF
                    v = v - (1 << 26) if v & (1 << 25) else v
                elif v > 0x7FFF:
                    v -= 0x10000
                st.append(v)
            elif re.fullmatch(r"(Global|Map)\.\w+\[\d+\]", tok):
                st.append(("scalar", tok))
            elif tok in ("B_SIN2", "B_COS2", "B_SIN", "B_COS"):
                v = self._read(st.pop())
                fn = math.sin if "SIN" in tok else math.cos
                if tok.endswith("2"):
                    if self.strict_reduced:
                        assert 0 <= v <= 4095, f"{tok} argument {v} is not reduced to [0, 4095]"
                    st.append(_wrap26(ff9_rtrig(fn, v)))
                else:
                    st.append(_wrap26(ff9_rtrig(fn, v << 4)))
            elif tok == "B_LET":
                val, dst = self._read(st.pop()), st.pop()
                self._write(dst, val)
                st.append(val)
            else:
                b, a = self._read(st.pop()), self._read(st.pop())
                if tok == "B_AND":
                    st.append(_wrap26(a & b))
                elif tok in _ARITH:
                    st.append(_wrap26(_ARITH[tok](a, b)))
                else:
                    ops = {"B_LT": int(a < b), "B_GT": int(a > b), "B_LE": int(a <= b), "B_GE": int(a >= b),
                           "B_EQ": int(a == b), "B_NE": int(a != b)}
                    if tok not in ops:
                        raise AssertionError(f"interpreter has no rule for {tok!r} in {text!r}")
                    st.append(ops[tok])
        return self._read(st[-1]) if st else 0

    def ticks(self, body: bytes, n: int) -> list:
        """Run ``body`` for ``n`` ticks (a ``Wait`` ends a tick). Returns, per tick, the list of
        ``(op, uid, operand values)`` for every 0xAD / 0x87 it issued."""
        ins_at = {i.off: i for i in D.iter_code(body, 0, len(body))}
        out, cur, pc, last, steps = [], [], 0, 0, 0
        while len(out) < n:
            steps += 1
            assert steps < 10_000_000, "runaway daemon"
            ins = ins_at[pc]
            if ins.op == 0x05:
                last = self.eval(D.pretty_expr(body, ins.off + 1)[0])
            elif ins.op in (0xAD, 0x87):
                vals, off = [], ins.off + 3
                while off < ins.end:
                    txt, off = D.pretty_expr(body, off)
                    vals.append(self.eval(txt))
                cur.append((ins.op, body[ins.off + 2], tuple(vals)))
            elif ins.op == 0x22:                              # Wait: the tick boundary
                out.append(cur)
                cur = []
            elif ins.op == 0x01:
                pc = D.jump_target(ins)
                continue
            elif ins.op == 0x02:
                if last == 0:
                    pc = D.jump_target(ins)
                    continue
            elif ins.op == 0x04:
                break
            pc = ins.end
        return out


# ================================================================================ the photo daemon's engine
class CameraModel:
    """The field camera as rung 0 of photo mode MEASURED it (studies/photo-mode, runs 2-6, worst error 0 px):

    * follow: the view centre = the follow point clamped to the effective box (X narrowed under widescreen);
    * ``MoveCamera(x, y, n, type)`` starts from the CURRENT view, X is clamped once AT ISSUE and only under widescreen,
      Y never; frame k of n puts the view at start + (end - start) * f(k) (f = k/n, or the cosine ease for type 8);
      the finished move HOLDS (follow stays off);
    * ``ReleaseCamera(n, type)`` computes its target ONCE, from the follow point at issue, and glides there; on its last
      frame follow resumes in the SAME update (so a moved player is snapped to at once);
    * the readback (0xEA) truncates the float view.
    ``box`` = the camera's vrp box (lox, hix, loy, hiy); under widescreen X narrows by d = min(78, hix - lox) // 2."""

    def __init__(self, box, follow, *, widescreen: bool = True):
        self.box = tuple(box)
        self.widescreen = widescreen
        lox, hix, loy, hiy = self.box
        d = min(78, max(0, hix - lox)) // 2 if widescreen else 0
        self.xbox = (lox + d, hix - d)
        self.follow = follow                        # callable -> the raw (unclamped) follow point (x, y)
        self.v = list(self._follow_point())
        self.state, self.move = "follow", None
        self.active = True

    def _follow_point(self) -> tuple:
        fx, fy = self.follow()
        _lox, _hix, loy, hiy = self.box
        return (min(max(fx, self.xbox[0]), self.xbox[1]), min(max(fy, loy), hiy))

    def readback(self) -> tuple:
        return int(self.v[0]), int(self.v[1])

    def move_camera(self, x: int, y: int, n: int, typ: int) -> None:
        assert n > 0, "a MoveCamera duration of 0 divides by zero in the engine"
        if not self.active:
            return
        if self.widescreen:
            x = min(max(x, self.xbox[0]), self.xbox[1])
        self.move = (list(self.v), (x, y), n, 0, typ)
        self.state = "move"

    def release_camera(self, n: int, typ: int) -> None:
        assert n > 0, "a ReleaseCamera duration of 0 divides by zero in the engine"
        if not self.active:
            return
        self.move = (list(self.v), self._follow_point(), n, 0, typ)
        self.state = "release"

    def update(self) -> None:
        import math
        if self.state in ("move", "release"):
            s, e, n, k, typ = self.move
            k += 1
            if typ == 8:
                f = (ff9_rtrig(math.cos, 2048 * k // n + 2048) + 4096) / 8192
            else:
                f = k / n
            self.v = [s[i] + (e[i] - s[i]) * f for i in (0, 1)]
            self.move = (s, e, n, k, typ)
            if k >= n:
                if self.state == "move":
                    self.state = "hold"
                else:
                    self.state = "follow"
                    self.v = list(self._follow_point())
        elif self.state == "follow" and self.active:
            self.v = list(self._follow_point())


class FieldTickEngine(MotionEngine):
    """:class:`MotionEngine` + what the ``[photo]`` daemon reads and does, run TICK by tick against a
    :class:`CameraModel`: ``B_KEY`` (``keys`` = the held logical bits), ``B_SYSVAR[1|2|12|13]`` (camera index,
    usercontrol, the 0xEA readback -- any other index raises), ``Map.Bit[n]`` (``map_bits``), ``obj(uid=U).f[4]``
    (``objects`` = {uid: flags}; an absent uid RAISES, as the engine's getvobj does), B_AND / B_OR / B_ANDAND / B_OROR;
    ops 0x2D / 0x2E (usercontrol), 0xEA, 0x6F / 0x70 (the camera), 0x14 (runs the SEATED function bytes in
    ``functions[(uid, tag)]`` -- its 0x93 applies (flags & ~63) | (v & 63) -- and ends the caller's tick, the engine's
    wait=255 until the callee returns; an absent uid stalls FOR EVER), 0xD5 / 0xD6 (pflags), 0xEC (the grade).
    Any other op raises (STRICT). ``effects`` = [(tick, op, args)]."""

    def __init__(self, loc: int, camera: CameraModel, *, objects=None, functions=None):
        super().__init__(loc, strict_reduced=True)
        self.camera = camera
        self.objects = dict(objects or {250: 15})
        self.pflags: dict = {}
        self.functions = dict(functions or {})
        self.keys = 0
        self.usercontrol = 1
        self.camidx = 0
        self.map_bits: dict = {}
        self.ssys = [0, 0]
        self.grade = (0, 0, 0)
        self.effects: list = []
        self.tick = 0
        self.pc = 0
        self.no_tick = False                        # field 257 only (ProcessEvents.cs:112-116): no object runs
                                                    # while a dialog animates open -- never a novel field's case
        self._ins = None
        self._body = None

    def eval(self, text: str) -> int:
        st: list = []
        for tok in text.strip("{} ").split():
            if tok == "B_EXPR_END":
                break
            ref = self._inst_ref(tok)
            m = re.fullmatch(r"const4?\((-?\d+)\)", tok)
            mo = re.fullmatch(r"obj\(uid=(\d+)\)\.f\[4\]", tok)
            if ref is not None:
                st.append(ref)
            elif m:
                v = int(m.group(1))
                if tok.startswith("const4"):
                    v &= 0x3FFFFFF
                    v = v - (1 << 26) if v & (1 << 25) else v
                elif v > 0x7FFF:
                    v -= 0x10000
                st.append(v)
            elif re.fullmatch(r"B_SYSVAR\[\d+\]", tok):
                n = int(tok[9:-1])
                st.append({1: self.camidx, 2: self.usercontrol, 12: self.ssys[0], 13: self.ssys[1]}[n])
            elif re.fullmatch(r"Map\.Bit\[\d+\]", tok):
                st.append(int(bool(self.map_bits.get(int(tok[8:-1]), 0))))
            elif mo:
                uid = int(mo.group(1))
                if uid not in self.objects:
                    raise AssertionError(f"obj(uid={uid}) does not exist -- the engine's getvobj throws")
                st.append(self.objects[uid])
            elif tok == "B_KEY":
                st.append(1 if (self.keys & self._read(st.pop())) else 0)
            elif tok == "B_LET":
                val, dst = self._read(st.pop()), st.pop()
                self._write(dst, val)
                st.append(val)
            else:
                b, a = self._read(st.pop()), self._read(st.pop())
                if tok in _ARITH:
                    st.append(_wrap26(_ARITH[tok](a, b)))
                    continue
                ops = {"B_AND": a & b, "B_OR": a | b, "B_LT": int(a < b), "B_GT": int(a > b), "B_LE": int(a <= b),
                       "B_GE": int(a >= b), "B_EQ": int(a == b), "B_NE": int(a != b),
                       "B_ANDAND": int(bool(a) and bool(b)), "B_OROR": int(bool(a) or bool(b))}
                if tok not in ops:
                    raise AssertionError(f"interpreter has no rule for {tok!r} in {text!r}")
                st.append(_wrap26(ops[tok]))
        return self._read(st[-1]) if st else 0

    def _operands(self, body: bytes, ins, sizes) -> list:
        flags, off, vals = body[ins.off + 1], ins.off + 2, []
        for k, sz in enumerate(sizes):
            if flags & (1 << k):
                txt, off = D.pretty_expr(body, off)
                vals.append(self.eval(txt))
            else:
                vals.append(int.from_bytes(body[off:off + sz], "little", signed=(sz == 2)))
                off += sz
        return vals

    def _run_function(self, uid: int, tag: int) -> None:
        body = self.functions[(uid, tag)]
        for ins in D.iter_code(body, 0, len(body)):
            if ins.op == 0x93:
                v = self._operands(body, ins, (1,))[0]
                self.objects[uid] = (self.objects[uid] & ~63) | (v & 63)
            elif ins.op == 0x04:
                return
            else:
                raise AssertionError(f"a seated function runs op 0x{ins.op:02X} the interpreter does not model")

    def run(self, body: bytes, ticks: int) -> "FieldTickEngine":
        """Run ``ticks`` more ticks of ``body`` (the pc persists between calls)."""
        if self._body is not body:
            self._body, self._ins, self.pc = body, {i.off: i for i in D.iter_code(body, 0, len(body))}, 0
        for _ in range(ticks):
            self._one_tick()
        return self

    def _one_tick(self) -> None:
        body, last, steps = self._body, 0, 0
        if not self.no_tick:
            while True:
                steps += 1
                assert steps < 100_000, "runaway daemon tick"
                ins = self._ins[self.pc]
                op, nxt = ins.op, ins.end
                if op == 0x05:
                    last = self.eval(D.pretty_expr(body, ins.off + 1)[0])
                elif op == 0x01:
                    self.pc = D.jump_target(ins)
                    continue
                elif op == 0x02:
                    if last == 0:
                        self.pc = D.jump_target(ins)
                        continue
                elif op == 0x22:
                    self.pc = nxt
                    break
                elif op == 0x04:
                    raise AssertionError("the daemon RETURNED")
                elif op == 0xEA:
                    self.ssys = list(self.camera.readback())
                    self.effects.append((self.tick, 0xEA, tuple(self.ssys)))
                elif op == 0x6F:
                    x, y, n, typ = self._operands(body, ins, (2, 2, 1, 1))
                    self.effects.append((self.tick, 0x6F, (x, y, n, typ)))
                    self.camera.move_camera(x, y, n, typ)
                elif op == 0x70:
                    n, typ = self._operands(body, ins, (1, 1))
                    self.effects.append((self.tick, 0x70, (n, typ)))
                    self.camera.release_camera(n, typ)
                elif op == 0x2D:
                    self.usercontrol = 0
                    self.effects.append((self.tick, 0x2D, ()))
                elif op == 0x2E:
                    self.usercontrol = 1
                    self.effects.append((self.tick, 0x2E, ()))
                elif op == 0x14:
                    lv, uid, tag = body[ins.off + 2], body[ins.off + 3], body[ins.off + 4]
                    self.effects.append((self.tick, 0x14, (lv, uid, tag)))
                    if uid not in self.objects:
                        raise AssertionError(f"RunScriptSync on absent uid {uid}: the engine re-runs it for ever")
                    self._run_function(uid, tag)
                    self.pc = nxt                           # the caller waits (wait=255) until the callee returns:
                    break                                   # its next op runs on the next tick
                elif op in (0xD5, 0xD6):                    # DoEventCode.cs:2680-2706: PUSHHIDE snapshots EVERY
                    for u in self.objects:                      # PosObj (flag 32 only skips the hide); POPSHOW restores
                        if op == 0xD5:                          # bit 0 from pflags, which is 0 until a PUSHHIDE ran
                            self.pflags[u] = self.objects[u]    # (PosObj.cs:181) -- a ShowAll with no HideAll HIDES
                            if not self.objects[u] & 32:
                                self.objects[u] &= ~1
                        else:
                            self.objects[u] = (self.objects[u] & ~1) | (self.pflags.get(u, 0) & 1)
                    self.effects.append((self.tick, op, ()))
                elif op == 0xEC:
                    args = tuple(body[ins.off + 2:ins.end])
                    self.grade = args[3:]
                    self.effects.append((self.tick, 0xEC, args))
                else:
                    raise AssertionError(f"op 0x{op:02X} is not modelled (STRICT)")
                self.pc = nxt
        self.camera.update()
        self.tick += 1
