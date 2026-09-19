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


# ------------------------------------------------------------------ waves + win/loss
def test_timer_battle_toml_surface():
    raw = {**RAW, "behavior": {**RAW["behavior"], "timer": 180, "unit": [
        {"npc": "guard", "hp": 6, "branch": [
            {"when": [{"flag": "lost"}], "do": {"die": True}},
            {"when": [{"hp_le": 0}], "do": {"battle": 35}, "raise_flags": ["lost"]},
            {"when": [{"time_below": 1}], "do": {"announce": "We held!"},
             "raise_flags": ["won"], "once": "wincry"},
            {"do": {"hold": "post"}},
        ]},
        {"npc": "beast", "hp": 4, "branch": [
            {"when": [{"hp_le": 0}], "do": {"die": True}},
            {"when": [{"time_below": 170}, {"not_flag": "lost"}],
             "do": {"walk_to": "post"}},
            {"do": {"hold": [500, 500]}},
        ]},
    ]}}
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"guard": 2, "beast": 3},
                  behavior_txids={(0, 2): 700})
    assert fb.timer == 180 and fb.has_battle_actions()
    _verify_all(fb.compile())
    # negatives: time cond without timer / bad battle scene / bad timer
    bad = {**raw, "behavior": {**raw["behavior"]}}
    del bad["behavior"]["timer"]
    bad["behavior"] = {k: v for k, v in raw["behavior"].items() if k != "timer"}
    assert any("needs field-level" in p for p in BT.validate(bad))
    bad = {**raw, "behavior": {**raw["behavior"], "unit": [
        {"npc": "guard", "branch": [{"do": {"battle": "zaghnol"}},
                                    {"do": {"hold": "post"}}]}]}}
    assert any("battle takes a battle SCENE id" in p for p in BT.validate(bad))
    bad = {**raw, "behavior": {**raw["behavior"], "timer": 999999}}
    assert any("timer must be" in p for p in BT.validate(bad))


def test_battle_installs_reinit_in_built_eb(tmp_path):
    """Product path: a [behavior] battle action makes the build install the entry-0
    tag-10 Main_Reinit (the after-battle resume law) without any [encounter] block."""
    from ff9mapkit import build as BLD
    from ff9mapkit.eb.model import EbScript

    toml = (
        '[field]\nid = 30002\nname = "BHW"\narea = 11\n'
        "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
        '\n[[npc]]\nname = "gate"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Hold!"\n'
        "\n[behavior]\nwarmup = 30\ntimer = 120\n"
        '\n[[behavior.unit]]\nnpc = "gate"\nhp = 3\n'
        "\n[[behavior.unit.branch]]\n"
        'when = [{ hp_le = 0 }]\ndo = { battle = 35 }\n'
        "\n[[behavior.unit.branch]]\n"
        "do = { hold = [0, -300] }\n"
    )
    f = tmp_path / "bhw.field.toml"
    f.write_text(toml, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    plain = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501})
    eb = EbScript.from_bytes(plain)
    assert eb.entry(0).func_by_tag(10) is not None     # the after-battle Main_Reinit
    battle_ops = [ins for i in range(eb.entry_count) if eb.entry(i).size > 0
                  for fn in eb.entry(i).funcs
                  for ins in D.iter_code(plain, fn.abs_start, fn.abs_end)
                  if ins.op == 0x2A]
    assert len(battle_ops) == 1 and int(battle_ops[0].imm(1)) == 35
    again = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501})
    assert again == plain


# ------------------------------------------------------------------ pool economy
def test_pool_rows_parse_and_validate():
    raw = {**POOLED_RAW, "behavior": {**POOLED_RAW["behavior"],
                                      "pool": [{"name": "recruits", "price": 300,
                                                "button": True, "request_flag": 8848}]},
           "choice": [{"zone": [[9000, 9000], [9200, 9000], [9200, 8800], [9000, 8800]],
                       "prompt": "Deploy a soldier?", "instant": True,
                       "options": [{"text": "Hire (300 gil)", "set_flag": [8848, 1]},
                                   {"text": "Not now."}]}]}
    assert BT.validate(raw) == []
    specs = BT.pool_specs(raw)
    assert specs[0].price == 300 and specs[0].request_flag == 8848
    assert specs[0].button == B.DEFAULT_HIRE_BUTTONS   # true -> the default mask
    ci, n = BT.pool_menu_choice(raw, 8848)
    assert (ci, n) == (0, 1)
    fb = BT.build(raw, npc_slots={"pest": 2, "r0": 3, "r1": 4})
    assert fb.pool_flags["recruits"] == 8848
    # negatives
    bad = {**raw, "behavior": {**raw["behavior"],
                               "pool": [{"name": "recruits", "button": True}]}}
    assert any("request_flag" in p for p in BT.validate(bad))
    bad = {**raw, "choice": []}                        # button but no parked menu
    assert any("no zone [[choice]]" in p for p in BT.validate(bad))
    bad = {**raw, "behavior": {**raw["behavior"],
                               "pool": [{"name": "ghost", "price": 1}]}}
    assert any("no pooled unit" in p for p in BT.validate(bad))
    bad = {**raw, "behavior": {**raw["behavior"],
                               "pool": [{"name": "recruits", "prize": 3}]}}
    assert any("unknown key" in p for p in BT.validate(bad))


def test_button_pool_installs_in_built_eb(tmp_path):
    """Product path: price + button pool -> the poller entry is seated (RunScriptSync
    at the parked choice's slot), RemoveGil rides the ticker, explicit request flag."""
    from ff9mapkit import build as BLD
    from ff9mapkit.eb.model import EbScript

    toml = (
        '[field]\nid = 30001\nname = "BHE"\narea = 11\n'
        "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
        '\n[[npc]]\nname = "r0"\npreset = "vivi"\npos = [400, -300]\ndialogue = "Hired!"\n'
        "\n[behavior]\nwarmup = 30\n"
        '\n[[behavior.pool]]\nname = "recruits"\nprice = 300\nbutton = true\n'
        "request_flag = 8848\n"
        '\n[[behavior.unit]]\nnpc = "r0"\npooled = true\npool = "recruits"\n'
        'branch = [{ do = { hold_post = true } }]\n'
        '\n[[choice]]\nzone = [[9000,9000],[9200,9000],[9200,8800],[9000,8800]]\n'
        'prompt = "Deploy a soldier?"\ninstant = true\n'
        '\n[[choice.options]]\ntext = "Hire (300 gil)"\nset_flag = [8848, 1]\n'
        '\n[[choice.options]]\ntext = "Not now."\n'
    )
    f = tmp_path / "bhe.field.toml"
    f.write_text(toml, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    CT = {0: {"prompt": 502, "replies": {}}}           # the parked hire menu's txids
    plain = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501}, choice_txids=CT)
    eb = EbScript.from_bytes(plain)
    gil_ops, sync_targets = 0, []
    for i in range(eb.entry_count):
        e = eb.entry(i)
        if e.size <= 0:
            continue
        for fn in e.funcs:
            for ins in D.iter_code(plain, fn.abs_start, fn.abs_end):
                if ins.op == 0xCF:
                    gil_ops += 1
                if ins.op == 0x14:                     # RunScriptSync(level, uid, tag)
                    sync_targets.append((int(ins.imm(0)), int(ins.imm(1)), int(ins.imm(2))))
    assert gil_ops == 1                                # one spawn site -> one RemoveGil
    pollers = [t for t in sync_targets if t[0] == 4 and t[2] == 3]
    assert len(pollers) == 1                           # the poller -> the parked menu
    choice_slot = pollers[0][1]
    assert eb.entry(choice_slot).size > 0              # ...which is a real seated entry
    again = BLD.build_script(BLD.FieldProject.load(f), "us", {501: 501}, choice_txids=CT)
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


def test_mesh_boundary_edges_seam_aware():
    """Cross-floor SEAMS (disjoint per-floor vertex sets, linked by tri neighbors)
    are NOT walls: the sweep must not warn on a clear route crossing one, while a
    real wall still warns. The 30414/30412 phantom "passes Nu from a walkmesh
    edge" bug: the raw one-triangle edge count called every seam a wall."""
    from types import SimpleNamespace as NS

    from ff9mapkit.scene import routes as R

    # two 1000x1000 floors side by side; the x=1000 seam verts are DUPLICATED
    # (floor A owns 0-3, floor B owns 4-7 -- the multi-floor .bgi convention)
    verts = [(0, 0, 0), (1000, 0, 0), (1000, 0, 1000), (0, 0, 1000),
             (1000, 0, 0), (2000, 0, 0), (2000, 0, 1000), (1000, 0, 1000)]
    # slot k edge = SLOT_PAIRS[k] = [(0,2),(0,1),(1,2)] of the tri's local verts
    tris = [NS(vtx=(0, 1, 2), nbr=[1, -1, 3]),    # s2=(1,2) = the seam -> T3
            NS(vtx=(0, 2, 3), nbr=[-1, 0, -1]),
            NS(vtx=(4, 5, 6), nbr=[3, -1, -1]),
            NS(vtx=(4, 6, 7), nbr=[0, 2, -1])]    # s0=(4,7) = the seam -> T0

    class TwoFloorMesh:
        def world_verts(self):
            return verts

        def __init__(self):
            self.tris = tris

        def point_on_walkmesh(self, x, z):
            return 0 if 0 <= x <= 2000 and 0 <= z <= 1000 else None

    wm = TwoFloorMesh()
    bedges = R.mesh_boundary_edges(wm)
    assert len(bedges) == 6                        # 4 outer walls as 6 segments, NO seam
    assert all(not (a[0] == b[0] == 1000) for a, b in bedges)   # the seam edge is gone
    # the raw count DOES call the seam a wall -- the exact defect guarded here
    raw = R.boundary_edges_xz(verts, [t.vtx for t in tris])
    assert any(a[0] == b[0] == 1000 for a, b in raw)

    # a mid-strip route across the seam: clear (500u from the real walls), no warning
    legs = R.sweep_polyline([(200, 500), (1800, 500)], wm, bedges)
    assert not R.describe_leg_problems("seam", legs)
    assert legs[0]["minwall"] > R.WALL_CLEARANCE_W
    # ...but the same route against raw edges would have phantom-warned
    assert R.describe_leg_problems("seam", R.sweep_polyline([(200, 500), (1800, 500)], wm, raw))

    # a real wall still warns: hugging z=0 at 30u < the 48u clearance
    hug = R.sweep_polyline([(200, 30), (1800, 30)], wm, bedges)
    warns = R.describe_leg_problems("hug", hug)
    assert warns and "passes" in warns[0] and "walkmesh edge" in warns[0]

    # tris without neighbor data fall back to the raw vertex-pair count
    bare = NS(world_verts=lambda: verts, tris=[NS(vtx=t.vtx) for t in tris])
    assert sorted(R.mesh_boundary_edges(bare)) == sorted(raw)


# ------------------------------------------------------------------ data tables (0xD3)
TABLE_RAW = {
    "npc": [
        {"name": "gate", "pos": [0, 0], "dialogue": "..."},
        {"name": "fang", "pos": [900, 900], "dialogue": "..."},
    ],
    "behavior": {
        "timer": 120,
        "counters": ["wave", "kills"],
        "table": [{"name": "sched", "values": [100, 80, 60]}],
        "schedule": [{"counter": "wave", "table": "sched"}],
        "unit": [
            {"npc": "gate", "hp": 6, "branch": [
                {"when": [{"counter_ge": ["kills", 1]}], "once": "won",
                 "do": {"announce": "The pest is down."}},
                {"when": [{"counter_eq": ["wave", 1]},
                          {"table_ge": ["sched", "wave", 1]}], "once": "w1",
                 "do": {"announce": "Wave one!"}},
                {"do": {"hold": [0, 0]}},
            ]},
            {"npc": "fang", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "kills"}},
                {"do": {"hold": [900, 900]}},
            ]},
        ],
    },
}


def test_table_toml_surface():
    assert BT.validate(TABLE_RAW) == []
    fb = BT.build(TABLE_RAW, npc_slots={"gate": 2, "fang": 3},
                  behavior_txids={(0, 0): 700, (0, 1): 701})
    cb = fb.compile()
    _verify_all(cb)
    assert fb.tables["sched"] == (B.TABLE_ID_BASE, (100, 80, 60))
    assert fb._counters == {"wave": 0, "kills": 1}
    assert fb._schedules == [("wave", "sched")]
    assert "schedule: wave += 1 while timer < sched[wave]" in cb.report
    # determinism through the TOML path
    fb2 = BT.build(TABLE_RAW, npc_slots={"gate": 2, "fang": 3},
                   behavior_txids={(0, 0): 700, (0, 1): 701})
    assert fb2.compile().stable_hash() == cb.stable_hash()


def test_table_toml_negatives():
    import copy

    def mut(fn):
        r = copy.deepcopy(TABLE_RAW)
        fn(r["behavior"])
        return BT.validate(r)

    assert any("is not a [[behavior.table]]" in p for p in
               mut(lambda b: b["schedule"][0].update(table="nope")))
    assert any("not in [behavior] counters" in p for p in
               mut(lambda b: b["schedule"][0].update(counter="nope")))
    assert any("needs field-level `timer" in p for p in
               mut(lambda b: b.pop("timer")))
    assert any("already has a schedule" in p for p in
               mut(lambda b: b["schedule"].append({"counter": "wave", "table": "sched"})))
    assert any("die counts" in p for p in
               mut(lambda b: b["unit"][1]["branch"][0].update(do={"die": "ghosts"})))
    assert any("out of range" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1]["when"].__setitem__(
                   1, {"table_ge": ["sched", 9, 1]})))
    assert any("is not in [behavior] counters" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1]["when"].__setitem__(
                   1, {"table_ge": ["sched", "ghosts", 1]})))
    assert any("counter_ge takes" in p for p in
               mut(lambda b: b["unit"][0]["branch"][0]["when"].__setitem__(
                   0, {"counter_ge": ["kills"]})))
    assert any("values must be" in p for p in
               mut(lambda b: b["table"][0].update(values=[])))
    assert any("26-bit" in p for p in
               mut(lambda b: b["table"][0].update(values=[1 << 26])))
    assert any("duplicate table" in p for p in
               mut(lambda b: b["table"].append({"name": "sched", "values": [1]})))
    assert any("collides with a counter" in p for p in
               mut(lambda b: b["table"].append({"name": "wave", "values": [1]})))
    assert any("id 77 used twice" in p for p in
               mut(lambda b: b["table"].__iadd__(
                   [{"name": "a", "values": [1], "id": 77},
                    {"name": "b", "values": [1], "id": 77}])))
    assert any("unknown key" in p for p in
               mut(lambda b: b["table"][0].update(cells=["x"])))
    assert any("unknown key" in p for p in
               mut(lambda b: b["schedule"][0].update(speed=9)))


def test_award_toml_surface_and_negatives():
    import copy
    raw = copy.deepcopy(TABLE_RAW)
    raw["behavior"]["unit"][0]["branch"].insert(0, {
        "when": [{"time_below": 1}], "once": "paid",
        "do": {"award": 2000, "item": 236}})
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"gate": 2, "fang": 3},
                  behavior_txids={(0, 1): 700, (0, 2): 701})
    cb = fb.compile()
    _verify_all(cb)
    award = next(b for _t, b in cb.action_funcs["gate"]
                 if any(i.op == 0xCE for i in D.iter_code(b, 0, len(b))))
    assert any(i.op == 0x48 for i in D.iter_code(award, 0, len(award)))

    def mut(fn):
        r = copy.deepcopy(raw)
        fn(r["behavior"])
        return BT.validate(r)

    assert any("needs `once" in p for p in
               mut(lambda b: b["unit"][0]["branch"][0].pop("once")))
    assert any("award takes a gil int" in p for p in
               mut(lambda b: b["unit"][0]["branch"][0].update(
                   do={"award": "lots"})))
    assert any("needs gil and/or an item" in p for p in
               mut(lambda b: b["unit"][0]["branch"][0].update(do={"award": 0})))
    assert any("count must be" in p for p in
               mut(lambda b: b["unit"][0]["branch"][0].update(
                   do={"award": 5, "count": 0})))


SCAN_RAW = {
    "npc": [
        {"name": "m0", "pos": [0, 0], "dialogue": "..."},
        {"name": "m1", "pos": [100, 0], "dialogue": "..."},
        {"name": "crier", "pos": [900, 0], "dialogue": "..."},
    ],
    "behavior": {
        "counters": ["at_shrine"],
        "scan": [{"name": "shrine", "units": ["m0", "m1"], "point": [800, 0],
                  "radius": 300, "count": "at_shrine", "flags": "near_shrine"}],
        "unit": [
            {"npc": "m0", "branch": [{"do": {"march": [[0, 0], [800, 0]]}}]},
            {"npc": "m1", "branch": [{"do": {"march": [[100, 0], [800, 0]]}}]},
            {"npc": "crier", "branch": [
                {"when": [{"counter_ge": ["at_shrine", 2]}], "once": "both",
                 "do": {"announce": "Both at the shrine."}},
                {"when": [{"table_eq": ["near_shrine", 0, 1]}], "once": "first",
                 "do": {"announce": "The first arrives."}},
                {"do": {"hold": [900, 0]}},
            ]},
        ],
    },
}


def test_scan_toml_surface():
    assert BT.validate(SCAN_RAW) == []
    fb = BT.build(SCAN_RAW, npc_slots={"m0": 2, "m1": 3, "crier": 4},
                  behavior_txids={(2, 0): 700, (2, 1): 701})
    cb = fb.compile()
    _verify_all(cb)
    assert [s.name for s in fb._scans] == ["shrine"]
    # the user-named flags table is a REAL table: table_* conds read it
    assert "near_shrine" in fb.tables
    assert "scan shrine: 2 unit(s)" in cb.report
    fb2 = BT.build(SCAN_RAW, npc_slots={"m0": 2, "m1": 3, "crier": 4},
                   behavior_txids={(2, 0): 700, (2, 1): 701})
    assert fb2.compile().stable_hash() == cb.stable_hash()


def test_scan_toml_negatives():
    import copy

    def mut(fn):
        r = copy.deepcopy(SCAN_RAW)
        fn(r["behavior"])
        return BT.validate(r)

    assert any("is not a [[behavior.unit]] npc" in p for p in
               mut(lambda b: b["scan"][0].update(units=["ghost"])))
    assert any("not in [behavior] counters" in p for p in
               mut(lambda b: b["scan"][0].update(count="nope")))
    assert any("needs `point" in p for p in
               mut(lambda b: b["scan"][0].update(point=[1])))
    assert any("radius must be" in p for p in
               mut(lambda b: b["scan"][0].update(radius=0)))
    assert any("needs `name" in p for p in
               mut(lambda b: b["scan"][0].update(name="BadName")))
    assert any("duplicate scan" in p for p in
               mut(lambda b: b["scan"].append(dict(b["scan"][0]))))
    assert any("unknown key" in p for p in
               mut(lambda b: b["scan"][0].update(speed=9)))
    assert any("duplicate units" in p for p in
               mut(lambda b: b["scan"][0].update(units=["m0", "m0"])))
    assert any("collides with a [[behavior.table]]" in p for p in
               mut(lambda b: (b.__setitem__("table", [{"name": "near_shrine",
                                                       "values": [1]}]))))


GROUP_RAW = {
    "npc": [
        {"name": "a0", "pos": [0, 0], "dialogue": "..."},
        {"name": "a1", "pos": [0, 300], "dialogue": "..."},
        {"name": "b0", "pos": [900, 0], "dialogue": "..."},
        {"name": "b1", "pos": [900, 300], "dialogue": "..."},
    ],
    "behavior": {
        "counters": ["fallen"],
        "group": [{"name": "reds", "units": ["a0", "a1"]},
                  {"name": "blues", "units": ["b0", "b1"]}],
        "unit": [
            {"npc": "a0", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "blues", "radius": 1500, "contact": 170}},
                {"do": {"hold": [0, 0]}}]},
            {"npc": "a1", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"when": [{"table_ge": ["group.blues.hp", 0, 1]}],
                 "do": {"engage": "blues"}},
                {"do": {"hold": [0, 300]}}]},
            {"npc": "b0", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "reds"}},
                {"do": {"hold": [900, 0]}}]},
            {"npc": "b1", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "reds", "speed": 70}},
                {"do": {"hold": [900, 300]}}]},
        ],
    },
}


def test_group_toml_surface():
    assert BT.validate(GROUP_RAW) == []
    slots = {"a0": 2, "a1": 3, "b0": 4, "b1": 5}
    fb = BT.build(GROUP_RAW, npc_slots=slots)
    cb = fb.compile()
    _verify_all(cb)
    assert set(fb._groups) == {"reds", "blues"}
    assert fb._member["a0"] == ("reds", 0) and fb._member["b1"] == ("blues", 1)
    assert set(fb._engages) == {"a0", "a1", "b0", "b1"}
    assert "group reds" in cb.report and "engage b1 -> group 'reds'" in cb.report
    fb2 = BT.build(GROUP_RAW, npc_slots=slots)
    assert fb2.compile().stable_hash() == cb.stable_hash()


def test_group_toml_negatives():
    import copy

    def mut(fn):
        r = copy.deepcopy(GROUP_RAW)
        fn(r["behavior"])
        return BT.validate(r)

    assert any("cannot engage its own group" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1]["do"].update(engage="reds")))
    assert any("is not a [[behavior.group]]" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1]["do"].update(engage="ghosts")))
    assert any("contact must be" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1]["do"].update(
                   radius=100, contact=100)))
    assert any("takes no raise_flags" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1].update(raise_flags=["x"])))
    assert any("already has an engage" in p for p in
               mut(lambda b: b["unit"][0]["branch"].insert(
                   2, {"do": {"engage": "blues"}})))
    assert any("has no `hp`" in p for p in
               mut(lambda b: b["unit"][1].pop("hp")))
    assert any("already in group" in p for p in
               mut(lambda b: b["group"][1]["units"].append("a0")))
    assert any("unknown key" in p for p in
               mut(lambda b: b["group"][0].update(color="red")))
    assert any("duplicate group" in p for p in
               mut(lambda b: b["group"].append({"name": "reds", "units": ["b0"]})))


SCOREBOARD_RAW = {
    "npc": [
        {"name": "a0", "pos": [0, 0], "dialogue": "..."},
        {"name": "a1", "pos": [0, 300], "dialogue": "..."},
        {"name": "b0", "pos": [900, 0], "dialogue": "..."},
        {"name": "b1", "pos": [900, 300], "dialogue": "..."},
        {"name": "crier", "pos": [500, 900], "dialogue": "..."},
    ],
    "behavior": {
        "counters": ["fallen", "reds_up", "blues_up"],
        "group": [{"name": "reds", "units": ["a0", "a1"]},
                  {"name": "blues", "units": ["b0", "b1"]}],
        "scan": [{"name": "ru", "group": "reds", "count": "reds_up",
                  "alive_only": True},
                 {"name": "bu", "group": "blues", "count": "blues_up",
                  "alive_only": True}],
        "hud": [{"window": 6, "values": ["reds_up", "blues_up", "fallen"],
                 "text": "[MPOS=10,8]R [NUMB=0]  B [NUMB=1]  X [NUMB=2]"}],
        "unit": [
            {"npc": "a0", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "blues", "nearest": True}},
                {"do": {"hold": [0, 0]}}]},
            {"npc": "a1", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "blues"}},
                {"do": {"hold": [0, 300]}}]},
            {"npc": "b0", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "reds", "nearest": True}},
                {"do": {"hold": [900, 0]}}]},
            {"npc": "b1", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": "fallen"}},
                {"do": {"engage": "reds"}},
                {"do": {"hold": [900, 300]}}]},
            {"npc": "crier", "branch": [
                {"when": [{"counter_eq": ["blues_up", 0]}], "once": "bwiped",
                 "do": {"announce": "Blues wiped!"}},
                {"do": {"hold": [500, 900]}}]},
        ],
    },
}


def test_scoreboard_toml_surface():
    assert BT.validate(SCOREBOARD_RAW) == []
    slots = {"a0": 2, "a1": 3, "b0": 4, "b1": 5, "crier": 6}
    tx = {(4, 0): 700, ("hud", 0): 941}
    fb = BT.build(SCOREBOARD_RAW, npc_slots=slots, behavior_txids=tx)
    cb = fb.compile()
    _verify_all(cb)
    assert len(fb._scans) == 2 and all(s.alive_only for s in fb._scans)
    assert fb._huds[0].txid == 941
    hud_text = BT.hud_mes_text(SCOREBOARD_RAW["behavior"]["hud"][0])
    assert hud_text.startswith("[IMME]")
    # THE TURBO-INJECTION LAW (arm B): a flags-16 [NFOC] strip is the predicate's window
    # half for the WHOLE field, so every strip carries [NTUR] -- exactly once.
    for tag in ("[NTUR]", "[NFOC]"):
        assert hud_text.count(tag) == 1, tag
    fb2 = BT.build(SCOREBOARD_RAW, npc_slots=slots, behavior_txids=tx)
    assert fb2.compile().stable_hash() == cb.stable_hash()


def test_scoreboard_toml_negatives():
    import copy

    def mut(fn):
        r = copy.deepcopy(SCOREBOARD_RAW)
        fn(r["behavior"])
        return BT.validate(r)

    assert any("alive_only needs group" in p for p in
               mut(lambda b: b["scan"][0].update(group=None, units=["a0"],
                                                 point=[0, 0], radius=100)))
    assert any("exactly one of" in p for p in
               mut(lambda b: b["scan"][0].update(units=["a0"])))
    assert any("flags need a point" in p for p in
               mut(lambda b: b["scan"][0].update(flags="f")))
    assert any("is not a [[behavior.group]]" in p for p in
               mut(lambda b: b["scan"][0].update(group="ghosts")))
    assert any("nearest takes" in p for p in
               mut(lambda b: b["unit"][0]["branch"][1]["do"].update(nearest=1)))
    assert any("window must be" in p for p in
               mut(lambda b: b["hud"][0].update(window=9)))
    assert any("NUMB=7" in p for p in
               mut(lambda b: b["hud"][0].update(text="[NUMB=7]")))
    assert any("is not a counter, 'gil', 'timer'" in p for p in
               mut(lambda b: b["hud"][0].update(values=["ghost"])))
    assert any("has no `hp`" in p for p in                     # hp: source
               mut(lambda b: b["hud"][0].update(values=["hp:crier"])))
    assert any("digits LIST" in p for p in
               mut(lambda b: b["hud"][0].update(digits=[2, 2])))
    assert BT.validate({**SCOREBOARD_RAW, "behavior": {                 # sources OK
        **SCOREBOARD_RAW["behavior"],
        "hud": [{"window": 6, "values": ["gil", "timer", "fallen"],
                 "digits": [6, 3, 2], "text": "[NUMB=0][NUMB=1][NUMB=2]"}]}}) == []
    assert any("already carries" in p for p in
               mut(lambda b: b["hud"].append({"window": 6, "values": ["fallen"],
                                              "text": "[NUMB=0]"})))


# ------------------------------------------------- the ITEM POOL (the shop bridge)
ITEM_RAW = {
    "player": {"spawn": [0, -900]},
    "npc": [
        {"name": "s0", "pos": [800, 800], "dialogue": "Levy!"},
        {"name": "s1", "pos": [850, 800], "dialogue": "Levy!"},
        {"name": "watch", "pos": [0, -300], "dialogue": "..."},
    ],
    "behavior": {"unit": [
        {"npc": "s0", "pooled": True, "pool": "levy",
         "branch": [{"do": {"hold_post": True}}]},
        {"npc": "s1", "pooled": True, "pool": "levy",
         "branch": [{"do": {"hold_post": True}}]},
        {"npc": "watch", "branch": [
            {"when": [{"have_item": ["Potion", 2]}],
             "do": {"announce": "Stocked!"}, "once": "st"},
            {"do": {"hold": [0, -300]}},
        ]},
    ], "pool": [{"name": "levy", "item": "Potion"}],
        "hud": [{"text": "[MPOS=10,48]P [NUMB=0]", "values": ["item:Potion"]}]},
}


def _item_fb():
    return BT.build(ITEM_RAW, npc_slots={"s0": 2, "s1": 3, "watch": 4},
                    npc_txids_by_name={"s0": 0, "s1": 0, "watch": 0},
                    behavior_txids={(2, 0): 900, ("hud", 0): 901})


def test_item_pool_toml_surface():
    """The shop-as-hire-menu bridge: an item pool has NO request-flag lane (holding
    the contract IS the request), RemoveItem sits at each spawn site, and the
    hireable flag reads the live inventory."""
    assert BT.validate(ITEM_RAW) == []
    fb = _item_fb()
    cb = fb.compile()
    _verify_all(cb)
    assert fb.pool_flags == {}                       # no request flag allocated
    assert "levy" in fb.pool_hireable                # hireable still published
    names = [ins.name for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body))]
    assert names.count("RemoveItem") == 2            # one per pooled unit's spawn site
    assert names.count("InitObject") == 2
    polls = [D.pretty_expr(cb.ticker_body, ins.off + 1)[0]
             for ins in D.iter_code(cb.ticker_body, 0, len(cb.ticker_body))
             if ins.op == 0x05]
    assert sum("B_HAVE_ITEM" in t for t in polls) == 3   # pool poll + hireable + cond
    # determinism
    assert _item_fb().compile().ticker_body == cb.ticker_body


def test_item_pool_report_names_the_item():
    assert "ITEM POOL (one Potion converts" in _item_fb().compile().report


def test_item_pool_validation():
    def mut(f):
        import copy
        r = copy.deepcopy(ITEM_RAW)
        f(r["behavior"])
        return BT.validate(r)

    assert any("does not resolve" in p for p in
               mut(lambda b: b["pool"][0].update(item="Bogusite")))
    assert any("exclusive with price" in p for p in
               mut(lambda b: b["pool"][0].update(price=300)))
    assert any("exclusive with request_flag" in p for p in
               mut(lambda b: b["pool"][0].update(request_flag=8848)))
    assert any("have_item" in p and "does not resolve" in p for p in
               mut(lambda b: b["unit"][2]["branch"][0]["when"][0].update(
                   have_item=["Bogusite", 1])))
    assert any("have_item count" in p for p in
               mut(lambda b: b["unit"][2]["branch"][0]["when"][0].update(
                   have_item=["Potion", 0])))
    assert any("item does not resolve" in p for p in
               mut(lambda b: b["hud"][0].update(values=["item:Bogusite"])))


# --------------------------------------------- ShopStock (AddShopItem 0x115)
def _stock_raw(**branch_over):
    br = {"when": [{"have_item": ["Potion", 3]}],
          "do": {"add_shop_item": [40, "Elixir"]}, "once": "stock2", **branch_over}
    return {
        "player": {"spawn": [0, -900]},
        "shop": [{"id": 40, "sells": ["Potion"]}],
        "npc": [{"name": "crier", "pos": [0, -300], "dialogue": "..."}],
        "behavior": {"unit": [
            {"npc": "crier", "branch": [br, {"do": {"hold": [0, -300]}}]},
        ]},
    }


def test_shop_stock_compiles_remove_then_add():
    """An add emits REMOVE then ADD (the engine's List.Add dupes — idempotence),
    on the event-Once lane (latch-first body)."""
    raw = _stock_raw()
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"crier": 2},
                  npc_txids_by_name={"crier": 0}, behavior_txids={})
    cb = fb.compile()
    _verify_all(cb)
    shop_ops = []
    for _tag, body in cb.action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.name == "AddShopItem":
                shop_ops.append((ins.imm(0), ins.imm(1), ins.imm(2)))
    from ff9mapkit import items as IT
    ex = IT.resolve("Elixir")
    assert shop_ops == [(40, ex, 0), (40, ex, 1)]        # remove first, then add
    # a remove-only verb emits just the remove
    raw2 = _stock_raw(do={"remove_shop_item": [40, "Elixir"]})
    fb2 = BT.build(raw2, npc_slots={"crier": 2},
                   npc_txids_by_name={"crier": 0}, behavior_txids={})
    ops2 = []
    for _tag, body in fb2.compile().action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.name == "AddShopItem":
                ops2.append(ins.imm(2))
    assert ops2 == [0]


def test_shop_stock_validation():
    import copy

    def mut(f):
        r = _stock_raw()
        f(r)
        return BT.validate(r)

    assert any("neither a [[shop]]" in p for p in
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0]["do"].update(
                   add_shop_item=[90, "Elixir"])))
    assert BT.validate(_stock_raw(do={"add_shop_item": [7, "Elixir"]})) == []  # vanilla 0-31 OK
    assert any("does not resolve" in p for p in
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0]["do"].update(
                   add_shop_item=[40, "Bogusite"])))
    assert any("needs `once" in p for p in
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0].pop("once")))
    assert any("takes [shop_id, item]" in p for p in
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0]["do"].update(
                   add_shop_item=40)))


def test_have_item_snapshot_precedes_pool_consumption():
    """THE ARMOURY ROUND-2 REGRESSION (owner-diagnosed): pool activation runs before
    the tree blocks, so a LIVE have_item read raced the pool's RemoveItem — buying
    exactly N contracts never satisfied `have_item >= N`. The cond must read a
    top-of-tick SNAPSHOT written BEFORE any pool consumes."""
    fb = _item_fb()
    cb = fb.compile()
    body = cb.ticker_body
    from ff9mapkit import items as IT
    iid = IT.resolve("Potion")
    m = fb._item_mirrors[iid]
    snap_off = pool_off = cond_off = None
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op != 0x05:
            if ins.name == "RemoveItem" and pool_off is None:
                pool_off = ins.off
            continue
        t = D.pretty_expr(body, ins.off + 1)[0]
        if "B_HAVE_ITEM" in t and f"Byte[{m}]" in t and snap_off is None:
            snap_off = ins.off                            # the snapshot write
        if f"Byte[{m}]" in t and "B_GE" in t and cond_off is None:
            cond_off = ins.off                            # the cond's mirror read
    assert snap_off is not None and pool_off is not None and cond_off is not None
    assert snap_off < pool_off < cond_off                 # snapshot -> consume -> judge


# ------------------------------------------- ShopSynth (AddShopSynthesis 0x116)
def _synth_raw(sel, **branch_over):
    br = {"when": [{"flag": "deep3"}],
          "do": {"add_shop_synth": [50, sel]}, "once": "synth2", **branch_over}
    return {
        "player": {"spawn": [0, -900]},
        "synthesis": [{"shop": 50, "recipes": [
            {"result": "Hi-Potion", "ingredients": ["Potion", "Potion"], "price": 60}]},
            {"shop": 51, "recipes": [
                {"result": "Phoenix Down", "ingredients": ["Potion", "Tent"], "price": 100}]}],
        "npc": [{"name": "crier", "pos": [0, -300], "dialogue": "..."}],
        "behavior": {"public_flags": ["deep3"], "unit": [
            {"npc": "crier", "branch": [br, {"do": {"hold": [0, -300]}}]},
        ]},
    }


def test_shop_synth_compiles_remove_then_add():
    """String selectors resolve via fb.synth_mints (injected here — no install
    dependency in tests); an add emits REMOVE then ADD of the 0x116 op."""
    raw = _synth_raw("Phoenix Down")
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"crier": 2},
                  npc_txids_by_name={"crier": 0}, behavior_txids={})
    from ff9mapkit import items as IT
    fb.synth_mints = {IT.resolve("Hi-Potion"): 64,           # keyed by RESOLVED item
                      IT.resolve("Phoenix Down"): 65}        # id (the mint map shape)
    cb = fb.compile()
    _verify_all(cb)
    ops = []
    for _tag, body in cb.action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.name == "AddShopSynthesis":
                ops.append((ins.imm(0), ins.imm(1), ins.imm(2)))
    assert ops == [(50, 65, 0), (50, 65, 1)]             # remove first, then add
    # an INT selector needs no mints map at all (a vanilla recipe row)
    fb2 = BT.build(_synth_raw(3), npc_slots={"crier": 2},
                   npc_txids_by_name={"crier": 0}, behavior_txids={})
    ops2 = []
    for _tag, body in fb2.compile().action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.name == "AddShopSynthesis":
                ops2.append(ins.imm(1))
    assert ops2 == [3, 3]


def test_shop_synth_unresolved_string_raises():
    fb = BT.build(_synth_raw("Phoenix Down"), npc_slots={"crier": 2},
                  npc_txids_by_name={"crier": 0}, behavior_txids={})
    fb.synth_mints = {}                                   # e.g. no reachable install
    with pytest.raises(B.BehaviorError, match="did not resolve"):
        fb.compile()


def test_shop_synth_validation():
    def mut(f):
        r = _synth_raw("Phoenix Down")
        f(r)
        return BT.validate(r)

    assert any("BUY shop" in p for p in                   # vanilla 0-31 = buy
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0]["do"].update(
                   add_shop_synth=[7, "Phoenix Down"])))
    assert any("BUY shop" in p for p in                   # a [[shop]] id here = buy
               mut(lambda r: r.update(shop=[{"id": 50, "sells": ["Potion"]}])))
    assert any("is not a [[synthesis]] result" in p for p in
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0]["do"].update(
                   add_shop_synth=[50, "Bogusite"])))
    assert any("needs `once" in p for p in
               mut(lambda r: r["behavior"]["unit"][0]["branch"][0].pop("once")))


# ------------------------------------------------- Sfx (RunSoundCode3 0xC8)
def _sfx_raw(do=None, **branch_over):
    br = {"when": [{"flag": "go"}], "do": do or {"sfx": 108},
          "once": "fanfare", **branch_over}
    return {
        "player": {"spawn": [0, -900]},
        "npc": [{"name": "crier", "pos": [0, -300], "dialogue": "..."}],
        "behavior": {"public_flags": ["go"], "unit": [
            {"npc": "crier", "branch": [br, {"do": {"hold": [0, -300]}}]},
        ]},
    }


def test_sfx_compiles_event_once():
    """Once-wrapped: ONE RunSoundCode3 with the chest-proven bank + pan/volume
    triple (content.chest — in-game on fields 200/407), on the event-Once lane."""
    raw = _sfx_raw()
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"crier": 2},
                  npc_txids_by_name={"crier": 0}, behavior_txids={})
    cb = fb.compile()
    _verify_all(cb)
    plays = []
    for _tag, body in cb.action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.name == "RunSoundCode3":
                plays.append(tuple(ins.imm(i) for i in range(5)))
    assert plays == [(53248, 108, 0, 128, 125)]           # bank, id, pan/volume
    # a custom bank passes through
    fb2 = BT.build(_sfx_raw(do={"sfx": 640, "bank": 4096}), npc_slots={"crier": 2},
                   npc_txids_by_name={"crier": 0}, behavior_txids={})
    plays2 = [(ins.imm(0), ins.imm(1))
              for _t, body in fb2.compile().action_funcs["crier"]
              for ins in D.iter_code(body, 0, len(body))
              if ins.name == "RunSoundCode3"]
    assert plays2 == [(4096, 640)]
    # sustain holds the level: play then Wait(N) BEFORE the run release (the
    # rung-C lesson — the event-once lane guarantees order, not duration)
    fb3 = BT.build(_sfx_raw(do={"sfx": 1942, "sustain": 55}),
                   npc_slots={"crier": 2}, npc_txids_by_name={"crier": 0},
                   behavior_txids={})
    seq = []
    for _t, body in fb3.compile().action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.name == "RunSoundCode3":
                seq.append("play")
            elif ins.op == 0x22:                  # Wait
                seq.append(("wait", ins.imm(0)))
    assert seq == ["play", ("wait", 55)]
    assert any("sfx sustain" in p for p in
               BT.validate(_sfx_raw(do={"sfx": 1942, "sustain": 999})))


def test_sfx_bare_and_validation():
    # BARE is legal (Announce's shape: play at dispatch, idle while selected)
    raw = _sfx_raw()
    del raw["behavior"]["unit"][0]["branch"][0]["once"]
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"crier": 2},
                  npc_txids_by_name={"crier": 0}, behavior_txids={})
    _verify_all(fb.compile())
    # id / bank / option-key validation
    assert any("sound id int" in p for p in BT.validate(_sfx_raw(do={"sfx": "boom"})))
    assert any("sound id int" in p for p in BT.validate(_sfx_raw(do={"sfx": 70000})))
    assert any("sfx bank" in p for p in
               BT.validate(_sfx_raw(do={"sfx": 108, "bank": "loud"})))
    assert any("unknown option key" in p for p in
               BT.validate(_sfx_raw(do={"sfx": 108, "volume": 5})))


def _theater_raw(swing_over=None, die_over=None, model="GEO_NPC_F3_CSO"):
    return {
        "player": {"spawn": [0, -900]},
        "npc": [{"name": "guard", "model": model, "pos": [0, 0], "dialogue": "!"},
                {"name": "beast", "model": "GEO_MON_F0_MUU", "pos": [400, 0],
                 "dialogue": "!"}],
        "behavior": {"unit": [
            {"npc": "guard", "hp": 5, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": True, **(die_over or {})}},
                {"when": [{"near": ["beast", 300]}],
                 "do": {"swing_at": "beast", **(swing_over or {})}},
                {"do": {"hold": [0, 0]}}]},
            {"npc": "beast", "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": True}},
                {"do": {"hold": [400, 0]}}]},
        ]},
    }


def test_swing_and_death_theater():
    """The strike's clip + hit cue ride the DAMAGE tick (inside the interval
    gate), and the death beat plays a clip + lingers BEFORE TerminateEntry —
    the fort-condor 'instant vanish' complaint. Gesture NAMES resolve against
    the unit's OWN model (the own-clip law)."""
    from ff9mapkit import catalog as C
    attack = C.own_form_gestures("GEO_NPC_F3_CSO")["attack_cid_1"]
    kneel = C.own_form_gestures("GEO_NPC_F3_CSO")["hiza_1"]
    raw = _theater_raw(swing_over={"anim": "attack_cid_1", "hit_sfx": 640},
                       die_over={"anim": "hiza_1", "linger": 45})
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"guard": 2, "beast": 3},
                  npc_txids_by_name={}, behavior_txids={})
    cb = fb.compile()
    _verify_all(cb)
    bodies = {}
    for tag, body in cb.action_funcs["guard"]:
        bodies[tag] = [(ins.op, ins.name) for ins in D.iter_code(body, 0, len(body))]
    flat = [op for ops in bodies.values() for op, _n in ops]
    assert 0x40 in flat                                   # RunAnimation emitted
    # the DEATH body: RunAnimation + WaitAnimation + Wait(45) BEFORE TerminateEntry
    death = next(body for _t, body in cb.action_funcs["guard"]
                 if any(i.op == 0x1C for i in D.iter_code(body, 0, len(body))))
    seq = []
    for ins in D.iter_code(death, 0, len(death)):
        if ins.op in (0x33, 0x34, 0x40):
            seq.append(({0x33: "stand", 0x34: "walk", 0x40: "anim"}[ins.op],
                        ins.imm(0)))
        elif ins.op == 0x3F:                              # SetAnimationFlags
            seq.append(("flags", ins.imm(0), ins.imm(1)))
        elif ins.op == 0x41:
            seq.append("waitanim")
        elif ins.op == 0x22:
            seq.append(("wait", ins.imm(0)))
        elif ins.op == 0x1C:                              # TerminateEntry
            seq.append("terminate")
    # run is HELD (255) for the whole beat and never released — a dead unit must
    # never dispatch again (the rung-E "still swinging after death" playtest)
    runs = [ins for ins in D.iter_code(death, 0, len(death)) if ins.op == 0x05]
    assert any("const(255)" in D.pretty_expr(death, i.off + 1)[0] for i in runs)
    # THE DEATH POSE, both halves playtest-driven: no WaitAnimation (round 2
    # rendered nothing), and the clip is installed as the object's STAND + WALK
    # animation before the one-shot — otherwise it ends and the model stands
    # back up (round 3's soldier), or a blocked march's walk clip overrides it
    # outright (round 3's raiders).
    # ... and FREEZE AT END (mode 1, 0 repeats): a stand clip loops by
    # definition, so without this the corpse replays its death for the whole
    # linger (round 4: "loop their death animation 3 times").
    assert seq == [("stand", kneel), ("walk", kneel), ("flags", 1, 0),
                   ("anim", kneel), ("wait", 45), "terminate"]
    # the SWING body: the clip is FIRE-AND-FORGET (no WaitAnimation would wedge
    # the loop) and the hit cue rides with it, both after the damage write
    swing = next(body for _t, body in cb.action_funcs["guard"]
                 if any(i.op == 0xC8 for i in D.iter_code(body, 0, len(body))))
    ops = [ins.name for ins in D.iter_code(swing, 0, len(swing))]
    assert "WaitAnimation" not in ops
    sw = [(ins.op, ins.imm(1) if ins.op == 0xC8 else ins.imm(0))
          for ins in D.iter_code(swing, 0, len(swing)) if ins.op in (0x40, 0xC8)]
    assert sw == [(0x40, attack), (0xC8, 640)]


def test_own_clip_law_refuses_a_foreign_gesture():
    """A gesture the model does not own is an ERROR naming what it does own —
    field MONSTER rigs carry no attack clip at all (MUU owns only locomotive
    gestures + jump), which is exactly the trap this catches."""
    probs = BT.validate(_theater_raw(swing_over={"anim": "attack_cid_1"},
                                     model="GEO_MON_F0_MUU"))
    assert any("owns no gesture 'attack_cid_1'" in p and "It owns:" in p
               for p in probs), probs


def _clock_raw(*, timer=60, stop=False, scene=35):
    br = [{"when": [{"hp_le": 0}], "do": {"battle": scene}, "raise_flags": ["lost"]},
          {"do": {"hold": [0, -300]}}]
    if stop:
        br.insert(0, {"when": [{"hp_le": 0}], "do": {"stop_timer": True},
                      "once": "clockstop"})
    b = {"unit": [{"npc": "base", "hp": 5, "branch": br}]}
    if timer is not None:
        b["timer"] = timer
    return {"player": {"spawn": [0, -900]},
            "npc": [{"name": "base", "pos": [0, -300], "dialogue": "..."}],
            "behavior": b}


def test_published_flags_are_visible_to_the_flag_lint():
    """The compiled ticker WRITES each pool's `hireable` gate and every declared
    public flag. A flag lint that only scans [[event]]s would call every generated
    hire menu dangling — the shipped [siege] example is what exposed it."""
    raw = {
        "player": {"spawn": [0, -900]},
        "npc": [{"name": "hand", "pos": [9000, 9000], "dialogue": "..."}],
        "behavior": {"public_flags": ["opened"],
                     "pool": [{"name": "hand", "price": 100}],
                     "unit": [{"npc": "hand", "pooled": True, "pool": "hand",
                               "branch": [{"do": {"hold_post": True}}]}]},
    }
    pub = BT.published_flags(raw)
    assert len(pub) == 2                       # the pool's hireable + the public flag
    assert all(isinstance(f, int) for f in pub)
    # deterministic across calls (the allocation contract the two-pass relies on)
    assert BT.published_flags(raw) == pub
    # never raises, whatever it is handed
    assert BT.published_flags({}) == set()
    assert BT.published_flags({"behavior": {"unit": [{"npc": "ghost"}]}}) == set()


def test_hud_digits_beyond_the_u16_reach_warns():
    """A width reserve wider than the value operand can ever carry. The sentinel rides
    SetTextVariable's u16 -> it saturates at 65535 (5 chars), so 6/7 silently mean 5.
    A WARNING, not an error: the accepted range stays 1..7 so existing fields build."""
    def hud(digits):
        return {"behavior": {"unit": [{"npc": "u", "hp": 5}],     # table() needs a unit row
                             "hud": [{"window": 6, "values": ["gil"],
                                      "text": "[NUMB=0]", "digits": digits}]}}
    w = BT.hud_digits_warnings(hud([6, 2, 2, 2]))
    assert len(w) == 1 and "[6]" in w[0] and "65535" in w[0]
    assert BT.hud_digits_warnings(hud(7))                    # a bare int, not a list
    assert BT.hud_digits_warnings(hud([7, 6]))[0].count(",") >= 1   # both named once
    for ok in (5, 2, [5, 5], [1, 2, 3, 4, 5]):               # everything reachable is silent
        assert BT.hud_digits_warnings(hud(ok)) == [], ok
    assert BT.hud_digits_warnings({"behavior": {"unit": [{"npc": "u"}]}}) == []   # no hud rows


def test_draining_condition_lint():
    """THE DRAINING-CONDITION LAW as a lint: N once-branches on one gate need it to
    hold for N consecutive ticks. Sticky gates are exempt; drainable ones warn."""
    def unit(branches):
        return {"player": {"spawn": [0, -900]},
                "npc": [{"name": "u", "pos": [0, 0], "dialogue": "."}],
                "behavior": {"timer": 60, "counters": ["kills", "seen"],
                             "scan": [{"name": "s", "units": ["u"], "point": [0, 0],
                                       "radius": 300, "count": "seen"}],
                             "unit": [{"npc": "u", "hp": 5, "branch": branches + [
                                 {"do": {"hold": [0, 0]}}]}]}}
    stack = lambda when: [                                   # noqa: E731
        {"when": when, "do": {"sfx": 1}, "once": "a"},
        {"when": when, "do": {"announce": "x"}, "once": "b"}]
    # DRAINABLE gates warn, and the message names the offending cond + the fix
    w = BT.draining_once_warnings(unit(stack([{"any_near": [["u"], 400]}])))
    assert len(w) == 1 and "any_near" in w[0] and "raise_flags" in w[0]
    assert BT.draining_once_warnings(unit(stack([{"have_item": ["Potion", 2]}])))
    assert BT.draining_once_warnings(unit(stack([{"counter_eq": ["kills", 3]}])))
    assert BT.draining_once_warnings(unit(stack([{"time_above": 30}])))
    # a counter a SCAN feeds rises AND falls -> counter_ge on it is NOT sticky
    assert BT.draining_once_warnings(unit(stack([{"counter_ge": ["seen", 2]}])))
    # STICKY gates are exempt: flags, a spent clock band, a dead unit, a tally
    for when in ([{"flag": "won"}], [{"not_flag": "won"}], [{"time_below": 1}],
                 [{"hp_le": 0}], [{"counter_ge": ["kills", 3]}]):
        assert BT.draining_once_warnings(unit(stack(when))) == [], when
    # ... unless something CLEARS that flag, which un-sticks it
    cleared = unit(stack([{"flag": "won"}]))
    cleared["behavior"]["unit"][0]["branch"][0]["clear_flags"] = ["won"]
    assert BT.draining_once_warnings(cleared)
    # ONE branch on a drainable gate is fine (nothing queues behind it)
    assert BT.draining_once_warnings(unit(
        [{"when": [{"any_near": [["u"], 400]}], "do": {"sfx": 1}, "once": "a"}])) == []


def test_siege_alarm_chain_latches_the_moment():
    """[siege]'s alarm gate (`any_near`) DRAINS, so its cue + lines latch a flag and
    the rest gate on it -- the law's own authoring fix, generated. Found by the lint
    above firing on the shipped generator."""
    from ff9mapkit.content import siege as S
    b = S.behavior_raw(S.from_raw({
        "timer": 60, "waves": [45], "alarm_sfx": 638, "text_alarm": ["one", "two"],
        "base": {"model": "GEO_NPC_F4_CSO", "pos": [0, 100]},
        "ally": [{"name": "g", "label": "G", "model": "GEO_NPC_F0_CSO", "count": 1,
                  "price": 100, "stance": "hold", "radius": 300}],
        "raider": [{"name": "r", "model": "GEO_MON_F0_MUU", "count": 1, "wave": 1,
                    "entrance": [[-800, -600]], "route": [[-400, 0]],
                    "autoroute": False}]}))
    chain = [x for x in b["unit"][0]["branch"]
             if str(x.get("once", "")).startswith("alarm")]
    assert [x["once"] for x in chain] == ["alarmcue", "alarm", "alarm1"]
    assert chain[0]["raise_flags"] == ["alarmed"]            # the cue latches
    assert all(x["when"] == [{"flag": "alarmed"}] for x in chain[1:])
    assert BT.draining_once_warnings({"behavior": b}) == []  # and the lint agrees


def test_clock_coupled_battle_lint():
    """THE CLOCK-COUPLED BATTLE LAW as a lint WARNING (not an error — stopping the
    clock makes the same design correct). Probe injected so the check is testable
    without a reachable install."""
    hunt = lambda s: s == 35            # noqa: E731 — the Hunt scene reads the clock
    warn = BT.clock_coupled_warnings(_clock_raw(), probe=hunt)
    assert len(warn) == 1
    assert "READS THE COUNTDOWN" in warn[0] and "stop_timer" in warn[0]
    # quiet when the law is already met, or there is no clock to expire, or the
    # scene ignores it, or the scene can't be read (unknown -> no claim)
    assert BT.clock_coupled_warnings(_clock_raw(stop=True), probe=hunt) == []
    assert BT.clock_coupled_warnings(_clock_raw(timer=None), probe=hunt) == []
    assert BT.clock_coupled_warnings(_clock_raw(scene=37), probe=hunt) == []
    assert BT.clock_coupled_warnings(_clock_raw(), probe=lambda s: None) == []
    # a probe that explodes must never break lint
    def boom(_s):
        raise RuntimeError("no install")
    assert BT.clock_coupled_warnings(_clock_raw(), probe=boom) == []
    # and the generated [siege] loss lane is quiet BY CONSTRUCTION (it stops the clock)
    from ff9mapkit.content import siege as S
    sraw = {"behavior": S.behavior_raw(S.from_raw({
        "timer": 60, "waves": [55, 40, 20], "loss_battle": 35,
        "base": {"model": "GEO_NPC_F4_CSO", "pos": [0, 400]},
        "ally": [{"name": "a", "label": "A", "model": "GEO_NPC_F0_CSO", "count": 1,
                  "price": 10, "stance": "hold", "radius": 300}],
        "raider": [{"name": "r", "model": "GEO_MON_F0_MUU", "count": 1, "wave": 1,
                    "entrance": [[-800, -600]], "route": [[-400, 0]],
                    "autoroute": False}]}))}
    assert BT.clock_coupled_warnings(sraw, probe=hunt) == []


def test_cross_form_clip_trap_is_refused():
    """THE CROSS-FORM CLIP TRAP (in-game, REDOUBT rung E): the CSO token's
    attack clips live only in the F3 form, and playing one on an F1 rig twists
    the model upside-down — a different FORM is a different SKELETON. The token
    join finds it, so this must be refused explicitly, not resolved."""
    from ff9mapkit import catalog as C
    assert "attack_cid_1" in C.animations_for_model("GEO_NPC_F1_CSO")   # token join
    assert "attack_cid_1" not in C.own_form_gestures("GEO_NPC_F1_CSO")  # ... not its rig
    probs = BT.validate(_theater_raw(swing_over={"anim": "attack_cid_1"},
                                     model="GEO_NPC_F1_CSO"))
    assert any("only in ANOTHER FORM" in p and "ANH_NPC_F3_CSO_ATTACK_CID_1" in p
               for p in probs), probs
    # the F0 soldier's kneel is genuinely its own; the F1 defender's is NOT
    assert "hiza_1" in C.own_form_gestures("GEO_NPC_F0_CSO")
    assert "hiza_1" not in C.own_form_gestures("GEO_NPC_F1_CSO")
    # a raw id passes through untouched (no model lookup at all)
    assert BT.validate(_theater_raw(swing_over={"anim": 7336})) == []
    # ... and is refused out of range / by type
    assert any("anim id must be" in p for p in
               BT.validate(_theater_raw(swing_over={"anim": 70000})))
    assert any("hit_sfx must be an int" in p for p in
               BT.validate(_theater_raw(swing_over={"hit_sfx": "boom"})))
    assert any("linger must be an int" in p for p in
               BT.validate(_theater_raw(die_over={"linger": 999})))


def test_announce_delay_sustain():
    """delay = a silent level-hold BEFORE the window opens (the staged-text
    primitive: the previous line's read time), sustain = the hold AFTER (ring
    before a queued Battle) — emission order pinned."""
    raw = _sfx_raw(do={"announce": "The city holds.", "delay": 120, "sustain": 30})
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"crier": 2}, npc_txids_by_name={"crier": 0},
                  behavior_txids={(0, 0): 905})
    seq = []
    for _t, body in fb.compile().action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.op == 0x22:                            # Wait
                seq.append(("wait", ins.imm(0)))
            elif ins.op == 0x20:                          # WindowAsync
                seq.append("open")
    assert seq == [("wait", 120), "open", ("wait", 30)]
    assert any("announce delay" in p for p in
               BT.validate(_sfx_raw(do={"announce": "x", "delay": 999})))
    assert any("announce sustain" in p for p in
               BT.validate(_sfx_raw(do={"announce": "x", "sustain": True})))


def test_flash_compiles_stock_add_pair():
    """The flash body is stock's ADD-channel white-out idiom (field 682, twice):
    CalcScreenPos + FadeFilter(0,24,255,rgb) + Wait(25 = out+1, stock's own
    pause) + the held beat + CalcScreenPos + FadeFilter(1,16,255,black) +
    Wait(16). NOT modes 6/7 — SUB toward white is the warp fade to BLACK
    (the REDOUBT round-2 playtest)."""
    raw = _sfx_raw(do={"flash": [255, 200, 120]})
    assert BT.validate(raw) == []
    fb = BT.build(raw, npc_slots={"crier": 2},
                  npc_txids_by_name={"crier": 0}, behavior_txids={})
    cb = fb.compile()
    _verify_all(cb)
    seq = []
    for _tag, body in cb.action_funcs["crier"]:
        for ins in D.iter_code(body, 0, len(body)):
            if ins.op == 0xEC:                            # FadeFilter
                seq.append(tuple(ins.imm(i) for i in range(6)))
            elif ins.op == 0xA9:                          # CalculateScreenPosition
                seq.append("csp")
            elif ins.op == 0x22:                          # Wait
                seq.append(("wait", ins.imm(0)))
    assert seq == ["csp", (0, 24, 255, 255, 200, 120), ("wait", 25), ("wait", 20),
                   "csp", (1, 16, 255, 0, 0, 0), ("wait", 16)]
    # pause is a dial (`hold` is the feed verb — the key would double-match);
    # pause = 0 drops its wait entirely
    fb2 = BT.build(_sfx_raw(do={"flash": [255, 255, 255], "pause": 0}),
                   npc_slots={"crier": 2}, npc_txids_by_name={"crier": 0},
                   behavior_txids={})
    waits = [ins.imm(0) for _t, body in fb2.compile().action_funcs["crier"]
             for ins in D.iter_code(body, 0, len(body)) if ins.op == 0x22]
    assert waits == [25, 16]
    # validation: three ints 0..255, no bool smuggling; pause range-checked
    assert any("flash takes [r, g, b]" in p for p in
               BT.validate(_sfx_raw(do={"flash": [255, 255]})))
    assert any("flash takes [r, g, b]" in p for p in
               BT.validate(_sfx_raw(do={"flash": [255, 300, 0]})))
    assert any("flash takes [r, g, b]" in p for p in
               BT.validate(_sfx_raw(do={"flash": True})))
    assert any("flash pause" in p for p in
               BT.validate(_sfx_raw(do={"flash": [255, 255, 255], "pause": 999})))
