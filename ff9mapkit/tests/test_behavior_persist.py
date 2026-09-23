"""PERSISTENT data tables (`persist = true` on [[behavior.table]]) -- studies/persistent-tables/.

A persistent table is NOT re-seeded at Main_Init: a guard vector (id + 1e6) holds a check word over
the table's name and length, and the table seeds only when it is stale. Rung 0 proved in-game that
vectors survive save -> quit -> relaunch -> load and ride only the Memoria extra file; these tests pin
the emitted bytecode by RUNNING it through a small interpreter that ports the engine's own vector
read/write rules (EBin.cs:1639-1658, :1917-1958) -- calibrated first against the ordinary seed, whose
in-game behaviour is proven -- so the claims are about what the bytes DO, not what they look like."""
import random
import re

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.eb import disasm as D
from ff9mapkit.eb.labelasm import asm

from .test_behavior import _expr_stmts, _verify_all, table_field

SEED10 = (1001, 2002, 3003, 4004, 5005, 6006, 7007, 8008, 9009, 10010)
T, G = 6004242, 7004242


# ------------------------------------------------------------------------------------ interpreter
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
                ops = {"B_PLUS": a + b, "B_MINUS": a - b, "B_LT": int(a < b), "B_GT": int(a > b),
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


def _memo_field(*, adjust_index=None, extra_tables=()):
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))],
                         tables=[B.TableSpec("memo", SEED10, id=T, persist=True), *extra_tables],
                         counters=("k",))
    adj = () if adjust_index is None else (
        B.AdjustSpec(table="memo", index=adjust_index, by=7, lo=0, hi=100000),)
    fb.units["u"].tree = B.Do(B.Hold((0, 0)), adjust=adj)
    return fb


W10 = B.persist_check_word("memo", 10)


# ------------------------------------------------------------------------------------------ T1
def test_persist_check_word_pinned():
    """A PERMANENT CONTRACT with every shipped save: if these move, every persistent table a
    player holds silently re-seeds. Change them only by bumping PERSIST_SALT on purpose."""
    assert B.persist_check_word("memo", 10) == 27929820
    assert B.persist_check_word("memo", 11) == 27601081
    assert B.persist_check_word("ledger", 4) == 20755519
    rng = random.Random(9)
    for _ in range(5000):
        name = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz_0123456789") for _ in range(rng.randint(1, 12)))
        w = B.persist_check_word(name, rng.randint(1, 64))
        assert B.PERSIST_CHECK_FLOOR <= w <= B.TABLE_VALUE_MAX       # never 0, bit 25 clear
    assert B.persist_check_word("memo", 10) != B.persist_check_word("memx", 10)
    assert B.persist_check_word("memo", 10) != B.persist_check_word("memo", 9)


# ------------------------------------------------------------------------------------------ T2
def test_persist_block_shape():
    blk = B.persist_seed_block("memo", T, SEED10)
    stmts = _expr_stmts(blk)
    assert stmts[0] == (f"{{const4({G}) const(0) B_VECTOR const4({W10}) B_NE const4({T}) "
                        f"B_VECTOR_SIZE const(10) B_NE B_OROR B_EXPR_END}}")
    assert stmts[1] == f"{{const4({T}) B_VECTOR_SIZE const(0) B_LET B_EXPR_END}}"
    assert stmts[2] == f"{{const4({T}) B_VECTOR_SIZE const(10) B_LET B_EXPR_END}}"
    assert len(stmts) == 3 + 10 + 2
    assert stmts[-2] == f"{{const4({G}) B_VECTOR_SIZE const(1) B_LET B_EXPR_END}}"
    assert stmts[-1] == f"{{const4({G}) const(0) B_VECTOR const4({W10}) B_LET B_EXPR_END}}"   # LAST
    jumps = [i for i in D.iter_code(blk, 0, len(blk)) if i.op in (0x01, 0x02, 0x03)]
    assert [j.op for j in jumps] == [0x02]                     # one JMP_IFNOT, never JMP_IF
    assert D.jump_target(jumps[0]) == len(blk)                  # skips the whole seed


# ------------------------------------------------------------------------------------------ T3
def test_the_interpreter_is_calibrated_against_the_proven_ordinary_seed():
    """Calibrate the instrument before judging with it: the ORDINARY seed (in-game proven, rung 0
    and bench 30415) must wipe stale save tails and rebuild the declared tables exactly."""
    fb = table_field()
    cb = fb.compile()
    sched, cost = fb.tables["sched"][0], fb.tables["cost"][0]
    e = Engine({sched: [9] * 7, cost: [1], fb._ctr_tid: [5, 5, 5]}).run(cb.main_init)
    assert e.vec[sched] == [100, 80, 0]
    assert e.vec[cost] == [300, 500]
    assert e.vec[fb._ctr_tid] == [0, 0]


BUMPED = list(SEED10[:3]) + [4011] + list(SEED10[4:])


@pytest.mark.parametrize("start, want", [
    ({}, {T: list(SEED10), G: [W10]}),                                    # fresh game / lost extra
    ({T: BUMPED, G: [W10]}, {T: BUMPED, G: [W10]}),                        # a matching save: KEPT
    ({T: BUMPED, G: [W10 ^ 1]}, {T: list(SEED10), G: [W10]}),              # foreign word: re-seed
    ({T: BUMPED + [7], G: [W10]}, {T: list(SEED10), G: [W10]}),            # n+1 cells: re-seed to n
    ({T: BUMPED}, {T: list(SEED10), G: [W10]}),                            # guard missing
    ({G: [W10]}, {T: list(SEED10), G: [W10]}),                             # table missing
    ({T: BUMPED, G: [W10, 55, 66]}, {T: BUMPED, G: [W10, 55, 66]}),        # extra guard cells: kept
])
def test_persist_block_runs_like_the_engine(start, want):
    blk = B.persist_seed_block("memo", T, SEED10)
    e = Engine(start).run(blk)
    assert {k: e.vec[k] for k in want} == want
    again = Engine(e.vec).run(blk)                                         # idempotent
    assert {k: again.vec[k] for k in want} == want


def test_a_zero_seed_cell_is_left_zero_filled_not_written():
    blk = B.persist_seed_block("z", T, (0, 5, 0))
    assert Engine().run(blk).vec[T] == [0, 5, 0]
    assert len(_expr_stmts(blk)) == 3 + 1 + 2                  # only the non-zero cell is written


# ------------------------------------------------------------------------------------------ T4
def test_persist_compile_splices_the_guard_and_keeps_the_ordinary_seed():
    fb = _memo_field(extra_tables=(B.TableSpec("eph", (5005,)),))
    cb = fb.compile()
    _verify_all(cb)
    mi = bytes(cb.main_init)
    assert B.persist_seed_block("memo", T, SEED10) in mi
    stmts = _expr_stmts(mi)
    assert sum(s.startswith(f"{{const4({T}) B_VECTOR_SIZE const(0)") for s in stmts) == 1
    eph = fb.tables["eph"][0]
    # the ordinary twin still seeds UNCONDITIONALLY (it runs whatever the save held)
    e = Engine({T: BUMPED, G: [W10], eph: [9999]}).run(mi)
    assert e.vec[T] == BUMPED and e.vec[eph] == [5005]


# ------------------------------------------------------------------------------------------ T5
def test_no_persist_emits_no_guard_and_no_reserved_id():
    for fb in (table_field(),):
        cb = fb.compile()
        text = " ".join(_expr_stmts(bytes(cb.main_init)) + _expr_stmts(bytes(cb.ticker_body)))
        assert "B_OROR" not in " ".join(_expr_stmts(bytes(cb.main_init)))
        for tid in re.findall(r"const4?\((\d+)\) B_VECTOR", text):
            assert not B.PERSIST_RESERVED_LO <= int(tid) <= B.PERSIST_RESERVED_HI


# ------------------------------------------------------------------------------------------ T6
@pytest.mark.parametrize("spec, msg", [
    (dict(values=(1,), id=6_000_000), "reserved persistent band"),
    (dict(values=(1,), id=7_999_999), "reserved persistent band"),
    (dict(values=(1,), persist=True), "needs an explicit id"),
    (dict(values=(1,), id=7_000_000, persist=True), "outside the persistent band"),
    (dict(values=(1,), id=5_999_999, persist=True), "outside the persistent band"),
    (dict(values=(1,), id=6_000_000, persist=1), "persist must be true or false"),
    (dict(values=(1,), id=True), "id must be"),
])
def test_persist_band_enforced_at_assignment(spec, msg):
    with pytest.raises(B.BehaviorError, match=msg):
        B.FieldBehavior([], tables=[B.TableSpec("x", **spec)])


def test_the_band_edges_that_stay_legal():
    B.FieldBehavior([], tables=[B.TableSpec("a", (1,), id=5_999_999),
                                B.TableSpec("b", (1,), id=8_000_000),
                                B.TableSpec("c", (1,), id=6_000_000, persist=True),
                                B.TableSpec("d", (1,), id=6_999_999, persist=True)])


def test_both_auto_allocators_refuse_the_reserved_band(monkeypatch):
    monkeypatch.setattr(B, "TABLE_ID_BASE", B.PERSIST_RESERVED_LO - 1)
    with pytest.raises(B.BehaviorError, match="reached the reserved persistent band"):
        B.FieldBehavior([], tables=[B.TableSpec("a", (1,)), B.TableSpec("b", (1,))])
    monkeypatch.undo()
    fb = B.FieldBehavior([])
    fb._next_tid = B.PERSIST_RESERVED_LO - 1
    assert fb._alloc_tid() == B.PERSIST_RESERVED_LO - 1
    with pytest.raises(B.BehaviorError, match="reached the reserved persistent band"):
        fb._alloc_tid()


# ------------------------------------------------------------------------------------------ T7
def test_persist_value_fence():
    B.FieldBehavior([], tables=[B.TableSpec("a", (-1_000_000, 1_000_000), id=6_000_001, persist=True)])
    with pytest.raises(B.BehaviorError, match="within ±1000000"):
        B.FieldBehavior([], tables=[B.TableSpec("a", (1_000_001,), id=6_000_001, persist=True)])
    # the ORDINARY lane keeps its wider 26-bit domain
    B.FieldBehavior([], tables=[B.TableSpec("a", (1_000_001,))])


# ------------------------------------------------------------------------------------------ T8
def test_persist_adjust_fence_blocks_the_engine_append():
    fb = _memo_field(adjust_index="k")
    spec = B.AdjustSpec(table="memo", index="k", by=7, lo=0, hi=100000)
    body = asm(fb._adjust_write(spec, "t"))
    ctr = fb._ctr_tid
    assert _expr_stmts(body)[0] == f"{{const({ctr}) const(0) B_VECTOR const(10) B_LT B_EXPR_END}}"
    # k parked at exactly n (the wave clock's resting place): the write is SKIPPED, no n+1th cell
    e = Engine({T: list(SEED10), ctr: [10]}).run(body)
    assert e.vec[T] == list(SEED10)
    # an in-range k writes as before
    e = Engine({T: list(SEED10), ctr: [3]}).run(body)
    assert e.vec[T] == BUMPED
    # the fence is in the COMPILED bytes, not only in the helper
    cb = fb.compile()
    _verify_all(cb)
    bodies = [bytes(cb.ticker_body)] + [bytes(b) for fs in cb.action_funcs.values() for _t, b in fs]
    fence = f"{{const({ctr}) const(0) B_VECTOR const(10) B_LT B_EXPR_END}}"
    assert any(fence in _expr_stmts(b) for b in bodies)


def test_ordinary_tables_keep_the_engine_append_unchanged():
    """Pins the PRE-EXISTING ordinary behaviour (unfenced: the next entry re-seeds anyway), so the
    fence can never leak into every existing build's bytes."""
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))],
                         tables=[B.TableSpec("memo", (1, 2, 3))], counters=("k",))
    spec = B.AdjustSpec(table="memo", index="k", by=7, lo=0, hi=100)
    body = asm(fb._adjust_write(spec, "t"))
    tid, ctr = fb.tables["memo"][0], fb._ctr_tid
    assert not _expr_stmts(body)[0].endswith("B_LT B_EXPR_END}") or "B_PLUS" in _expr_stmts(body)[0]
    e = Engine({tid: [1, 2, 3], ctr: [3]}).run(body)
    assert e.vec[tid] == [1, 2, 3, 7]                           # the engine APPENDS at index == n


# ------------------------------------------------------------------------------------------ T9
def test_persist_report_lines():
    rep = _memo_field().compile().report
    assert "PERSISTENT rows are guarded instead" in rep
    assert f"memo: id {T} PERSISTENT, 10 cell(s)" in rep
    assert f"guard vector {G} = [check word {W10}]" in rep
    assert "PERSISTENT" not in table_field().compile().report


# ------------------------------------------------------------------------------------------ T10
def test_persist_is_in_the_harvested_field_schema():
    from ff9mapkit import _fieldschema
    assert "persist" in _fieldschema.VOCAB["behavior.table"]
    assert "behavior.table" in _fieldschema.ENFORCED
