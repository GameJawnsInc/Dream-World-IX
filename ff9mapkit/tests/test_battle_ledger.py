"""``[scene.ledger]`` -- a battle writes a field's persistent table (studies/fight-ledger/, rung 1).

Claims are pinned by RUNNING the emitted fragments through ``tests/_ebengine.BattleEngine`` -- calibrated first
(test_the_battle_interpreter_reproduces_rung_0) against the cells rung 0 MEASURED in-game from its hand-written
tag-9 body -- so each test is about what the bytes DO. Every guard has a twin or a mutation that proves the test
can fail. Synthetic, install-free fixtures (an EF_R007-shaped eb: entry 1 = the Fang's AI, entry 2 = the
Goblin's, which owns a tag-7 Reaction)."""
import random
import re
import textwrap

import pytest

from ff9mapkit.battle import battleai, event_data, ledger as L, scene_data
from ff9mapkit.battle.build import BattleBuildError, BattleProject, build_battle_mod, validate_battle
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.content import behavior as B
from ff9mapkit.eb import disasm as D
from ff9mapkit.eb import edit as _edit
from ff9mapkit.eb import exprasm, exprsem
from ff9mapkit.eb.model import EbScript

from ._ebengine import BattleEngine, Engine
from .test_battle import _battle_eb, _raw16

NAME, TID, N = "dwix_t", 6004880, 12
GID = TID + B.PERSIST_GUARD_OFFSET
W = B.persist_check_word(NAME, N)
FLAG_IDX = 8910
LIVE = {TID: [0] * N, GID: [W]}


def _stmt_body(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def goblin_eb(*, counter: bool = False, donor_tag9: bool = False) -> bytes:
    """EF_R007-shaped: entry 0 Main_Init, entry 1 (tags 0/1/5, no Reaction), entry 2 (tags 0/1/5/7)."""
    eb = _battle_eb([(2, 0x80)], n_ai=2)
    ret = bytes([0x04])
    for entry, tags in ((1, (1, 5)), (2, (1, 5, 7))):
        for tag in tags:
            eb = _edit.add_function(eb, entry, tag, _stmt_body(f"Instance.Byte[{tag}] const(1) B_LET") + ret)
    if counter:
        eb = _edit.add_function(eb, 2, 6, _stmt_body("Instance.Byte[6] const(1) B_LET") + ret)
    if donor_tag9:
        eb = _edit.add_function(eb, 2, 9, _stmt_body("Instance.Byte[9] const(1) B_LET") + ret)
    return eb


def goblin_raw16(*, flags0: int = 2, flags1: int = 0) -> bytes:
    raw = _raw16(typcount=2, monster_count=3)            # slots 0/2 -> type 0, slot 1 -> type 1
    raw = scene_data.with_mon_flags(raw, 0, flags0)      # the Goblin carries die_dmg, like EF_R007's
    return scene_data.with_mon_flags(raw, 1, flags1)


FIELD = f'''
[[flag]]
name = "slain"
index = {FLAG_IDX}

[[npc]]
name = "keeper"
model = "GEO_NPC_F0_CSO"
pos = [0, 0]

[behavior]
  [[behavior.table]]
  name = "{NAME}"
  id = {TID}
  persist = true
  values = {[0] * N}

  [[behavior.unit]]
  npc = "keeper"
    [[behavior.unit.branch]]
    do = {{ hold = [0, 0] }}
'''


def write_field(tmp_path, text: str = FIELD, name: str = "keep.field.toml"):
    (tmp_path / name).write_text(textwrap.dedent(text), encoding="utf-8")
    return name


SC_HEAD = {"monster_count": 3, "enemy": [{"slot": 0, "type": 0, "ai_entry": 2},
                                          {"slot": 1, "type": 0, "ai_entry": 2},
                                          {"slot": 2, "type": 1, "ai_entry": 1}]}


def scene(writes, **extra) -> dict:
    return {**SC_HEAD, **extra, "ledger": {"declared_in": "keep.field.toml", "table": NAME, "write": writes}}


def plan(tmp_path, writes, *, eb=None, raw16=None, field=FIELD, sc=None, **extra):
    write_field(tmp_path, field)
    sc = sc if sc is not None else scene(writes, **extra)
    r16, _ = scene_data.apply_scene_edits(raw16 if raw16 is not None else goblin_raw16(), sc)
    donor = eb if eb is not None else goblin_eb()
    mc = r16[9]
    from ff9mapkit.battle.build import _ai_entries, _compose_ai
    composed = _compose_ai(donor, sc, slot_types=[r16[16 + 12 * s] for s in range(mc)],
                           ai_entries=_ai_entries(sc, mc), atk_count=None)
    return L.plan(tmp_path, sc, raw16=r16, eb_donor=donor, eb_composed=composed)


def ok_plan(tmp_path, writes, **kw):
    p, errors, warnings = plan(tmp_path, writes, **kw)
    assert errors == [] and p is not None, errors
    return p


def splice(p, entry, tag):
    got = [sp for sp in p.splices if (sp.entry, sp.tag) == (entry, tag)]
    assert len(got) == 1, [(sp.entry, sp.tag) for sp in p.splices]
    return got[0]


def run(body: bytes, vectors, *, me: int, killer: int = 1, sv28=1, sv29=176, units=None) -> BattleEngine:
    """Run a fragment as enemy ``me``'s object (B_SYSLIST[1] = me), killed by player bit ``killer``."""
    units = units or {1: {70: 0, 36: 77, 35: 131}, 16: {36: 0, 35: 60}, 32: {36: 0, 35: 60}, 64: {36: 0, 35: 40}}
    return BattleEngine(vectors, syslist={0: killer, 1: me, 3: 16 | 32 | 64},
                        sysvar={28: sv28, 29: sv29, 191: 30880}, units=units).run(body)


# ---------------------------------------------------------------------------------------- calibration
def test_the_battle_interpreter_reproduces_rung_0():
    """Calibrate the instrument FIRST: rung 0's hand-written scene-B tag-9 source (verbatim from its bench),
    run with the state rung 0 MEASURED, must produce the cells rung 0 read back from the save."""
    import tomllib
    from pathlib import Path
    bench = Path(__file__).resolve().parents[2] / "studies" / "fight-ledger" / "bench" / "scene_b" / "battle.toml"
    src = tomllib.loads(bench.read_text(encoding="utf-8"))["scene"]["ai_function"][0]["source"]
    from ff9mapkit.eb import cmdasm
    body = cmdasm.assemble_block(src)
    e = BattleEngine({6004870: [0] * 16}, syslist={0: 1, 1: 16, 3: 16}, sysvar={28: 1, 29: 176},
                     units={1: {35: 131}, 16: {36: 0}}).run(body)
    assert e.vec[6004870][8:15] == [1, 1, 1, 176, 0, 131, 1]           # rung 0's measured cells 8..14
    assert e.scalars["Global.Bit[8901]"] == 1


# ---------------------------------------------------------------------------------------- the gate
def _eval(vec, text):
    return Engine(vec).eval(text)


@pytest.mark.parametrize("state", [
    {}, {TID: [0] * N}, {TID: [0] * N, GID: [W ^ 1]}, {TID: [0] * (N - 1), GID: [W]},
    {TID: [0] * (N + 1), GID: [W]}, {TID: [0] * N, GID: [W]}])
def test_live_is_the_exact_negation_of_stale(state):
    live = _eval(state, B.persist_live_expr(NAME, TID, N))
    stale = _eval(state, B.persist_stale_expr(NAME, TID, N))
    assert live == int(not stale)
    assert live == int(state == LIVE)


STALE = {"never seeded": {}, "guard missing": {TID: [0] * N}, "foreign word": {TID: [0] * N, GID: [W ^ 1]},
         "n-1 cells": {TID: [0] * (N - 1), GID: [W]}, "n+1 cells": {TID: [0] * (N + 1), GID: [W]}}
ALL_ROWS = [
    {"on": "init", "slot": 0, "cell": 0, "set": 2}, {"on": "init", "slot": 0, "cell": 1, "add": 1},
    {"on": "reaction", "slot": [0, 1], "cell": 2, "add": 1}, {"on": "reaction", "slot": 1, "cell": 3, "set": "hp"},
    {"on": "dying", "slot": [0, 1], "cell": N - 1, "set": 1}, {"on": "dying", "slot": 1, "cell": 5, "set": "killer"},
    {"on": "dying", "slot": 1, "flag": "slain", "set": 1}]


@pytest.mark.parametrize("why", sorted(STALE))
def test_the_gate_leaves_every_stale_table_untouched_and_flags_still_land(tmp_path, why):
    p = ok_plan(tmp_path, ALL_ROWS)
    for sp in p.splices:
        for me in (16, 32):
            e = run(sp.body, STALE[why], me=me)
            assert e.vec == STALE[why], (why, sp.note)                  # never created, appended, grown
    e = run(splice(p, 2, 9).body, STALE[why], me=32)
    assert e.scalars.get(f"Global.Bit[{FLAG_IDX}]") == 1                # the flag is outside the gate


def test_twin_without_the_gate_the_same_writes_would_create_and_append():
    """The fixture CAN fail: ungated, a never-seeded save gets a table CREATED, and index n APPENDS."""
    ref = f"{B._cnum(TID)} {B._cnum(0)} B_VECTOR"
    e = BattleEngine({}).run(_stmt_body(f"{ref} const(2) B_LET"))
    assert e.vec == {TID: [2]}
    e = BattleEngine({TID: [0] * N, GID: [W]}).run(_stmt_body(f"{B._cnum(TID)} {B._cnum(N)} B_VECTOR const(1) B_LET"))
    assert len(e.vec[TID]) == N + 1


def test_live_table_takes_the_writes(tmp_path):
    """Cells start at a sentinel (99) and the killer is Steiner (CharacterId 3), so every asserted value is one
    the fragment WROTE -- a zero-seeded table would pass with no write at all."""
    p = ok_plan(tmp_path, ALL_ROWS)
    live = {TID: [99] * N, GID: [W]}
    e = run(splice(p, 2, 0).body, live, me=16)
    assert e.vec[TID][:2] == [2, 100]
    units = {1: {70: 3, 36: 77}, 32: {36: 0}}
    e = run(splice(p, 2, 9).body, live, me=32, units=units)
    assert e.vec[TID][5] == 3 and e.vec[TID][N - 1] == 1                 # killer = CharacterId 3 (Steiner)
    assert e.vec[TID][2] == 100 and e.vec[TID][3] == 0                   # the REPLAYED reaction rows: add, hp set
    assert len(e.vec[TID]) == N


@pytest.mark.parametrize("src,hook,ctx,want", [
    ("field", "init", {"sysvar": {191: 30880}}, 30880),
    ("hp", "reaction", {"units": {16: {36: 41}}}, 41),
    ("command", "reaction", {"sysvar": {28: 3}}, 3),
    ("ability", "dying", {"sysvar": {29: 188}}, 188),
    ("killer", "dying", {"syslist": {0: 4}, "units": {4: {70: 2}}}, 2),
    ("killer_hp", "dying", {"syslist": {0: 2}, "units": {2: {36: 123}}}, 123),
])
def test_every_source_reads_its_own_engine_value(tmp_path, src, hook, ctx, want):
    """Each source's RPN reads the engine slot it claims, with a value no other source would produce."""
    p = ok_plan(tmp_path, [{"on": hook, "slot": 0, "cell": 4, "set": src}])
    body = splice(p, 2, L.HOOK_TAGS[hook]).body
    sl = {1: 16, **ctx.get("syslist", {})}
    e = BattleEngine({TID: [99] * N, GID: [W]}, syslist=sl, sysvar=ctx.get("sysvar", {}),
                     units=ctx.get("units", {})).run(body)
    assert e.vec[TID][4] == want


def test_a_flag_row_is_scoped_to_its_slot(tmp_path):
    """Goblin A (slot 0) shares entry 2's tag 9 with Goblin B: B's story flag must not fire on A's death."""
    p = ok_plan(tmp_path, [{"on": "dying", "slot": 1, "flag": "slain", "set": 1},
                           {"on": "dying", "slot": 0, "cell": 0, "set": 1}])
    body = splice(p, 2, 9).body
    assert f"Global.Bit[{FLAG_IDX}]" not in run(body, LIVE, me=16).scalars
    assert run(body, LIVE, me=32).scalars.get(f"Global.Bit[{FLAG_IDX}]") == 1


# ---------------------------------------------------------------------------------------- the slot filter
def test_the_self_filter_scopes_rows_to_their_slot(tmp_path):
    p = ok_plan(tmp_path, [{"on": "init", "slot": 0, "cell": 1, "add": 1},
                           {"on": "reaction", "slot": 1, "cell": 3, "add": 1}])
    init = splice(p, 2, 0).body                         # both Goblins run entry 2's Init
    vec = {k: list(v) for k, v in LIVE.items()}
    for me in (16, 32):
        vec = run(init, vec, me=me).vec
    assert vec[TID][1] == 1                             # counted ONCE per battle, not per Goblin
    assert run(splice(p, 2, 7).body, LIVE, me=16).vec[TID][3] == 0     # slot 0's object: not slot 1's row
    assert run(splice(p, 2, 7).body, LIVE, me=32).vec[TID][3] == 1


def test_twin_without_the_filter_both_goblins_would_count():
    """The fixture CAN fail: the same write without the filter runs once per object sharing the entry."""
    body = asm_add = _stmt_body(f"{B._cnum(TID)} const(1) B_VECTOR {B._cnum(TID)} const(1) B_VECTOR const(1) B_PLUS B_LET")
    vec = {k: list(v) for k, v in LIVE.items()}
    for me in (16, 32):
        vec = BattleEngine(vec, syslist={1: me}).run(body).vec
    assert vec[TID][1] == 2 and asm_add


def test_the_filter_constant_is_the_objects_battle_bit(tmp_path):
    p = ok_plan(tmp_path, [{"on": "init", "slot": s, "cell": s, "set": 1} for s in range(3)])
    for sp in p.splices:
        consts = re.findall(r"B_SYSLIST\[1\] const\((\d+)\) B_EQ", _text(sp.body))
        slots = [b.slot for b in p.bindings if b.entry == sp.entry]
        assert [int(c) for c in consts] == [16 << s for s in slots]


def test_bindings_are_the_rewritten_main_inits(tmp_path):
    p = ok_plan(tmp_path, [{"on": "init", "slot": 0, "cell": 0, "set": 1}])
    r16, _ = scene_data.apply_scene_edits(goblin_raw16(), SC_HEAD)
    types = [r16[16 + 12 * s] for s in range(3)]
    rewritten = event_data.rewrite_main_init(goblin_eb(), types, [2, 2, 1])
    s = EbScript.from_bytes(rewritten)
    inits = [i.imm(0) for i in s.instrs(s.entry(0).func_by_tag(0)) if i.op == 0x09]
    assert inits == [b.entry for b in p.bindings] == [2, 2, 1]


# ---------------------------------------------------------------------------------------- values
def test_values_are_clamped_to_the_persistent_fence(tmp_path):
    p = ok_plan(tmp_path, [{"on": "reaction", "slot": 0, "cell": 0, "add": 5},
                           {"on": "reaction", "slot": 0, "cell": 1, "add": -5},
                           {"on": "reaction", "slot": 0, "cell": 2, "set": "hp"}])
    vec = {TID: [999_999, -999_998] + [0] * (N - 2), GID: [W]}
    e = run(splice(p, 2, 7).body, vec, me=16, units={16: {36: 2_000_000}})
    assert e.vec[TID][:3] == [B.ADJUST_MAG_MAX, -B.ADJUST_MAG_MAX, B.ADJUST_MAG_MAX]
    e = run(splice(p, 2, 7).body, vec, me=16, units={16: {36: -2_000_000}})
    assert e.vec[TID][2] == -B.ADJUST_MAG_MAX


def test_property_no_store_ever_changes_the_tables_size(tmp_path):
    p = ok_plan(tmp_path, ALL_ROWS)
    rng = random.Random(4)
    for _ in range(600):
        n = rng.choice([0, N - 1, N, N, N, N + 1])
        vec = {TID: [rng.randint(-2_000_000, 2_000_000) for _ in range(n)]} if n else {}
        if rng.random() < 0.8:
            vec[GID] = [W if rng.random() < 0.8 else W + 1]
        before = {k: len(v) for k, v in vec.items()}
        sp = rng.choice(p.splices)
        e = run(sp.body, vec, me=rng.choice([16, 32, 64]), killer=rng.choice([1, 2, 4]),
                units={b: {36: rng.randint(-3_000_000, 3_000_000), 70: rng.randint(0, 11)} for b in (1, 2, 4, 16, 32, 64)})
        assert {k: len(v) for k, v in e.vec.items() if k in before} == before
        assert set(e.vec) == set(before)
        if vec.get(GID) == [W] and n == N:
            touched = [c for c, (a, b) in enumerate(zip(vec[TID], e.vec[TID])) if a != b]
            assert all(abs(e.vec[TID][c]) <= B.ADJUST_MAG_MAX for c in touched)


def _text(body: bytes) -> str:
    return "\n".join(D.pretty_expr(body, i.off + 1)[0] for i in D.iter_code(body, 0, len(body)) if i.op == 0x05)


def test_every_statement_balances_and_writes_only_a_cell_below_n_or_a_declared_flag(tmp_path):
    p = ok_plan(tmp_path, ALL_ROWS)
    for sp in p.splices:
        for ins in D.iter_code(sp.body, 0, len(sp.body)):
            if ins.op != 0x05:
                continue
            text = D.pretty_expr(sp.body, ins.off + 1)[0].strip().strip("{}").strip()
            a = exprsem.analyze(text)
            if not a.writes:
                continue
            assert len(a.writes) == 1 and text.count("B_LET") == 1, text
            lval = text.split(" B_LET")[0]
            m = re.match(r"const4\((\d+)\) const\((\d+)\) B_VECTOR", lval)
            if m:
                assert int(m.group(1)) == TID and int(m.group(2)) < N, text
            else:
                assert lval.startswith(f"Global.Bit[{FLAG_IDX}]"), text
            assert "B_VECTOR_SIZE" not in lval and str(GID) not in lval


# ---------------------------------------------------------------------------------------- hooks
def test_hook_names_are_the_kits_tag_labels():
    assert {h: battleai._tag_role(t).lower() for h, t in L.HOOK_TAGS.items()} == {h: h for h in L.HOOK_TAGS}


def test_the_legality_table_refuses_stale_reads():
    assert L.SOURCES["hp"].why_not("init") and L.SOURCES["hp"].why_not("dying") and not L.SOURCES["hp"].why_not("reaction")
    for src in ("killer", "killer_hp"):
        assert L.SOURCES[src].why_not("init") and L.SOURCES[src].why_not("reaction") and not L.SOURCES[src].why_not("dying")
    for src in ("command", "ability"):
        assert L.SOURCES[src].why_not("init") and not L.SOURCES[src].why_not("reaction")
    assert not any(L.SOURCES["field"].why_not(h) for h in L.HOOK_TAGS)
    for src in L.SOURCES:                               # every source's RPN balances to one value
        exprsem.analyze(f"{L.SOURCES[src].rpn} B_EXPR_END")


def test_replay_runs_reaction_rows_in_tag_9_exactly_when_tag_9_takes_the_lethal_effect(tmp_path):
    react = {"on": "reaction", "slot": 0, "cell": 2, "add": 1}
    # (a) a dying row: die_atk ORed, tag 9 added -> the reaction row is replayed there first
    p = ok_plan(tmp_path, [react, {"on": "dying", "slot": 0, "cell": 0, "set": 1}])
    assert "replay[c2+=1]" in splice(p, 2, 9).note
    # (b) no dying rows, no die_atk -> no tag 9 at all
    p = ok_plan(tmp_path, [react])
    assert all(sp.tag != 9 for sp in p.splices)
    # (c) die_atk natively but no tag 9 -> the engine runs tag 7 on the lethal hit: no replay
    p = ok_plan(tmp_path, [react], raw16=goblin_raw16(flags0=3))
    assert all(sp.tag != 9 for sp in p.splices)
    # (d) die_atk + a stock tag 9, only reaction rows -> replayed INTO the stock tag 9 (prepended)
    p = ok_plan(tmp_path, [react], raw16=goblin_raw16(flags0=3), eb=goblin_eb(donor_tag9=True))
    sp = splice(p, 2, 9)
    assert sp.mode == "prepend" and "replay[c2+=1]" in sp.note


def test_splice_modes_and_the_ledger_goes_after_ai_insert(tmp_path):
    p = ok_plan(tmp_path, [{"on": "reaction", "slot": 2, "cell": 4, "add": 1},      # the Fang: entry 1, no tag 7
                           {"on": "reaction", "slot": 0, "cell": 2, "add": 1},      # entry 2 has tag 7
                           {"on": "dying", "slot": 0, "cell": 0, "set": 1}])
    assert splice(p, 1, 7).mode == "add" and splice(p, 1, 7).body.endswith(bytes([0x04]))
    assert splice(p, 2, 7).mode == "prepend" and splice(p, 2, 9).mode == "add"
    # an author ai_insert at body offset K lands on the same instruction with and without the ledger
    ins = [{"entry": 2, "tag": 5, "at": 0, "source": "SET({Instance.Byte[30] const(7) B_LET B_EXPR_END})"}]
    p2, errors, _w = plan(tmp_path, [{"on": "reaction", "slot": 0, "cell": 2, "add": 1}], ai_insert=ins)
    assert errors == []
    from ff9mapkit.battle.build import _ai_entries, _compose_ai
    sc = scene([{"on": "reaction", "slot": 0, "cell": 2, "add": 1}], ai_insert=ins)
    r16, _ = scene_data.apply_scene_edits(goblin_raw16(), sc)
    composed = _compose_ai(goblin_eb(), sc, slot_types=[r16[16 + 12 * s] for s in range(3)],
                           ai_entries=_ai_entries(sc, 3), atk_count=None)
    final = L.apply(composed, p2)
    tag5 = lambda b: bytes(EbScript.from_bytes(b).data[EbScript.from_bytes(b).entries[2].func_by_tag(5).abs_start:
                                                         EbScript.from_bytes(b).entries[2].func_by_tag(5).abs_end])
    assert tag5(final) == tag5(composed)               # the ledger never touched tag 5


def test_die_atk_is_ored_into_only_the_dying_types(tmp_path):
    p, errors, warnings = plan(tmp_path, [{"on": "dying", "slot": 1, "cell": 0, "set": 1}])
    assert errors == [] and p.or_types == ((0, 2, 3),)
    assert any("die_atk added to type 0" in w and "(0, 1)" in w for w in warnings)
    out = L.apply_die_atk(goblin_raw16(), p)
    assert scene_data.mon_flags(out, 0) == 3 and scene_data.mon_flags(out, 1) == 0


# ---------------------------------------------------------------------------------------- refusals
BAD = [
    ({"on": "death", "slot": 0, "cell": 0, "set": 1}, "did you mean 'dying'"),
    ({"on": "init", "slot": 3, "cell": 0, "set": 1}, "monster_count = 3"),
    ({"on": "init", "slot": [0, 0], "cell": 0, "set": 1}, "unique ints"),
    ({"on": "init", "slot": 0, "set": 1}, "exactly one of cell"),
    ({"on": "init", "slot": 0, "cell": N, "set": 1}, "APPENDS"),
    ({"on": "init", "slot": 0, "cell": True, "set": 1}, "outside"),
    ({"on": "init", "slot": 0, "flag": "slian", "set": 1}, "not a [[flag]]"),
    ({"on": "init", "slot": 0, "cell": 0}, "exactly one of set / add"),
    ({"on": "init", "slot": 0, "flag": "slain", "add": 1}, "flag takes set = 0 or 1"),
    ({"on": "init", "slot": 0, "flag": "slain", "set": 2}, "0 or 1"),
    ({"on": "init", "slot": 0, "cell": 0, "set": 2_000_000}, "fence"),
    ({"on": "init", "slot": 0, "cell": 0, "set": "kiler"}, "did you mean 'killer'"),
    ({"on": "init", "slot": 0, "cell": 0, "set": "scene"}, "build-time constant"),
    ({"on": "init", "slot": 0, "cell": 0, "add": 0}, "nonzero"),
    ({"on": "init", "slot": 0, "cell": 0, "set": "hp"}, "binds this enemy's battle data"),
    ({"on": "init", "slot": 0, "cell": 0, "set": "ability"}, "call level"),
    ({"on": "reaction", "slot": 0, "cell": 0, "set": "killer"}, "only inside dying"),
    ({"on": "dying", "slot": 0, "cell": 0, "set": "hp"}, "always reads 0"),
    ({"on": "init", "slot": 0, "cell": 0, "set": 1, "tabel": 1}, "unknown key 'tabel'"),
]


@pytest.mark.parametrize("row,msg", BAD)
def test_refusal_matrix(tmp_path, row, msg):
    p, errors, _w = plan(tmp_path, [row])
    assert p is None and any(msg in e for e in errors), errors


def test_duplicate_writes_are_refused(tmp_path):
    _p, errors, _w = plan(tmp_path, [{"on": "init", "slot": [0, 1], "cell": 0, "set": 1},
                                     {"on": "init", "slot": 1, "cell": 0, "set": 2}])
    assert any("both write cell 0 on init for slot 1" in e for e in errors)


@pytest.mark.parametrize("field,msg", [
    (FIELD.replace("persist = true", "persist = false"), "ordinary table"),
    (FIELD.replace(f"id = {TID}", "id = 4200"), "outside the persistent band"),
    (FIELD.replace(f'name = "{NAME}"', 'name = "other"'), "not a persist = true"),
    (FIELD.split("  [[behavior.unit]]")[0], "never compiles"),
    ("[behavior\nbroken", "not readable TOML"),
    (FIELD.replace("index = 8910", "index = 8400"), "[[flag]] table is invalid"),
    (FIELD.replace(f"values = {[0] * N}", "values = 3"), "list of ints"),
    (FIELD + f'\n  [[behavior.table]]\n  name = "{NAME}"\n  id = 6004881\n  persist = true\n  values = [0]\n',
     "twice"),
])
def test_resolve_table_refuses_without_ever_raising_a_parse_error(tmp_path, field, msg):
    p, errors, _w = plan(tmp_path, [{"on": "init", "slot": 0, "cell": 0, "set": 1}], field=field)
    assert p is None and any(msg in e for e in errors), errors


def test_missing_declaring_field_and_monster_count(tmp_path):
    sc = scene([{"on": "init", "slot": 0, "cell": 0, "set": 1}])
    sc["ledger"]["declared_in"] = "nope.field.toml"
    _p, errors, _w = plan(tmp_path, None, sc=sc)
    assert any("not found" in e for e in errors)
    sc = {k: v for k, v in scene([{"on": "init", "slot": 0, "cell": 0, "set": 1}]).items() if k != "monster_count"}
    r16 = goblin_raw16()
    _p, errors, _w = L.plan(tmp_path, sc, raw16=r16, eb_donor=goblin_eb(), eb_composed=goblin_eb())
    assert any("monster_count" in e for e in errors)


def test_dying_refusals_non_dying_boss_explicit_flags_and_a_dormant_donor_tag9(tmp_path):
    dying = [{"on": "dying", "slot": 0, "cell": 0, "set": 1}]
    _p, errors, _w = plan(tmp_path, dying, raw16=goblin_raw16(flags0=4 | 2))
    assert any("non_dying_boss" in e for e in errors)
    sc = scene(dying)
    sc["enemy"] = [dict(sc["enemy"][0], flags=["die_dmg"])] + sc["enemy"][1:]
    _p, errors, _w = plan(tmp_path, None, sc=sc)
    assert any("REPLACES the type's flag word without die_atk" in e for e in errors)
    _p, errors, _w = plan(tmp_path, dying, eb=goblin_eb(donor_tag9=True))
    assert any("never run" in e for e in errors)
    # the fix-it the message names -- replace the donor tag 9 -- is accepted
    fixed = [{"entry": 2, "tag": 9, "replace": True, "source": "RET()"}]
    p, errors, _w = plan(tmp_path, dying, eb=goblin_eb(donor_tag9=True), ai_function=fixed)
    assert errors == [] and splice(p, 2, 9).mode == "prepend"


def test_reaction_on_a_countering_enemy_is_refused(tmp_path):
    rows = [{"on": "reaction", "slot": 0, "cell": 0, "add": 1}]
    _p, errors, _w = plan(tmp_path, rows, eb=goblin_eb(counter=True))
    assert any("Counter (tag 6)" in e for e in errors)
    p, errors, _w = plan(tmp_path, [{"on": "init", "slot": 0, "cell": 0, "set": 1},
                                    {"on": "dying", "slot": 0, "cell": 1, "set": 1}], eb=goblin_eb(counter=True))
    assert errors == [] and p is not None


def test_scene_key_near_miss_and_shape():
    assert any("did you mean [scene.ledger]" in e for e in L.scene_key_problems({"leger": {}}))
    assert L.scene_key_problems({k: 1 for k in L.KNOWN_SCENE_KEYS if k != "ledger"}) == []
    assert any("ONE table" in e for e in L.scene_key_problems({"ledger": [{}]}))


# ---------------------------------------------------------------------------------------- build
def _mint(tmp_path, body: str):
    (tmp_path / "BBG_B013.fbx").write_text("; fbx\n", encoding="ascii")
    sd = tmp_path / "scene"
    (sd / "eb").mkdir(parents=True, exist_ok=True)
    (sd / "mes").mkdir(parents=True, exist_ok=True)
    (sd / "dbfile0000.raw16.bytes").write_bytes(goblin_raw16())
    (sd / "btlseq.raw17.bytes").write_bytes(b"RAW17")
    for lang in LANGS:
        (sd / "eb" / f"{lang}.eb.bytes").write_bytes(goblin_eb())
        (sd / "mes" / f"{lang}.mes").write_bytes(b"MES")
    write_field(tmp_path)
    head = '''
        [battlemap]
        bbg = "BBG_B200"
        fbx = "BBG_B013.fbx"
        scene_id = 30990
        scene_name = "LEDGERT"
        [scene]
        monster_count = 3
        [[scene.enemy]]
        slot = 0
        type = 0
        ai_entry = 2
        [[scene.enemy]]
        slot = 1
        type = 0
        ai_entry = 2
        [[scene.enemy]]
        slot = 2
        type = 1
        ai_entry = 1
        [scene.ledger]
        declared_in = "keep.field.toml"
        table = "dwix_t"
    '''
    (tmp_path / "battle.toml").write_text(textwrap.dedent(head) + textwrap.dedent(body), encoding="utf-8")
    return BattleProject.load(tmp_path / "battle.toml")


ROWS_TOML = '''
    [[scene.ledger.write]]
    on = "init"
    slot = 0
    cell = 0
    set = 2
    [[scene.ledger.write]]
    on = "reaction"
    slot = [0, 1]
    cell = 2
    add = 1
    [[scene.ledger.write]]
    on = "dying"
    slot = 1
    cell = 5
    set = "killer"
    [[scene.ledger.write]]
    on = "dying"
    slot = 1
    flag = "slain"
    set = 1
'''


def test_build_ships_the_validated_plan_in_every_language(tmp_path):
    proj = _mint(tmp_path, ROWS_TOML)
    assert validate_battle(proj) == []
    info = build_battle_mod([proj], tmp_path / "dist")
    lay = ModLayout(tmp_path / "dist")
    ebs = {lay.battle_eb_path(lang, "LEDGERT").read_bytes() for lang in LANGS}
    assert len(ebs) == 1                                                 # identical splices in every language
    shipped = EbScript.from_bytes(ebs.pop())
    assert shipped.entries[2].func_by_tag(9) is not None                 # the added Dying
    raw16 = (lay.battle_scene_dir("LEDGERT") / "dbfile0000.raw16.bytes").read_bytes()
    assert scene_data.mon_flags(raw16, 0) == 3 and scene_data.mon_flags(raw16, 1) == 0
    assert any(ln.startswith(f"ledger {NAME}: id {TID}, {N} cells, check word {W}") for ln in info["ledger"])
    assert any("die_atk added" in w for w in info["warnings"])


def test_build_refuses_what_validate_refuses(tmp_path):
    proj = _mint(tmp_path, ROWS_TOML.replace("cell = 5", f"cell = {N}"))
    assert any("APPENDS" in p for p in validate_battle(proj))
    with pytest.raises(BattleBuildError, match="APPENDS"):
        build_battle_mod([proj], tmp_path / "dist")


def test_a_battle_without_a_ledger_reports_none(tmp_path):
    proj = _mint(tmp_path, "")
    txt = (tmp_path / "battle.toml").read_text(encoding="utf-8").split("[scene.ledger]")[0]
    (tmp_path / "battle.toml").write_text(txt, encoding="utf-8")
    info = build_battle_mod([BattleProject.load(tmp_path / "battle.toml")], tmp_path / "dist")
    assert info["ledger"] == []


def test_member_70_is_named_slot_no():
    from ff9mapkit.eb._membertable import member_name, member_selector
    assert member_name(70) == "slot_no" and member_selector("slot_no") == 70


# ---------------------------------------------------------------------------------------- docs + benches
def _doc_example() -> str:
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[1] / "docs" / "BATTLE_DESIGN.md").read_text(encoding="utf-8")
    i = doc.index("<!-- ledger-example -->")
    a = doc.index("```toml\n", i) + len("```toml\n")
    return doc[a:doc.index("```", a)]


def test_the_battle_design_example_validates(tmp_path):
    """The BATTLE_DESIGN.md example is real: its [scene] + [scene.ledger] validate against a declaring field
    built from the doc's own field example (ids/names/flags taken from the doc, not restated here)."""
    from pathlib import Path
    import tomllib
    doc = (Path(__file__).resolve().parents[1] / "docs" / "BATTLE_DESIGN.md").read_text(encoding="utf-8")
    i = doc.index("The declaring field (`village.field.toml`)")
    a = doc.index("```toml\n", i) + len("```toml\n")
    field = doc[a:doc.index("```", a)]
    field = '[[npc]]\nname = "elder"\nmodel = "GEO_NPC_F0_CSO"\npos = [0, 0]\n\n' + field
    sub = tmp_path / "battle"
    sub.mkdir()
    (tmp_path / "village.field.toml").write_text(field, encoding="utf-8")
    sc = tomllib.loads(_doc_example())["scene"]
    raw16 = scene_data.with_mon_flags(_raw16(typcount=3, monster_count=1), 0, 2)
    eb = goblin_eb()
    r16, _ = scene_data.apply_scene_edits(raw16, sc)
    from ff9mapkit.battle.build import _ai_entries, _compose_ai
    composed = _compose_ai(eb, sc, slot_types=[r16[16]], ai_entries=_ai_entries(sc, 1), atk_count=None)
    p, errors, _w = L.plan(sub, sc, raw16=r16, eb_donor=eb, eb_composed=composed)
    assert errors == [] and p is not None, errors
    assert p.table.name == "goblin_fight" and p.table.n == 4 and dict(p.table.flags)["goblin_slain"] == 8910


def test_the_rung1_bench_battles_resolve_their_ledgers():
    """The in-game benches keep resolving: their declared_in fields declare what the battles write."""
    from pathlib import Path
    import tomllib
    bench = Path(__file__).resolve().parents[2] / "studies" / "fight-ledger" / "bench"
    for scene_dir, n, word in (("scene_win", 12, 17972799), ("scene_stale", 13, 26511439)):
        sc = tomllib.loads((bench / scene_dir / "battle.toml").read_text(encoding="utf-8"))["scene"]
        t = L.resolve_table(bench / scene_dir, sc["ledger"])
        assert (t.n, t.word) == (n, word)
        writes, errors = L.parse_writes(sc["ledger"], t, sc["monster_count"])
        assert errors == [] and writes


# ---------------------------------------------------------------------------------------- review round
def test_a_multipart_master_takes_rows_and_a_slave_is_refused(tmp_path):
    """BTL_SCENE.GetMonGeoID: a SLAVE is TypeNo > 0 WITH the multipart bit; the master (type 0) carries the bit
    too, and every part's hits route to it -- so it must be writable, and the slave refused."""
    write_field(tmp_path)
    raw16 = _raw16(typcount=2, monster_count=2, put_flags=3)            # [(type 0, 3), (type 1, 3)]
    for slot, ok in ((0, True), (1, False)):
        sc = {"monster_count": 2, "ledger": {"declared_in": "keep.field.toml", "table": NAME,
                                              "write": [{"on": "init", "slot": slot, "cell": 0, "set": 1}]}}
        p, errors, _w = L.plan(tmp_path, sc, raw16=raw16, eb_donor=goblin_eb(), eb_composed=goblin_eb())
        assert (p is not None) == ok, errors
        if not ok:
            assert any("SLAVE" in e and "master" in e for e in errors), errors


def test_a_slot_whose_enemy_differs_between_patterns_is_refused(tmp_path):
    write_field(tmp_path)
    raw = bytearray(_raw16(patcount=2, typcount=2, monster_count=1))
    raw[8 + 56 + 8] = 1                                                  # pattern 1, slot 0 -> type 1
    sc = {"monster_count": 1, "ledger": {"declared_in": "keep.field.toml", "table": NAME,
                                         "write": [{"on": "dying", "slot": 0, "cell": 0, "set": 1}]}}
    r16, _ = scene_data.apply_scene_edits(bytes(raw), sc)
    _p, errors, _w = L.plan(tmp_path, sc, raw16=r16, eb_donor=goblin_eb(), eb_composed=goblin_eb())
    assert any("different enemy in different patterns" in e for e in errors), errors
    sc["enemy"] = [{"slot": 0, "type": 0}]                               # the fix the message names
    r16, _ = scene_data.apply_scene_edits(bytes(raw), sc)
    p, errors, _w = L.plan(tmp_path, sc, raw16=r16, eb_donor=goblin_eb(), eb_composed=goblin_eb())
    assert errors == [] and p is not None


@pytest.mark.parametrize("on", [["init"], {"a": 1}, 3, None])
def test_a_non_string_hook_is_a_clean_refusal(tmp_path, on):
    _p, errors, _w = plan(tmp_path, [{"on": on, "slot": 0, "cell": 0, "set": 1}])
    assert any("the hooks are init" in e for e in errors), errors


def test_an_unusable_declared_in_path_is_a_clean_refusal(tmp_path):
    sc = scene([{"on": "init", "slot": 0, "cell": 0, "set": 1}])
    sc["ledger"]["declared_in"] = "a\x00b.toml"
    _p, errors, _w = plan(tmp_path, None, sc=sc)
    assert any("not a usable path" in e for e in errors), errors


def test_explicit_flags_are_seen_through_a_string_slot(tmp_path):
    """apply_scene_edits int()s the slot, so the ledger must too, or it ORs die_atk over an explicit word."""
    sc = scene([{"on": "dying", "slot": 0, "cell": 0, "set": 1}])
    sc["enemy"] = [dict(sc["enemy"][0], slot="0", flags=["die_dmg"])] + sc["enemy"][1:]
    _p, errors, _w = plan(tmp_path, None, sc=sc)
    assert any("REPLACES the type's flag word without die_atk" in e for e in errors), errors


def test_command_in_init_is_refused_for_the_real_reason(tmp_path):
    _p, errors, _w = plan(tmp_path, [{"on": "init", "slot": 0, "cell": 0, "set": "command"}])
    assert any("stale command" in e for e in errors), errors


def test_the_build_runs_an_author_ai_insert_BEFORE_the_ledger_splice(tmp_path):
    """The shipped function must be [ledger fragment][author ai_insert][donor body]: the author's at = 0 is
    measured against the donor, and the ledger prepends last. Built through the real pipeline."""
    proj = _mint(tmp_path, ROWS_TOML + '''
    [[scene.ai_insert]]
    entry = 2
    tag = 7
    at = 0
    source = "SET({Instance.Byte[30] const(7) B_LET B_EXPR_END})"
    ''')
    assert validate_battle(proj) == []
    build_battle_mod([proj], tmp_path / "dist")
    shipped = EbScript.from_bytes(ModLayout(tmp_path / "dist").battle_eb_path("us", "LEDGERT").read_bytes())
    f = shipped.entries[2].func_by_tag(7)
    body = bytes(shipped.data[f.abs_start:f.abs_end])
    author = _stmt_body("Instance.Byte[30] const(7) B_LET")
    donor = _stmt_body("Instance.Byte[7] const(1) B_LET") + bytes([0x04])
    assert body.endswith(author + donor), body.hex()
    assert body.startswith(bytes([0x05])) and body.index(author) > 0     # the ledger's gate comes first
    assert B.persist_live_expr(NAME, TID, N) in _text(body[:body.index(author)])
