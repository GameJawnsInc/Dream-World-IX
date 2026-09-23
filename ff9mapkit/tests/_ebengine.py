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
