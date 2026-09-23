"""ROLL STREAMS in the behavior compiler -- [[behavior.stream]], branch ``roll``, seeded wander, ``stream:``.

The claims are pinned by RUNNING the compiled bytes through tests/_ebengine (calibrated on the roll-stream rung 0
in-game rows) against the oracle in content/rollstream.py -- for EVERY one of the 65536 states where it matters --
and every law has a test that goes red without it."""
import copy
import re
import textwrap
import tomllib

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.content import rollstream as R
from ff9mapkit.eb import disasm as D
from ff9mapkit.eb import exprsem

from ._ebengine import Engine

FIELD = '''
[[npc]]
name = "keeper"
model = "GEO_NPC_F0_CSO"
pos = [700, -400]
[[npc]]
name = "walker"
model = "GEO_NPC_F0_CSO"
pos = [0, -1100]

[behavior]
public_flags = ["draw_e", "draw_d", "draw_p"]
counters = ["pick", "die", "pickp", "tally0"]
  [[behavior.table]]
  name = "tally"
  values = [0, 0, 0, 0, 0, 0]
  [[behavior.stream]]
  name = "eph"
  seed = 1
  [[behavior.stream]]
  name = "dwix_rs1"
  seed = 1
  persist = true
  id = 6004900
  [[behavior.unit]]
  npc = "keeper"
    [[behavior.unit.branch]]
    when = [{ flag = "draw_e" }]
    roll = { stream = "eph", counter = "pick", range = [0, 5] }
    clear_flags = ["draw_e"]
    adjust = { table = "tally", index = "pick", by = 1, clamp = [0, 999] }
    do = { hold_post = true }
    [[behavior.unit.branch]]
    when = [{ flag = "draw_d" }]
    roll = { stream = "eph", counter = "die", range = [1, 6] }
    clear_flags = ["draw_d"]
    do = { hold_post = true }
    [[behavior.unit.branch]]
    when = [{ flag = "draw_p" }]
    roll = { stream = "dwix_rs1", counter = "pickp", range = [1, 100] }
    clear_flags = ["draw_p"]
    do = { hold_post = true }
    [[behavior.unit.branch]]
    do = { hold_post = true }
  [[behavior.unit]]
  npc = "walker"
    [[behavior.unit.branch]]
    do = { wander = [0, -1100], radius = 300, every = 45, seed = 1 }
'''


def raw(text: str = FIELD) -> dict:
    return tomllib.loads(textwrap.dedent(text))


def compiled(text: str = FIELD):
    return BT.dry_compile(raw(text))


def stmts(body: bytes) -> list:
    out = []
    for i in D.iter_code(body, 0, len(body)):
        if i.op == 0x05:
            t = D.pretty_expr(body, i.off + 1)[0].strip().strip("{}").strip()
            out.append(t[:-len(" B_EXPR_END")] if t.endswith(" B_EXPR_END") else t)
    return out


SIG = f"const({R.A}) B_MULT const4({R.M}) B_REM B_LET"


# ---------------------------------------------------------------------------------------- the oracle
def test_every_state_the_compiled_advance_and_draws_equal_the_oracle():
    """The EMITTED statements, run in the calibrated VM for every state 1..65536 (the advance, the [1, 100]
    draw, both wander axes), equal content/rollstream.py -- so the build's predictions ARE the game's."""
    fb, cb = compiled()
    texts = stmts(cb.ticker_body)
    info = fb.streams["dwix_rs1"]
    S = B.stream_ref(info.tid)
    adv = next(t for t in texts if t.startswith(f"{S} {S}") and SIG in t)
    draw = next(t for t in texts if "const(100) B_REM" in t)
    w = fb.wander_streams["walker"]
    WS = B.stream_ref(w.tid)
    wx = next(t for t in texts if f"{WS} const(256) B_REM" in t)
    wz = next(t for t in texts if f"{WS} const(256) B_DIV const(256) B_REM" in t)
    e = Engine()
    for s in range(1, R.M):
        e.vec = {info.tid: [s], fb._ctr_tid: [0] * 4, w.tid: [s]}
        e.eval(adv + " B_EXPR_END")
        assert e.vec[info.tid][0] == R.advance(s), s
    e = Engine()
    for s in range(1, R.M):
        e.vec = {info.tid: [s], fb._ctr_tid: [0] * 4, w.tid: [s]}
        e.eval(draw + " B_EXPR_END")
        assert e.vec[fb._ctr_tid][2] == R.roll_value(s, 1, 100), s
        e.eval(wx + " B_EXPR_END")
        e.eval(wz + " B_EXPR_END")
        tx, tz = (e.scalars[k] for k in sorted(e.scalars, key=lambda k: int(re.findall(r"\d+", k)[0])))
        assert (tx, tz) == R.wander_target(s, 0, -1100, 300), s


def test_one_advance_per_roll_and_per_seeded_wander_and_none_anywhere_else():
    fb, cb = compiled()
    assert sum(SIG in t for t in stmts(cb.ticker_body)) == 4          # 3 roll branches + 1 seeded wander
    assert not any(SIG in t for t in stmts(cb.main_init))
    for body in list(cb.duty_bodies.values()) + [b for fs in cb.action_funcs.values() for _t, b in fs]:
        assert not any(SIG in t for t in stmts(body))
    # the draw follows its own advance, never the other way round
    texts = stmts(cb.ticker_body)
    for i, t in enumerate(texts):
        if " B_REM" in t and SIG not in t and "B_SYSVAR" not in t and "const(256)" not in t:
            assert SIG in texts[i - 1], (texts[i - 1], t)


def test_every_stream_statement_balances():
    _fb, cb = compiled()
    for t in stmts(cb.ticker_body) + stmts(cb.main_init):
        exprsem.analyze(t + " B_EXPR_END")


def test_the_roll_runs_before_the_same_branchs_adjust():
    """adjust = { table = "tally", index = "pick" } sees the FRESH roll (the roll sits before adjust)."""
    fb, cb = compiled()
    texts = stmts(cb.ticker_body)
    eph = fb.streams["eph"]
    i_adv = next(i for i, t in enumerate(texts) if t.startswith(B.stream_ref(eph.tid)) and SIG in t)
    i_tally = next(i for i, t in enumerate(texts) if f"{B._cnum(fb.tables['tally'][0])} " in t and "B_PLUS" in t)
    assert i_adv < i_tally


# ---------------------------------------------------------------------------------------- Main_Init
def _main_init_state(vectors):
    fb, cb = compiled()
    e = Engine(copy.deepcopy(vectors)).run(cb.main_init)
    return fb, e


def test_main_init_seeds_the_ephemeral_stream_every_entry():
    fb, _ = compiled()
    eph = fb.streams["eph"]
    _fb, e = _main_init_state({eph.tid: [12345]})
    assert e.vec[eph.tid] == [eph.x0]


@pytest.mark.parametrize("cell,kept", [(12345, True), (65536, True), (0, False), (70000, False), (-5, False),
                                       (65537, False)])
def test_the_persistent_stream_keeps_a_live_state_and_repairs_a_bad_one(cell, kept):
    fb, _ = compiled()
    p = fb.streams["dwix_rs1"]
    _fb, e = _main_init_state({p.tid: [cell], p.tid + B.PERSIST_GUARD_OFFSET: [p.word]})
    assert e.vec[p.tid] == ([cell] if kept else [p.x0])
    assert e.vec[p.tid + B.PERSIST_GUARD_OFFSET] == [p.word]


@pytest.mark.parametrize("guard", [[], [B.persist_check_word("dwix_rs1.lehmer237.65537", 1)],
                                   [B.persist_check_word("dwix_rs1", 1)]])
def test_a_foreign_or_older_generator_word_reseeds(guard):
    """The check word hashes the BACKING KEY, which folds the generator in: a 237-built stream, a table-shaped
    word, or no guard at all re-seed to x0."""
    fb, _ = compiled()
    p = fb.streams["dwix_rs1"]
    vecs = {p.tid: [4242]}
    if guard:
        vecs[p.tid + B.PERSIST_GUARD_OFFSET] = guard
    _fb, e = _main_init_state(vecs)
    assert e.vec[p.tid] == [p.x0] and e.vec[p.tid + B.PERSIST_GUARD_OFFSET] == [p.word]


def _strip_streams(r: dict) -> dict:
    b = r["behavior"]
    del b["stream"]
    for u in b["unit"]:
        for br in u["branch"]:
            br.pop("roll", None)
            if isinstance(br.get("do"), dict):
                br["do"].pop("seed", None)
    return r


def test_adding_streams_moves_no_declared_table_or_counter_id_and_a_stream_free_field_emits_none():
    """Streams allocate AFTER the declared tables and counters, so adding one to a field keeps every id those
    already had (compiled both ways here); a stream-free compile emits nothing stream-shaped. (Byte identity of
    every repo [behavior] toml was checked before/after the feature by compiling each one.)"""
    fb_s, _cb = compiled()
    fb, cb = BT.dry_compile(_strip_streams(raw()))
    assert not fb.streams and not fb.wander_streams
    assert all(SIG not in t for t in stmts(cb.ticker_body) + stmts(cb.main_init))
    assert fb.tables["tally"][0] == fb_s.tables["tally"][0] == B.TABLE_ID_BASE
    assert fb._ctr_tid == fb_s._ctr_tid
    assert all(fb_s.tables[k][0] > fb_s._ctr_tid for k in fb_s._stream_keys
               if fb_s.tables[k][0] < B.PERSIST_TID_LO)          # ephemeral streams come after, never between


# ---------------------------------------------------------------------------------------- report + HUD
def test_the_report_and_warning_carry_the_oracle():
    fb, cb = compiled()
    eph = fb.streams["eph"]
    assert f"states 1-8: {' '.join(map(str, R.states(eph.x0, 8)))}" in cb.report
    p = fb.streams["dwix_rs1"]
    rolls = " ".join(str(R.roll_value(v, 1, 100)) for v in R.states(p.x0, 8))
    assert f"rolls 1-8: {rolls}" in cb.report
    assert "shared by 2 consumers" in cb.report
    # a SHARED stream lists each site's roll from the same states (the docs promise it)
    for ctr, lo, hi, flag in (("pick", 0, 5, "draw_e"), ("die", 1, 6, "draw_d")):
        per = " ".join(str(R.roll_value(v, lo, hi)) for v in R.states(eph.x0, 8))
        assert f"{ctr} (on {flag!r}): {per}" in cb.report
    assert f"check word {p.word}" in fb.streams_warning()
    assert "(225,-915)" in cb.report                          # the walker's first target
    assert "dwix_rs1.lehmer236.65537:" not in cb.report       # not listed again as a table


def test_the_hud_reads_a_stream_and_never_advances_it():
    fb, _ = compiled()
    assert fb._hud_ref("stream:eph") == B.stream_ref(fb.streams["eph"].tid)
    with pytest.raises(B.BehaviorError, match="unknown stream"):
        fb._hud_ref("stream:nope")
    S = B.stream_ref(fb.streams["eph"].tid)
    with pytest.raises(B.BehaviorError):
        B.hud_expr_tokens("expr:" + B.stream_advance_rpn(S))
    r = raw()
    r["behavior"]["hud"] = [{"window": 6, "values": ["stream:eph"], "digits": [3], "text": "S [NUMB=0]"}]
    assert any("digits = 5" in w for w in BT.hud_digits_warnings(r))


# ---------------------------------------------------------------------------------------- the laws
def _with(mut) -> dict:
    r = raw()
    mut(r["behavior"])
    return r


def _compile_err(r) -> str:
    with pytest.raises((B.BehaviorError, BT.BehaviorTomlError)) as ei:
        BT.dry_compile(r)
    return str(ei.value)


def _keeper(b):
    return b["unit"][0]["branch"]


def test_edge_law_a_roll_needs_its_flag_in_when_and_clear_flags():
    msg = _compile_err(_with(lambda b: _keeper(b)[0].pop("clear_flags")))
    assert "THE EDGE IDIOM" in msg
    msg = _compile_err(_with(lambda b: _keeper(b)[0].update(when=[{"counter_eq": ["pick", 0]}])))
    assert "THE EDGE IDIOM" in msg


def test_edge_law_the_flag_must_be_public():
    def m(b):
        b["public_flags"].remove("draw_e")
    assert "THE EDGE IDIOM" in _compile_err(_with(m))


def test_edge_law_no_branch_may_raise_the_edge():
    def m(b):
        _keeper(b)[3]["raise_flags"] = ["draw_e"]
    assert "raised by a branch" in _compile_err(_with(m))


def test_edge_law_no_other_branch_may_clear_the_edge():
    def m(b):
        _keeper(b)[3]["clear_flags"] = ["draw_e"]
    assert "cleared by another branch" in _compile_err(_with(m))


def _straight_blocks(body: bytes) -> list:
    """The body cut into straight-line runs: a run ends at a jump and a new one starts at any jump TARGET."""
    ins = list(D.iter_code(body, 0, len(body)))
    targets = {D.jump_target(i) for i in ins if i.op in D.JUMP_OPS}
    blocks, cur = [], []
    for i in ins:
        if i.off in targets and cur:
            blocks.append(cur)
            cur = []
        cur.append(i)
        if i.op in D.JUMP_OPS:
            blocks.append(cur)
            cur = []
    return blocks + ([cur] if cur else [])


@pytest.mark.parametrize("deco", [None, {"cooldown": 30}, {"once": "told"}])
def test_every_roll_advance_runs_only_in_a_pass_that_clears_its_edge(deco):
    """One draw per raise, whatever decorates the branch: each roll's advance sits in the SAME straight-line
    run as its edge's clear, after it -- so the pass that draws is the pass that consumes the edge, and the next
    tick's `when` fails. (A decorator may gate the run; it can never split the draw from the consume.)"""
    def m(b):
        if deco:
            _keeper(b)[0].update(deco)
    fb, cb = BT.dry_compile(_with(m))
    body = cb.ticker_body
    clear_re = re.compile(r"Global\.Bit\[(\d+)\] const\(0\) B_LET")
    for stream, sites in fb.stream_sites.items():
        S = B.stream_ref(fb.streams[stream].tid)
        consumed = []                        # for each advance of S: the edge its straight-line run cleared
        for blk in _straight_blocks(body):
            last_clear = None
            for i in blk:
                if i.op != 0x05:
                    continue
                t = stmts(body[i.off:i.end])[0]
                mc = clear_re.fullmatch(t)
                if mc:
                    last_clear = int(mc.group(1))
                elif t.startswith(f"{S} {S}") and SIG in t:
                    consumed.append(last_clear)
        # exactly one advance per draw site, each after ITS OWN edge's clear in the same run
        assert sorted(consumed, key=str) == sorted((bit for _o, _f, bit, *_r in sites), key=str),             (stream, consumed)
    assert sum(len(v) for v in fb.stream_sites.values()) == 3
    assert sum(SIG in t for t in stmts(body)) == 4                  # + the seeded wander's own advance


def test_a_roll_whose_when_also_negates_its_edge_is_refused():
    def m(b):
        _keeper(b)[0]["when"] = [{"flag": "draw_e"}, {"not_flag": "draw_e"}]
    assert "can never be selected" in _compile_err(_with(m))


def test_an_alternator_edge_is_refused():
    """A flag that is public AND an alternator is a clock, not an event: the alternator clause itself fires
    (the flag stays public here, so no other clause can)."""
    def m(b):
        b["alternators"] = [{"name": "draw_e", "frames": 30}]
    assert "is an alternator -- a clock, not an event" in _compile_err(_with(m))


def test_a_roll_into_the_schedule_counter_is_refused():
    def m(b):
        b["timer"] = 120
        b["schedule"] = [{"counter": "pick", "table": "tally"}]
    assert "a clock rewrites that counter" in _compile_err(_with(m))


def test_a_scan_flags_table_may_not_take_a_streams_name():
    def m(b):
        b["counters"].append("hc")
        b["scan"] = [{"name": "sc", "units": ["walker"], "point": [0, -1100], "radius": 300, "count": "hc",
                      "flags": "eph"}]
    r = _with(m)
    assert any("collides with a [[behavior.stream]]" in p for p in BT.validate(r))
    assert "taken by a roll stream" in _compile_err(r)


@pytest.mark.parametrize("centre,radius,bad", [([0, -1100], 300, False), ([30000, 0], 4000, True),
                                               ([0, -32000], 800, True), ([32000, 0], 767, False)])
def test_a_wander_box_past_the_int16_target_slots_is_refused(centre, radius, bad):
    """The re-roll stores wtx/wtz as Int16: a box past +-32767 would wrap (and a seeded prediction would lie)."""
    def m(b):
        b["unit"][1]["branch"][0]["do"].update(wander=centre, radius=radius)
    r = _with(m)
    probs = [p for p in BT.validate(r) if "Int16" in p]
    assert bool(probs) == bad
    if bad:
        assert "Int16" in _compile_err(r)
    else:
        BT.dry_compile(r)


def test_a_roll_into_a_scan_counter_is_refused():
    def m(b):
        b["scan"] = [{"name": "hc", "units": ["walker"], "point": [0, -1100], "radius": 300, "count": "pick"}]
    assert "a clock rewrites that counter" in _compile_err(_with(m))


def test_a_seeded_wander_must_be_the_units_only_wander():
    def m(b):
        b["unit"][1]["branch"].insert(0, {"when": [{"flag": "draw_d"}],
                                          "do": {"wander": [100, -900], "radius": 100}})
    assert "only wander" in _compile_err(_with(m))


def test_a_declared_stream_no_roll_draws_is_refused():
    def m(b):
        b["stream"].append({"name": "orphan", "seed": 3})
    assert "no roll draws it" in _compile_err(_with(m))


def test_brains_fields_refuse_streams():
    def m(b):
        b["brains"] = True
    assert "v1-ticker only" in _compile_err(_with(m))


def test_nothing_else_may_write_a_stream():
    fb, _ = compiled()
    with pytest.raises(B.BehaviorError, match="is a roll stream"):
        fb._table_ref("eph", 0)
    with pytest.raises(B.BehaviorError, match="is a roll stream"):
        fb._table_ref(R.backing_key("eph"), 0)
    with pytest.raises(B.BehaviorError, match="is a roll stream"):
        fb._counter_ref("eph")


@pytest.mark.parametrize("row,msg", [
    ({"name": "x", "seed": 0}, "seed must be an int"),
    ({"name": "x", "seed": True}, "seed must be an int"),
    ({"name": "x y", "seed": 1}, "must be [A-Za-z0-9_]+"),
    ({"name": "x", "seed": 1, "persist": True}, "needs an explicit id"),
    ({"name": "x", "seed": 1, "persist": True, "id": 42}, "outside the persistent band"),
    ({"name": "x", "seed": 1, "id": 6004901}, "only for persist = true"),
    ({"name": "x", "seed": 1, "persist": "yes"}, "persist must be true or false"),
])
def test_stream_declaration_refusals_in_validate_and_the_compiler(row, msg):
    r = _with(lambda b: b["stream"].append(row))
    assert any(msg in p for p in BT.validate(r)), BT.validate(r)
    assert msg in _compile_err(r)


def test_stream_namespace_collisions():
    r = _with(lambda b: b["stream"].append({"name": "pick", "seed": 2}))
    assert any("collides" in p for p in BT.validate(r))
    assert "collides" in _compile_err(r)
    r = _with(lambda b: b["stream"].append({"name": "q", "seed": 2, "persist": True, "id": 6004900}))
    assert any("used twice" in p for p in BT.validate(r))


@pytest.mark.parametrize("roll,msg", [
    ([{"stream": "eph", "counter": "pick", "range": [0, 5]}], "ONE dict"),
    ({"stream": "eph", "counter": "pick"}, "missing ['range']"),
    ({"stream": "eph", "counter": "pick", "range": [5, 5]}, "lo < hi"),
    ({"stream": "eph", "counter": "pick", "range": [0, 256]}, "must hold 2..256"),
    ({"stream": "eph", "counter": "pick", "range": [0, 5], "every": 3}, "unknown ['every']"),
])
def test_roll_shape_refusals(roll, msg):
    r = _with(lambda b: _keeper(b)[0].update(roll=roll))
    assert any(msg in p for p in BT.validate(r)), BT.validate(r)


def test_roll_references_are_checked_in_validate():
    r = _with(lambda b: _keeper(b)[0].update(roll={"stream": "nope", "counter": "zzz", "range": [0, 5]}))
    probs = BT.validate(r)
    assert any("not a [[behavior.stream]]" in p for p in probs)
    assert any("not in [behavior] counters" in p for p in probs)


@pytest.mark.parametrize("cond", [{"roll": ["eph", 6]}, {"chance": 30}])
def test_a_roll_in_a_condition_is_refused_permanently(cond):
    r = _with(lambda b: _keeper(b)[3].update(when=[cond]))
    assert any("roll is a branch effect, not a condition" in p for p in BT.validate(r))


def test_a_unitless_behavior_block_is_refused():
    r = {"behavior": {"stream": [{"name": "s", "seed": 1}], "counters": ["c"]}}
    assert any("compiles to NOTHING" in p for p in BT.validate(r))


def test_persistent_streams_join_the_campaign_agreement_lints():
    from ff9mapkit import campaign
    decl = BT.persistent_tables(raw())
    assert (R.backing_key("dwix_rs1"), 6004900, (R.seed_state("dwix_rs1", 1),)) in decl
    other = [("m2", "dwix_rs1_ledger", 6004900, (0, 0))]
    errs, _w = campaign.persistent_table_conflicts(
        [("m1", nm, tid, vals) for nm, tid, vals in decl] + other)
    assert errs                                             # a stream and a table on one id
    reseeded = raw(FIELD.replace("seed = 1\n  persist", "seed = 2\n  persist"))
    _e, warns = campaign.persistent_table_conflicts(
        [("m1", *d) for d in decl] + [("m2", *d) for d in BT.persistent_tables(reseeded)])
    assert any("seeds different values" in w for w in warns)


def test_a_walk_tread_that_re_raises_a_roll_edge_every_frame_is_refused(tmp_path):
    from ff9mapkit import build
    fb, _ = compiled()
    edge_bit = fb.bb.flag("draw_e")
    base = ('[field]\nid=4003\nname="Z"\narea=11\ntext_block=1073\n\n'
            '[camera]\npitch=45\nfov=42.2\n\n'
            '[walkmesh]\nquad=[[-1500,-2000],[1500,-2000],[1500,500],[-1500,500]]\n\n' + FIELD +
            '\n[[event]]\nzone=[[10,-10],[50,-10],[50,-50],[10,-50]]\n')

    def probs(extra):
        p = tmp_path / "v.field.toml"
        p.write_text(base + extra, encoding="utf-8")
        return [x for x in build.validate(build.FieldProject.load(p)) if "roll edge" in x]
    assert probs(f"once=false\nset_flag=[{edge_bit},1]\n")
    assert probs(f"once=true\nset_flag=[{edge_bit},1]\n") == []
    assert probs(f'trigger="action"\nonce=false\nset_flag=[{edge_bit},1]\n') == []
    assert probs(f"once=false\nset_flag=[{fb.bb.flag('draw_p') + 7},1]\n") == []
    assert probs(f"once=0\nset_flag=[{edge_bit},1]\n")             # the build latches on TRUTHINESS
    # a latched tread whose once-latch IS the edge: the roll's clear re-arms it every frame
    assert probs(f"flag={edge_bit}\nset_flag=[{edge_bit},1]\n")
    assert probs(f'trigger="action"\nflag={edge_bit}\nset_flag=[{edge_bit},1]\n') == []


@pytest.mark.parametrize("mode", ["hold", "once"])
def test_a_coop_gate_that_writes_a_roll_edge_is_refused(tmp_path, mode):
    """A [[coop]] gate is polled every frame: hold rewrites its level, once latches ON the flag (so the roll's
    clear re-arms it) -- either way the roll would draw once per tick while the plate is held."""
    from ff9mapkit import build
    fb, _ = compiled()
    base = ('[field]\nid=4003\nname="Z"\narea=11\ntext_block=1073\n\n[camera]\npitch=45\nfov=42.2\n\n'
            '[walkmesh]\nquad=[[-1500,-2000],[1500,-2000],[1500,500],[-1500,500]]\n\n' + FIELD)

    def probs(bit):
        p = tmp_path / "c.field.toml"
        p.write_text(base + f'\n[[coop]]\nname="g"\nmode="{mode}"\nplate=[100,-100,300,-300]\nset_flag={bit}\n',
                     encoding="utf-8")
        return [x for x in build.validate(build.FieldProject.load(p)) if "roll edge" in x]
    assert probs(fb.bb.flag("draw_e"))
    assert probs(fb.bb.flag("draw_p") + 7) == []


def test_roll_edge_flags_is_exactly_the_drawn_edges_and_never_raises():
    """Only the flag each roll DRAWS on is an edge -- not another public flag the branch also clears -- and a
    malformed table yields {} (validate reports it) instead of raising out of build.validate."""
    def m(b):
        b["public_flags"].append("tidy")
        _keeper(b)[0]["clear_flags"] = ["draw_e", "tidy"]
    r = _with(m)
    fb, _ = BT.dry_compile(r)
    edges = BT.roll_edge_flags(r)
    assert set(edges.values()) == {"draw_e", "draw_d", "draw_p"}
    assert fb.bb.flag("tidy") not in edges
    bad = raw()
    _keeper(bad["behavior"])[0]["clear_flags"] = 5
    assert BT.roll_edge_flags(bad) == {}


def test_any_behavior_block_on_a_verbatim_fork_is_refused_by_name():
    r = raw()
    del r["behavior"]["unit"]
    probs = BT.validate(r, verbatim=True)
    assert len(probs) == 1 and "VERBATIM fork is not wired" in probs[0]
    assert "has no [[behavior.unit]]" in BT.validate(r)[0]


def test_the_branch_editor_round_trips_a_roll_branch():
    from ff9mapkit.workspace import behaviorscan as BS
    br = {"when": [{"flag": "draw_e"}], "do": {"hold_post": True}, "clear_flags": ["draw_e"],
          "roll": {"stream": "eph", "counter": "pick", "range": [0, 5]}}
    parsed, err = BS.parse_branch(BS.branch_toml(br))
    assert err is None and parsed == br


def test_the_behavior_doc_example_builds_and_its_rolls_are_the_oracles():
    """The docs' roll-stream example is what authors copy: it must validate, compile as written, and the rolls
    its report prints must equal an INDEPENDENT recomputation -- the seed recipe and the recurrence written out
    here with literal constants, not the rollstream functions the compiler itself calls."""
    import hashlib
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[1] / "docs" / "BEHAVIOR.md").read_text(encoding="utf-8")
    sect = doc[doc.index("### Roll streams"):]
    start = sect.index("```toml") + len("```toml")
    raw = tomllib.loads('[[npc]]\nname = "teller"\npos = [0, 0]\n' + sect[start:sect.index("```", start)])
    assert BT.validate(raw) == []
    fb, cb = BT.dry_compile(raw)
    info = fb.streams["mymod_fate"]
    d = hashlib.sha256(b"ff9mapkit.stream.v1\0mymod_fate\x007").digest()
    x = 1 + int.from_bytes(d[:4], "little") % 65536
    assert info.persist and info.tid == 6412346 and info.x0 == x
    omens = []
    for _ in range(8):
        x = 236 * x % 65537
        omens.append(1 + x % 6)
    assert f"rolls 1-8: {' '.join(map(str, omens))}" in cb.report
    assert [(o, f, c, lo, hi) for o, f, _b, c, lo, hi in fb.stream_sites["mymod_fate"]] == \
        [("teller", "ask", "omen", 1, 6)]
    assert list(fb.persist_words) == [R.backing_key("mymod_fate")]
    assert fb.persist_words[R.backing_key("mymod_fate")] == info.word
