"""The adjust/drift lane (studies/sims rung 0) — the vocabulary's first numeric WRITE.

``adjust`` rides a branch like raise_flags (a clamped write while selected, with an
optional byte-timer rate divider); ``drift`` is the field-level metabolism lane in the
ticker's clock segment (an Int16 timer, independent of any tree's selection — the
draining-condition law is exactly why decay lives here and not on branches). Every body
is instruction-walked; the negatives pin the fences (mandatory clamp, the ±10^6
magnitude fence against the 26-bit re-read overflow, the never-raised drift gate)."""
from __future__ import annotations

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.eb import disasm as D
from ff9mapkit.eb import exprasm


def _verify_body(body: bytes) -> None:
    starts = set()
    for ins in D.iter_code(body, 0, len(body)):
        starts.add(ins.off)
        assert ins.end <= len(body)
    ends = starts | {len(body)}
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op in (0x01, 0x02, 0x03):
            t = D.jump_target(ins)
            if t is not None:
                assert t in ends


def _verify_all(cb: B.CompiledBehavior) -> None:
    _verify_body(cb.ticker_body)
    _verify_body(cb.main_init)
    for body in cb.duty_bodies.values():
        _verify_body(body)
    for funcs in cb.action_funcs.values():
        for _tag, body in funcs:
            _verify_body(body)


def _stmt_bytes(text: str) -> bytes:
    """The exact 0x05-statement bytes the compiler emits for ``text``
    (assemble() already appends the 0x7F terminator for B_EXPR_END)."""
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def sim_field(*, brains: bool = False, every: int = 0) -> B.FieldBehavior:
    """One Sim, one need (a counter), one stove point — the rung-1 shape."""
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         counters=["hunger", "cur_obj"],
                         tables=[B.TableSpec("need", (100, 100, 100))],
                         brains=brains)
    cook = B.Do(B.Hold((300, 0)),
                adjust=B.AdjustSpec(counter="hunger", by=3, lo=0, hi=100,
                                    every=every))
    fb.units["sim"].tree = B.Selector(
        B.Sequence(fb.counter_le("hunger", 94), cook),
        B.Do(B.Hold((0, 0))),
    )
    return fb


# ------------------------------------------------------------------ AdjustSpec fences
def test_spec_needs_exactly_one_target():
    with pytest.raises(B.BehaviorError, match="exactly one target"):
        B.AdjustSpec(by=1, lo=0, hi=10)
    with pytest.raises(B.BehaviorError, match="exactly one target"):
        B.AdjustSpec(counter="c", table="t", index=0, by=1, lo=0, hi=10)


def test_spec_table_needs_index_and_counter_refuses_it():
    with pytest.raises(B.BehaviorError, match="needs index"):
        B.AdjustSpec(table="t", by=1, lo=0, hi=10)
    with pytest.raises(B.BehaviorError, match="takes no index"):
        B.AdjustSpec(counter="c", index=0, by=1, lo=0, hi=10)


def test_spec_by_zero_and_bad_clamp_refused():
    with pytest.raises(B.BehaviorError, match="by=0"):
        B.AdjustSpec(counter="c", by=0, lo=0, hi=10)
    with pytest.raises(B.BehaviorError, match="lo .* must be < hi"):
        B.AdjustSpec(counter="c", by=1, lo=10, hi=10)


def test_spec_magnitude_fence():
    with pytest.raises(B.BehaviorError, match="26-bit"):
        B.AdjustSpec(counter="c", by=B.ADJUST_MAG_MAX + 1, lo=0, hi=10)
    with pytest.raises(B.BehaviorError, match="26-bit"):
        B.AdjustSpec(counter="c", by=1, lo=-(B.ADJUST_MAG_MAX + 1), hi=10)


def test_branch_every_is_a_byte():
    with pytest.raises(B.BehaviorError, match="byte timer"):
        B.Do(B.Hold((0, 0)),
             adjust=B.AdjustSpec(counter="c", by=1, lo=0, hi=10, every=256))


# ------------------------------------------------------------------ compilation
def test_counter_adjust_compiles_and_the_write_shape_lands():
    fb = sim_field()
    cb = fb.compile()
    _verify_all(cb)
    # the exact clamped-write statements, byte-for-byte, in the ticker
    cell = fb._counter_ref("hunger")
    assert _stmt_bytes(f"{cell} {cell} const(3) B_PLUS B_LET") in cb.ticker_body
    assert _stmt_bytes(f"{cell} const(0) B_LT") in cb.ticker_body
    assert _stmt_bytes(f"{cell} const(100) B_GT") in cb.ticker_body


def test_table_adjust_computed_index():
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         counters=["cur_obj"],
                         tables=[B.TableSpec("need", (100, 100, 100))])
    fb.units["sim"].tree = B.Selector(
        B.Do(B.Hold((0, 0)),
             adjust=B.AdjustSpec(table="need", index="cur_obj", by=-2,
                                 lo=0, hi=100)),
    )
    cb = fb.compile()
    _verify_all(cb)
    cell = fb._table_ref("need", "cur_obj")            # nested VECTOR read as index
    assert _stmt_bytes(f"{cell} {cell} const(-2) B_PLUS B_LET") in cb.ticker_body


def test_table_adjust_constant_index_bounds_checked():
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         tables=[B.TableSpec("need", (100, 100))])
    fb.units["sim"].tree = B.Selector(
        B.Do(B.Hold((0, 0)),
             adjust=B.AdjustSpec(table="need", index=5, by=1, lo=0, hi=100)))
    with pytest.raises(B.BehaviorError, match="out of range"):
        fb.compile()


def test_adjusted_table_seed_fence():
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         tables=[B.TableSpec("big", (2_000_000,))])
    fb.units["sim"].tree = B.Selector(
        B.Do(B.Hold((0, 0)),
             adjust=B.AdjustSpec(table="big", index=0, by=1, lo=0, hi=100)))
    with pytest.raises(B.BehaviorError, match="seeds"):
        fb.compile()


def test_adjust_every_allocates_a_v1_timer():
    fb = sim_field(every=30)
    cb = fb.compile()
    _verify_all(cb)
    assert any("adj" in n for n, _f in fb._cooldowns), \
        "every>0 must allocate a central-clock byte timer"


def test_adjust_under_brains_uses_instance_timer():
    fb = sim_field(brains=True, every=30)
    cb = fb.compile()
    _verify_all(cb)
    assert not any("adj" in n for n, _f in fb._cooldowns)
    # the timer is a Seq-private Instance slot, registered for the brain's own
    # decrement loop (the ref text is the slot, the key carries the name)
    assert any(k.startswith("adj") for (_o, k) in fb._inst_slots
               if _o == "sim"), "under brains the every-timer is Seq-private"
    assert fb._brain_cooldowns.get("sim"), "…and brain-decremented"


def test_unused_lane_is_deterministic_and_reportable():
    # the master byte-identity itself was verified out-of-band at rung 0
    # (working-tree vs HEAD compile of the same field: ccfef59a580d1ba5 both);
    # in-suite we pin determinism, which is what makes that check meaningful
    h1 = sim_field().compile().stable_hash()
    h2 = sim_field().compile().stable_hash()
    assert h1 == h2


# ------------------------------------------------------------------ drift
def drift_field(**kw) -> B.FieldBehavior:
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         counters=["hunger"])
    fb.units["sim"].tree = B.Selector(B.Do(B.Hold((0, 0))))
    fb.drift(counter="hunger", by=-1, clamp=[0, 100], **kw)
    return fb


def test_drift_compiles_and_seeds_its_timer():
    fb = drift_field(every=90)
    cb = fb.compile()
    _verify_all(cb)
    t = fb._drifts[0][2]
    # Main_Init seeds the Int16 timer to `every` — first write one period in
    assert _stmt_bytes(f"Global.Int16[{t}] const(90) B_LET") in cb.main_init
    cell = fb._counter_ref("hunger")
    assert _stmt_bytes(f"{cell} {cell} const(-1) B_PLUS B_LET") in cb.ticker_body


def test_drift_every_required_range():
    with pytest.raises(B.BehaviorError, match="1..30000"):
        drift_field(every=0)
    with pytest.raises(B.BehaviorError, match="1..30000"):
        drift_field(every=30001)


def test_drift_gate_never_raised_refused():
    fb = drift_field(every=90, flag="tock")
    with pytest.raises(B.BehaviorError, match="never raised"):
        fb.compile()


def test_drift_gate_alternator_ok():
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         counters=["hunger"])
    fb.alternator("tock", 300)
    fb.units["sim"].tree = B.Selector(B.Do(B.Hold((0, 0))))
    fb.drift(counter="hunger", by=-1, clamp=[0, 100], every=90, flag="tock")
    _verify_all(fb.compile())


def test_drift_gate_raise_flags_ok():
    fb = B.FieldBehavior([B.UnitSpec("sim", entry=2, spawn=(0, 0))],
                         counters=["hunger"])
    fb.units["sim"].tree = B.Selector(
        B.Sequence(fb.near("sim", B.PLAYER, 400),
                   B.Do(B.Hold((0, 0)), raise_flags=("busy",))),
        B.Do(B.Hold((0, 0))),
    )
    fb.drift(counter="hunger", by=-1, clamp=[0, 100], every=90, flag="busy")
    _verify_all(fb.compile())


# ------------------------------------------------------------------ the TOML surface
RAW = {
    "player": {"spawn": [0, -900]},
    "npc": [{"name": "sim", "pos": [0, 0], "dialogue": "Kupo."}],
    "marker": [{"name": "stove", "pos": [300, 0]}],
    "behavior": {
        "counters": ["hunger", "cur_obj"],
        "table": [{"name": "need", "values": [100, 100, 100]}],
        "alternators": [{"name": "tock", "frames": 300}],
        "drift": [{"counter": "hunger", "by": -1, "clamp": [0, 100],
                   "every": 90, "flag": "tock"}],
        "unit": [
            {"npc": "sim", "branch": [
                {"when": [{"counter_le": ["hunger", 94]}],
                 "do": {"hold": "stove"},
                 "adjust": {"counter": "hunger", "by": 3, "clamp": [0, 100],
                            "every": 15}},
                {"do": {"hold": [0, 0]}},
            ]},
        ],
    },
}


def _toml_build(raw):
    return BT.build(raw, npc_slots={"sim": 2})


def test_toml_end_to_end():
    fb = _toml_build(RAW)
    cb = fb.compile()
    _verify_all(cb)
    assert len(fb._drifts) == 1
    cell = fb._counter_ref("hunger")
    assert _stmt_bytes(f"{cell} {cell} const(3) B_PLUS B_LET") in cb.ticker_body
    assert _stmt_bytes(f"{cell} {cell} const(-1) B_PLUS B_LET") in cb.ticker_body


def _mut(path, value):
    """RAW with one nested value replaced (a fresh deep copy)."""
    import copy
    raw = copy.deepcopy(RAW)
    node = raw
    for k in path[:-1]:
        node = node[k]
    if value is _DEL:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return raw


_DEL = object()


def test_toml_unknown_adjust_key_refused():
    raw = _mut(("behavior", "unit", 0, "branch", 0, "adjust", "typo"), 1)
    with pytest.raises(BT.BehaviorTomlError, match="unknown adjust key"):
        _toml_build(raw)


def test_toml_clamp_required():
    raw = _mut(("behavior", "unit", 0, "branch", 0, "adjust", "clamp"), _DEL)
    with pytest.raises(BT.BehaviorTomlError, match="clamp"):
        _toml_build(raw)


def test_toml_drift_every_required():
    raw = _mut(("behavior", "drift", 0, "every"), _DEL)
    with pytest.raises(BT.BehaviorTomlError, match="needs every"):
        _toml_build(raw)


def test_toml_unknown_counter_refused():
    raw = _mut(("behavior", "unit", 0, "branch", 0, "adjust", "counter"), "hungr")
    with pytest.raises(BT.BehaviorTomlError, match="unknown counter"):
        _toml_build(raw)


def test_toml_engage_refuses_adjust():
    raw = _mut(("behavior", "unit", 0, "branch", 0, "do"), {"engage": "g"})
    raw["behavior"]["unit"][0]["hp"] = 5              # a grouped member needs hp
    raw["behavior"]["group"] = [{"name": "g", "units": ["sim"]}]
    with pytest.raises(BT.BehaviorTomlError, match="engage takes no adjust"):
        _toml_build(raw)


def test_toml_adjust_list_form():
    raw = _mut(("behavior", "unit", 0, "branch", 0, "adjust"),
               [{"counter": "hunger", "by": 3, "clamp": [0, 100]},
                {"table": "need", "index": "cur_obj", "by": 1,
                 "clamp": [0, 100]}])
    fb = _toml_build(raw)
    _verify_all(fb.compile())
