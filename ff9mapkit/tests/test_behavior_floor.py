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


def _fold(F: str) -> str:
    return f"{F} {F} {F} const(255) B_EQ const(256) B_MULT B_MINUS B_LET"


def test_every_floor_read_is_followed_by_the_battle_byte_fold():
    """THE BATTLE-BYTE FOLD: a battle backs activeFloor up into a Byte, so an UNKNOWN (-1) floor comes back as
    255. Each mirror read is immediately followed by M -= (M == 255) * 256, which the calibrated interpreter shows
    maps 255 -> -1 and leaves -1..254 alone. [dropping the fold, or folding anything else, turns this red]"""
    fb, cb = compiled()
    ss = stmts(cb.ticker_body)
    reads = [i for i, t in enumerate(ss) if "B_BGIFLOOR" in t]
    assert reads
    for i in reads:
        F = ss[i].rsplit(" B_PTR(250)" if "B_PTR(250)" in ss[i] else " const(", 1)[0]   # the mirror written
        assert ss[i + 1] == _fold(F), (ss[i], ss[i + 1])
    Fp = fb._uref("player", "flr")
    rhs = f"{Fp} {Fp} const(255) B_EQ const(256) B_MULT B_MINUS"
    assert _fold(Fp) == f"{Fp} {rhs} B_LET"
    for v, want in ((255, -1), (-1, -1), (0, 0), (1, 1), (254, 254)):
        assert _eval(rhs, {Fp: v}) == want, v


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
        assert stmts(body[ins[k + 1].off:ins[k + 1].end]) == [_fold(F)]         # the battle-byte fold, then
        assert ins[k + 2].op == 0x01 and D.jump_target(ins[k + 2]) == tgt.end   # the live arm skips the off arm


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
    assert any('same_floor = "<target>"' in ln for ln in routes.describe_pursuit_problems("guard", plain))
    # [review] the gated sweep still TESTS pairs (a sweep of nothing reads clean) and drops EXACTLY the cross-floor
    # jams: every blocked pair on this mesh is cross-floor, so the same-floor half comes back clean
    assert gated["same_floor"] and gated["cross"] == 0 and 0 < gated["tested"] < plain["tested"]
    assert gated["blocked"] == plain["blocked"] - plain["cross"]
    lines = routes.describe_pursuit_problems("guard", gated)
    assert all("same-floor pairs only" in ln for ln in lines if ln.startswith("pursuit"))
    # ...and a SAME-floor jam is still reported: the ground floor with its south-east face cut out is an L, so a
    # straight leg across the notch leaves the mesh on its own floor
    from ff9mapkit.scene import bgi
    V = [(-1200, 0, 1200), (0, 0, 1200), (0, 0, 0), (-1200, 0, 0), (0, 0, -1200), (-1200, 0, -1200),
         (0, 0, 1200), (1200, 0, 1200), (1200, 0, 0), (0, 0, 0), (1200, 0, -1200), (0, 0, -1200)]
    F = [(0, 1, 2), (0, 2, 3), (3, 4, 5), (6, 7, 8), (6, 8, 9), (9, 8, 10), (9, 10, 11)]
    notch = bgi.build(V, F, floor_ids=[0, 0, 0, 1, 1, 1, 1])
    g2 = routes.sweep_pursuit(notch, 2400.0, standoff=100.0, same_floor=True)
    assert g2["tested"] > 0 and g2["blocked"] > 0 and g2["cross"] == 0, g2


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


@pytest.mark.parametrize("make", [
    lambda fb: fb.on_floor("pack", 0),
    lambda fb: fb.same_floor("pack", "player"),
    lambda fb: fb.any_of(fb.near("pack", "player", 300), fb.near("w", "player", 300)),
])
def test_a_class_self_is_refused_outside_its_own_tree(make):
    """[review] A CLASS name as the SELF reads the strided cell at MYUID -- in an unclassed unit's tree that is a
    cell no mirror writes (zero-filled: on_floor('pack', 0) read a KNOWN floor 0, always true). The Python API
    now refuses it at compile; the same Cond inside the class's own tree compiles."""
    def field():
        return B.FieldBehavior([B.UnitSpec("w", 2, (0, 0)), B.UnitSpec("c0", 5, (100, 0)),
                                B.UnitSpec("c1", 6, (200, 0))], brains=True,
                               classes=[B.ClassSpec("pack", ("c0", "c1"))])
    fb = field()
    fb.units["w"].tree = B.Selector(B.Sequence(make(fb), B.Do(B.Hold((50, 50)))), B.Do(B.Hold((0, 0))))
    fb.classes["pack"].tree = B.Do(B.Hold((0, 0)))
    with pytest.raises(B.BehaviorError, match="reads class 'pack' as its SELF"):
        fb.compile()
    ok = field()
    ok.units["w"].tree = B.Do(B.Hold((0, 0)))
    ok.classes["pack"].tree = B.Selector(B.Sequence(make(ok), B.Do(B.Hold((50, 50)))), B.Do(B.Hold((0, 0))))
    ok.compile()


# ------------------------------------------------------------------------------------ the build-side wiring, end to end
# `o terrace` is DECLARED first but has no faces until after `o ground`'s: built floors number by first appearance
# among the FACES, so ground = 0 and terrace = 1 (a declaration-order resolver would swap them)
_WIRE_OBJ = """v -600 0 -200
v 0 0 -200
v 0 0 -1400
v -600 0 -1400
v 0 0 -200
v 600 0 -200
v 600 0 -1400
v 0 0 -1400
o terrace
o ground
f 1 2 3
f 1 3 4
o terrace
f 5 6 7
f 5 7 8
"""
_WIRE_TOML = """[field]
id = 30998
name = "FLW"
area = 11
[camera]
pitch = 45
[walkmesh]
{walk}
[player]
spawn = [-300, -800]
[[npc]]
name = "bell"
pos = [-300, -600]
[behavior]
  [[behavior.unit]]
  npc = "bell"
    [[behavior.unit.branch]]
    when = [{{ on_floor = "{floor}", who = "player" }}]
    do = {{ hold_post = true }}
    [[behavior.unit.branch]]
    do = {{ hold_post = true }}
"""


def _wire(tmp_path, floor="terrace", walk='obj = "w.obj"', obj=True):
    from ff9mapkit import build
    if obj:
        (tmp_path / "w.obj").write_text(_WIRE_OBJ, encoding="utf-8")
    t = tmp_path / "flw.field.toml"
    t.write_text(_WIRE_TOML.format(floor=floor, walk=walk), encoding="utf-8")
    return build.FieldProject.load(t), t


def test_the_build_resolves_a_floor_name_to_its_built_index(tmp_path):
    """[review] The build-side table (build.behavior_floor_table), not a test fixture: the name resolves against
    the SHIPPED mesh's first-appearance numbering, and the compiled condition compares the player's mirror with it."""
    from ff9mapkit import build
    proj, _ = _wire(tmp_path)
    ft = build.behavior_floor_table(proj)
    assert (ft.names, ft.count) == ({"ground": 0, "terrace": 1}, 2)
    assert build.lint_behavior_compile(proj) == []
    fb, cb = BT.dry_compile(proj.raw, floors=ft)
    want = f"{fb._uref('player', 'flr')} const(1) B_EQ"
    assert any(want in t for body in all_bodies(cb).values() for t in stmts(body)), want


def test_an_unknown_floor_name_is_a_lint_error_and_a_clean_cli_error(tmp_path, capsys):
    """[review] lint and `behavior compile`/`view` refuse an unknown name with a message -- compile used to die in
    dry_compile with a traceback."""
    from ff9mapkit import build, cli
    proj, t = _wire(tmp_path, floor="attic")
    errs = build.lint_behavior_compile(proj)
    assert errs and "attic" in errs[0], errs
    for verb in ("compile", "view", "lint"):
        assert cli.main(["behavior", verb, str(t)]) == 1
        cap = capsys.readouterr()
        text = cap.err + cap.out                                  # lint reports on stdout, compile/view on stderr
        assert "error:" in text and "attic" in text and "Traceback" not in text, (verb, text)


def test_a_floor_table_that_cannot_resolve_refuses_compile(tmp_path, capsys):
    """[review] The mesh is missing: compile used to run with PLACEHOLDER floors (every name read as floor 0) and
    print a clean report. Now it is the same error lint gives."""
    from ff9mapkit import cli
    _p, t = _wire(tmp_path, obj=False)
    assert cli.main(["behavior", "compile", str(t)]) == 1
    assert "floor table" in capsys.readouterr().err


def test_a_quad_mesh_is_one_nameless_floor_and_lint_says_so(tmp_path):
    from ff9mapkit import build
    proj, _ = _wire(tmp_path, floor="0", walk="quad = [[-600, -200], [600, -200], [600, -1400], [-600, -1400]]")
    proj.raw["behavior"]["unit"][0]["branch"][0]["when"][0]["on_floor"] = 0
    ft = build.behavior_floor_table(proj)
    assert (ft.names, ft.count) == ({}, 1)
    rep = build.lint_all(proj)
    assert any("ONE-floor walkmesh" in w for w in rep.logic), rep.logic


def test_a_borrow_reads_the_donor_mesh_beside_its_camera_or_warns_unchecked(tmp_path):
    """[review] A hand-written BG-borrow (no reference, no sibling walkmesh.bgi) left every on_floor index
    unchecked and silent. The table now also reads the extract cache beside [camera] borrow; with no mesh at all
    it WARNS that the index is unchecked."""
    from ff9mapkit import build
    from ff9mapkit.scene import bgi
    field = tmp_path / "f"
    cache = field / "cache"
    cache.mkdir(parents=True)
    (cache / "w.obj").write_text(_WIRE_OBJ, encoding="utf-8")
    (cache / "walkmesh.bgi").write_bytes(bgi.obj_to_bgi(str(cache / "w.obj")))
    t = field / "b.field.toml"
    t.write_text(_WIRE_TOML.format(floor="0", walk="").replace(
        "[camera]\npitch = 45", '[camera]\npitch = 45\nborrow = "cache/camera.bgx"').replace(
        'area = 11', 'area = 11\nborrow_bg = "FBG_N00_TEST_MAP000_TS_ZZZ_0"'), encoding="utf-8")
    proj = build.FieldProject.load(t)
    proj.raw["behavior"]["unit"][0]["branch"][0]["when"][0]["on_floor"] = 7
    ft = build.behavior_floor_table(proj)
    assert ft.count == 2
    errs, _w = BT.floor_problems(proj.raw, ft)
    assert errs and "7" in errs[0], errs
    (cache / "walkmesh.bgi").unlink()
    ft = build.behavior_floor_table(proj)
    assert ft.count is None
    errs, warns = BT.floor_problems(proj.raw, ft)
    assert errs == [] and any("UNCHECKED" in w for w in warns), warns
