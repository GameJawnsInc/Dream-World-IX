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
    eb = _field_reading(770)           # worldmap_unlocks: reserved, and story (not in the noise mask)
    v = storyseed.resolve(eb, 9999, _census(770, sc=[[0, 7, 0, "==", 1000]])).verdicts[0]
    assert v.decision == "refused" and v.note == "worldmap_unlocks"


def test_named_word_read_is_refused_by_bit_index():
    # named_word_at takes a BIT index; the old call passed bit // 8, which checked byte bit // 64 --
    # a read inside MagicDisabledFlag (byte 227 = bits 1816-1823) was seeded (byte 28 is no word)...
    v = storyseed.resolve(_field_reading(1816), 9999,
                          _census(1816, sc=[[0, 7, 0, "==", 1000]])).verdicts[0]
    assert v.decision == "refused" and v.note == "named word MagicDisabledFlag"
    # ...while a plain story bit at byte 25 was refused as FieldEntrance (byte 3)
    v = storyseed.resolve(_field_reading(200), 9999,
                          _census(200, sc=[[0, 7, 0, "==", 1000]])).verdicts[0]
    assert v.decision == "set" and v.lo == 1000


def test_moogle_latch_read_is_refused_by_name():
    # 8511 gates the first-meeting Mognet explanation (58 moogle fields): real save state, not noise, so
    # a fork's seed report names it -- booted mid-story with it clear, the fork replays the tutorial
    rep = storyseed.resolve(_field_reading(8510, 8511), 3115, _census(8511, sc=[[0, 7, 0, "<", 5990]]))
    assert [(v.bit, v.decision, v.note) for v in rep.verdicts] == [
        (8510, "refused", "mognet_moogle_latches"), (8511, "refused", "mognet_moogle_latches")]
    assert "# bit 8511: REFUSED" in storyseed.render_startup(rep)


def test_render_contains_provenance_and_flags_row():
    eb = _field_reading(2647)
    out = storyseed.render_startup(
        storyseed.resolve(eb, 3115, _census(2647, sc=[[0, 7, 0, "==", 3110]])))
    assert "[startup]" in out and "scenario = 3115" in out
    assert "{ flag = 2647, value = 1 }" in out and "window" in out


def test_read_set_skips_assign_target_and_story_noise():
    eb = EbScript.from_bytes(_eb_field([(0, [(0, """
        SET({Global.Bit[184] Global.Bit[189] B_ANDAND B_EXPR_END})
        JMP_IFNOT(l1)
        NOTHING()
    l1:
        SET({Global.Bit[8511] Global.Bit[14864] B_ANDAND Global.Bit[186] B_ANDAND B_EXPR_END})
        SET({Global.Bit[700] const(1) B_LET B_EXPR_END})
        SET({Global.Bit[701] Global.Bit[702] B_ANDAND B_EXPR_END})
        RET()
    """)])]))
    rs = storyseed.read_set(eb)
    assert 700 not in rs                    # assignment target is a write, not a read
    assert 701 in rs and 702 in rs          # compound reads both count
    # the kit's ONE story-noise mask (flags.story_noise_bits), not a local range: the menu + tent
    # guards and the behavior Blackboard never reach a verdict...
    assert rs.keys().isdisjoint({184, 189, 14864})
    assert 186 in rs                        # ...while stock-clear byte23_spare stays visible,
    assert 8511 in rs                       # and so does a moogle latch (side state, not noise)


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


def test_census_story_population_is_the_kit_mask():
    # research/dominance_census.py scores the rung-0 falsifier on story_sites(): the kit's story
    # POPULATION mask (flags.non_story_bits -- the noise plus the moogle latches), not its old local
    # 184-191 + 8192-8711 (which hid byte23_spare, byte 1046 and the payload hole, and let the kit's
    # Blackboard through). Loaded from the repo root with sys.path restored -- the script prepends.
    import importlib.util
    import pathlib
    import sys
    repo = pathlib.Path(__file__).resolve().parents[2]
    saved = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location(
            "_dominance_census", repo / "research" / "dominance_census.py")
        census = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(census)
    finally:
        sys.path[:] = saved
    sites = [{"bit": b} for b in (184, 186, 189, 770, 8368, 8400, 8505, 8508, 8511, 8520, 8600, 8620,
                                  14864, 14976)]
    assert [x["bit"] for x in census.story_sites(sites)] == [186, 770, 8368, 8505, 8600, 8620, 14976]


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


def test_seed_chain_emits_shared_once_sentinel(tmp_path):
    # every member gets the SAME once-stamp sentinel (safe band), so the first room entered
    # stamps the beat and later doors never rewind in-chain progression (the round-5 lesson)
    for name, mid in (("M1", 30830), ("M2", 30833)):
        d = tmp_path / name
        d.mkdir()
        (d / f"{name}.field.toml").write_text(
            f"id = {mid}\ndonor = 553\n[verbatim_eb]\ndonor = 553\n", encoding="utf-8")
    eb = _field_reading(2647)
    c = _census(2647, sc=[[0, 7, 0, "==", 3110]])
    storyseed.seed_chain(str(tmp_path), 3110, c, lambda _d: eb)
    want = storyseed.chain_once_flag([30830, 30833])
    from ff9mapkit import flags as flagsmod
    assert want >= flagsmod.FIRST_SAFE_FLAG
    for name in ("M1", "M2"):
        text = (tmp_path / name / f"{name}.field.toml").read_text(encoding="utf-8")
        assert f"once = {want}" in text


def test_hub_journey_row_update_and_strip(tmp_path):
    # the hub format (round 7): ONE [[journey]] row carries the chain's whole derived seed;
    # installing it is marker-idempotent; stripping returns members to pure verbatim forks
    for name, mid, donor in (("M1", 30830, 553), ("M2", 30833, 554)):
        d = tmp_path / name
        d.mkdir()
        (d / f"{name}.field.toml").write_text(
            f"id = {mid}\ndonor = {donor}\n[verbatim_eb]\ndonor = {donor}\n", encoding="utf-8")
    eb = _field_reading(2647)
    c = _census(2647, sc=[[0, 7, 0, "==", 3110]])
    row = storyseed.hub_journey_toml(str(tmp_path), 3115, c, lambda _d: eb,
                                     entry=30830, slug="test_3115")
    assert 'id    = "test_3115"' in row and "set_scenario = 3115" in row
    assert "entry = 30830" in row and "{ flag = 2647, value = 1 }" in row
    jt = tmp_path / "journeys.toml"
    jt.write_text('[hub]\nname = "X"\nid = 30850\n', encoding="utf-8")
    storyseed.update_hub_journeys(str(jt), row, "test_3115")
    storyseed.update_hub_journeys(str(jt), row, "test_3115")     # replace, never duplicate
    assert jt.read_text(encoding="utf-8").count("[[journey]]") == 1
    storyseed.seed_chain(str(tmp_path), 3115, c, lambda _d: eb)
    assert len(storyseed.strip_chain_seeds(str(tmp_path))) == 2
    for name in ("M1", "M2"):
        t = (tmp_path / name / f"{name}.field.toml").read_text(encoding="utf-8")
        assert "# story-seed" not in t and "[startup]" not in t
    assert storyseed.strip_chain_seeds(str(tmp_path)) == []      # nothing left to strip


def test_hub_render_and_option_body_carry_the_seed():
    # the journey row's seed reaches the compiled choice option: gen-hub renders the keys and
    # option_body emits the same startup/party bytes the [startup]/[party] path uses
    from ff9mapkit import hub as _hub
    from ff9mapkit.content import choice as _choice, party as _party, startup as _startup
    j = _hub.Journey(id="dali_2600", name="Dali (2600)", entry=30840, set_scenario=2600,
                     set_words=[{"byte": 297, "value": 1}],
                     party_add=["garnet", "steiner", "vivi", "zidane"])
    spec = _hub.HubSpec(name="NS_HUB", id=30850, borrow_bg="X", journeys=[j])
    text = _hub.render_hub_field_toml(spec)
    assert "set_words = [ { byte = 297, value = 1 } ]" in text
    assert 'party_add = [ "garnet", "steiner", "vivi", "zidane" ]' in text
    body = _choice.option_body({"set_scenario": 2600,
                                "set_words": [{"byte": 297, "value": 1}],
                                "party_add": ["vivi"], "warp": 30840})
    assert _startup.startup_body([], words=[(297, 1)]) in body
    assert _party.add_member(1) in body                          # vivi = CharacterOldIndex 1
    assert body.index(_party.add_member(1)) < body.index(b"\x2b")  # party BEFORE the warp


def test_startup_once_guard_bytecode_roundtrip():
    # the injected once-guard must decode as `if (Bit[S]==0) { stamp...; Bit[S]=1 }` through
    # the kit's OWN readers: the rung-0 CFG sees the guard cond, and the stamp is skipped when
    # the sentinel is set (jump-if-false over body incl. the sentinel write)
    from ff9mapkit.content import startup as _startup
    from ff9mapkit.eb.cfg import FuncFlow, parse_set, OP_SET
    body = _startup.startup_body([(2647, 1)], scenario=2600, words=[(297, 1)], once_flag=8822)
    plain = _startup.startup_body([(2647, 1)], scenario=2600, words=[(297, 1)])
    assert body != plain and plain in body            # the guard WRAPS the same stamp bytes
    code = body + bytes([0x04])                       # RET terminator for the CFG
    fl = FuncFlow.build(code, 0, len(code))
    writes = [parse_set(code, ins) for blk in fl.blocks for ins in blk.instrs
              if ins.op == OP_SET]
    assigns = [(st.vtype, st.index, st.value) for st in writes if st.kind == "assign"]
    assert (1, 8822, 1) in assigns                    # the sentinel latch write
    sc_writes = [st for st in writes if st.kind == "assign" and st.vtype in (6, 7)
                 and st.index == 0]
    g = fl.guards_at(sc_writes[0].off)
    assert any(c.vtype in (0, 1) and c.index == 8822 and c.cmp == "==" and c.value == 0
               for c in g)                            # the stamp is DOMINATED by sentinel==0


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


# ---------------------------------------------------------------- F5b: the post-advance phase
# An entry AFTER the beat's own advance carries what the advance and the exit into the entry leave;
# an entry BEFORE it (F5's member(359)) keeps today's row byte for byte. Synthetic fields: 900 = the
# advance room (its SC := 2600 store sits in case 28 of a dispatch loop, like 352 e17 t1; case 60
# advances to 2610 and warps; case 70 advances to 2620 and then removes a member; entries 4/5 are two
# advance functions of 2630, only one of which removes and sets 2080), 901 = the room behind its exit
# gateway at entrance 6 (that exit clears 2079 and re-sets SC only under SC == 2640), 903 = behind a
# second exit (entrance 7) that re-sets SC unconditionally and a third (entrance 8, entry 6) whose
# warp runs only at SC == 2700, 902 = a room nothing warps to.

_ADV = """
l0:
    SET({Map.Int16[29] B_EXPR_END})
    SWITCHEX(ldef, 28, lwake, 52, lother, 60, lwarp, 70, lparty)
lwake:
    SET({Global.Bit[2078] const(1) B_LET B_EXPR_END})
    SET({Global.Bit[2086] const(1) B_LET B_EXPR_END})
    SET({const(2) B_PARTYCHK B_EXPR_END})
    JMP_IFNOT(lstore)
    RemoveParty(2)
    SET({Global.Byte[303] const(0) B_EQ B_EXPR_END})
    JMP_IFNOT(lstore)
    SET({Map.Bit[148] const(2) B_PARTYADD B_LET B_EXPR_END})
lstore:
    SET({Global.UInt16[0] const(2600) B_LET B_EXPR_END})
    SET({Global.Bit[2079] const(1) B_LET B_EXPR_END})
    SET({Global.Bit[2080] const(1) B_LET B_EXPR_END})
    JMP(ldef)
lother:
    SET({Global.Bit[2064] const(1) B_LET B_EXPR_END})
    SET({Global.Bit[2086] const(0) B_LET B_EXPR_END})
    JMP(ldef)
lwarp:
    SET({Global.UInt16[0] const(2610) B_LET B_EXPR_END})
    SET({Global.Int16[2] const(3) B_LET B_EXPR_END})
    Field(901)
    JMP(ldef)
lparty:
    SET({Global.UInt16[0] const(2620) B_LET B_EXPR_END})
    RemoveParty(3)
    JMP(ldef)
ldef:
    op_22(1)
    JMP(l0)
"""

_ADV2630_REMOVES = """
    SET({Global.Bit[2080] const(1) B_LET B_EXPR_END})
    SET({const(2) B_PARTYCHK B_EXPR_END})
    JMP_IFNOT(lst)
    RemoveParty(2)
lst:
    SET({Global.UInt16[0] const(2630) B_LET B_EXPR_END})
    RET()
"""

_ADV2630_KEEPS = """
    SET({Global.UInt16[0] const(2630) B_LET B_EXPR_END})
    RET()
"""


def _reader(*bits, zidane=False):
    conds = "\n".join(
        f"SET({{Global.Bit[{b}] B_EXPR_END}})\nJMP_IFNOT(l{b})\nNOTHING()\nl{b}:" for b in bits)
    if zidane:      # a roster the removes cannot empty: this room checks and adds Zidane
        conds += ("\nSET({const(0) B_PARTYCHK B_EXPR_END})\nJMP_IF(lz)\n"
                  "SET({Map.Bit[148] const(0) B_PARTYADD B_LET B_EXPR_END})\nlz:")
    return conds + "\nRET()"


def _gateway(to, entrance, walk_in=""):
    """A region entry holding a SetRegion and ``<walk_in> ; Int16[2] := entrance ; Field(to)``."""
    return (1, [(0, "SetRegion(4, 0, 0, 100, 0, 100, 100, 0, 100)\nRET()"),
                (2, walk_in + f"SET({{Global.Int16[2] const({entrance}) B_LET B_EXPR_END}})\n"
                              f"Field({to})\nRET()")])


_EXIT6 = """SET({Global.UInt16[0] const(2640) B_EQ Global.Byte[208] B_ANDAND B_EXPR_END})
JMP_IFNOT(lx)
SET({Global.UInt16[0] const(2650) B_LET B_EXPR_END})
lx:
SET({Global.Bit[2079] const(0) B_LET B_EXPR_END})
"""
_EXIT7 = "SET({Global.UInt16[0] const(2650) B_LET B_EXPR_END})\n"
# a second exit into 903 (entrance 8) whose warp runs only at SC == 2700: dead at 2600
_EXIT8_DEAD = (1, [(0, "SetRegion(4, 0, 0, 100, 0, 100, 100, 0, 100)\nRET()"),
                   (2, "SET({Global.UInt16[0] const(2700) B_EQ B_EXPR_END})\nJMP_IFNOT(ld)\n"
                       "SET({Global.Int16[2] const(8) B_LET B_EXPR_END})\nField(903)\nld:\nRET()")])


def _post_zone(tmp_path, survivor=True):
    from ff9mapkit.eb.cfg import FuncFlow
    ebs = {900: EbScript.from_bytes(_eb_field([(0, [(0, _reader(2078, 2086, 2064, 2079, 2080))]),
                                               (0, [(0, "RET()"), (1, _ADV)]),
                                               _gateway(901, 6, _EXIT6),
                                               _gateway(903, 7, _EXIT7),
                                               (0, [(1, _ADV2630_REMOVES)]),
                                               (0, [(1, _ADV2630_KEEPS)]),
                                               _EXIT8_DEAD])),
           901: EbScript.from_bytes(_eb_field([(0, [(0, _reader(2078, 2086, zidane=survivor))])])),
           902: EbScript.from_bytes(_eb_field([(0, [(0, _reader(2086))])])),
           903: EbScript.from_bytes(_eb_field([(0, [(0, _reader(2086))])]))}
    eb = ebs[900]
    sc_sites = []
    for ei in (1, 4, 5):
        f = next(f for f in eb.entries[ei].funcs if f.tag == 1)
        fl = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
        for st, _b in fl.iter_sets(eb.data):
            if st.kind == "assign" and st.index == 0 and st.source == 0 and st.value:
                sc_sites.append({"field": 900, "entry": ei, "func": 1, "off": st.off,
                                 "value": st.value})
    store = next(s["off"] for s in sc_sites if s["value"] == 2600)
    blank = {"sc": [], "sc_armed": [], "flags": [], "other": []}
    census = {"sc_sites": sc_sites,
              "bit_sites": [   # 2078 set by the advance AND cleared elsewhere: the resolver's TOGGLE
                  dict(blank, bit=2078, value=1, field=900, entry=1, func=1, off=store - 1),
                  dict(blank, bit=2078, value=0, field=901, entry=0, func=0, off=0),
                  dict(blank, bit=2086, value=1, field=900, entry=1, func=1, off=store - 1)],
              "party_sites": [], "word_sites": []}
    chain = tmp_path / "chain"
    for mid, don in ((31000, 900), (31001, 901), (31002, 902), (31003, 903)):
        (chain / str(mid)).mkdir(parents=True)
        (chain / str(mid) / "m.field.toml").write_text(f"id = {mid}\ndonor = {don}\n", encoding="utf-8")
    return str(chain), census, ebs.__getitem__


# ONE advance room for the shape cases: 910's function loops over a dispatch (as 352 e17 t1) whose case 28
# sets 2078/2086, runs <mid>, stores SC := 2600, runs <after> and hands back round the loop; case 52 runs
# <other> and never reaches the store forward. Its exit into 911 at entrance 6 walks in with <exit_walk>
# (or <exit> replaces the whole region entry). 911 reads <bits> and checks/adds the four leads, so every
# lead is in the derived party (a remove is visible in the row, and never empties it).
def _leads():
    return "".join(f"SET({{const({c}) B_PARTYCHK B_EXPR_END}})\nJMP_IF(lp{c})\n"
                   f"SET({{Map.Bit[{148 + c}] const({c}) B_PARTYADD B_LET B_EXPR_END}})\nlp{c}:\n"
                   for c in range(4))


def _adv_zone(tmp_path, mid="", after="", other="", exit_walk="", exit=None, bits=(2078, 2086, 2065)):
    from ff9mapkit.eb.cfg import FuncFlow
    adv = ("l0:\nSET({Map.Int16[29] B_EXPR_END})\nSWITCHEX(ldef, 28, lwake, 52, lother)\nlwake:\n"
           "SET({Global.Bit[2078] const(1) B_LET B_EXPR_END})\n"
           "SET({Global.Bit[2086] const(1) B_LET B_EXPR_END})\n"
           + mid + "SET({Global.UInt16[0] const(2600) B_LET B_EXPR_END})\n" + after
           + "JMP(ldef)\nlother:\n" + other + "JMP(ldef)\nldef:\nop_22(1)\nJMP(l0)\n")
    ebs = {910: EbScript.from_bytes(_eb_field([(0, [(0, _reader(*bits))]), (0, [(0, "RET()"), (1, adv)]),
                                               exit or _gateway(911, 6, exit_walk)])),
           911: EbScript.from_bytes(_eb_field([(0, [(0, _leads() + _reader(*bits))])]))}
    eb = ebs[910]
    f = next(f for f in eb.entries[1].funcs if f.tag == 1)
    fl = FuncFlow.build(eb.data, f.abs_start, f.abs_end)
    sc = [{"field": 910, "entry": 1, "func": 1, "off": st.off, "value": st.value}
          for st, _b in fl.iter_sets(eb.data)
          if st.kind == "assign" and (st.source, st.vtype, st.index) == (0, 7, 0) and st.value]
    census = {"sc_sites": sc, "bit_sites": [], "party_sites": [], "word_sites": []}
    chain = tmp_path / "chain"
    for mid_, don in ((31010, 910), (31011, 911)):
        (chain / str(mid_)).mkdir(parents=True)
        (chain / str(mid_) / "m.field.toml").write_text(f"id = {mid_}\ndonor = {don}\n", encoding="utf-8")
    return str(chain), census, ebs.__getitem__


def _adv_row(tmp_path, **kw):
    chain, census, ebf = _adv_zone(tmp_path, **kw)
    return storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31011, entrance=6, after_advance=True)


def test_pre_phase_row_leaves_the_advance_to_the_advance(tmp_path):
    chain, census, ebf = _post_zone(tmp_path)
    row = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31000)
    assert "set_flags" not in row and "party_remove" not in row and "entrance" not in row
    assert 'name  = "' in row and "(SC 2600)\"" in row      # the historical label, untouched


def test_post_phase_carries_what_the_hand_over_leaves(tmp_path):
    chain, census, ebf = _post_zone(tmp_path)
    row = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31001, entrance=6,
                                     after_advance=True)
    assert "entrance = 6" in row and "past the advance" in row
    # 2078: a TOGGLE for resolve(), set before the store on every path -> carried
    assert "{ flag = 2078, value = 1 }" in row
    # 2086: cleared in case 52, which reaches the store round the dispatch loop -- but case 28 re-sets
    # it before its store on every path: one literal at the hand-back
    assert "{ flag = 2086, value = 1 }" in row
    # 2064: written only in ANOTHER case: never one literal, never carried
    assert "flag = 2064" not in row and "2064" in row.split("not carried")[1]
    # 2080: written AFTER the store, in the tail the advance runs before it hands back -> carried
    assert "{ flag = 2080, value = 1 }" in row
    # 2079: the tail sets it, but the EXIT clears it before its Field(): the hand-over holds 0
    assert "flag = 2079" not in row
    assert "# bit 2079 = 0 at the hand-over: the exit 900 e2 t2 +22 before Field(901)" in row
    # the exit's SC := 2650 runs only under SC == 2640 && ...: dead at 2600, noted, not a clash
    assert "# dead at the hand-over:" in row
    # garnet: `if PARTYCHK(2) RemoveParty(2)` -> leaves; her survivor re-add is conditional -> noted
    assert 'party_remove = [ "garnet" ]' in row and "ASSUMED NOT TAKEN" in row
    assert 'party_add = [ "zidane" ]' in row
    # the row id names the phase (a post row never replaces the chain's pre-phase row)
    assert 'id    = "chain_2600_e6_post"' in row


def test_post_phase_refusals(tmp_path):
    chain, census, ebf = _post_zone(tmp_path)
    post = dict(after_advance=True)
    for kw, msg in (
            (dict(entry=31002, entrance=6), "not behind an exit gateway"),
            (dict(entry=31001), "needs --entrance"),
            (dict(entry=31001, entrance=5), "pass --entrance 6"),
            (dict(entry=31000, entrance=6), "is the advance room 900 itself"),    # hands back in place
            (dict(entry=31000, entrance=0), "is the advance room 900 itself"),
            (dict(entry=31003, entrance=7), "re-sets the scenario"),              # a live SC store
            (dict(entry=31003, entrance=8), "cannot run at SC 2600"),             # its warp is dead
    ):
        with pytest.raises(ValueError, match=msg):
            storyseed.hub_journey_toml(chain, 2600, census, ebf, **kw, **post)
    with pytest.raises(ValueError, match="no member donor writes SC := 2605"):
        storyseed.hub_journey_toml(chain, 2605, census, ebf, entry=31001, entrance=6, **post)
    with pytest.raises(ValueError, match="leaves the scene"):                    # its own warp
        storyseed.hub_journey_toml(chain, 2610, census, ebf, entry=31001, entrance=6, **post)
    with pytest.raises(ValueError, match="changes the party after"):
        storyseed.hub_journey_toml(chain, 2620, census, ebf, entry=31001, entrance=6, **post)
    # shapes the pass does not model, each refused (never a row that silently disagrees with stock)
    sc_eq5 = "SET({Global.UInt16[0] const(5) B_EQ B_EXPR_END})\nJMP_IFNOT(lv)\nRemoveParty(1)\nlv:\n"
    one_of_two = ("SET({const(3) B_PARTYCHK B_EXPR_END})\nJMP_IFNOT(lx)\nRemoveParty(3)\nJMP(la)\nlx:\n"
                  "SET({Map.Bit[1] B_EXPR_END})\nJMP_IFNOT(lb)\nla:\n"
                  "SET({Global.UInt16[0] const(2600) B_LET B_EXPR_END})\nJMP(ldef)\nlb:\n")
    for n, (kw, msg) in enumerate((
            # an exit that INCREMENTS SC before its Field: the hand-over is at 2601, not the beat
            (dict(exit_walk="SET({Global.UInt16[0] B_POST_PLUS B_EXPR_END})\n"), "exit re-sets the scenario"),
            # the advance's own run re-sets SC after its store: it hands back at 2605 / SC-1
            (dict(after="SET({Global.UInt16[0] const(2605) B_LET B_EXPR_END})\n"), "run re-sets the scenario"),
            (dict(after="SET({Global.UInt16[0] B_PRE_MINUS B_EXPR_END})\n"), "run re-sets the scenario"),
            # a RemoveParty on the way to the store that is not `if PARTYCHK(c) RemoveParty(c)` on every
            # path: unguarded, guarded by something else, or on the way to one store of two
            (dict(mid="RemoveParty(2)\n"), "changes the roster on its way"),
            (dict(mid=sc_eq5), "changes the roster on its way"),
            (dict(mid=one_of_two), "changes the roster on its way"),
            # the party menu / SetPartyReserve after the store: the roster at the hand-back is the player's
            (dict(after="SetPartyReserve(15)\n"), "changes the party after"),
            (dict(after="Party(4, 0)\n"), "changes the party after"))):
        with pytest.raises(ValueError, match=msg):
            _adv_row(tmp_path / f"shape{n}", **kw)


def test_post_phase_roster_rules(tmp_path):
    chain, census, ebf = _post_zone(tmp_path)
    # two advance functions of 2630: only one removes garnet -> the hand-back still holds her
    row = storyseed.hub_journey_toml(chain, 2630, census, ebf, entry=31001, entrance=6,
                                     after_advance=True)
    assert "party_remove" not in row
    # the same two functions: only the removing one sets 2080 before its store; the other hands it
    # back as it came in -- no single literal on every store, so it is not carried
    assert "flag = 2080" not in row and "2080" in row.split("not carried")[1]
    # no survivor in the derived party: the removes would empty it -> refused, never a guess
    chain2, census2, ebf2 = _post_zone(tmp_path / "b", survivor=False)
    with pytest.raises(ValueError, match="leave no member"):
        storyseed.hub_journey_toml(chain2, 2600, census2, ebf2, entry=31001, entrance=6,
                                   after_advance=True)
    # a re-add every path from the remove to the store passes CANCELS it (the member stays, nothing is
    # assumed): in the remove's own block, post-dominating it in another block, or dominating the store
    chk = "SET({const(%d) B_PARTYCHK B_EXPR_END})\nJMP_IFNOT(lk)\nRemoveParty(%d)\n"
    add = "SET({Map.Bit[148] const(%d) B_PARTYADD B_LET B_EXPR_END})\n"
    for n, mid in enumerate((chk % (2, 2) + add % 2 + "lk:\n",
                             chk % (2, 2) + "SET({Map.Bit[1] B_EXPR_END})\nJMP_IFNOT(lr)\nNOTHING()\nlr:\n"
                             + add % 2 + "lk:\n",
                             chk % (3, 3) + "lk:\n" + add % 3)):
        row = _adv_row(tmp_path / f"undo{n}", mid=mid)
        assert "party_remove" not in row and "ASSUMED NOT TAKEN" not in row, row
    # a re-add BEFORE the remove (dominating the store) cancels nothing: steiner leaves
    row = _adv_row(tmp_path / "before", mid=add % 3 + chk % (3, 3) + "lk:\n")
    assert 'party_remove = [ "steiner" ]' in row and "ASSUMED NOT TAKEN" not in row
    # a remove whose path never reaches the store (it returns) is not this hand-over's: no leave, no refusal
    row = _adv_row(tmp_path / "ret", mid=chk % (3, 3) + "RET()\nlk:\n")
    assert "party_remove" not in row


def test_pre_phase_row_past_the_advance_needs_the_control_flag(tmp_path):
    chain, census, ebf = _post_zone(tmp_path)
    with pytest.raises(ValueError, match="lies AFTER the advance"):
        storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31001, entrance=6)
    row = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31001, entrance=6,
                                     pre_phase_control=True)
    assert "set_flags" not in row and "party_remove" not in row and "entrance = 6" in row
    assert "# PRE-PHASE ROW ENTERED PAST THE ADVANCE" in row and "pre-phase control" in row
    with pytest.raises(ValueError, match="nothing to control"):
        storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31002, entrance=6,
                                   pre_phase_control=True)
    # an entrance into the advance room itself is a PRE-phase entry (it may replay the advance)
    assert "entrance = 4" in storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31000,
                                                        entrance=4)
    # an exit whose warp into the entry is DEAD at the beat (903 at entrance 8 runs only at SC == 2700)
    # hands nothing over there: it does not put the entry past the advance -- the pre-phase row stands,
    # and there is nothing to control (the post phase refuses it as 'cannot run at SC 2600')
    row = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31003, entrance=8)
    assert "entrance = 8" in row and "(SC 2600, entrance 8)" in row and "PRE-PHASE ROW" not in row
    with pytest.raises(ValueError, match="nothing to control"):
        storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31003, entrance=8,
                                   pre_phase_control=True)


def _stmt(expr):
    """``(data, ins)`` of ONE assembled ``SET({<expr> B_EXPR_END})`` statement."""
    eb = EbScript.from_bytes(_eb_field([(0, [(0, f"SET({{{expr} B_EXPR_END}})\nRET()")])]))
    return eb.data, next(i for i in eb.instrs(eb.entries[0].funcs[0]) if i.op == 0x05)


def test_set_targets_reads_the_rpn_stack():
    # the reader names only what the engine WRITES -- an assignment's lvalue, an inc/dec's operand
    def t(expr):
        return storyseed._set_targets(*_stmt(expr))
    assert t("Map.Int16[5] Global.UInt16[0] B_LET") == [(1, 6, 5, None)]       # SC is READ, not written
    assert t("Global.Byte[226] Global.Bit[7175] B_LET") == [(0, 5, 226, None)]
    assert t("Global.UInt16[0] B_POST_PLUS") == [(0, 7, 0, None)]               # SC++ is a store of SC
    assert t("Global.Byte[7] B_PRE_MINUS") == [(0, 5, 7, None)]
    assert t("Global.UInt16[0] const(2600) B_LET") == [(0, 7, 0, 2600)]
    assert sorted(t("Global.Bit[5] Global.Bit[6] const(1) B_LET B_LET")) == [(0, 1, 5, 1), (0, 1, 6, 1)]
    assert t("Global.Byte[3] const(4) B_OR_LET") == [(0, 5, 3, None)]           # compound: no literal
    # an assignment INSIDE the expression (under &&) may be skipped at run time: a store, value unknown
    assert t("Global.UInt16[0] const(9050) B_EQ Global.Bit[3608] const(1) B_LET B_ANDAND") \
        == [(0, 1, 3608, None)]
    assert t("Global.UInt16[0] const(2640) B_EQ") == []                          # a condition writes nothing
    # a bit store sets the bit for ANY nonzero value (the engine's rule), not the literal's low bit
    assert storyseed._bit_value_of(1, 2065, 2, 2065) == 1 and storyseed._bit_value_of(0, 7, 0, 7) == 0


def test_truth_at_beat_keeps_unknowns_unknown():
    # a dead verdict is never guessed: every condition an unknown operand can decide stays None at 2600
    def tr(expr):
        return storyseed._truth_at_beat(*_stmt(expr), 2600)
    x = "Global.Bit[5]"
    for expr in (f"Global.UInt16[0] const(2600) B_EQ {x} B_ANDAND",     # true && unknown
                 f"Global.UInt16[0] const(2600) B_NE {x} B_OROR",       # false || unknown
                 f"{x} B_NOT", f"{x} const(0) B_OROR", f"{x} const(1) B_ANDAND",
                 "Global.Byte[5] const(5) B_EQ", "Global.Byte[5] const(5) B_NE",   # one side unknown
                 "Map.UInt16[0] const(2600) B_EQ",                      # a MAP word at index 0 is not SC
                 "Global.Byte[0] const(40) B_EQ"):                      # nor is SC's low byte
        assert tr(expr) is None, expr
    assert tr(f"Global.UInt16[0] const(2640) B_EQ {x} B_ANDAND") is False
    assert tr(f"Global.UInt16[0] const(2600) B_EQ {x} B_OROR") is True
    assert tr("Global.UInt16[0] const(2640) B_EQ B_NOT") is True
    assert tr("Global.Int16[0] const(2600) B_EQ") is True
    # a flexible varfunc (0xD3) lives inside the var-token space: sized as itself, an unknown operand
    assert tr("Global.UInt16[0] const(2640) B_EQ const(1) flex(21,1) B_ANDAND") is False


def test_handover_reads_are_not_writes(tmp_path):
    # an exit that only CACHES SC into a map local does not re-set it
    assert "set_scenario = 2600" in _adv_row(
        tmp_path / "s1", exit_walk="SET({Map.Int16[5] Global.UInt16[0] B_LET B_EXPR_END})\n")
    # an exit that only READS latch 2078, or an advance tail that reads 2086, leaves them carried
    latches = "set_flags = [ { flag = 2078, value = 1 }, { flag = 2086, value = 1 } ]"
    for n, kw in (("s2", dict(exit_walk="SET({Map.Bit[5] Global.Bit[2078] B_LET B_EXPR_END})\n")),
                  ("s2b", dict(after="SET({Map.Bit[6] Global.Bit[2086] B_LET B_EXPR_END})\n"))):
        row = _adv_row(tmp_path / n, **kw)
        assert latches in row and "not carried" not in row, row
    # Bit := 2 sets the bit
    assert "{ flag = 2065, value = 1 }" in _adv_row(
        tmp_path / "two", mid="SET({Global.Bit[2065] const(2) B_LET B_EXPR_END})\n")
    # a store INSIDE the exit's condition (a stock `=` for `==`) is a store: no literal, not carried
    row = _adv_row(tmp_path / "mid", exit_walk="SET({Global.UInt16[0] const(2600) B_EQ Global.Bit[2065] "
                                               "const(1) B_LET B_ANDAND B_EXPR_END})\nJMP_IFNOT(lm)\n"
                                               "NOTHING()\nlm:\n")
    assert "# not carried (no single literal at the hand-over): bits [2065]" in row
    # an exit whose Field sits under `SC == beat && <unknown>` is LIVE: an unknown never kills a block
    live = (1, [(0, "SetRegion(4, 0, 0, 100, 0, 100, 100, 0, 100)\nRET()"),
                (2, "SET({Global.UInt16[0] const(2600) B_EQ Global.Bit[5] B_ANDAND B_EXPR_END})\n"
                    "JMP_IFNOT(ld)\nSET({Global.Int16[2] const(6) B_LET B_EXPR_END})\nField(911)\nld:\nRET()")])
    assert "entrance = 6" in _adv_row(tmp_path / "live", exit=live)


def test_handover_tail_and_the_stamped_words(tmp_path):
    # the row stamps set_words; a store the advance's run makes AFTER its SC := beat store moves the
    # hand-over off that stamp (refused, as the exit's clash) unless it re-writes the stamp's own value
    def post(n, after):
        chain, census, ebf = _adv_zone(tmp_path / n, after=after)
        return storyseed._post_advance(census, [910, 911], storyseed.chain_donors(chain), 31011, 6, 2600,
                                       ebf, {2078, 2086}, {}, {208: 1}, {"garnet", "zidane"})
    with pytest.raises(ValueError, match="run re-sets the scenario or a stamped word"):
        post("w5", "SET({Global.UInt16[208] const(5) B_LET B_EXPR_END})\n")
    with pytest.raises(ValueError, match="not one literal"):
        post("wor", "SET({Global.UInt16[208] const(8) B_OR_LET B_EXPR_END})\n")
    for n, after in (("w1", "SET({Global.UInt16[208] const(1) B_LET B_EXPR_END})\n"),
                     ("b1", "SET({Global.Byte[208] const(1) B_LET B_EXPR_END})\n"),
                     ("hi0", "SET({Global.Byte[209] const(0) B_LET B_EXPR_END})\n")):
        _new, _rm, notes = post(n, after)
        assert any("re-writes the beat / a stamped word at its own value" in x for x in notes), notes


def test_handover_notes_split_kept_from_not_carried(tmp_path):
    # a bit the advance writes only on ANOTHER path (case 52 returns): only the value the function was
    # entered with reaches this hand-back -- the pre-phase value stands, never 'not carried'
    assert "2065" not in _adv_row(tmp_path / "entry",
                                  other="SET({Global.Bit[2065] const(1) B_LET B_EXPR_END})\nRET()\n")
    # a bit with no single literal keeps the PRE-PHASE value: when the row still stamps it (1), the
    # note says so -- 'not carried' only for the bits the row leaves clear
    chain, census, ebf = _post_zone(tmp_path / "split")
    members = storyseed.chain_donors(chain)
    _new, _rm, notes = storyseed._post_advance(census, sorted({d for _m, d in members}), members, 31001, 6,
                                               2600, ebf, {2064, 2078, 2079, 2080, 2086}, {2064: 1}, {},
                                               {"garnet", "zidane"})
    assert "# kept at the pre-phase value 1 (no single literal at the hand-over): bits [2064]" in notes
    assert not any(n.startswith("# not carried") for n in notes), notes


def test_hub_row_name_is_escaped_and_the_slug_names_the_phase(tmp_path):
    import tomllib
    chain, census, ebf = _post_zone(tmp_path)
    name = 'Dali "morning" C:\\x'
    row = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31000, name=name)
    assert tomllib.loads(row)["journey"][0]["name"] == name
    # the id names what makes the row distinct; a plain row keeps its historical id byte for byte
    for kw, slug in ((dict(entry=31000), "chain_2600"), (dict(entry=31000, entrance=4), "chain_2600_e4"),
                     (dict(entry=31001, entrance=6, after_advance=True), "chain_2600_e6_post"),
                     (dict(entry=31001, entrance=6, pre_phase_control=True), "chain_2600_e6_control")):
        assert f'id    = "{slug}"' in storyseed.hub_journey_toml(chain, 2600, census, ebf, **kw)
        assert storyseed.hub_row_slug(chain, 2600, **{k: v for k, v in kw.items() if k != "entry"}) == slug


def test_story_seed_cli_hub_row_flags(tmp_path, monkeypatch, capsys):
    import json
    from ff9mapkit import cli, extract
    chain, census, ebf = _post_zone(tmp_path)
    cpath = tmp_path / "census.json"
    cpath.write_text(json.dumps(census), encoding="utf-8")

    class _Bundle:                                  # the install's event bundle, synthetic
        def eb_for_id(self, d):
            return ebf(d).data
    monkeypatch.setattr(extract, "EventBundle", _Bundle)
    jt = tmp_path / "journeys.toml"
    jt.write_text('[hub]\nname = "T"\nid = 30999\n', encoding="utf-8")
    base = ["story-seed", "--chain", chain, "--beat", "2600", "--census", str(cpath)]
    # a post row lands under its own phase-bearing id, BESIDE (never replacing) the chain's pre-phase row
    assert cli.main(base + ["--hub", str(jt), "--entry", "31000"]) == 0
    assert cli.main(base + ["--hub", str(jt), "--entry", "31001", "--entrance", "6", "--after-advance"]) == 0
    text = jt.read_text(encoding="utf-8")
    assert '# --- story-seed journey "chain_2600" ' in text
    assert '# --- story-seed journey "chain_2600_e6_post" ' in text and 'id    = "chain_2600_e6_post"' in text
    # a refused row returns 1 and leaves journeys.toml as it was
    before = jt.read_bytes()
    assert cli.main(base + ["--hub", str(jt), "--entry", "31001", "--entrance", "5", "--after-advance"]) == 1
    assert jt.read_bytes() == before
    capsys.readouterr()
    # the row flags need --chain --beat --hub: the ladder, the member seeding and one field refuse them
    for argv in (["story-seed", "--chain", chain, "--census", str(cpath), "--after-advance"],
                 base + ["--entrance", "6"], ["story-seed", "900", "--name", "x"]):
        assert cli.main(argv) == 1, argv
        assert "shape a hub journey row" in capsys.readouterr().err


# The real Dali pins. They need the rung-0 dominance census (research/dominance_census.json, generated
# from the user's install) and the install itself. The chain is SYNTHESIZED from F5's frozen member map
# (studies/story-trace/rung5_forks.json chains.F5.members), so no build dir is read or written. A skip
# here is NOT a pass: the gate step and rung5b_hub.py --offline-check assert these PASSED.
F5_MEMBERS = {31101: 351, 31102: 312, 31103: 350, 31104: 352, 31105: 353, 31106: 354, 31107: 355,
              31108: 356, 31109: 357, 31110: 358, 31111: 359, 31112: 450}
F5_ROW = ('[[journey]]\nid    = "dali_chain_2600"\nname  = "Dali (SC 2600)"\nentry = 31111\n'
          'set_scenario = 2600\nset_words = [ { byte = 208, value = 0 }, { byte = 297, value = 1 } ]\n'
          'party_add = [ "garnet", "steiner", "vivi", "zidane" ]')
POST_ROW = ('[[journey]]\nid    = "dali_chain_2600_e6_post"\nname  = "Dali (SC 2600)"\nentry = 31101\n'
            'entrance = 6\nset_scenario = 2600\n'
            'set_flags = [ { flag = 2078, value = 1 }, { flag = 2086, value = 1 } ]\n'
            'set_words = [ { byte = 208, value = 0 }, { byte = 297, value = 1 } ]\n'
            'party_add = [ "zidane" ]\nparty_remove = [ "garnet", "steiner", "vivi" ]')
CTL_ROW = ('[[journey]]\nid    = "dali_chain_2600_e6_control"\nname  = "Dali (SC 2600)"\n'
           'entry = 31101\nentrance = 6\nset_scenario = 2600\n'
           'set_words = [ { byte = 208, value = 0 }, { byte = 297, value = 1 } ]\n'
           'party_add = [ "garnet", "steiner", "vivi", "zidane" ]')


def _f5(tmp_path):
    import json
    import os
    cpath = (os.environ.get("FF9_STORY_CENSUS") or storyseed.find_census()
             or storyseed.find_census(os.environ.get("FF9_F5_DIR", r"C:\gd\_ns_playtest\f5")))
    if not cpath or not os.path.isfile(cpath):
        pytest.skip("F5 REGRESSION PIN NOT RUN: no dominance census (set FF9_STORY_CENSUS, or "
                    "FF9_F5_DIR to the F5 build dir holding research/dominance_census.json)")
    from ff9mapkit.extract import EventBundle
    try:
        b = EventBundle()
        b.eb_for_id(352)
    except Exception:
        pytest.skip("F5 REGRESSION PIN NOT RUN: the install's event bundle is unavailable")
    chain = tmp_path / "dali_chain"
    for mid, don in F5_MEMBERS.items():
        (chain / str(mid)).mkdir(parents=True)
        (chain / str(mid) / "m.field.toml").write_text(f"id = {mid}\ndonor = {don}\n",
                                                       encoding="utf-8")
    cache: dict = {}

    def ebf(d):
        if d not in cache:
            cache[d] = EbScript.from_bytes(b.eb_for_id(d))
        return cache[d]
    return str(chain), json.load(open(cpath, encoding="utf-8")), ebf


def _data(row):
    return "\n".join(l for l in row.split("\n") if not l.startswith("#"))


def test_real_f5_row_is_unchanged(tmp_path):
    # the frozen F5 row (rung5_predictions_v3.json hub.row; deployed as hub 31100) -- must not regress
    chain, census, ebf = _f5(tmp_path)
    assert storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31111) == F5_ROW


def test_real_dali_post_wake_row(tmp_path):
    chain, census, ebf = _f5(tmp_path)
    row = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31101, entrance=6,
                                     after_advance=True, slug="dali_chain_2600_e6_post",
                                     name="Dali (SC 2600)")
    assert _data(row) == POST_ROW
    assert "# bit 2103 = 0 at the hand-over: the exit 352 e14 t2 +116" in row
    ctl = storyseed.hub_journey_toml(chain, 2600, census, ebf, entry=31101, entrance=6,
                                     pre_phase_control=True, slug="dali_chain_2600_e6_control",
                                     name="Dali (SC 2600)")
    assert _data(ctl) == CTL_ROW
    for kw, msg in ((dict(entry=31103, entrance=2, after_advance=True), "not behind an exit"),
                    (dict(entry=31104, entrance=4, after_advance=True), "advance room 352 itself"),
                    (dict(entry=31101, entrance=6), "lies AFTER the advance")):
        with pytest.raises(ValueError, match=msg):
            storyseed.hub_journey_toml(chain, 2600, census, ebf, **kw)
    # Dali 2640's advance (355 e21 t1) warps away itself: its hand-over is that warp -> refused
    with pytest.raises(ValueError, match="leaves the scene"):
        storyseed.hub_journey_toml(chain, 2640, census, ebf, entry=31103, entrance=10,
                                   after_advance=True)
