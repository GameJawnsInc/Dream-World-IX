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

RAW = {"name": "duel", "result": 1998, "rounds": 8, "window": 45,
       "gil": True, "flag": 8712}


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


def test_prompt_texts_are_stock_bytes_plus_turbo_guard():
    """The prompt lines reproduce field 64's entries 112-119 (the [DBTN]/[MOBI]
    glyph pairs are the golden's own) with exactly ONE addition: the leading
    [NTUR] turbo-injection guard (arm B -- see mes_texts' docstring)."""
    texts = {p: t for p, t, _ in Q.mes_texts(_spec())}
    assert texts["p_left"] == "[NTUR][IMME]Press [DBTN=LEFT][MOBI=267] ![TIME=-1]"
    assert texts["p_circle"] == "[NTUR][IMME]Press [DBTN=CIRCLE][MOBI=273] ![TIME=-1]"
    assert texts["p_square"] == "[NTUR][IMME]Press [DBTN=SQUARE][MOBI=271] ![TIME=-1]"
    strts = {p: s for p, _t, s in Q.mes_texts(_spec())}
    assert strts["p_left"] == (54, 1)                    # stock's window geometry
    assert strts["payout"] == (147, 1)                   # stock 128's


def test_turbo_guard_coverage():
    """THE TURBO-INJECTION LAW (arm B): every inhibited Auto-style prompt carries
    [NTUR]; the WHOLE finale carries it -- score/payout as READOUTS, and the
    verdicts since the first A/B (2026-08-05) lost the "clap rating" to a latched
    F9. A custom score text with no live value stays plain (not a readout)."""
    spec = _spec()
    texts = {p: t for p, t, _ in Q.mes_texts(spec)}
    for b in spec.buttons:
        assert texts[f"p_{b}"].startswith("[NTUR]"), b
    assert texts["score"].startswith("[NTUR]") and "[NUMB=0]" in texts["score"]
    assert texts["payout"].startswith("[NTUR]") and "[NUMB=1]" in texts["payout"]
    for i in range(4):
        assert texts[f"verdict{i}"].startswith("[NTUR]")  # the outcome is press-gated
    plain = {p: t for p, t, _ in Q.mes_texts(_spec(score_text="Done!"))}
    assert "[NTUR]" not in plain["score"]                # no live value -> no guard
    dup = {p: t for p, t, _ in Q.mes_texts(_spec(score_text="[NTUR]Got [NUMB=0]."))}
    assert dup["score"].count("[NTUR]") == 1             # author's own tag: no second copy
    dv = {p: t for p, t, _ in Q.mes_texts(_spec(verdicts=["[NTUR]a", "b", "c", "d"]))}
    assert dv["verdict0"].count("[NTUR]") == 1           # same no-dup rule on a verdict


def test_finale_render_race_gaps():
    """THE FINALE RENDER-RACE (ENGARDE A/B): a Wait(FINALE_GAP) precedes the verdict
    tier dispatch and the payout open, so each guarded window opens from an idle turbo
    machine and its [NTUR] render pass wins. The score needs none (ROUND_GAP's quiet
    frames precede it -- it survived the same A/B unmodified)."""
    spec = _spec()
    body = Q.game_body(spec, _tx(spec))
    ins = list(D.iter_code(body, 0, len(body)))
    WAIT = 0x22
    sync_offs = [i for i, x in enumerate(ins) if x.name == "WindowSync"]
    score_i, payout_i = sync_offs[0], sync_offs[-1]
    assert ins[score_i + 1].op == WAIT                   # the gap right AFTER the score
    assert ins[payout_i - 1].op == WAIT                  # and right BEFORE the payout


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
    # `flag` must sit in the safe custom band [FIRST_SAFE_FLAG, CHOICE_SCRATCH_FLOOR), like a
    # [[flag]] index -- the reserved regions below/inside it are live save state (Mognet letters,
    # read-mail scratch, the co-op cells) plus the game's own scratch band.
    ({"flag": 8300}, "mognet_mailbox"),          # a live letter-slot byte (the old bench value)
    ({"flag": 8400}, "mognet_give_locks"),
    ({"flag": 8600}, "mognet_readmail_payload"),
    ({"flag": 16200}, "qte_scratch"),            # the game's OWN scratch (bytes 2018-2031)
    ({"flag": 16256}, "netsync_coop_cells"),     # reserved INSIDE the band's numeric range
    ({"flag": 16320}, "choice_scratch"),
    # the result cap 2004 keeps the word strictly below the nameplate explored words
    # (bytes 2006-2017, live overworld visited state since 172c8b98) and the scratch band (2018+)
    ({"result": 2018}, "4..2004"),
    ({"result": 2006}, "4..2004"),               # the first nameplate word (the old pinned example)
    ({"result": 2016}, "4..2004"),               # the old cap top -- now inside the nameplate words
    ({"flag": 200}, "safe custom band"),         # free stock space, but outside the audited band
    ({"flag": True}, "BIT index"),
    # the result Int16 spans TWO bytes -- both must clear the reserved regions
    ({"result": 1030}, "mognet_mailbox"),        # squarely inside the mailbox bytes 1024-1045
    ({"result": 1046}, "mognet_give_locks"),     # the straddle: byte 1046 is free, byte 1047 is not
    ({"result": 1088}, "mognet_readmail_payload"),   # low byte = the payload band's last byte
    ({"result": 23}, "field_menu_guard"),        # the byte-23 engine menu handshake
    # self-collision: a flag bit inside the result word's own 16 bits -- the finale writes both
    ({"result": 1089, "flag": 8720}, "result word"),
])
def test_from_raw_rejects(over, frag):
    with pytest.raises(Q.QteError) as ei:
        _spec(**over)
    assert frag in str(ei.value)


def test_from_raw_safe_flag_and_clear_result_pass():
    """The tightened validation must not over-reject: the first safe bit, a result word just past
    the read-mail payload (bytes 1089-1090), the last clear word below the nameplate explored
    words (2004-2005), and the flagless form all load."""
    spec = _spec(flag=8712, result=1100)
    assert spec.flag == 8712 and spec.result == 1100
    assert _spec(flag=None, result=1089).result == 1089
    assert _spec(flag=None, result=2004).result == 2004
    assert _spec(flag=None).flag is None


def test_scratch_band_clears_the_coop_cells():
    """THE CO-OP CLOBBER REGRESSION: the engine rewrites the netsync co-op cells (bytes
    2032-2039) EVERY FRAME while [Netsync] co-op runs -- on ANY field, [[coop]] gates or
    none -- so the scratch band must sit strictly clear of them. The original band's four
    Int16 channels (combo/max/points/bonus at 2032/2034/2036/2038) landed exactly on the
    cells: a bout under live co-op had its scoring clobbered per frame."""
    from ff9mapkit import flags as F
    from ff9mapkit.content import coop as C, numinput as NI, region as R

    scratch = {Q.S_STATE, Q.S_EXPECT, Q.S_LAST, Q.S_COUNT, Q.S_ROUND}
    for w in (Q.S_COMBO, Q.S_MAXC, Q.S_POINTS, Q.S_BONUS):
        scratch |= {w, w + 1}                    # each Int16 spans two bytes
    coop_cells = set(range(F.COOP_CELLS_FLOOR // 8, F.CHOICE_SCRATCH_FLOOR // 8))
    assert {C.COOP_PRESENCE_BYTE, C.COOP_PEER_X, C.COOP_PEER_X + 1,
            C.COOP_PEER_Z, C.COOP_PEER_Z + 1} <= coop_cells
    assert not scratch & coop_cells
    # ... and of the neighbors: the choice-mask word + the numeric_input stepper scratch
    assert not scratch & {R.MASK_SCRATCH_IDX, R.MASK_SCRATCH_IDX + 1}
    assert not scratch & {NI.SCRATCH_VAL, NI.SCRATCH_VAL + 1,
                          NI.SCRATCH_RAMP, NI.SCRATCH_RAMP + 1, NI.SCRATCH_SEL}
    # every scratch bit sits inside the flags.py RESERVED region, so no flag/result
    # validation path (here or in lint_flag_bands) can admit an offset that collides
    for b in scratch:
        for bit in range(b * 8, b * 8 + 8):
            r = F.bit_region(bit)
            assert r is not None and r.reserved and r.name == "qte_scratch", (b, bit)
    # and the result cap admits no word touching the nameplate words below the band, either
    assert F.RESULT_WORD_CAP == 2004
    assert (F.RESULT_WORD_CAP + 1) * 8 + 7 < F.NAMEPLATE_EXPLORED_FLOOR < F.QTE_SCRATCH_FLOOR


_TOML = (
    '[field]\nid = 30001\nname = "QTE"\narea = 11\n'
    "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    '\n[[npc]]\nname = "duelist"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Well?"\n'
    '\n[[qte]]\nname = "duel"\nresult = 1998\nrounds = 8\nwindow = 45\ngil = true\n'
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


def test_qte_and_coop_share_a_field(tmp_path):
    """[[qte]] + [[coop]] on one field is LEGAL -- the scratch band was moved below the
    co-op cells precisely so a bout under live co-op keeps its scoring (and a refusal
    could not have closed the hole anyway: the engine writes the cells whenever co-op
    runs, [[coop]] gates or none)."""
    both = _TOML + ('\n[[coop]]\nname = "twin-seals"\nplate_a = [0, 0, 100, 100]\n'
                    'plate_b = [300, 0, 400, 100]\nset_flag = 8720\n')
    f = tmp_path / "both.field.toml"
    f.write_text(both, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []


def test_par_calibrates_the_score_divisor():
    """ENGARDE round-1 calibration: scoring against 100% of theoretical made 100
    impossible (~85 superhuman ceiling, a good human run ~70). Default par 65: stock's combo channel only pays over its 48 rounds, so
    short bouts need a kinder divisor (round 2, owner-called)."""
    spec = _spec()                                       # rounds 8, window 45
    body = Q.game_body(spec, _tx(spec))
    exprs = [D.pretty_expr(body, ins.off + 1)[0]
             for ins in D.iter_code(body, 0, len(body)) if ins.op == 0x05]
    assert any(f"const({8 * 45 * 65 // 100})" in e and "B_DIV" in e for e in exprs)
    hard = _spec(par=100)
    bh = Q.game_body(hard, _tx(hard))
    exprs_h = [D.pretty_expr(bh, ins.off + 1)[0]
               for ins in D.iter_code(bh, 0, len(bh)) if ins.op == 0x05]
    assert any(f"const({8 * 45})" in e and "B_DIV" in e for e in exprs_h)
    with pytest.raises(Q.QteError, match="par"):
        _spec(par=5)
