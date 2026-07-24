"""Rung-4 tests: the [behavior] TOML surface (content.behaviortoml) + the route-sweep
core (scene.routes). The compiled output is walked with the same instruction-level
discipline as test_behavior; parity is asserted against a hand-built DSL reference."""
from __future__ import annotations

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.eb import disasm as D

RAW = {
    "player": {"spawn": [0, -900]},
    "npc": [
        {"name": "guard", "pos": [0, 0], "dialogue": "Halt!"},
        {"name": "beast", "pos": [500, 500], "dialogue": "Grr."},
    ],
    "marker": [
        {"name": "post", "pos": [0, 0]},
        {"name": "ring", "pos": [0, 0], "path": [[0, 0], [400, 0], [400, 400], [0, 400]],
         "closed": True},
        {"name": "lane", "pos": [500, 500], "path": [[500, 500], [200, 200], [0, 0]]},
    ],
    "behavior": {
        "warmup": 30,
        "alternators": [{"name": "shift", "frames": 300}],
        "public_flags": ["go"],
        "unit": [
            {"npc": "guard", "hp": 5, "speed": 40, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": True}},
                {"when": [{"flag": "alarm"}, {"active": "beast"},
                          {"near": ["beast", 300]}],
                 "do": {"swing_at": "beast", "damage": 2}},
                {"when": [{"any_near": [["beast"], 700]}],
                 "do": {"chase": "beast", "standoff": 180, "speed": 65},
                 "raise_flags": ["alarm"]},
                {"when": [{"flag": "shift"}], "do": {"patrol": "ring"}},
                {"do": {"hold": "post"}},
            ]},
            {"npc": "beast", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": True}},
                {"when": [{"flag": "go"}, {"near_point": ["post", 250]}],
                 "do": {"announce_npc": "beast"}, "once": "gloat"},
                {"when": [{"flag": "go"}], "do": {"march": "lane", "arrive_r": 200}},
                {"do": {"wander": [500, 500], "radius": 300, "every": 90, "speed": 30}},
            ]},
        ],
    },
}


def _verify_body(body: bytes) -> None:
    starts = set()
    for ins in D.iter_code(body, 0, len(body)):
        starts.add(ins.off)
        assert ins.end <= len(body)
    ends = starts | {len(body)}
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op in (0x01, 0x02, 0x03):
            t = D.jump_target(ins)
            assert t is None or t in ends


def _verify_all(cb: B.CompiledBehavior) -> None:
    _verify_body(cb.ticker_body)
    _verify_body(cb.main_init)
    for body in cb.duty_bodies.values():
        _verify_body(body)
    for funcs in cb.action_funcs.values():
        for _tag, body in funcs:
            _verify_body(body)


def _build(raw=RAW):
    return BT.build(raw, npc_slots={"guard": 2, "beast": 3},
                    npc_txids_by_name={"guard": 501, "beast": 502},
                    behavior_txids={})


# ------------------------------------------------------------------ the surface
def test_toml_surface_compiles_and_verifies():
    fb = _build()
    cb = fb.compile()
    _verify_all(cb)
    assert "1=Die" in cb.report and "Patrol" in cb.report and "March" in cb.report
    assert "shift.clock" in cb.report                  # the alternator registered
    assert fb.public_flag("go") == fb.bb.flag("go")    # stable public index


def test_validate_clean_and_determinism():
    assert BT.validate(RAW) == []
    h1 = _build().compile().stable_hash()
    h2 = _build().compile().stable_hash()
    assert h1 == h2


def test_route_marker_resolution():
    fb = _build()
    patrol = [a for a in fb._collect_actions(fb.units["guard"])
              if isinstance(a, B.Patrol)]
    assert patrol and patrol[0].points == ((0, 0), (400, 0), (400, 400), (0, 400))
    march = [a for a in fb._collect_actions(fb.units["beast"])
             if isinstance(a, B.March)]
    assert march and march[0].points[-1] == (0, 0)
    assert BT.route_names(RAW) == {"ring", "lane"}


def test_announce_lines_and_txids():
    raw = {**RAW, "behavior": {**RAW["behavior"], "unit": [
        {"npc": "guard", "branch": [
            {"when": [{"flag": "x"}], "do": {"announce": "The gate is lost!"}},
            {"do": {"hold": [0, 0]}},
        ]}]}}
    lines = BT.announce_lines(raw)
    assert [(u, b) for u, b, _ in lines] == [(0, 0)]
    fb = BT.build(raw, npc_slots={"guard": 2}, behavior_txids={(0, 0): 777})
    ann = [a for a in fb._collect_actions(fb.units["guard"])
           if isinstance(a, B.Announce)]
    assert ann[0].txid == 777


def test_verb_negatives():
    def with_branch(br):
        return {**RAW, "behavior": {"unit": [
            {"npc": "guard", "branch": [br, {"do": {"hold": [0, 0]}}]}]}}
    # two verb keys in one action dict
    bad = with_branch({"do": {"hold": [0, 0], "walk_to": [1, 1]}})
    assert any("exactly ONE verb" in p for p in BT.validate(bad))
    # unknown option key
    bad = with_branch({"do": {"chase": "player", "radius": 5}})
    assert any("unknown option" in p for p in BT.validate(bad))
    # unknown route marker
    bad = with_branch({"do": {"patrol": "ghostring"}})
    assert any("ghostring" in p for p in BT.validate(bad))
    # a plain point marker used as a route
    bad = with_branch({"do": {"march": "post"}})
    assert any("no `path`" in p for p in BT.validate(bad))
    # swing_at a unit with no hp
    bad = {**RAW, "behavior": {"unit": [
        {"npc": "guard", "branch": [{"do": {"swing_at": "beast"}},
                                    {"do": {"hold": [0, 0]}}]},
        {"npc": "beast", "branch": [{"do": {"hold": [500, 500]}}]}]}}
    assert any("no `hp`" in p for p in BT.validate(bad))
    # once + cooldown together
    bad = with_branch({"do": {"hold": [0, 0]}, "once": "a", "cooldown": 30})
    with pytest.raises(BT.BehaviorTomlError, match="mutually exclusive"):
        BT.build(bad, npc_slots={"guard": 2})
    # unknown npc binding
    bad = {**RAW, "behavior": {"unit": [
        {"npc": "nobody", "branch": [{"do": {"hold": [0, 0]}}]}]}}
    assert any("not a named" in p for p in BT.validate(bad))


def test_verbatim_refused():
    raw = {**RAW, "verbatim_eb": {"bin": "x.eb"}}
    probs = BT.validate(raw, verbatim=True)
    assert any("VERBATIM" in p for p in probs)


def test_cutscene_cast_conflict():
    raw = {**RAW, "cutscene": [{"actors": ["guard"], "steps": []}]}
    assert any("cast actors" in p for p in BT.validate(raw))


# ------------------------------------------------------------------ pooled units
POOLED_RAW = {
    "player": {"spawn": [0, -900]},
    "npc": [
        {"name": "pest", "pos": [500, 500], "dialogue": "Grr."},
        {"name": "r0", "pos": [800, 800], "dialogue": "At your service!"},
        {"name": "r1", "pos": [850, 800], "dialogue": "Ready!"},
    ],
    "behavior": {"unit": [
        {"npc": "pest", "hp": 3, "branch": [
            {"when": [{"hp_le": 0}], "do": {"die": True}},
            {"do": {"wander": [500, 500], "radius": 300}},
        ]},
        {"npc": "r0", "hp": 4, "pooled": True, "pool": "recruits", "branch": [
            {"when": [{"hp_le": 0}], "do": {"die": True}},
            {"when": [{"active": "pest"}, {"near": ["pest", 250]}],
             "do": {"swing_at": "pest"}},
            {"when": [{"active": "pest"}, {"near": ["pest", 700]}],
             "do": {"chase": "pest", "standoff": 160}},
            {"do": {"hold_post": True}},
        ]},
        {"npc": "r1", "hp": 4, "pooled": True, "pool": "recruits", "branch": [
            {"do": {"hold_post": True}},
        ]},
    ]},
}


def test_pooled_toml_surface():
    assert BT.validate(POOLED_RAW) == []
    fb = BT.build(POOLED_RAW, npc_slots={"pest": 2, "r0": 3, "r1": 4})
    cb = fb.compile()
    _verify_all(cb)
    assert list(fb.pool_flags) == ["recruits"]
    assert BT.pooled_npcs(POOLED_RAW) == {"r0", "r1"}
    ops = [ins.op for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body))]
    assert ops.count(0x09) == 2 and ops.count(0xBF) == 2


def test_pooled_negatives():
    # pool= without pooled
    bad = {**POOLED_RAW, "behavior": {"unit": [
        {"npc": "pest", "pool": "x", "branch": [{"do": {"hold": [0, 0]}}]}]}}
    assert any("needs `pooled = true`" in p for p in BT.validate(bad))
    # bad pool charset
    bad = {**POOLED_RAW, "behavior": {"unit": [
        {"npc": "pest", "pooled": True, "pool": "no spaces!",
         "branch": [{"do": {"hold": [0, 0]}}]}]}}
    assert any("A-Za-z0-9_" in p for p in BT.validate(bad))
    # hold_post takes true
    bad = {**POOLED_RAW, "behavior": {"unit": [
        {"npc": "pest", "branch": [{"do": {"hold_post": [0, 0]}}]}]}}
    assert any("hold_post takes `true`" in p for p in BT.validate(bad))
    # a prop attached to a pooled npc
    bad = {**POOLED_RAW, "prop": [{"prop": "lantern", "pos": [800, 800],
                                   "attach_to": "r0"}]}
    assert any("attach_to pooled" in p for p in BT.validate(bad))
    # requires_flag still refused (pooled needs no flag — the build skips boot spawn)
    bad = {**POOLED_RAW, "npc": [dict(POOLED_RAW["npc"][0]),
                                 {**POOLED_RAW["npc"][1], "requires_flag": 9000},
                                 dict(POOLED_RAW["npc"][2])]}
    probs = BT.validate(bad)
    assert any("requires_flag" in p and "skips" in p for p in probs)


def test_pooled_installs_in_built_eb(tmp_path):
    """Product path: the pooled npc's entry is seated with duty + dispatch tags but
    entry 0 has NO boot InitObject for it — only the ticker spawns it."""
    from ff9mapkit import build as BLD
    from ff9mapkit.eb.model import EbScript

    toml = (
        '[field]\nid = 30000\nname = "BHP"\narea = 11\n'
        "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
        '\n[[npc]]\nname = "guard"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Halt!"\n'
        '\n[[npc]]\nname = "r0"\npreset = "vivi"\npos = [400, -300]\ndialogue = "Hired!"\n'
        "\n[behavior]\nwarmup = 30\n"
        '\n[[behavior.unit]]\nnpc = "guard"\nbranch = [{ do = { hold = [0, -300] } }]\n'
        '\n[[behavior.unit]]\nnpc = "r0"\npooled = true\npool = "recruits"\n'
        'branch = [{ do = { hold_post = true } }]\n'
    )
    f = tmp_path / "bhp.field.toml"
    f.write_text(toml, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    plain = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501})
    eb = EbScript.from_bytes(plain)
    units = [i for i in range(eb.entry_count)
             if eb.entry(i).size > 0
             and eb.entry(i).func_by_tag(B.FIRST_ACTION_TAG) is not None]
    assert len(units) == 2                             # both units carry dispatch tags
    # every InitObject in ENTRY 0 (Main_Init + activate blocks): the boot spawns.
    boot_inits = set()
    for fn in eb.entry(0).funcs:
        for ins in D.iter_code(plain, fn.abs_start, fn.abs_end):
            if ins.op == 0x09:
                boot_inits.add(int(ins.imm(0)))
    # whole-file InitObject targets, per slot
    all_inits = []
    for i in range(eb.entry_count):
        for fn in eb.entry(i).funcs:
            for ins in D.iter_code(plain, fn.abs_start, fn.abs_end):
                if ins.op == 0x09:
                    all_inits.append(int(ins.imm(0)))
    pooled_only = [s for s in set(all_inits) if s not in boot_inits]
    assert len(pooled_only) == 1                       # exactly one runtime-only spawn
    assert all_inits.count(pooled_only[0]) == 1        # ...issued once, by the ticker
    # THE STAGED-LATCH EXISTENCE FIX: every DefinePlayerCharacter (0x2C) in a tag-0
    # is immediately followed by the player.bound announce (a 0x05 statement) — the
    # ticker may not deref obj(250) before the player's own Init has confirmed it
    bind_sites = 0
    for i in range(eb.entry_count):
        e = eb.entry(i)
        if e.size <= 0 or e.func_by_tag(0) is None:
            continue
        fn = e.func_by_tag(0)
        instrs = list(D.iter_code(plain, fn.abs_start, fn.abs_end))
        for k, ins in enumerate(instrs):
            if ins.op == 0x2C:
                bind_sites += 1
                assert k + 1 < len(instrs) and instrs[k + 1].op == 0x05, \
                    "0x2C not followed by the player.bound announce"
    assert bind_sites >= 1
    # determinism
    again = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501})
    assert again == plain


# ------------------------------------------------------------------ the built .eb
def test_behavior_installs_in_built_eb(tmp_path):
    """End-to-end through the PRODUCT PATH: a field.toml with a [behavior] table ->
    build_script -> the unit's tag-1 standby is a duty walk, dispatch/nudge tags
    exist, the ticker entry is seated, and every touched function walks clean."""
    from ff9mapkit import build as BLD
    from ff9mapkit.eb.model import EbScript

    toml = (
        '[field]\nid = 30000\nname = "BHV"\narea = 11\n'
        "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
        '\n[[npc]]\nname = "guard"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Halt!"\n'
        "\n[behavior]\nwarmup = 30\n"
        '\n[[behavior.unit]]\nnpc = "guard"\nhp = 3\n'
        "\n[[behavior.unit.branch]]\n"
        'when = [{ hp_le = 0 }]\ndo = { die = true }\n'
        "\n[[behavior.unit.branch]]\n"
        'when = [{ near = ["player", 400] }]\ndo = { chase = "player", speed = 60 }\n'
        "\n[[behavior.unit.branch]]\n"
        "do = { patrol = [[0, -300], [400, -300]] }\n"
    )
    f = tmp_path / "bhv.field.toml"
    f.write_text(toml, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    plain = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501})
    eb = EbScript.from_bytes(plain)
    STANDBY = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])
    units_with_tags = [i for i in range(eb.entry_count)
                       if eb.entry(i).size > 0
                       and eb.entry(i).func_by_tag(B.FIRST_ACTION_TAG) is not None]
    assert len(units_with_tags) == 1                   # the one behavior unit
    e = eb.entry(units_with_tags[0])
    f1 = e.func_by_tag(1)
    assert bytes(plain[f1.abs_start:f1.abs_end]) != STANDBY   # the duty walk replaced it
    assert len(eb.entry(units_with_tags[0]).funcs) >= 4       # 0/1/3 + dispatch/nudge
    # determinism across languages: a second build of the same project is identical
    again = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501})
    assert again == plain


# ------------------------------------------------------------------ scene.routes
def test_sweep_polyline_core():
    from ff9mapkit.scene import routes as R

    class FakeMesh:
        def world_verts(self):
            return []

        tris = ()

        def point_on_walkmesh(self, x, z):
            return 0 if 0 <= x <= 1000 else None       # a 1000u-wide walkable strip

    legs = R.sweep_polyline([(0, 0), (2000, 0)], FakeMesh(), bedges=[])
    assert len(legs) == 1 and legs[0]["spans"]         # the second half is off-mesh
    t0, t1 = legs[0]["spans"][0]
    assert t0 > 0.45 and t1 == 1.0
    warns = R.describe_leg_problems("test", legs)
    assert warns and "OFF-MESH" in warns[0]
    clean = R.sweep_polyline([(0, 0), (900, 0)], FakeMesh(), bedges=[])
    assert not clean[0]["spans"]
