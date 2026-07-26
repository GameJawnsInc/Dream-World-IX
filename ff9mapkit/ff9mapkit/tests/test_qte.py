"""``[[qte]]`` -- the Blank-duel reaction core (:mod:`ff9mapkit.content.qte`).

Golden provenance: field 64 (``test2_15``) entries 3/5+ -- the poller's nine
edge tests, the countdown-leftover speed channel, the combo bonus channel, the
no-repeat random pick, the tiered finale + purse -- and its ``.mes`` 112-119
prompt glyph lines, reproduced verbatim."""
from __future__ import annotations

import pytest

from ff9mapkit import build as BLD
from ff9mapkit.content import qte as Q
from ff9mapkit.eb import disasm as D, opcodes
from ff9mapkit.eb.model import EbScript

RAW = {"name": "duel", "result": 2006, "rounds": 8, "window": 45,
       "gil": True, "flag": 8300}


def _spec(**over):
    return Q.from_raw({**RAW, **over}, 0)


def _tx(spec):
    return {p: 500 + i for i, (p, _t, _s) in enumerate(Q.mes_texts(spec))}


def _verify_body(body: bytes) -> int:
    starts, count = set(), 0
    for ins in D.iter_code(body, 0, len(body)):
        starts.add(ins.off)
        count += 1
        assert ins.end <= len(body)
    ends = starts | {len(body)}
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op in (0x01, 0x02, 0x03):
            t = D.jump_target(ins)
            assert t is None or t in ends, f"jump at {ins.off} -> {t} misses a boundary"
    return count


def test_prompt_texts_are_stock_bytes():
    """The prompt lines reproduce field 64's entries 112-119 byte-for-byte
    (the [DBTN]/[MOBI] glyph pairs are the golden's own)."""
    texts = {p: t for p, t, _ in Q.mes_texts(_spec())}
    assert texts["p_left"] == "[IMME]Press [DBTN=LEFT][MOBI=267] ![TIME=-1]"
    assert texts["p_circle"] == "[IMME]Press [DBTN=CIRCLE][MOBI=273] ![TIME=-1]"
    assert texts["p_square"] == "[IMME]Press [DBTN=SQUARE][MOBI=271] ![TIME=-1]"
    strts = {p: s for p, _t, s in Q.mes_texts(_spec())}
    assert strts["p_left"] == (54, 1)                    # stock's window geometry
    assert strts["payout"] == (147, 1)                   # stock 128's


def test_body_structure_and_census():
    spec = _spec()
    body = Q.game_body(spec, _tx(spec))
    n = _verify_body(body)
    assert n > 100
    names = [ins.name for ins in D.iter_code(body, 0, len(body))]
    assert names.count("WindowAsync") == len(spec.buttons)   # one prompt open per button
    # score + 4 verdicts + payout, all sync
    assert names.count("WindowSync") == 6
    assert names.count("CloseWindow") == 1
    assert names.count("SetTextVariable") == 2               # score slot 0 + purse slot 1
    assert any(n2.startswith("AddGi") for n2 in names)       # the expression-form purse


def test_body_no_gil_drops_payout():
    spec = _spec(gil=False)
    body = Q.game_body(spec, _tx(spec))
    _verify_body(body)
    names = [ins.name for ins in D.iter_code(body, 0, len(body))]
    assert names.count("WindowSync") == 5                    # no payout line
    assert names.count("SetTextVariable") == 1
    assert not any(n2.startswith("AddGi") for n2 in names)


def test_body_scoring_channels():
    """The two stock channels: points += the countdown LEFTOVER, bonus += the
    combo (before its increment); a miss zeroes the combo."""
    spec = _spec()
    body = Q.game_body(spec, _tx(spec))
    exprs = [D.pretty_expr(body, ins.off + 1)[0]
             for ins in D.iter_code(body, 0, len(body)) if ins.op == 0x05]
    assert any(f"Int16[{Q.S_POINTS}]" in e and f"Byte[{Q.S_COUNT}]" in e
               and "B_PLUS_LET" in e for e in exprs)
    assert any(f"Int16[{Q.S_BONUS}]" in e and f"Int16[{Q.S_COMBO}]" in e
               and "B_PLUS_LET" in e for e in exprs)
    assert any(f"Int16[{Q.S_COMBO}]" in e and "const(0)" in e.replace(" ", "")
               .replace("const(0)", "const(0)") and "B_LET" in e for e in exprs)
    # the random pick uses random8 % n
    assert any("B_SYSVAR" in e and "B_REM" in e for e in exprs)


def test_body_deterministic_and_subset_buttons():
    spec = _spec(buttons=["cross", "circle", "up", "down"])
    body = Q.game_body(spec, _tx(spec))
    _verify_body(body)
    assert body == Q.game_body(spec, _tx(spec))
    names = [ins.name for ins in D.iter_code(body, 0, len(body))]
    assert names.count("WindowAsync") == 4


def test_entry_and_call():
    spec = _spec()
    eb = Q.entry_bytes(spec, _tx(spec))
    assert eb[0] == 0x00 and eb[1] == 0x02
    assert Q.call_bytes(9) == opcodes.run_script_sync(Q.DISPATCH_LEVEL, 9, Q.QTE_TAG)


@pytest.mark.parametrize("over,frag", [
    ({"rounds": 0}, "rounds"),
    ({"window": 5}, "window"),
    ({"result": 2030}, "result"),
    ({"buttons": ["cross"]}, "buttons"),
    ({"buttons": ["cross", "bogus"]}, "unknown button"),
    ({"verdicts": ["a", "b"]}, "verdicts"),
    ({"bogus": 1}, "unknown"),
])
def test_from_raw_rejects(over, frag):
    with pytest.raises(Q.QteError) as ei:
        _spec(**over)
    assert frag in str(ei.value)


_TOML = (
    '[field]\nid = 30001\nname = "QTE"\narea = 11\n'
    "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    '\n[[npc]]\nname = "duelist"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Well?"\n'
    '\n[[qte]]\nname = "duel"\nresult = 2006\nrounds = 8\nwindow = 45\ngil = true\n'
    '\n[[choice]]\nnpc = "duelist"\nprompt = "Cross blades?"\n'
    'options = [ { text = "En garde!", qte = "duel" }, { text = "Not today" } ]\n'
)


def test_full_build_seats_and_wires(tmp_path):
    f = tmp_path / "q.field.toml"
    f.write_text(_TOML, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    (mes, txids, ev, cs, ch, oe, ate, chest, gw, co, sp, bh, ni) = BLD.collect_text(p)
    assert {k[2] for k in ni if len(k) == 3 and k[0] == "qte"} >= {"p_left", "score",
                                                                   "verdict3", "payout"}
    assert "[DBTN=SQUARE][MOBI=271]" in mes
    plain = BLD.build_script(BLD.FieldProject.load(f), "us", txids, choice_txids=ch,
                             numinput_txids=ni)
    eb = EbScript.from_bytes(plain)
    qte_slots = []
    for i in range(1, eb.entry_count):
        e = eb.entry(i)
        if e.size <= 0 or e.func_by_tag(Q.QTE_TAG) is None or e.func_by_tag(0) is None:
            continue
        fn0 = e.func_by_tag(0)
        if plain[fn0.abs_start:fn0.abs_end] == bytes(opcodes.RETURN):
            qte_slots.append(i)
    assert len(qte_slots) == 1
    slot = qte_slots[0]
    assert Q.call_bytes(slot) in plain                   # the choice row dispatches it
    armed = set()
    for fn in eb.entry(0).funcs:
        for ins in D.iter_code(plain, fn.abs_start, fn.abs_end):
            if ins.op == 0x07:
                armed.add(int(ins.imm(0)))
    assert slot in armed
    fn3 = eb.entry(slot).func_by_tag(Q.QTE_TAG)
    _verify_body(plain[fn3.abs_start:fn3.abs_end])
    again = BLD.build_script(BLD.FieldProject.load(f), "us", txids, choice_txids=ch,
                             numinput_txids=ni)
    assert again == plain


def test_validate_negatives(tmp_path):
    bad = _TOML.replace('qte = "duel"', 'qte = "nope"')
    f = tmp_path / "bad.field.toml"
    f.write_text(bad, encoding="utf-8")
    probs = BLD.validate(BLD.FieldProject.load(f))
    assert any("qte" in pr and "nope" in pr for pr in probs)
    beh = _TOML + ('\n[behavior]\nwarmup = 30\n'
                   '\n[[behavior.unit]]\nnpc = "duelist"\n'
                   'branch = [{ do = { hold = [0, -300] } }]\n')
    f2 = tmp_path / "beh.field.toml"
    f2.write_text(beh, encoding="utf-8")
    probs2 = BLD.validate(BLD.FieldProject.load(f2))
    assert any("blackboard" in pr for pr in probs2)


def test_par_calibrates_the_score_divisor():
    """ENGARDE round-1 calibration: scoring against 100% of theoretical made 100
    impossible (~85 superhuman ceiling, a good human run ~70). Default par 80
    mirrors stock's divisor feel: a great run reaches 100, the clamp absorbs
    the top."""
    spec = _spec()                                       # rounds 8, window 45
    body = Q.game_body(spec, _tx(spec))
    exprs = [D.pretty_expr(body, ins.off + 1)[0]
             for ins in D.iter_code(body, 0, len(body)) if ins.op == 0x05]
    assert any(f"const({8 * 45 * 80 // 100})" in e and "B_DIV" in e for e in exprs)
    hard = _spec(par=100)
    bh = Q.game_body(hard, _tx(hard))
    exprs_h = [D.pretty_expr(bh, ins.off + 1)[0]
               for ins in D.iter_code(bh, 0, len(bh)) if ins.op == 0x05]
    assert any(f"const({8 * 45})" in e and "B_DIV" in e for e in exprs_h)
    with pytest.raises(Q.QteError, match="par"):
        _spec(par=5)
