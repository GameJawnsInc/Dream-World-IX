"""Tests for storyseed (narrative-state rung 1)."""
import pytest

from ff9mapkit import storyseed
from ff9mapkit.eb import EbScript, cmdasm
from tests.test_ebcfg import _eb_field


def _field_reading(*bits):
    conds = "\n".join(
        f"SET({{Global.Bit[{b}] B_EXPR_END}})\nJMP_IFNOT(l{b})\nNOTHING()\nl{b}:" for b in bits)
    return EbScript.from_bytes(_eb_field([(0, [(0, conds + "\nRET()")])]))


def _census(bit, value=1, sc=None, sc_armed=None, field=999):
    site = {"bit": bit, "value": value, "field": field, "entry": 0, "func": 0, "off": 0,
            "sc": sc or [], "sc_armed": sc_armed or [], "flags": [], "other": []}
    return {"bit_sites": [site], "sc_sites": [{"value": 4000, "field": field,
                                               "entry": 0, "func": 0, "off": 0}]}


def test_window_evidence_decides_set_vs_clear():
    eb = _field_reading(2647)
    c = _census(2647, sc=[[0, 7, 0, "==", 3110]])
    assert storyseed.resolve(eb, 3111, c).verdicts[0].decision == "set"
    assert storyseed.resolve(eb, 3000, c).verdicts[0].decision == "clear"


def test_strict_within_beat_rule():
    # lo == beat -> the write happens DURING this beat's own play, so the bit boots clear
    # (the Dali-latch lesson: pre-tripping a beat's own once-latches suppresses its content)
    eb = _field_reading(2647)
    c = _census(2647, sc=[[0, 7, 0, "==", 3110]])
    v = storyseed.resolve(eb, 3110, c).verdicts[0]
    assert v.decision == "clear" and v.lo == 3110
    out = storyseed.render_startup(storyseed.resolve(eb, 3110, c))
    assert "DURING this beat" in out


def test_armed_and_envelope_fallbacks():
    eb = _field_reading(2647)
    v = storyseed.resolve(eb, 5000, _census(2647, sc_armed=[[0, 7, 0, "==", 4500]])).verdicts[0]
    assert (v.decision, v.estimator) == ("set", "armed")
    v = storyseed.resolve(eb, 5000, _census(2647)).verdicts[0]
    assert (v.decision, v.estimator, v.lo) == ("set", "envelope", 4000)


def test_toggle_is_reported_never_seeded():
    eb = _field_reading(3536)
    c = _census(3536, sc=[[0, 7, 0, "==", 3000]])
    c["bit_sites"].append(dict(c["bit_sites"][0], value=0))
    v = storyseed.resolve(eb, 9999, c).verdicts[0]
    assert v.decision == "toggle"
    assert not storyseed.resolve(eb, 9999, c).set_bits


def test_reserved_band_read_is_refused():
    eb = _field_reading(8400)          # the Mognet lock band
    v = storyseed.resolve(eb, 9999, _census(8400, sc=[[0, 7, 0, "==", 1000]])).verdicts[0]
    assert v.decision == "refused"


def test_render_contains_provenance_and_flags_row():
    eb = _field_reading(2647)
    out = storyseed.render_startup(
        storyseed.resolve(eb, 3115, _census(2647, sc=[[0, 7, 0, "==", 3110]])))
    assert "[startup]" in out and "scenario = 3115" in out
    assert "{ flag = 2647, value = 1 }" in out and "window" in out


def test_read_set_skips_assign_target_and_handshake():
    eb = EbScript.from_bytes(_eb_field([(0, [(0, """
        SET({Global.Bit[190] B_EXPR_END})
        JMP_IFNOT(l1)
        NOTHING()
    l1:
        SET({Global.Bit[700] const(1) B_LET B_EXPR_END})
        SET({Global.Bit[701] Global.Bit[702] B_ANDAND B_EXPR_END})
        RET()
    """)])]))
    rs = storyseed.read_set(eb)
    assert 700 not in rs                    # assignment target is a write, not a read
    assert 190 not in rs                    # handshake band excluded
    assert 701 in rs and 702 in rs          # compound reads both count


def test_real_553_seed(tmp_path):
    from ff9mapkit.extract import EventBundle
    try:
        data = EventBundle().eb_for_id(553)
    except Exception:
        pytest.skip("install unavailable")
    cpath = storyseed.find_census()
    if not cpath:
        pytest.skip("census not generated")
    import json
    rep = storyseed.resolve(EbScript.from_bytes(data), 3115,
                            json.load(open(cpath, encoding="utf-8")))
    assert any(v.bit == 2647 and v.decision == "set" for v in rep.verdicts)


def _install_eb(fid):
    from ff9mapkit.extract import EventBundle
    try:
        return EventBundle().eb_for_id(fid)
    except Exception:
        pytest.skip("install unavailable")


def test_party_seed_nonzidane_player_111():
    ps = storyseed.party_seed(EbScript.from_bytes(_install_eb(111)))
    assert ps["add"] == ["vivi"] and ps["player"] == ["Vivi"]


def test_party_seed_dali_cast_and_dormant_quina_352():
    ps = storyseed.party_seed(EbScript.from_bytes(_install_eb(352)))
    assert ps["add"] == ["garnet", "steiner", "vivi", "zidane"]
    assert ps["dormant"] == ["Quina"]          # checked but never added -> assert-by-hand only
    out = storyseed.render_party(ps)
    assert "[party]" in out and "Quina" in out and "NOT seeded" in out


def test_seed_chain_appends_and_replaces(tmp_path):
    d = tmp_path / "M1"
    d.mkdir()
    toml = d / "M1.field.toml"
    toml.write_text("id = 30999\ndonor = 553\n[verbatim_eb]\ndonor = 553\n", encoding="utf-8")
    eb = _field_reading(2647)
    c = _census(2647, sc=[[0, 7, 0, "==", 3110]])
    rows = storyseed.seed_chain(str(tmp_path), 3110, c, lambda _d: eb)
    assert rows == [(str(toml), 30999, 553)]
    text = toml.read_text(encoding="utf-8")
    assert "[startup]" in text and "scenario = 3110" in text
    rows2 = storyseed.seed_chain(str(tmp_path), 2000, c, lambda _d: eb)
    text2 = toml.read_text(encoding="utf-8")
    assert text2.count("# story-seed") == 1 and "scenario = 2000" in text2


def test_backwards_advance_hazard_detection():
    c = {"sc_sites": [{"field": 352, "value": 2600}, {"field": 352, "value": 2990},
                      {"field": 351, "value": 2660}]}
    assert storyseed.backwards_advance_hazards(c, 352, 2650) == [2600]   # the Dali morning write
    assert storyseed.backwards_advance_hazards(c, 352, 2500) == []      # nothing below the beat
    assert storyseed.backwards_advance_hazards(c, 351, 2650) == []


def _ws(idx, value, sc_val, *, vt=5, pure=True, field=352):
    return {"idx": idx, "vt": vt, "value": value, "pure": pure, "field": field,
            "entry": 0, "func": 0, "off": 0, "sc": [[0, 7, 0, "==", sc_val]], "sc_armed": []}


def test_party_windowing_excludes_future_visit_add():
    # the chain-round-3 red case in miniature: char 10 (Marcus) adds only under a LATER
    # visit's SC window; char 1's add is windowed at the beat; char 3 has no census evidence
    c = {"party_sites": [
        {"kind": "add", "char": 10, "field": 350, "entry": 35, "func": 0, "off": 0,
         "sc": [], "sc_armed": [[0, 7, 0, ">=", 2990]]},
        {"kind": "add", "char": 1, "field": 350, "entry": 2, "func": 0, "off": 0,
         "sc": [[0, 7, 0, "==", 2600]], "sc_armed": []}],
        "sc_sites": []}
    kept, out = storyseed._window_party_adds([1, 3, 10], 2600, c, 350)
    assert kept == [1, 3]                    # windowed-in + no-evidence fallback
    assert out == [(10, 2990)]               # the Marcus class: a later visit's roster
    kept2, out2 = storyseed._window_party_adds([1, 10], 3000, c, 350)
    assert kept2 == [1, 10] and out2 == []   # at its own beat the add is back in


def test_ate_word_values_pure_floor_then_or():
    c = {"word_sites": [
        _ws(236, 1, 1000), _ws(236, 3, 2600),
        _ws(236, 4, 2610, pure=False), _ws(236, 8, 5000, pure=False)],
        "sc_sites": []}
    assert storyseed.ate_word_values([236], 2600, c, [352]) == {236: 3}   # latest pure resets
    assert storyseed.ate_word_values([236], 2620, c, [352]) == {236: 7}   # then ORs accumulate
    assert storyseed.ate_word_values([236], 2500, c, [352]) == {236: 1}
    assert storyseed.ate_word_values([236], 900, c, [352]) == {236: None}
    assert storyseed.ate_word_values([236], 2600, c, [999]) == {236: None}  # donors only


def test_ate_word_value_word_write_covers_high_byte():
    c = {"word_sites": [_ws(236, 0x0201, 100, vt=6)], "sc_sites": []}
    assert storyseed.ate_word_values([236, 237], 100, c, [352]) == {236: 1, 237: 2}


def test_ate_word_value_evidence_free_zone_write_is_arrival_state():
    # a zone donor's pure write with NO SC evidence contributes before every beat (the Dali
    # hub-enable 297 = 1, written by the village entrance with no SC gate)
    site = {"idx": 297, "vt": 7, "value": 1, "pure": True, "field": 359,
            "entry": 0, "func": 0, "off": 0, "sc": [], "sc_armed": []}
    c = {"word_sites": [site], "sc_sites": []}
    assert storyseed.ate_word_values([297], 2600, c, [359]) == {297: 1}
    # a later windowed pure write still supersedes it as the floor
    c["word_sites"].append(_ws(297, 64, 2790, vt=7, field=456))
    assert storyseed.ate_word_values([297], 2600, c, [359, 456]) == {297: 1}
    assert storyseed.ate_word_values([297], 2800, c, [359, 456]) == {297: 64}


def test_render_words_derived_vs_fallback():
    out = storyseed.render_words({239: 6, 296: None})
    assert "{ byte = 239, value = 6 }" in out and "{ byte = 296, value = 1 }" in out
    assert "windowed" in out and "WIDEN" in out


def test_red_case_dali_350_marcus_windowed_out():
    """The chain-round-3 red case, pinned on real bytes: at the Dali morning beat (2600),
    donor 350's Marcus add (a 2990-band visit's roster) is windowed OUT, and the zone's
    ATE availability masks derive nonzero (the ATEs are story-required at Dali)."""
    import json
    cpath = storyseed.find_census()
    if not cpath:
        pytest.skip("census not generated")
    census = json.load(open(cpath, encoding="utf-8"))
    if "party_sites" not in census or "word_sites" not in census:
        pytest.skip("census predates party/word capture -- re-run dominance_census.py")
    eb350 = EbScript.from_bytes(_install_eb(350))
    ps = storyseed.party_seed(eb350, beat=2600, census=census, donor=350)
    assert "marcus" not in ps["add"]
    assert any(n == "Marcus" for n, _lo in ps["future"])
    eb352 = EbScript.from_bytes(_install_eb(352))
    ps2 = storyseed.party_seed(eb352, beat=2600, census=census, donor=352)
    assert "vivi" in ps2["add"] and "marcus" not in ps2["add"]
    # the ATE round-4 lesson pinned: the REAL Dali avail word is the hub-enable 297 (a
    # bitwise `& 1` test, invisible to the comparison channel), written by the entrance
    # with no SC gate; the room-code/sequencer words 239/296 are donor-self-managed and
    # must NOT be detected
    zone = [312, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 450]
    det = storyseed.ate_word_seed(EbScript.from_bytes(_install_eb(351)))
    assert det.get(297) == "expr" and 239 not in det and 296 not in det
    vals = storyseed.ate_word_values([297], 2600, census, zone)
    assert vals[297] == 1
    # the proven rung-2 Lindblum case still detects via the comparison channel
    det552 = storyseed.ate_word_seed(EbScript.from_bytes(_install_eb(552)))
    assert det552.get(236) == "cmp"
    # and the morning latches boot CLEAR under the strict within-beat rule
    rep = storyseed.resolve(EbScript.from_bytes(_install_eb(351)), 2600, census)
    for bit in (2064, 2075, 2079):
        assert any(v.bit == bit and v.decision == "clear" for v in rep.verdicts)


def test_chain_ladder_is_the_write_channel():
    c = {"sc_sites": [{"field": 352, "value": 2600}, {"field": 354, "value": 2610},
                      {"field": 352, "value": 2650}, {"field": 999, "value": 5000}]}
    ladder = storyseed.chain_ladder(c, [352, 354])
    assert [(v, w) for v, _n, w in ladder] == [(2600, [352]), (2610, [354]), (2650, [352])]
    # a non-member's write never enters the zone's ladder
    assert all(v != 5000 for v, _n, _w in ladder)
