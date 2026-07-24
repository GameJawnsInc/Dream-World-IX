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
    assert len(cb.action_funcs["beast"]) == 3          # SwingAt + Die + speed nudge
    assert len(cb.action_funcs["guard"]) == 1          # feeds only -> just the nudge
    assert "guard" in cb.report and "blackboard" in cb.report
    # the staged latch's existence source (set by the player Init at install)
    assert "player.bound" in cb.report


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


# ------------------------------------------------------------------ pooled units
def pooled_field() -> B.FieldBehavior:
    """One boot-spawned pest + two pooled recruits (pool 'recruits') — the
    placement-defender reference: activate at the player, hold the post, intercept."""
    fb = B.FieldBehavior([
        B.UnitSpec("pest", entry=2, spawn=(500, 500), hp=3),
        B.UnitSpec("r0", entry=3, spawn=(0, 0), hp=4, pooled=True, pool="recruits"),
        B.UnitSpec("r1", entry=4, spawn=(0, 0), hp=4, pooled=True, pool="recruits"),
    ])
    fb.units["pest"].tree = B.Selector(
        B.Sequence(fb.hp_le("pest", 0), B.Do(B.Die())),
        B.Do(B.Wander((500, 500), radius=300)),
    )
    for r in ("r0", "r1"):
        fb.units[r].tree = B.Selector(
            B.Sequence(fb.hp_le(r, 0), B.Do(B.Die())),
            B.Sequence(fb.active("pest"), fb.near(r, "pest", 250), B.Do(B.SwingAt("pest"))),
            B.Sequence(fb.active("pest"), fb.near(r, "pest", 700),
                       B.Do(B.Chase("pest", standoff=160))),
            B.Do(B.HoldPost()),
        )
    return fb


def _ticker_ops(cb: B.CompiledBehavior) -> list:
    return [ins.op for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body))]


def test_pooled_units_compile_and_verify():
    fb = pooled_field()
    cb = fb.compile()
    _verify_all(cb)
    ops = _ticker_ops(cb)
    # the activation lane: one runtime InitObject (0x09) + one MoveInstantEx (0xBF)
    # attempt per pooled unit, and NOWHERE else in the ticker
    assert ops.count(0x09) == 2 and ops.count(0xBF) == 2
    assert fb.pool_flags == {"recruits": fb.bb.flag("pool.recruits.spawn")}
    assert "pool.recruits.spawn" in cb.report and "units [r0, r1]" in cb.report
    # pooled allocations exist; the post pair presets in Main_Init
    assert "r0.spawned" in cb.report and "r1.px" in cb.report


def test_pooled_determinism():
    assert pooled_field().compile().stable_hash() == pooled_field().compile().stable_hash()


def test_holdpost_on_boot_spawned_unit():
    """hold_post on a NON-pooled unit = hold at its own spawn (the post presets)."""
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(120, -80))])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.near("u", B.PLAYER, 300), B.Do(B.Chase(B.PLAYER))),
        B.Do(B.HoldPost()),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert "u.px" in cb.report and "u.pz" in cb.report
    assert _ticker_ops(cb).count(0x09) == 0            # no pool -> no activation lane


def test_unpooled_field_allocates_no_pool_names():
    """Byte hygiene: a field with no pooled units and no HoldPost gets ZERO new
    allocations from the pooled lane (existing fields rebuild byte-identical)."""
    cb = guard_field().compile()
    assert ".spawned" not in cb.report and "pool." not in cb.report \
        and ".px" not in cb.report
    assert _ticker_ops(cb).count(0x09) == 0 and _ticker_ops(cb).count(0xBF) == 0


def test_pool_name_charset_refused():
    with pytest.raises(B.BehaviorError, match="pool name"):
        B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0),
                                    pooled=True, pool="bad name!")])


# ------------------------------------------------------------------ pool economy
def economy_field() -> B.FieldBehavior:
    fb = B.FieldBehavior(
        [B.UnitSpec("pest", entry=2, spawn=(500, 500), hp=3),
         B.UnitSpec("r0", entry=3, spawn=(0, 0), hp=4, pooled=True, pool="recruits"),
         B.UnitSpec("r1", entry=4, spawn=(0, 0), hp=4, pooled=True, pool="recruits")],
        pools=[B.PoolSpec("recruits", price=300, button=B.DEFAULT_HIRE_BUTTONS,
                          request_flag=8848)])
    fb.units["pest"].tree = B.Selector(
        B.Sequence(fb.hp_le("pest", 0), B.Do(B.Die())),
        B.Do(B.Wander((500, 500), radius=300)))
    for r in ("r0", "r1"):
        fb.units[r].tree = B.Selector(
            B.Sequence(fb.hp_le(r, 0), B.Do(B.Die())),
            B.Sequence(fb.active("pest"), fb.near(r, "pest", 250),
                       B.Do(B.SwingAt("pest"))),
            B.Do(B.HoldPost()))
    return fb


def test_pool_economy_compiles():
    fb = economy_field()
    cb = fb.compile()
    _verify_all(cb)
    assert fb.pool_flags["recruits"] == 8848           # explicit request flag wins
    ops = _ticker_ops(cb)
    assert ops.count(0xCF) == 2                        # RemoveGil at each SPAWN site
    assert "price 300 gil" in cb.report and "0x80001" in cb.report
    assert fb.compile().stable_hash() == economy_field().compile().stable_hash()


def test_poller_body_shape():
    """The rung-3 proven poller shape: poll stmt, blip (0xC8), RunScriptSync (0x14),
    post-menu debounce + Wait(1) cadence."""
    fb = economy_field()
    body = fb._poller_body(B.DEFAULT_HIRE_BUTTONS, 21)
    _verify_body(body)
    ops = [ins.op for ins in D.iter_code(body, 0, len(body))]
    assert 0xC8 in ops and 0x14 in ops and ops.count(0x22) == 2


def test_pool_spec_negatives():
    u = [B.UnitSpec("u", entry=2, spawn=(0, 0), pooled=True, pool="p")]
    with pytest.raises(B.BehaviorError, match="request_flag"):
        B.FieldBehavior(list(u), pools=[B.PoolSpec("p", button=1)])
    with pytest.raises(B.BehaviorError, match="blackboard band"):
        B.FieldBehavior(list(u), pools=[B.PoolSpec("p", request_flag=8900)])
    with pytest.raises(B.BehaviorError, match="no pooled unit"):
        B.FieldBehavior(list(u), pools=[B.PoolSpec("ghost")])
    with pytest.raises(B.BehaviorError, match="twice"):
        B.FieldBehavior(list(u), pools=[B.PoolSpec("p"), B.PoolSpec("p")])


# ------------------------------------------------------------------ waves + win/loss
def siege_field() -> B.FieldBehavior:
    fb = B.FieldBehavior(
        [B.UnitSpec("gate", entry=2, spawn=(0, 0), hp=6),
         B.UnitSpec("raider", entry=3, spawn=(900, 900), hp=4)],
        timer=180)
    fb.units["gate"].tree = B.Selector(
        B.Sequence(fb.flag("lost"), B.Do(B.Die())),
        B.Sequence(fb.hp_le("gate", 0), B.Do(B.Battle(35), raise_flags=("lost",))),
        B.Sequence(fb.time_below(1), B.Do(B.Announce(700), raise_flags=("won",))),
        B.Do(B.Hold((0, 0))),
    )
    fb.units["raider"].tree = B.Selector(
        B.Sequence(fb.hp_le("raider", 0), B.Do(B.Die())),
        B.Sequence(fb.active("gate"), fb.near("raider", "gate", 250),
                   B.Do(B.SwingAt("gate"))),
        B.Sequence(fb.time_below(170), B.Invert(fb.flag("lost")),
                   B.Do(B.WalkTo((0, 0)))),
        B.Do(B.Hold((900, 900))),
    )
    return fb


def test_timer_and_battle_compile():
    fb = siege_field()
    cb = fb.compile()
    _verify_all(cb)
    # the countdown triplet in Main_Init: ChangeTimerTime/ShowTimer/RunTimer
    mi_ops = [ins.op for ins in D.iter_code(cb.main_init, 0, len(cb.main_init))]
    assert 0x69 in mi_ops and 0x8D in mi_ops and 0x7D in mi_ops
    # the Battle body exists and carries the 0x2A + the one-shot latch set
    bodies = dict(cb.action_funcs["gate"])
    battle_bodies = [b for b in bodies.values()
                     if any(i.op == 0x2A for i in D.iter_code(b, 0, len(b)))]
    assert len(battle_bodies) == 1
    assert "gate.battled" in cb.report                 # the latch is allocated + visible
    assert fb.has_battle_actions()
    assert not guard_field().has_battle_actions()
    assert siege_field().compile().stable_hash() == cb.stable_hash()


def test_battle_scene_range_refused():
    with pytest.raises(B.BehaviorError, match="scene"):
        B.Battle(70000)
    with pytest.raises(B.BehaviorError, match="timer"):
        B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))], timer=0)
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    with pytest.raises(B.BehaviorError, match="time_below"):
        fb.time_below(999999)


# ------------------------------------------------------------------ rung-3 vocabulary
def test_flee_compiles_and_verifies():
    fb = B.FieldBehavior([B.UnitSpec("g", entry=2, spawn=(0, 0), hp=4)])
    fb.units["g"].tree = B.Selector(
        B.Sequence(fb.hp_le("g", 1),
                   B.Do(B.Flee(B.PLAYER, [(-2000, 900), (-600, 800)], speed=80))),
        B.Do(B.Flee(B.PLAYER, [(0, 0), (100, 100), (200, 200), (300, 300)])),
    )                                                  # flee doubles as the fallback
    cb = fb.compile()
    _verify_all(cb)
    assert "2=Flee" in cb.report


def test_flee_validation():
    with pytest.raises(B.BehaviorError, match="2..4 refuge"):
        B.Flee(B.PLAYER, [(0, 0)])
    with pytest.raises(B.BehaviorError, match="2..4 refuge"):
        B.Flee(B.PLAYER, [(i, i) for i in range(5)])
    with pytest.raises(B.BehaviorError, match="avoid_r"):
        B.Flee(B.PLAYER, [(0, 0), (1, 1)], avoid_r=0)
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Do(B.Flee("ghost", [(0, 0), (1, 1)]))
    with pytest.raises(B.BehaviorError, match="unknown unit"):
        fb.compile()


def test_wander_compiles_and_verifies():
    fb = B.FieldBehavior([B.UnitSpec("w", entry=2, spawn=(-1400, 300))])
    fb.units["w"].tree = B.Do(B.Wander((-1400, 300), radius=500, hold=120, speed=30))
    cb = fb.compile()
    _verify_all(cb)
    assert "w.wtx" in cb.report and "w.wtimer" in cb.report
    with pytest.raises(B.BehaviorError, match="radius"):
        B.Wander((0, 0), radius=0)
    with pytest.raises(B.BehaviorError, match="hold"):
        B.Wander((0, 0), hold=300)


def test_per_action_speed_and_nudge():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0), walk_speed=40)])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.near("u", B.PLAYER, 500), B.Do(B.Chase(B.PLAYER, speed=70))),
        B.Do(B.Hold((0, 0))),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert len(cb.action_funcs["u"]) == 1              # the nudge body (no dispatches)
    assert cb.action_funcs["u"][0][0] == B.FIRST_ACTION_TAG
    assert "spd@" in cb.report
    bad = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    bad.units["u"].tree = B.Do(B.Hold((0, 0), speed=0))
    with pytest.raises(B.BehaviorError, match="speed must be 1..255"):
        bad.compile()
    with pytest.raises(B.BehaviorError, match="walk_speed"):
        B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0), walk_speed=0)])


def test_alternator():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    shift = fb.alternator("shift", 300)
    assert isinstance(shift, B.Cond)
    with pytest.raises(B.BehaviorError, match="already registered"):
        fb.alternator("shift", 400)
    with pytest.raises(B.BehaviorError, match="1..30000"):
        fb.alternator("other", 0)
    fb.units["u"].tree = B.Selector(
        B.Sequence(shift, B.Do(B.Patrol([(0, 0), (100, 0)]))),
        B.Do(B.Patrol([(200, 200), (300, 200)])),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert "shift.clock" in cb.report


def test_do_raise_flags():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.near("u", B.PLAYER, 400),
                   B.Do(B.Hold((0, 0)), raise_flags="alarm")),   # str coerces to tuple
        B.Do(B.Hold((0, 0)), clear_flags=("alarm",)),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert "alarm" in cb.report                        # allocated + visible in ~ Flags


def test_march_compiles_and_verifies():
    """March = Patrol that stops: multi-leg one-way routes as one feed (minted by
    the BTRAID showcase — straight WalkTo lines wedge in concave walkmesh notches)."""
    fb = B.FieldBehavior([B.UnitSpec("b", entry=2, spawn=(0, -1600), hp=3)])
    fb.units["b"].tree = B.Selector(
        B.Sequence(fb.hp_le("b", 0), B.Do(B.Die())),
        B.Sequence(fb.flag("go"),
                   B.Do(B.March([(800, -850), (1100, 1150), (-1400, 900)],
                                arrive_r=250, speed=55))),
        B.Do(B.Hold((0, -1600))),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert "b.wp" in cb.report
    with pytest.raises(B.BehaviorError, match="2..8 waypoints"):
        B.March([(0, 0)])
    fb2 = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
    fb2.units["u"].tree = B.Do(B.March([(0, 0), (500, 0)]))   # fallback-eligible
    _verify_all(fb2.compile())


def test_any_of_and_shared_announce_dedupe():
    """The watcher pattern: ONE Announce object selected from two notice branches
    must compile to ONE dispatch body (one action id), and any_of ORs Conds."""
    fb = B.FieldBehavior([
        B.UnitSpec("w", entry=2, spawn=(0, 0)),
        B.UnitSpec("b0", entry=3, spawn=(500, 0), hp=2),
        B.UnitSpec("b1", entry=4, spawn=(0, 500), hp=2),
    ])
    for b in ("b0", "b1"):
        fb.units[b].tree = B.Selector(
            B.Sequence(fb.hp_le(b, 0), B.Do(B.Die())), B.Do(B.Hold((0, 0))))
    cry = B.Announce(7)
    fb.units["w"].tree = B.Selector(
        B.Sequence(fb.active("b0"), fb.near("w", "b0", 600),
                   B.Do(cry, raise_flags="alarm")),
        B.Sequence(fb.active("b1"), fb.near("w", "b1", 600),
                   B.Do(cry, raise_flags="alarm")),
        B.Sequence(fb.any_of(fb.flag("alarm"), fb.near("w", B.PLAYER, 100)),
                   B.Do(B.WalkTo((900, 900), speed=70))),
        B.Do(B.Hold((0, 0))),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert len(cb.action_funcs["w"]) == 2              # ONE Announce body + the nudge
    assert cb.report.count("1=Announce") == 1
    with pytest.raises(B.BehaviorError, match="2\\+ Conds"):
        fb.any_of(fb.flag("alarm"))


def test_showcase_shaped_integration():
    """All rung-3 vocabulary composed in one field — the BTRAID shape in miniature."""
    fb = B.FieldBehavior([
        B.UnitSpec("guard", entry=2, spawn=(0, 0), hp=5, walk_speed=40),
        B.UnitSpec("bandit", entry=3, spawn=(900, 900), hp=4),
        B.UnitSpec("civ", entry=4, spawn=(400, 400)),
    ])
    shift = fb.alternator("shift", 300)
    fb.units["guard"].tree = B.Selector(
        B.Sequence(fb.hp_le("guard", 0), B.Do(B.Die())),
        B.Sequence(fb.hp_le("guard", 1),
                   B.Do(B.Flee("bandit", [(-500, -500), (0, -900)], speed=75))),
        B.Sequence(fb.flag("alarm"), fb.active("bandit"),
                   B.Selector(
                       B.Sequence(fb.near("guard", "bandit", 300),
                                  B.Do(B.SwingAt("bandit"))),
                       B.Do(B.Chase("bandit", speed=65)))),
        B.Sequence(shift, B.Do(B.Patrol([(0, 0), (400, 0)]))),
        B.Do(B.Patrol([(0, 400), (400, 400)])),
    )
    fb.units["bandit"].tree = B.Selector(
        B.Sequence(fb.hp_le("bandit", 0), B.Do(B.Die())),
        B.Sequence(fb.near("bandit", "guard", 300), B.Do(B.SwingAt("guard")),
                   ),
        B.Do(B.WalkTo((0, 0), speed=55)),
    )
    fb.units["civ"].tree = B.Selector(
        B.Sequence(fb.flag("alarm"),
                   B.Do(B.Flee("bandit", [(-800, 0), (800, 0)], speed=80))),
        B.Do(B.Wander((400, 400), radius=400, hold=90, speed=30)),
    )
    # the watcher pattern: raising the alarm rides any Do — here bandit's approach is
    # noticed by the guard tree via raise_flags on a chase
    fb.units["guard"].tree.children[2].children[2].children[1].raise_flags = ("alarm",)
    cb = fb.compile()
    _verify_all(cb)
    h1, h2 = cb.stable_hash(), fb.compile().stable_hash()
    assert h1 == h2


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
