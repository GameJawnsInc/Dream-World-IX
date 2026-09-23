"""The walkmesh FLOOR sensor in [behavior] (studies/walkmesh-sensor/ rung 1): on_floor / same_floor / other_floor and
the floor:<who> HUD source. B_BGIFLOOR -- proven in-game at rung 0 -- is read ONLY in the ticker's mirror block
(THE SENSOR-MIRROR LAW); conditions read Int16 mirrors whose -1 means UNKNOWN (THE UNKNOWN-FLOOR LAW)."""
import copy
import re
import tomllib

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.eb import disasm as D

from ._ebengine import Engine

FIELD = '''
[[npc]]
name = "guard"
pos = [-400, -400]
[[npc]]
name = "watcher"
pos = [400, -400]
[[npc]]
name = "ghost"
pos = [0, -800]

[behavior]
public_flags = ["arm", "spawn_g"]
counters = ["seen"]

  [[behavior.unit]]
  npc = "guard"
    [[behavior.unit.branch]]
    when = [{ flag = "arm" }, { near = ["player", 900] }, { same_floor = "player" }]
    do = { chase = "player", standoff = 200 }
    [[behavior.unit.branch]]
    do = { hold_post = true }

  [[behavior.unit]]
  npc = "watcher"
    [[behavior.unit.branch]]
    when = [{ on_floor = "terrace", who = "player" }]
    do = { hold_post = true }
    raise_flags = ["p_up"]
    [[behavior.unit.branch]]
    when = [{ other_floor = "player" }]
    do = { hold_post = true }
    [[behavior.unit.branch]]
    do = { hold_post = true }

  [[behavior.unit]]
  npc = "ghost"
  pooled = true
  pool = "g"
    [[behavior.unit.branch]]
    when = [{ on_floor = [0, 1] }]
    do = { hold_post = true }
    [[behavior.unit.branch]]
    do = { hold_post = true }

  [[behavior.hud]]
  window = 6
  digits = [2, 2, 2]
  values = ["floor:player", "floor:guard", "floor:ghost"]
  text = "[MPOS=8,8]P [NUMB=0] G [NUMB=1] H [NUMB=2]"
'''
FLOORS = BT.FloorTable({"ground": 0, "terrace": 1}, 2, "test mesh")


def raw(text: str = FIELD) -> dict:
    return tomllib.loads(text)


def compiled(r=None, floors=FLOORS):
    return BT.dry_compile(r if r is not None else raw(), floors=floors)


def stmts(body: bytes) -> list:
    out = []
    for i in D.iter_code(body, 0, len(body)):
        if i.op == 0x05:
            t = D.pretty_expr(body, i.off + 1)[0].strip().strip("{}").strip()
            out.append(t[:-len(" B_EXPR_END")] if t.endswith(" B_EXPR_END") else t)
    return out


def all_bodies(cb) -> dict:
    out = {"ticker": cb.ticker_body, "main_init": cb.main_init}
    out.update({f"duty:{k}": v for k, v in cb.duty_bodies.items()})
    out.update({f"brain:{k}": v for k, v in cb.brain_bodies.items()})
    for k, funcs in cb.action_funcs.items():
        out.update({f"act:{k}:{t}": b for t, b in funcs})
    return out


# ------------------------------------------------------------------------------------ the truth table
def _eval(text: str, cells: dict) -> int:
    e = Engine()
    e.scalars.update(cells)
    return e.eval(text + " B_EXPR_END")


def test_the_three_verbs_never_hold_on_unknown():
    """The COMPILED condition texts, evaluated over every mirror state in {-1, 0, 1, 2}^2 by the calibrated
    interpreter: on_floor is never true at -1; same_floor iff equal and known; other_floor iff both known and
    different. [a dropped `>= 0` guard turns this red]"""
    fb, _ = compiled()
    Fp, Fg = fb._uref("player", "flr"), fb._uref("guard", "flr")
    on = fb.on_floor("player", [0, 1]).text
    same = fb.same_floor("guard", "player").text
    other = fb.other_floor("guard", "player").text
    for a in (-1, 0, 1, 2):
        for b in (-1, 0, 1, 2):
            cells = {Fg: a, Fp: b}
            assert _eval(on, cells) == int(b in (0, 1)), (a, b)
            assert _eval(same, cells) == int(a == b and a >= 0), (a, b)
            assert _eval(other, cells) == int(a != b and a >= 0 and b >= 0), (a, b)


# ------------------------------------------------------------------------------------ placement
def test_the_engine_token_runs_only_in_the_ticker_mirror_block():
    """THE SENSOR-MIRROR LAW: B_BGIFLOOR appears in exactly the ticker's mirror writes -- the player through
    B_PTR(250), each sensed unit through const(<entry>) (never B_PTR, which dereferences unchecked); no other
    body, and no B_BGIID anywhere."""
    fb, cb = compiled()
    hits = {name: [t for t in stmts(body) if "B_BGIFLOOR" in t or "B_BGIID" in t]
            for name, body in all_bodies(cb).items()}
    assert {k for k, v in hits.items() if v} == {"ticker"}
    reads = hits["ticker"]
    assert all(t.endswith("B_BGIFLOOR B_LET") and "B_BGIID" not in t for t in reads)
    assert f"{fb._uref('player', 'flr')} B_PTR(250) B_BGIFLOOR B_LET" in reads
    for u in ("guard", "ghost"):
        assert f"{fb._uref(u, 'flr')} const({fb.units[u].entry}) B_BGIFLOOR B_LET" in reads
    assert not any(re.search(r"B_PTR\((?!250\))", t) for t in reads)
    assert len(reads) == 1 + len([u for u in fb.units if u in fb._sensed])


def _ticker_ins(cb):
    body = cb.ticker_body
    return body, list(D.iter_code(body, 0, len(body)))


def test_a_sensed_units_read_is_inside_its_active_gate_and_its_off_arm_writes_unknown():
    """The read sits between the unit's `active` JMP_IFNOT and the off label; the JMP_IFNOT lands on the
    INACTIVE ARM, which writes -1 (warm-up, dormant pool, dead). [removing the arm or moving the read out of
    the gate turns this red]"""
    fb, cb = compiled()
    body, ins = _ticker_ins(cb)
    for u in ("guard", "ghost"):
        F = fb._uref(u, "flr")
        act = fb._uref(u, "active")
        k = next(i for i, x in enumerate(ins) if x.op == 0x05
                 and stmts(body[x.off:x.end]) == [f"{F} const({fb.units[u].entry}) B_BGIFLOOR B_LET"])
        g = max(i for i in range(k) if ins[i].op == 0x05 and stmts(body[ins[i].off:ins[i].end]) == [act])
        assert ins[g + 1].op == 0x02                                   # JMP_IFNOT on the active cell
        off = D.jump_target(ins[g + 1])
        assert all(ins[i].op not in D.JUMP_OPS for i in range(g + 2, k))   # straight line gate -> read
        tgt = next(x for x in ins if x.off == off)
        assert stmts(body[tgt.off:tgt.end]) == [f"{F} const(65535) B_LET"]  # -1 (the disassembler prints u16)
        assert ins[k + 1].op == 0x01 and D.jump_target(ins[k + 1]) == tgt.end   # the live arm skips it


def test_main_init_presets_every_sensed_mirror_to_unknown():
    fb, cb = compiled()
    mi = stmts(cb.main_init)
    for m in ("player", "guard", "watcher", "ghost"):
        assert f"{fb._uref(m, 'flr')} const(65535) B_LET" in mi, m      # -1, never a zero-filled floor 0


def test_a_pooled_units_activation_seeds_its_floor_from_the_players():
    """It spawns at the player's press-time position; its tree ticks the same pass -- so its floor is the
    player's, not UNKNOWN. The player is sensed automatically for it."""
    fb, cb = compiled()
    assert "player" in fb._sensed
    t = stmts(cb.ticker_body)
    seed = f"{fb._uref('ghost', 'flr')} {fb._uref('player', 'flr')} B_LET"
    assert seed in t
    assert t.index(seed) < t.index(f"{fb._uref('ghost', 'active')} const(1) B_LET")


def test_a_field_without_floor_verbs_senses_and_emits_nothing():
    r = raw()
    b = r["behavior"]
    for u in b["unit"]:
        for br in u["branch"]:
            br["when"] = [c for c in br.get("when", []) if not any(v in c for v in BT.FLOOR_VERBS)] or None
            if br["when"] is None:
                del br["when"]
    del b["hud"]
    assert not BT.wants_floors(r)
    fb, cb = BT.dry_compile(r)
    assert fb._sensed == {} and ".flr" not in fb.bb.report()
    assert not any("B_BGIFLOOR" in t for body in all_bodies(cb).values() for t in stmts(body))


# ------------------------------------------------------------------------------------ the laws
@pytest.mark.parametrize("text", ["const(3) B_BGIFLOOR const(1) B_EQ", "const(3) B_BGIID const(1) B_EQ",
                                  "B_PTR(250) B_ANGLEA const(1) B_EQ", "const(1) B_ANGLE const(1) B_EQ",
                                  "const(1) B_DISTANCE const(1) B_EQ", "const(1) B_FRAME const(1) B_EQ"])
def test_author_cond_text_may_not_read_an_object_or_the_sensor(text):
    fb, _ = compiled()
    with pytest.raises(B.BehaviorError, match="player-ref eval law"):
        fb.raw(text)
    assert fb.raw(text, unsafe_ok=True).text == text


def test_b_angle2_is_pure_math_and_stays_legal():
    fb, _ = compiled()
    assert fb.raw("const(1) const(2) B_ANGLE2 const(0) B_GT").text


def test_invert_refuses_a_floor_sensor_even_inside_a_composition():
    fb, _ = compiled()
    with pytest.raises(B.BehaviorError, match="UNKNOWN-FLOOR LAW"):
        B.Invert(fb.on_floor("player", 0))
    with pytest.raises(B.BehaviorError, match="UNKNOWN-FLOOR LAW"):
        B.Invert(fb.any_of(fb.flag("arm"), fb.same_floor("guard", "player")))
    B.Invert(fb.flag("arm"))                                            # an ordinary Cond still inverts


@pytest.mark.parametrize("neg", ["not_on_floor", "not_same_floor", "not_other_floor"])
def test_negated_floor_verbs_are_refused_by_name(neg):
    r = raw()
    r["behavior"]["unit"][1]["branch"][0]["when"] = [{neg: "player"}]
    with pytest.raises(BT.BehaviorTomlError, match="UNKNOWN-FLOOR LAW"):
        BT.dry_compile(r, floors=FLOORS)
    assert any("UNKNOWN-FLOOR LAW" in p for p in BT.validate(r))


# ------------------------------------------------------------------------------------ the TOML surface
def test_names_resolve_against_the_shipped_meshs_floors():
    w = raw()
    w["behavior"]["unit"][1]["branch"][0]["when"] = [{"on_floor": ["ground", "terrace"], "who": "player"}]
    fb, _ = compiled(w)
    c = BT._build_cond(fb, "watcher", {"on_floor": ["terrace"], "who": "player"}, {}, "t", FLOORS)
    assert c.text == fb.on_floor("player", [1]).text


@pytest.mark.parametrize("value,floors,msg", [
    ("attic", FLOORS, "is not a floor of this field's walkmesh (test mesh); its floors are: 0 'ground', 1 'terrace'"),
    ("attic", BT.FloorTable({}, 3, "[walkmesh] bgi w.bgi"), "has no floor NAMES"),
    (-1, FLOORS, "-1 means 'unknown', never a floor"),
    (2, FLOORS, "does not exist — this walkmesh has 2 floor(s)"),
    ([], FLOORS, "1..8 floors"),
    (True, FLOORS, "a floor is an int index or an o/g name"),
])
def test_floor_resolution_errors(value, floors, msg):
    with pytest.raises(BT.BehaviorTomlError) as ei:
        BT._resolve_floors(value, floors, "ctx")
    assert msg in str(ei.value)
    r = raw()
    r["behavior"]["unit"][1]["branch"][0]["when"] = [{"on_floor": value, "who": "player"}]
    errs, _w = BT.floor_problems(r, floors)
    assert errs and msg in errs[0]


def test_placeholder_mode_is_recorded_and_the_real_build_needs_a_table():
    fb = BT.build(raw(), npc_slots=BT.placeholder_slots(raw()),
                  behavior_txids={("hud", 0): 0})
    assert fb.floor_placeholder is True
    fb2 = BT.build(raw(), npc_slots=BT.placeholder_slots(raw()), behavior_txids={("hud", 0): 0},
                   floors=FLOORS)
    assert fb2.floor_placeholder is False


def test_class_targets_and_self_comparisons_are_refused():
    r = raw()
    r["behavior"]["unit"][0]["branch"][0]["when"] = [{"same_floor": "guard"}]
    with pytest.raises(B.BehaviorError, match="compared with itself"):
        BT.dry_compile(r, floors=FLOORS)
    assert any("compares the unit with itself" in p for p in BT.validate(r))
    r2 = raw()
    r2["behavior"]["unit"][1]["branch"][0]["when"] = [{"on_floor": 0, "who": "nobody"}]
    assert any("who = 'nobody' is not a behavior unit or player" in p for p in BT.validate(r2))


def test_one_floor_mesh_and_misleading_floor_n_names_warn():
    _e, w = BT.floor_problems(raw(), BT.FloorTable({}, 1, "[walkmesh] quad"))
    assert w and all("ONE-floor walkmesh" in x for x in w)
    r = raw()
    r["behavior"]["unit"][1]["branch"][0]["when"] = [{"on_floor": "floor_1", "who": "player"}]
    _e, w = BT.floor_problems(r, BT.FloorTable({"floor_1": 0, "floor_0": 1}, 2, "blender export"))
    assert any("'floor_1' is BUILT floor 0, not 1" in x for x in w)


def test_wants_floors_sees_verbs_and_hud_sources():
    assert BT.wants_floors(raw())
    r = raw()
    for u in r["behavior"]["unit"]:
        for br in u["branch"]:
            br.pop("when", None)
    assert BT.wants_floors(r)                                           # the floor: HUD rows
    del r["behavior"]["hud"]
    assert not BT.wants_floors(r)


# ------------------------------------------------------------------------------------ the HUD source
def test_the_floor_hud_source_reads_the_same_mirror_a_condition_reads():
    fb, cb = compiled()
    assert fb._hud_ref("floor:guard") == fb._uref("guard", "flr")
    assert any(t.startswith("floor sensors") or "floor sensors" in t for t in cb.report.splitlines())


@pytest.mark.parametrize("value,msg", [("floor:nobody", "is not a behavior unit"),
                                       ("floor:guardians", "is not a behavior unit")])
def test_the_floor_hud_source_refuses_non_units(value, msg):
    r = raw()
    r["behavior"]["hud"][0]["values"][1] = value
    with pytest.raises(B.BehaviorError, match=msg):
        BT.dry_compile(r, floors=FLOORS)
    assert any("not a [[behavior.unit]] npc or 'player'" in p for p in BT.validate(r))


def test_a_floor_source_is_refused_in_a_TEXT_slot_and_warns_when_too_narrow():
    r = raw()
    r["behavior"]["hud"][0]["text"] = "[MPOS=8,8]P [TEXT=1,0] G [NUMB=1] H [NUMB=2]"
    with pytest.raises(B.BehaviorError, match=r"turn UNKNOWN \(-1\) into row 0"):
        BT.dry_compile(r, floors=FLOORS)
    assert any("turn UNKNOWN (-1) into row 0" in p for p in BT.validate(r))
    r2 = raw()
    r2["behavior"]["hud"][0]["digits"] = [1, 2, 2]
    assert any("can show -1" in w for w in BT.hud_digits_warnings(r2))


# ------------------------------------------------------------------------------------ brains + classes
def test_brains_unclassed_conditions_read_the_same_global_mirror():
    fb1, _ = compiled()
    r = raw()
    r["behavior"]["brains"] = True
    fb2, _ = compiled(r)
    assert fb1.same_floor("guard", "player").text == fb2.same_floor("guard", "player").text


CLASS_FIELD = '''
[[npc]]
name = "c0"
pos = [-400, -400]
[[npc]]
name = "c1"
pos = [400, -400]

[behavior]
brains = true
public_flags = ["arm"]
  [[behavior.unit]]
  npcs = ["c0", "c1"]
  class = "pack"
    [[behavior.unit.branch]]
    when = [{ flag = "arm" }, { same_floor = "player" }]
    do = { chase = "player", standoff = 250 }
    [[behavior.unit.branch]]
    do = { hold_post = true }
'''


def test_a_class_brain_reads_its_own_strided_floor_cell_and_members_are_written_by_entry():
    fb, cb = compiled(raw(CLASS_FIELD))
    tid = fb._cls_tids["cls.pack.flr"]
    assert fb._uref("pack", "flr") == f"const({tid}) {B.MYUID} B_VECTOR"
    reads = [t for t in stmts(cb.ticker_body) if "B_BGIFLOOR" in t]
    for m in ("c0", "c1"):
        assert f"const({tid}) const({fb.units[m].entry}) B_VECTOR const({fb.units[m].entry}) B_BGIFLOOR B_LET" \
            in reads
    brain = b"".join(cb.brain_bodies.values())
    assert any(f"const({tid}) {B.MYUID} B_VECTOR" in t for t in stmts(brain))
    for m in ("c0", "c1"):                                              # -1 per member, in the class seed
        assert fb._cls_values["cls.pack.flr"][fb.units[m].entry] == -1


def test_a_class_is_refused_as_a_target_or_a_who():
    r = raw(CLASS_FIELD)
    r["npc"].append({"name": "w", "pos": [0, -900]})
    r["behavior"]["unit"].append({"npc": "w", "branch": [{"when": [{"same_floor": "pack"}],
                                                          "do": {"hold_post": True}},
                                                         {"do": {"hold_post": True}}]})
    with pytest.raises(BT.BehaviorTomlError, match="names a CLASS"):
        BT.dry_compile(r, floors=FLOORS)
    assert any("names a CLASS" in p for p in BT.validate(r))
    # ...and as an on_floor `who` (outside its own brain a class's strided self cell is meaningless)
    r["behavior"]["unit"][1]["branch"][0]["when"] = [{"on_floor": 0, "who": "pack"}]
    with pytest.raises(BT.BehaviorTomlError, match="on_floor who = 'pack' names a CLASS"):
        BT.dry_compile(r, floors=FLOORS)
    assert any("on_floor who = 'pack' names a CLASS" in p for p in BT.validate(r))


# ------------------------------------------------------------------------------------ lint + tooling
def test_the_pursuit_ref_carries_the_branchs_floor_gate():
    refs = BT.pursuit_refs(raw())
    guard = next(x for x in refs if x["unit"] == "guard")
    assert guard["same_floor"] is True
    r = raw()
    r["behavior"]["unit"][0]["branch"][0]["when"] = [{"flag": "arm"}, {"near": ["player", 900]}]
    assert next(x for x in BT.pursuit_refs(r) if x["unit"] == "guard")["same_floor"] is False


def _lip_mesh():
    """Two floors split at x = 0, seamed only on the south half: the north half of x = 0 is a WALL."""
    from ff9mapkit.scene import bgi
    V = [(-1200, 0, 1200), (0, 0, 1200), (0, 0, 0), (-1200, 0, 0), (0, 0, -1200), (-1200, 0, -1200),
         (0, 0, 1200), (1200, 0, 1200), (1200, 0, 0), (0, 0, 0), (1200, 0, -1200), (0, 0, -1200)]
    F = [(0, 1, 2), (0, 2, 3), (3, 2, 4), (3, 4, 5), (6, 7, 8), (6, 8, 9), (9, 8, 10), (9, 10, 11)]
    m = bgi.build(V, F, floor_ids=[0, 0, 0, 0, 1, 1, 1, 1])
    edge = tuple(sorted(((0, 0, 0), (0, 0, -1200))))              # a seam matches ONE edge by world position
    linked, missing, _ = m.apply_seams([(0, edge, 1, edge)])
    assert (linked, missing) == (1, 0)
    return m


def test_the_same_floor_sweep_drops_cross_floor_pairs():
    from ff9mapkit.scene import routes
    m = _lip_mesh()
    plain = routes.sweep_pursuit(m, 2400.0, standoff=100.0)
    gated = routes.sweep_pursuit(m, 2400.0, standoff=100.0, same_floor=True)
    assert plain["blocked"] > 0 and plain["cross"] > 0
    assert gated["same_floor"] and gated["cross"] == 0 and gated["tested"] < plain["tested"]
    assert gated["blocked"] < plain["blocked"]
    lines = routes.describe_pursuit_problems("guard", gated)
    assert all("same-floor pairs only" in ln for ln in lines if ln.startswith("pursuit"))


def test_the_workspace_formats_the_who_option_and_the_sim_admits_it_cannot_sense():
    from ff9mapkit.workspace import behaviorscan as BS
    from ff9mapkit.workspace import behaviorsim as SIM
    assert BS.fmt_cond({"on_floor": 1, "who": "player"}) == "on_floor 1 who=player"
    sim = SIM.Sim(raw())
    sim.run_to(40)
    assert any("floor sensors" in n for n in sim.notes)


def test_the_schema_harvest_records_every_condition_verb_and_its_options():
    """The LIVE half of the vocabulary check (the shipped _fieldschema.py is the freshness half): run
    validate over a spy-wrapped raw and require every COND_VERBS key plus on_floor's `who` to be probed at
    behavior.unit.branch.when. Iterating the when dict (the old _one_verb) recorded nothing."""
    from ff9mapkit import fieldschema as fs
    rec = fs.Recorder()
    BT.validate(fs.wrap(copy.deepcopy(raw()), rec))
    got = rec.probes.get("behavior.unit.branch.when", set())
    assert set(BT.COND_VERBS) | {"who"} <= got, sorted(set(BT.COND_VERBS) - got)


def test_the_behavior_doc_example_builds():
    """The docs' Floors example is what authors copy: it validates and compiles as written against a mesh
    with a 'terrace' floor, and the guard's chase gate is the same_floor verb."""
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[1] / "docs" / "BEHAVIOR.md").read_text(encoding="utf-8")
    sect = doc[doc.index("## Floors"):]
    start = sect.index("```toml") + len("```toml")
    r = tomllib.loads('[[npc]]\nname = "guard"\npos = [0, 0]\n[[npc]]\nname = "bellringer"\npos = [300, 0]\n'
                      "[behavior]\n" + sect[start:sect.index("```", start)])
    assert BT.validate(r) == []
    fb, _cb = BT.dry_compile(r, floors=BT.FloorTable({"ground": 0, "terrace": 1}, 2, "doc mesh"))
    assert set(fb._sensed) == {"guard", "player"}
