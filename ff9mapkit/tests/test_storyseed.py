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
    assert storyseed.resolve(eb, 3110, c).verdicts[0].decision == "set"
    assert storyseed.resolve(eb, 3000, c).verdicts[0].decision == "clear"


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
        storyseed.resolve(eb, 3110, _census(2647, sc=[[0, 7, 0, "==", 3110]])))
    assert "[startup]" in out and "scenario = 3110" in out
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
    rep = storyseed.resolve(EbScript.from_bytes(data), 3110,
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


def test_chain_ladder_is_the_write_channel():
    c = {"sc_sites": [{"field": 352, "value": 2600}, {"field": 354, "value": 2610},
                      {"field": 352, "value": 2650}, {"field": 999, "value": 5000}]}
    ladder = storyseed.chain_ladder(c, [352, 354])
    assert [(v, w) for v, _n, w in ladder] == [(2600, [352]), (2610, [354]), (2650, [352])]
    # a non-member's write never enters the zone's ladder
    assert all(v != 5000 for v, _n, _w in ladder)
