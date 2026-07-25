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
    # the EDGE-LATCHED request (the siege round-1 clobber fix): selection sets breq;
    # the dispatch fires on breq/!latch/run==0 independent of the CURRENT selection
    assert "gate.breq" in cb.report
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


# ------------------------------------------------------------------ data tables (0xD3)
def _expr_stmts(body: bytes) -> list:
    """Every 0x05 expression statement in the body, pretty-printed."""
    out = []
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op == 0x05:
            txt, _ = D.pretty_expr(body, ins.off + 1)
            out.append(txt)
    return out


def table_field() -> B.FieldBehavior:
    """The rung-5 reference shape: a schedule-clocked wave counter + a kill counter
    bumped by Die(count=) + counter/table conds (one with a COMPUTED index)."""
    fb = B.FieldBehavior(
        [B.UnitSpec("gate", entry=2, spawn=(0, 0), hp=6),
         B.UnitSpec("fang", entry=3, spawn=(900, 900), hp=3)],
        timer=120,
        tables=[B.TableSpec("sched", (100, 80, 0)),
                B.TableSpec("cost", (300, 500), id=2000)],
        counters=("wave", "kills"))
    fb.schedule("wave", "sched")
    fb.units["gate"].tree = B.Selector(
        B.Sequence(fb.counter_ge("kills", 1), B.Do(B.Announce(700))),
        B.Sequence(fb.counter_eq("wave", 1), fb.table_ge("sched", "wave", 1),
                   B.Do(B.Announce(701))),
        B.Do(B.Hold((0, 0))),
    )
    fb.units["fang"].tree = B.Selector(
        B.Sequence(fb.hp_le("fang", 0), B.Do(B.Die(count="kills"))),
        B.Do(B.Hold((900, 900))),
    )
    return fb


def test_tables_allocate_seed_and_verify():
    fb = table_field()
    cb = fb.compile()
    _verify_all(cb)
    # allocation: declared tables from TABLE_ID_BASE in order, an explicit id wins,
    # the internal counter table takes the next free auto slot
    assert fb.tables["sched"][0] == B.TABLE_ID_BASE
    assert fb.tables["cost"][0] == 2000
    assert fb._ctr_tid == B.TABLE_ID_BASE + 1
    # THE SEED: size<-0 wipes the save's copy, size<-n zero-fills fresh, then only
    # NON-zero cells are written (sched[2] == 0 needs no statement)
    seeds = _expr_stmts(cb.main_init)
    base = B.TABLE_ID_BASE
    assert f"{{const({base}) B_VECTOR_SIZE const(0) B_LET B_EXPR_END}}" in seeds
    assert f"{{const({base}) B_VECTOR_SIZE const(3) B_LET B_EXPR_END}}" in seeds
    assert f"{{const({base}) const(0) B_VECTOR const(100) B_LET B_EXPR_END}}" in seeds
    assert f"{{const({base}) const(1) B_VECTOR const(80) B_LET B_EXPR_END}}" in seeds
    assert not any(f"const({base}) const(2) B_VECTOR" in s for s in seeds)
    # the counters table seeds in EXACTLY two statements (all-zero by definition)
    ctr = fb._ctr_tid
    ctr_seeds = [s for s in seeds if f"const({ctr})" in s]
    assert ctr_seeds == [f"{{const({ctr}) B_VECTOR_SIZE const(0) B_LET B_EXPR_END}}",
                         f"{{const({ctr}) B_VECTOR_SIZE const(2) B_LET B_EXPR_END}}"]
    # THE SCHEDULE CLOCK in the ticker: the computed-index read (sched indexed BY the
    # wave cell — nested VECTOR, the lane's whole point) + the self-increment
    ticks = _expr_stmts(cb.ticker_body)
    assert (f"{{B_SYSVAR[17] const({base}) const({ctr}) const(0) B_VECTOR B_VECTOR "
            f"B_LT B_EXPR_END}}") in ticks
    assert (f"{{const({ctr}) const(0) B_VECTOR const({ctr}) const(0) B_VECTOR "
            f"const(1) B_PLUS B_LET B_EXPR_END}}") in ticks
    # Die(count=): the fang's Die body bumps the kills cell (cell 1) exactly once
    die_bodies = [b for _t, b in cb.action_funcs["fang"]]
    bump = (f"{{const({ctr}) const(1) B_VECTOR const({ctr}) const(1) B_VECTOR "
            f"const(1) B_PLUS B_LET B_EXPR_END}}")
    assert any(bump in _expr_stmts(b) for b in die_bodies)
    # report + determinism
    assert "sched: id 1000" in cb.report and "cost: id 2000" in cb.report
    assert "wave=cell 0" in cb.report and "schedule: wave += 1" in cb.report
    assert table_field().compile().stable_hash() == cb.stable_hash()


def test_table_negatives():
    u = [B.UnitSpec("u", entry=2, spawn=(0, 0))]
    with pytest.raises(B.BehaviorError, match="values"):
        B.FieldBehavior(list(u), tables=[B.TableSpec("t", ())])
    with pytest.raises(B.BehaviorError, match="26-bit"):
        B.FieldBehavior(list(u), tables=[B.TableSpec("t", (1 << 26,))])
    with pytest.raises(B.BehaviorError, match="duplicate table"):
        B.FieldBehavior(list(u), tables=[B.TableSpec("t", (1,)),
                                         B.TableSpec("t", (2,))])
    with pytest.raises(B.BehaviorError, match="used twice"):
        B.FieldBehavior(list(u), tables=[B.TableSpec("a", (1,), id=5),
                                         B.TableSpec("b", (1,), id=5)])
    with pytest.raises(B.BehaviorError, match="collides"):
        B.FieldBehavior(list(u), tables=[B.TableSpec("w", (1,))], counters=("w",))
    with pytest.raises(B.BehaviorError, match="must be"):
        B.FieldBehavior(list(u), counters=("bad name",))
    fb = B.FieldBehavior(list(u), tables=[B.TableSpec("t", (1, 2))], counters=("c",))
    with pytest.raises(B.BehaviorError, match="unknown counter"):
        fb.counter_ge("nope", 1)
    with pytest.raises(B.BehaviorError, match="unknown table"):
        fb.table_ge("nope", 0, 1)
    with pytest.raises(B.BehaviorError, match="out of range"):
        fb.table_ge("t", 5, 1)
    with pytest.raises(B.BehaviorError, match="timer"):
        fb.schedule("c", "t")                        # no timer= on the field
    fb2 = B.FieldBehavior(list(u), timer=60,
                          tables=[B.TableSpec("t", (1,))], counters=("c",))
    fb2.schedule("c", "t")
    with pytest.raises(B.BehaviorError, match="already has a schedule"):
        fb2.schedule("c", "t")


def test_die_count_unknown_counter_refused():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0), hp=1)])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.hp_le("u", 0), B.Do(B.Die(count="ghosts"))),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="unknown counter"):
        fb.compile()


def test_cnum_literal_widths():
    # const() is a SIGNED Int16 at runtime — anything outside rides const4()
    assert B._cnum(32767) == "const(32767)"
    assert B._cnum(-32768) == "const(-32768)"
    assert B._cnum(32768) == "const4(32768)"
    assert B._cnum(40000) == "const4(40000)"
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))],
                         tables=[B.TableSpec("big", (100000,), id=50000)])
    fb.units["u"].tree = B.Do(B.Hold((0, 0)))
    seeds = _expr_stmts(fb.compile().main_init)
    assert "{const4(50000) const(0) B_VECTOR const4(100000) B_LET B_EXPR_END}" in seeds


# ------------------------------------------------------- the EVENT Once (starvation)
def herald_field() -> B.FieldBehavior:
    """BTTABLE round 2's exact defect shape: a Once+Announce on a MONOTONIC cond
    (a kill tally) ABOVE another Once+Announce — sticky semantics held the top
    branch selected forever and starved the lower line."""
    fb = B.FieldBehavior([B.UnitSpec("herald", entry=2, spawn=(0, 0))],
                         counters=("kills", "wave"))
    fb.units["herald"].tree = B.Selector(
        B.Once("won", B.Sequence(fb.counter_ge("kills", 2), B.Do(B.Announce(700)))),
        B.Once("w3", B.Sequence(fb.counter_eq("wave", 3), B.Do(B.Announce(701)))),
        B.Do(B.Hold((0, 0))),
    )
    return fb


def test_once_announce_is_an_event_not_an_engagement():
    fb = herald_field()
    cb = fb.compile()
    _verify_all(cb)
    # NO engagement flags — the event form has no sticky machinery to hold the
    # selection open on a never-falsifying condition
    assert "onceeng" not in cb.report
    # each announce got a request flag + rides the one-shot lane
    assert "herald.areq1" in cb.report and "herald.areq2" in cb.report
    req1 = fb.bb.flag("herald.areq1")
    latch1 = fb.bb.flag("herald.once.won")
    ticks = _expr_stmts(cb.ticker_body)
    # the Once gate is latch-only, and selection edge-latches the request
    assert f"{{Global.Bit[{latch1}] B_EXPR_END}}" in ticks
    assert f"{{Global.Bit[{req1}] const(1) B_LET B_EXPR_END}}" in ticks
    # the lane checks req -> latch -> run==0 (the Battle clobber shape)
    assert f"{{Global.Bit[{req1}] B_EXPR_END}}" in ticks
    # the dispatch body: latch FIRST, window, release — and NO idle loop (no wait op)
    bodies = [b for _t, b in cb.action_funcs["herald"]]
    won_body = next(b for b in bodies
                    if f"{{Global.Bit[{latch1}] const(1) B_LET B_EXPR_END}}"
                    in _expr_stmts(b))
    ops = [i.op for i in D.iter_code(won_body, 0, len(won_body))]
    assert 0x22 not in ops                       # no Wait (0x22) — fire and return
    assert _expr_stmts(won_body)[0] == f"{{Global.Bit[{latch1}] const(1) B_LET B_EXPR_END}}"
    # the CONTROL: a bare (un-Onced) Announce keeps its idle loop — Wait present
    fb2 = B.FieldBehavior([B.UnitSpec("g", entry=2, spawn=(0, 0))])
    fb2.units["g"].tree = B.Selector(
        B.Sequence(fb2.flag("f1"), B.Do(B.Announce(700))),
        B.Do(B.Hold((0, 0))),
    )
    bare = [b for _t, b in fb2.compile().action_funcs["g"]][0]
    assert 0x22 in [i.op for i in D.iter_code(bare, 0, len(bare))]
    # determinism
    assert herald_field().compile().stable_hash() == cb.stable_hash()


def test_once_over_a_feed_stays_sticky():
    fb = B.FieldBehavior([B.UnitSpec("g", entry=2, spawn=(0, 0))])
    fb.units["g"].tree = B.Selector(
        B.Once("meet", B.Sequence(fb.near("g", B.PLAYER, 400), B.Do(B.Chase(B.PLAYER)))),
        B.Do(B.Hold((0, 0))),
    )
    cb = fb.compile()
    _verify_all(cb)
    assert "g.onceeng.meet" in cb.report         # the engagement flag survives
    assert "areq" not in cb.report


def test_once_announce_shared_with_bare_site_refused():
    fb = B.FieldBehavior([B.UnitSpec("g", entry=2, spawn=(0, 0))])
    a = B.Announce(700)
    fb.units["g"].tree = B.Selector(
        B.Once("x", B.Sequence(fb.flag("f1"), B.Do(a))),
        B.Sequence(fb.flag("f2"), B.Do(a)),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="shared between"):
        fb.compile()


def test_once_announce_shared_between_two_onces_refused():
    fb = B.FieldBehavior([B.UnitSpec("g", entry=2, spawn=(0, 0))])
    a = B.Announce(700)
    fb.units["g"].tree = B.Selector(
        B.Once("x", B.Sequence(fb.flag("f1"), B.Do(a))),
        B.Once("y", B.Sequence(fb.flag("f2"), B.Do(a))),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="two [Oo]nce"):
        fb.compile()


# ------------------------------------------------------------------ award + hireable
def test_award_compiles_hireable_publishes():
    fb = B.FieldBehavior(
        [B.UnitSpec("base", 2, spawn=(2000, -100), hp=20),
         B.UnitSpec("s0", 3, spawn=(0, 0), hp=4, pooled=True, pool="soldiers"),
         B.UnitSpec("s1", 4, spawn=(0, 0), hp=4, pooled=True, pool="soldiers")],
        timer=240, pools=[B.PoolSpec("soldiers", price=300)])
    fb.units["base"].tree = B.Selector(
        B.Once("paid", B.Sequence(fb.time_below(1), B.Do(B.Award(gil=2000, item=236)))),
        B.Do(B.Hold((2000, -100))),
    )
    for s in ("s0", "s1"):
        fb.units[s].tree = B.Selector(
            B.Sequence(fb.hp_le(s, 0), B.Do(B.Die())), B.Do(B.HoldPost()))
    cb = fb.compile()
    _verify_all(cb)
    # the Award body: latch FIRST, AddGil (0xCE) + AddItem (0x48), no idle Wait
    award = next(b for _t, b in cb.action_funcs["base"]
                 if any(i.op == 0xCE for i in D.iter_code(b, 0, len(b))))
    ops = [i.op for i in D.iter_code(award, 0, len(award))]
    assert 0x48 in ops and 0x22 not in ops
    latch = fb.bb.flag("base.once.paid")
    assert _expr_stmts(award)[0] == f"{{Global.Bit[{latch}] const(1) B_LET B_EXPR_END}}"
    # the published hireable flag: preset 1 in Main_Init, refreshed in the ticker as
    # (gil >= price) AND NOT (all spawned)
    h = fb.pool_hireable["soldiers"]
    assert f"{{Global.Bit[{h}] const(1) B_LET B_EXPR_END}}" in _expr_stmts(cb.main_init)
    s0 = fb.bb.flag("s0.spawned")
    s1 = fb.bb.flag("s1.spawned")
    assert (f"{{Global.Bit[{h}] B_SYSVAR[6] const(300) B_GE Global.Bit[{s0}] "
            f"Global.Bit[{s1}] B_ANDAND B_NOT B_ANDAND B_LET B_EXPR_END}}"
            ) in _expr_stmts(cb.ticker_body)
    assert f"hireable flag {h}" in cb.report


def test_award_negatives():
    with pytest.raises(B.BehaviorError, match="gil"):
        B.Award(gil=-1)
    with pytest.raises(B.BehaviorError, match="needs gil"):
        B.Award()
    with pytest.raises(B.BehaviorError, match="count"):
        B.Award(gil=1, count=0)
    fb = B.FieldBehavior([B.UnitSpec("u", 2, spawn=(0, 0))])
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.flag("f"), B.Do(B.Award(gil=100))),
        B.Do(B.Hold((0, 0))),
    )
    with pytest.raises(B.BehaviorError, match="wrapped in Once"):
        fb.compile()


def test_hold_ground_pin():
    """The PIN: a dispatch action whose selection halts the walk and whose body
    idles while selected — no window, no writes, resumes on deselect."""
    fb = B.FieldBehavior([B.UnitSpec("r", 2, spawn=(0, 0), hp=3)])
    fb.units["r"].tree = B.Selector(
        B.Sequence(fb.near("r", B.PLAYER, 240), B.Do(B.HoldGround())),
        B.Do(B.Hold((500, 500))),
    )
    cb = fb.compile()
    _verify_all(cb)
    bodies = [b for _t, b in cb.action_funcs["r"]]
    pin = bodies[0]                                   # first dispatch tag
    ops = [i.op for i in D.iter_code(pin, 0, len(pin))]
    assert 0x22 in ops and 0x20 not in ops            # idles; opens no window
    with pytest.raises(B.BehaviorError, match="fallback"):
        bad = B.FieldBehavior([B.UnitSpec("u", 2, spawn=(0, 0))])
        bad.units["u"].tree = B.Do(B.HoldGround())    # not a static feed
        bad.compile()


# ------------------------------------------------------------------ byte histogram
def test_size_histogram_accounts_every_ticker_byte():
    """The budget sheet: segment sizes come from the pre-relaxation measure and
    must tile the ticker exactly (markers are zero-width, so with no islands the
    content size IS the emitted size)."""
    cb = guard_field().compile()
    s = cb.sizes
    assert s is not None
    assert sum(n for _nm, n in s["ticker_segments"]) == s["ticker_content"]
    assert s["ticker_content"] == len(cb.ticker_body)  # small program: no islands
    names = [nm for nm, _n in s["ticker_segments"]]
    assert names[0] == "head" and "mirrors" in names and "tail" in names
    assert "unit guard" in names and "unit beast" in names
    assert s["duty"] == {n: len(b) for n, b in cb.duty_bodies.items()}
    for u, fns in s["dispatch"].items():
        assert sum(n for _t, _k, n in fns) == sum(len(b) for _t, b in
                                                  cb.action_funcs[u])
    txt = cb.size_report()
    assert "byte histogram" in txt and "guard:" in txt and "nudge" in txt


def test_size_histogram_covers_pool_segments():
    cb = economy_field().compile()
    names = [nm for nm, _n in cb.sizes["ticker_segments"]]
    assert "pool recruits" in names and "hireable" in names
    assert sum(n for _nm, n in cb.sizes["ticker_segments"]) \
        == cb.sizes["ticker_content"]


def test_size_histogram_markers_do_not_change_bytes():
    """Golden stability for the markers themselves: the report path must not
    perturb compilation (determinism test covers run-to-run; this pins that the
    ticker walks clean and starts with the staged-latch stmt, as always)."""
    cb = guard_field().compile()
    assert cb.ticker_body[0] == 0x05                   # the staged-latch stmt


# ------------------------------------------------------------------ swarm stress
def test_swarm_stress_forty_units_relaxes_and_accounts():
    """The offline stress ceiling probe: 40 concurrent units (the in-game proven
    swarm scale) with mutual-swing branches — the ticker sails past the old
    ±32K jump wall, every body still walks clean, the histogram still tiles the
    content bytes, and compilation stays deterministic.

    MEASURED WALL pinned here: at 40 units the blackboard byte band (820 bytes
    of gEventGlobal scratch) holds ~6 swing pairs per unit — a 7th exhausts it
    (~14B unit kit + ~1B per swing timer). The band is physical (Byte[2048]
    minus the reserved low bytes), so v1's unrolled-pair architecture tops out
    near this scale on THREE independent walls: band, ticker content, file."""
    def build():
        units = [B.UnitSpec(f"w{i}", entry=2 + i, spawn=(i * 40, 0), hp=4)
                 for i in range(40)]
        fb = B.FieldBehavior(units)
        for i, u in enumerate(units):
            foes = [f"w{j}" for j in range(40) if j != i][:6]
            branches = [B.Sequence(fb.hp_le(u.name, 0), B.Do(B.Die()))]
            for o in foes:
                branches.append(B.Sequence(fb.active(o), fb.near(u.name, o, 220),
                                           B.Do(B.SwingAt(o))))
            branches.append(B.Do(B.Hold((i * 40, 0))))
            fb.units[u.name].tree = B.Selector(*branches)
        return fb

    cb = build().compile()
    _verify_all(cb)
    assert len(cb.ticker_body) > 32767                 # islands are live in here
    s = cb.sizes
    assert sum(n for _nm, n in s["ticker_segments"]) == s["ticker_content"]
    assert len(cb.ticker_body) >= s["ticker_content"]  # island overhead >= 0
    assert build().compile().stable_hash() == cb.stable_hash()


# ------------------------------------------------------------------ the vector loop
def scan_field() -> B.FieldBehavior:
    fb = B.FieldBehavior(
        [B.UnitSpec(f"p{i}", entry=2 + i, spawn=(i * 100, 0)) for i in range(3)],
        counters=("at_shrine",))
    for i in range(3):
        fb.units[f"p{i}"].tree = B.Do(B.Hold((i * 100, 0)))
    fb.scan("shrine", ["p0", "p1", "p2"], (500, 0), 300, "at_shrine",
            flags="near_shrine")
    return fb


def test_scan_compiles_and_verifies():
    fb = scan_field()
    cb = fb.compile()
    _verify_all(cb)
    # the loop is a BACKWARD conditional jump in the ticker — the new shape
    back_ifs = []
    for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body)):
        if ins.op == 0x03:
            t = D.jump_target(ins)
            if t is not None and t < ins.off:
                back_ifs.append(ins.off)
    assert back_ifs, "the scan loop must close with a backward JMP_IF"
    # registered tables: px/pz internal + the user-named flags table
    assert "scan.shrine.px" in fb.tables and "near_shrine" in fb.tables
    assert "scan shrine" in cb.report and "at_shrine" in cb.report
    # histogram: the scan has its own segment with real bytes in it
    segs = dict(cb.sizes["ticker_segments"])
    assert segs.get("scan shrine", 0) > 100
    assert scan_field().compile().stable_hash() == cb.stable_hash()


def test_scan_seeds_tables_in_main_init():
    cb = scan_field().compile()
    # three zero tables -> exactly two size statements each, no cell writes;
    # cheap structural proxy: main_init walks clean and mentions nothing odd
    _verify_body(cb.main_init)
    # the seed wipes then grows every scan table (0xD3 appears in main_init)
    assert bytes([0xD3]) in bytes(cb.main_init)


def test_scan_negatives():
    fb = scan_field()
    with pytest.raises(B.BehaviorError, match="already registered"):
        fb.scan("shrine", ["p0"], (0, 0), 100, "at_shrine")
    with pytest.raises(B.BehaviorError, match="unknown unit"):
        fb.scan("ghost", ["nobody"], (0, 0), 100, "at_shrine")
    with pytest.raises(B.BehaviorError, match="unknown counter"):
        fb.scan("badctr", ["p0"], (0, 0), 100, "missing")
    with pytest.raises(B.BehaviorError, match="radius"):
        fb.scan("badr", ["p0"], (0, 0), 0, "at_shrine")
    with pytest.raises(B.BehaviorError, match="duplicate"):
        fb.scan("dup", ["p0", "p0"], (0, 0), 100, "at_shrine")
    with pytest.raises(B.BehaviorError, match="table cap"):
        fb2 = B.FieldBehavior(
            [B.UnitSpec("u", entry=2, spawn=(0, 0))], counters=("c",))
        fb2.units["u"].tree = B.Do(B.Hold((0, 0)))
        fb2.scan("big", ["u"] * 65, (0, 0), 100, "c")


def test_scan_table_ids_are_deterministic():
    """Scan tables allocate AFTER the ctor's autos + the counter table, in
    declaration order — the allocation contract extends to scans."""
    fb = scan_field()
    ctr = fb._ctr_tid
    px, _ = fb.tables["scan.shrine.px"]
    pz, _ = fb.tables["scan.shrine.pz"]
    fl, _ = fb.tables["near_shrine"]
    assert (px, pz, fl) == (ctr + 1, ctr + 2, ctr + 3)


# ------------------------------------------------------------------ the group loop
def group_brawl_field(n=3):
    """Two rosters engaging each other through the group loop — die/engage/hold."""
    units = ([B.UnitSpec(f"a{i}", entry=2 + i, spawn=(0, i * 300), hp=3)
              for i in range(n)]
             + [B.UnitSpec(f"b{i}", entry=2 + n + i, spawn=(900, i * 300), hp=3)
                for i in range(n)])
    fb = B.FieldBehavior(units, counters=("fallen",))
    fb.group("reds", [f"a{i}" for i in range(n)])
    fb.group("blues", [f"b{i}" for i in range(n)])
    for i in range(n):
        for nm, foe in ((f"a{i}", "blues"), (f"b{i}", "reds")):
            fb.units[nm].tree = B.Selector(
                B.Sequence(fb.hp_le(nm, 0), B.Do(B.Die(count="fallen"))),
                fb.engage_node(nm, B.Engage(foe, radius=1500, contact=170)),
                B.Do(B.Hold(fb.units[nm].spawn)),
            )
    return fb


def test_group_loop_compiles_and_verifies():
    fb = group_brawl_field()
    cb = fb.compile()
    _verify_all(cb)
    # ONE swing body per unit regardless of roster size: Die + _GroupSwing + nudge
    assert all(len(cb.action_funcs[u]) == 3 for u in fb.units)
    # the hp conds route to roster cells, not Global bytes
    assert "B_VECTOR" in fb.hp_le("a0", 0).text
    assert "B_VECTOR" in fb.hp_gt("b2", 1).text
    assert "group reds" in cb.report and "engage a0 -> group 'blues'" in cb.report
    # acquire loops close with backward conditional jumps (one per engage unit)
    back_ifs = 0
    for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body)):
        if ins.op == 0x03:
            t = D.jump_target(ins)
            if t is not None and t < ins.off:
                back_ifs += 1
    assert back_ifs >= len(fb.units)
    assert group_brawl_field().compile().stable_hash() == cb.stable_hash()


def test_group_loop_beats_unrolled_pairs_on_bytes():
    """THE ECONOMY PIN: at 6v6 the group lane must cost less than HALF the
    unrolled pair machinery (ticker + dispatch bodies together) — the reason
    this rung exists. If this ratio regresses, the three-walls win is gone."""
    n = 6
    grouped = group_brawl_field(n).compile()

    units = ([B.UnitSpec(f"a{i}", entry=2 + i, spawn=(0, i * 300), hp=3)
              for i in range(n)]
             + [B.UnitSpec(f"b{i}", entry=2 + n + i, spawn=(900, i * 300), hp=3)
                for i in range(n)])
    fb = B.FieldBehavior(units, counters=("fallen",))
    for i in range(n):
        for nm, foes in ((f"a{i}", [f"b{j}" for j in range(n)]),
                         (f"b{i}", [f"a{j}" for j in range(n)])):
            branches = [B.Sequence(fb.hp_le(nm, 0), B.Do(B.Die(count="fallen")))]
            for o in foes:
                branches.append(B.Sequence(fb.active(o), fb.near(nm, o, 170),
                                           B.Do(B.SwingAt(o))))
                branches.append(B.Sequence(fb.active(o), fb.near(nm, o, 1500),
                                           B.Do(B.Chase(o, standoff=170))))
            branches.append(B.Do(B.Hold(fb.units[nm].spawn)))
            fb.units[nm].tree = B.Selector(*branches)
    unrolled = fb.compile()

    def cost(cb):
        return (len(cb.ticker_body)
                + sum(len(b) for fns in cb.action_funcs.values() for _t, b in fns))

    assert cost(grouped) < cost(unrolled) / 2, \
        f"group {cost(grouped)}B vs unrolled {cost(unrolled)}B"


def test_group_negatives():
    fb = group_brawl_field()
    with pytest.raises(B.BehaviorError, match="OWN group"):
        fb.engage_node("a0", B.Engage("reds"))
    with pytest.raises(B.BehaviorError, match="already has an engage"):
        fb.engage_node("a0", B.Engage("blues"))
    with pytest.raises(B.BehaviorError, match="unknown group"):
        fb.engage_node("a1", B.Engage("ghosts"))
    with pytest.raises(B.BehaviorError, match="already registered"):
        fb.group("reds", ["a0"])
    with pytest.raises(B.BehaviorError, match="already in group"):
        fb.group("more", ["a0"])
    with pytest.raises(B.BehaviorError, match="no hp"):
        fb2 = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))])
        fb2.group("g", ["u"])
    with pytest.raises(B.BehaviorError, match="contact"):
        B.Engage("g", radius=100, contact=100)
    with pytest.raises(B.BehaviorError, match="fallback"):
        fb3 = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0), hp=2),
                               B.UnitSpec("v", entry=3, spawn=(9, 9), hp=2)])
        fb3.group("vs", ["v"])
        fb3.units["v"].tree = B.Do(B.Hold((9, 9)))
        fb3.units["u"].tree = fb3.engage_node("u", B.Engage("vs"))
        fb3.compile()


def test_classic_swing_at_grouped_target_damages_the_cell():
    """A CLASSIC SwingAt whose target is a roster member must decrement the
    member's hp CELL (its only home), not a dead Global byte."""
    fb = B.FieldBehavior([B.UnitSpec("raider", entry=2, spawn=(0, 0), hp=5),
                          B.UnitSpec("m", entry=3, spawn=(100, 0), hp=4)],
                         counters=("fallen",))
    fb.group("guards", ["m"])
    fb.units["raider"].tree = B.Selector(
        B.Sequence(fb.active("m"), fb.near("raider", "m", 200),
                   B.Do(B.SwingAt("m"))),
        B.Do(B.Hold((0, 0))),
    )
    fb.units["m"].tree = B.Selector(
        B.Sequence(fb.hp_le("m", 0), B.Do(B.Die(count="fallen"))),
        B.Do(B.Hold((100, 0))),
    )
    cb = fb.compile()
    _verify_all(cb)
    swing = cb.action_funcs["raider"][0][1]
    assert bytes([0xD3]) in swing      # the damage write reaches into the table


# ------------------------------------------------------------------ scan v2 forms
def test_group_scan_alive_only_headcount():
    """The team-wipe primitive: a boxless group scan counting act && hp>0."""
    fb = group_brawl_field()
    fb._counters["reds_alive"] = len(fb._counters)
    sc = fb.scan("reds_up", group="reds", count="reds_alive", alive_only=True)
    assert sc.point is None and sc.flags is None and sc.group == "reds"
    cb = fb.compile()
    _verify_all(cb)
    assert "scan reds_up" in cb.report and "ALIVE-ONLY" in cb.report \
        and "no box (headcount)" in cb.report
    # no own tables: the scan loops the GROUP's px/pz (no scan.px table)
    assert "scan.reds_up.px" not in fb.tables


def test_group_scan_with_box_and_flags():
    fb = group_brawl_field()
    fb._counters["near_gate"] = len(fb._counters)
    fb.scan("gatewatch", group="blues", point=(900, 0), radius=400,
            count="near_gate", flags="blues_near_gate", alive_only=True)
    cb = fb.compile()
    _verify_all(cb)
    assert "blues_near_gate" in fb.tables


def test_scan_form_negatives():
    fb = group_brawl_field()
    fb._counters["c2"] = len(fb._counters)
    with pytest.raises(B.BehaviorError, match="exactly one of"):
        fb.scan("s1", units=["a0"], group="reds", count="c2")
    with pytest.raises(B.BehaviorError, match="alive_only needs group"):
        fb.scan("s2", units=["a0"], point=(0, 0), radius=100, count="c2",
                alive_only=True)
    with pytest.raises(B.BehaviorError, match="flags need a point"):
        fb.scan("s3", group="reds", count="c2", flags="f")
    with pytest.raises(B.BehaviorError, match="units form needs point"):
        fb.scan("s4", units=["a0"], count="c2")
    with pytest.raises(B.BehaviorError, match="come together"):
        fb.scan("s5", group="reds", point=(0, 0), count="c2")


# ------------------------------------------------------------------ nearest engage
def test_nearest_engage_compiles_and_shares_scratch():
    n = 3
    units = ([B.UnitSpec(f"a{i}", entry=2 + i, spawn=(0, i * 300), hp=3)
              for i in range(n)]
             + [B.UnitSpec(f"b{i}", entry=2 + n + i, spawn=(900, i * 300), hp=3)
                for i in range(n)])
    fb = B.FieldBehavior(units, counters=("fallen",))
    fb.group("reds", [f"a{i}" for i in range(n)])
    fb.group("blues", [f"b{i}" for i in range(n)])
    for i in range(n):
        for nm, foe in ((f"a{i}", "blues"), (f"b{i}", "reds")):
            fb.units[nm].tree = B.Selector(
                B.Sequence(fb.hp_le(nm, 0), B.Do(B.Die(count="fallen"))),
                fb.engage_node(nm, B.Engage(foe, radius=1500, contact=170,
                                            nearest=True)),
                B.Do(B.Hold(fb.units[nm].spawn)),
            )
    cb = fb.compile()
    _verify_all(cb)
    assert "NEAREST" in cb.report
    # ONE shared scratch set regardless of unit count
    assert "engage.scratch.dx" in cb.report and cb.report.count("scratch.dx") == 1
    h1 = cb.stable_hash()
    fb2 = B.FieldBehavior(list(units), counters=("fallen",))
    fb2.group("reds", [f"a{i}" for i in range(n)])
    fb2.group("blues", [f"b{i}" for i in range(n)])
    for i in range(n):
        for nm, foe in ((f"a{i}", "blues"), (f"b{i}", "reds")):
            fb2.units[nm].tree = B.Selector(
                B.Sequence(fb2.hp_le(nm, 0), B.Do(B.Die(count="fallen"))),
                fb2.engage_node(nm, B.Engage(foe, radius=1500, contact=170,
                                             nearest=True)),
                B.Do(B.Hold(fb2.units[nm].spawn)),
            )
    assert fb2.compile().stable_hash() == h1


# ------------------------------------------------------------------ the hud strip
def hud_field() -> B.FieldBehavior:
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0), hp=3)],
                         counters=("kills", "score"))
    fb.units["u"].tree = B.Selector(
        B.Sequence(fb.hp_le("u", 0), B.Do(B.Die(count="kills"))),
        B.Do(B.Hold((0, 0))),
    )
    fb.hud("[MPOS=12,10]K [NUMB=0]  S [NUMB=1]", ["kills", "score"],
           window=6, txid=940, digits=3)
    return fb


def test_hud_compiles_and_draws():
    cb = hud_field().compile()
    _verify_all(cb)
    ops = [i.op for i in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body))]
    # two live writes + two open-pass SENTINEL writes (the width reserve)
    assert ops.count(0x66) == 4
    # THE FLICKER LAW (playtest 1: "the strip flickers"): the window opens
    # EXACTLY ONCE behind the shown-latch — the engine re-renders [NUMB]s in
    # place, and re-issuing WindowAsync disposes+recreates (blink per change)
    assert ops.count(0x20) == 1
    assert "hud0.shown" in cb.report and "3-digit reserve" in cb.report
    # THE WIDTH-RESERVE LAW (playtest 2: "double digits causes clipping"):
    # Dialog.AutomaticSize bakes the width ONCE at open, so the open pass must
    # feed the max-width sentinel (10^digits - 1) before the window opens
    ins = list(D.iter_code(cb.ticker_body, 0, len(cb.ticker_body)))
    win_at = next(i for i, x in enumerate(ins) if x.op == 0x20)
    sentinels = [x for x in ins[:win_at] if x.op == 0x66]
    assert len(sentinels) == 2
    assert bytes([999 & 0xFF, 999 >> 8]) in cb.ticker_body
    assert "hud #0: window 6, txid 940" in cb.report
    segs = dict(cb.sizes["ticker_segments"])
    assert segs.get("hud 0", 0) > 40
    assert hud_field().compile().stable_hash() == cb.stable_hash()


def test_hud_negatives():
    fb = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))],
                         counters=("kills",))
    fb.units["u"].tree = B.Do(B.Hold((0, 0)))
    with pytest.raises(B.BehaviorError, match="NUMB=3"):
        fb.hud("x [NUMB=3]", ["kills"], txid=1)
    with pytest.raises(B.BehaviorError, match="unknown counter"):
        fb.hud("x [NUMB=0]", ["ghost"], txid=1)
    fb.hud("k [NUMB=0]", ["kills"], window=5, txid=1)
    with pytest.raises(B.BehaviorError, match="already carries"):
        fb.hud("k2 [NUMB=0]", ["kills"], window=5, txid=2)
    fb2 = B.FieldBehavior([B.UnitSpec("u", entry=2, spawn=(0, 0))],
                          counters=("kills",))
    fb2.units["u"].tree = B.Do(B.Hold((0, 0)))
    fb2.hud("k [NUMB=0]", ["kills"])               # no txid: refused at compile
    with pytest.raises(B.BehaviorError, match="no txid"):
        fb2.compile()
