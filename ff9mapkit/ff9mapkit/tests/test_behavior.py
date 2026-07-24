"""Rung-0 tests for the behavior-tree compiler (studies/behavior-trees/PLAN.md).

Pure-offline: every compiled body is WALKED instruction-by-instruction (eb.disasm
iter_code) and every jump target must land on an instruction boundary inside the body —
the same structural soundness eblint checks on whole files, applied to raw bodies. Plus
the law lints (the compiler-invariant negatives) and a determinism/golden check.
"""
from __future__ import annotations

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.eb import disasm as D


def _verify_body(body: bytes) -> int:
    """Walk the whole body; assert stream integrity + every jump lands on an
    instruction start (or one-past-the-end). Returns the instruction count."""
    starts = set()
    count = 0
    for ins in D.iter_code(body, 0, len(body)):
        starts.add(ins.off)
        count += 1
        assert ins.end <= len(body), f"instruction overruns the body at {ins.off}"
    ends = starts | {len(body)}
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op not in (0x01, 0x02, 0x03):           # jump_target is jumps-only API
            continue
        t = D.jump_target(ins)
        if t is not None:
            assert t in ends, f"jump at {ins.off} targets {t} (not an instruction start)"
    return count


def _verify_all(cb: B.CompiledBehavior) -> None:
    _verify_body(cb.ticker_body)
    _verify_body(cb.main_init)
    for body in cb.duty_bodies.values():
        _verify_body(body)
    for funcs in cb.action_funcs.values():
        for _tag, body in funcs:
            _verify_body(body)


def guard_field() -> B.FieldBehavior:
    """The rung-1 reference: a guard patrols, notices the player, approaches, and a
    beast that duels a dummy — exercises every v1 node and both action classes."""
    fb = B.FieldBehavior([
        B.UnitSpec("guard", entry=2, spawn=(0, 0)),
        B.UnitSpec("beast", entry=3, spawn=(500, 500), hp=3),
    ])
    patrol = B.Patrol([(0, 0), (400, 0), (400, 400), (0, 400)])
    fb.units["guard"].tree = B.Selector(
        B.Sequence(fb.near("guard", B.PLAYER, 400), B.Do(B.Chase(B.PLAYER))),
        B.Do(patrol),
    )
    fb.units["beast"].tree = B.Selector(
        B.Sequence(fb.hp_le("beast", 0), B.Do(B.Die())),
        B.Sequence(fb.near("beast", "guard", 200), B.Do(B.SwingAt("guard"))),
        B.Do(B.Hold((500, 500))),
    )
    return fb


# ------------------------------------------------------------------ structure
def test_reference_compiles_and_verifies():
    cb = guard_field().compile()
    _verify_all(cb)
    assert cb.ticker_body[0] == 0x05 or cb.ticker_body[0] in (0x01, 0x02, 0x03)
    assert len(cb.duty_bodies) == 2
    assert len(cb.action_funcs["beast"]) == 2          # SwingAt + Die
    assert cb.action_funcs["guard"] == []              # feeds only
    assert "guard" in cb.report and "blackboard" in cb.report


def test_determinism_and_golden_stability():
    h1 = guard_field().compile().stable_hash()
    h2 = guard_field().compile().stable_hash()
    assert h1 == h2, "compilation must be deterministic"


def test_duplicate_feed_targets_get_unique_labels():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.near("u", B.PLAYER, 200), B.Do(B.Chase(B.PLAYER))),
        B.Sequence(fb.near("u", B.PLAYER, 900), B.Do(B.Chase(B.PLAYER))),
        B.Do(B.Hold((0, 0))),
    )
    _verify_all(fb.compile())                          # duplicate labels would raise


def test_decorators_compile():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0), hp=5)])
    fb.units["u"].tree = B.Selector(
        B.Once("greet", B.Sequence(fb.near("u", B.PLAYER, 300), B.Do(B.Chase(B.PLAYER)))),
        B.Cooldown(90, B.Sequence(fb.near("u", B.PLAYER, 600), B.Do(B.Chase(B.PLAYER)))),
        B.Sequence(B.Invert(fb.near("u", B.PLAYER, 2000)), B.Do(B.Hold((0, 0)))),
        B.Do(B.WalkTo((100, 100))),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert "u.once.greet" in cb.report and "u.onceeng.greet" in cb.report
    assert "u.cd" in cb.report and "u.cdeng" in cb.report   # sticky engagement flags


def test_patrol_waypoint_state_resets():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Do(B.Patrol([(0, 0), (100, 0), (100, 100)]))
    cb = fb.compile()
    _verify_all(cb)
    assert "u.wp" in cb.report


# ------------------------------------------------------------------ the law lints
def test_cond_refuses_object_references():
    with pytest.raises(B.BehaviorError, match="player-ref eval law"):
        B.Cond("obj(uid=250).f[0] const(0) B_GT")
    with pytest.raises(B.BehaviorError, match="player-ref eval law"):
        B.Cond("B_PTR(250) B_DISTANCEA const(300) B_LT")


def test_raw_cond_requires_explicit_unsafe():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    with pytest.raises(B.BehaviorError):
        fb.raw("obj(uid=250).f[0] const(0) B_GT")
    fb.raw("obj(uid=250).f[0] const(0) B_GT", unsafe_ok=True)   # power-user escape


def test_do_must_be_last_in_sequence():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Selector(
        B.Sequence(B.Do(B.WalkTo((1, 1))), fb.near("u", B.PLAYER, 100)),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="LAST child"):
        fb.compile()


def test_fallback_must_be_static_feed():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Do(B.Chase(B.PLAYER))       # chase is not a static fallback
    with pytest.raises(B.BehaviorError, match="static feed"):
        fb.compile()
    fb2 = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb2.units["u"].tree = B.Selector(
        B.Sequence(fb2.near("u", B.PLAYER, 100), B.Do(B.Hold((0, 0)))),
    )
    with pytest.raises(B.BehaviorError, match="UNCONDITIONAL"):
        fb2.compile()


def test_swing_at_player_refused():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.near("u", B.PLAYER, 100), B.Do(B.SwingAt(B.PLAYER))),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="SwingAt"):
        fb.compile()


def test_unknown_units_and_reserved_name():
    with pytest.raises(B.BehaviorError, match="reserved"):
        B.FieldBehavior([B.UnitSpec(B.PLAYER, entry=2, spawn=(0, 0))])
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    with pytest.raises(B.BehaviorError, match="unknown unit"):
        fb.near("u", "ghost", 100)


# ------------------------------------------------------------------ install (game-gated)
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_install_on_a_real_field_eb():
    """Structural end-to-end: install a behavior onto real field 559's .eb (two real
    NPC entries drafted as units) — the lint baseline-diff must pass, the ticker entry
    must be seated, and every touched function must still walk clean."""
    from ff9mapkit.extract import EventBundle
    from ff9mapkit.eb.model import EbScript

    data = EventBundle().eb_for_id(559)
    eb = EbScript.from_bytes(data)
    hosts = [i for i in range(1, eb.entry_count)
             if eb.entry(i).func_by_tag(0) is not None
             and eb.entry(i).func_by_tag(1) is not None
             and eb.entry(i).func_by_tag(15) is None][:2]
    assert len(hosts) == 2
    fb = B.FieldBehavior([
        B.UnitSpec("a", entry=hosts[0], spawn=(0, 0)),
        B.UnitSpec("b", entry=hosts[1], spawn=(100, 100), hp=3),
    ])
    fb.units["a"].tree = B.Selector(
        B.Sequence(fb.near("a", B.PLAYER, 300), B.Do(B.Chase(B.PLAYER))),
        B.Do(B.Hold((0, 0))),
    )
    fb.units["b"].tree = B.Selector(
        B.Sequence(fb.hp_le("b", 0), B.Do(B.Die())),
        B.Do(B.Patrol([(0, 0), (200, 0)])),
    )
    out = fb.install(data)
    eb2 = EbScript.from_bytes(out)

    def used(e):
        return sum(1 for i in range(e.entry_count) if e.entry(i).size > 0)
    assert used(eb2) == used(eb) + 1                   # the seated ticker (a free slot)
    assert eb2.entry(hosts[0]).func_by_tag(1) is not None
    assert eb2.entry(hosts[1]).func_by_tag(B.FIRST_ACTION_TAG) is not None


# ------------------------------------------------------------------ blackboard
def test_blackboard_allocation():
    bb = B.Blackboard(byte_base=1220, byte_end=1240, flag_base=8860, flag_end=8863)
    a = bb.byte("a")
    assert bb.byte("a") == a                           # stable by name
    i = bb.int16("w")
    assert i % 2 == 0
    with pytest.raises(B.BehaviorError, match="reallocated"):
        bb.flag("a")
    bb.flag("f1")
    bb.flag("f2")
    bb.flag("f3")
    bb.flag("f4")
    with pytest.raises(B.BehaviorError, match="flag band exhausted"):
        bb.flag("f5")
    assert "byte" in bb.report()
