"""Dialogue text: the faithful speaker convention + per-line window TAIL. Pure (no install needed).

FF9 has no name-box; attribution is authored INTO the text, and the real form (census 2026-07-18,
12,711 stock entries: 9,009 use it, ZERO use a colon) is the name on its OWN line followed by the
dialogue in literal curly quotes -- ``Name\\n“line”`` -- with a fully-parenthesized line rendering
as the silent-thought sibling ``Name\\n(line)`` and unattributed text carrying no name and no
quotes. The dialogue window's TAIL pointer still says who's talking. These check the text layer +
the collect_text integration (speaker form, per-line tail, txid mapping).
"""
from __future__ import annotations

from ff9mapkit import build
from ff9mapkit.content import text


def test_with_speaker_is_the_stock_name_line_plus_quotes():
    assert text.with_speaker("Vivi", "Hello.") == "Vivi\n“Hello.”"
    assert text.with_speaker(None, "Hello.") == "Hello."           # no speaker -> unchanged, unquoted
    assert text.with_speaker("[VIVI]", "Hi.") == "[VIVI]\n“Hi.”"   # name tag slots in identically
    assert text.with_speaker("[TEXT=0,0]", "Kupo!") == "[TEXT=0,0]\n“Kupo!”"   # variable speaker


def test_with_speaker_thought_form_and_wrap_composition():
    # a fully-parenthesized line = the stock silent-thought convention: parens, NO quotes
    assert text.with_speaker("[ZDNE]", "(Hmm...)") == "[ZDNE]\n(Hmm...)"
    # a paren that doesn't span the whole line is ordinary speech
    assert text.with_speaker("Vivi", "(sigh) Fine.") == "Vivi\n“(sigh) Fine.”"
    # wrap keeps ONE quote pair spanning all wrapped lines: open glued to the first word, close to
    # the last, interior lines bare -- the stock multi-line shape
    wrapped, overflow = text.wrap_text(text.with_speaker(
        "Vivi", "We can send and receive letters to and from moogles in other locations!"), 28.0)
    lines = wrapped.split("\n")
    assert lines[0] == "Vivi" and not overflow
    assert lines[1].startswith("“") and lines[-1].endswith("”")
    assert all("“" not in ln and "”" not in ln for ln in lines[2:-1])


def test_menu_style_is_the_stock_moogle_window_shape():
    """Stock field 300 txid 3's head, reproduced: [WDTH] (variable speaker) + [IMME] + the [FEED]
    indents (name 2, dialogue 4). txid 6 (the plain no-tents window) keeps [IMME]+[WDTH] but has NO
    feeds -- those ride the choice windows only."""
    attributed = text.with_speaker("[TEXT=0,0]", "Can I help you, kupo?")
    assert text.menu_style(attributed, speaker="[TEXT=0,0]") == (
        "[WDTH=0,2,6,0,-1][IMME][FEED=2][TEXT=0,0]\n[FEED=4]“Can I help you, kupo?”")
    assert text.menu_style(attributed, speaker="[TEXT=0,0]", feeds=False) == (
        "[WDTH=0,2,6,0,-1][IMME][TEXT=0,0]\n“Can I help you, kupo?”")
    # every wrapped dialogue line gets its own indent (stock's tent prompt feeds both of its lines)
    styled = text.menu_style("[TEXT=0,0]\n“one”\n“two”", speaker="[TEXT=0,0]")
    assert styled.count("[FEED=4]") == 2 and styled.count("[FEED=2]") == 1
    # a LITERAL speaker needs no width hint (the engine measures it) -- and no speaker, no name feed
    assert text.menu_style(text.with_speaker("Mog", "Hi."), speaker="Mog") == (
        "[IMME][FEED=2]Mog\n[FEED=4]“Hi.”")
    assert text.menu_style("Plain.", speaker=None) == "[IMME][FEED=4]Plain."


def test_width_hint_and_menu_pos_tags():
    assert text.width_hint("[TEXT=0,0]") == "[WDTH=0,2,6,0,-1]"
    assert text.width_hint("[TEXT=0,3]", base=7) == "[WDTH=0,7,6,3,-1]"
    assert text.width_hint("Mog") == "" and text.width_hint(None) == ""
    assert text.menu_pos_tag((20, 16)) == "[MPOS=20,16]"      # stock's own main-menu placement
    assert text.menu_pos_tag(None) == ""
    assert text.MENU_POS_STOCK == ((20, 16), (30, 26))


def test_mes_entry_tail():
    assert "[TAIL=UPL]" in text.mes_entry("hi", 500, tail="UPL")
    assert "[TAIL=UPR]" in text.mes_entry("hi", 500)              # default tail unchanged (UPR)


def test_build_mes_per_line_tails():
    body, mapping = text.build_mes(["a", "b", "c"], tails=["UPL", None, "LOC"])
    assert "[TAIL=UPL]a[ENDN]" in body
    assert "[TAIL=UPR]b[ENDN]" in body                           # None -> DEFAULT_TAIL
    assert "[TAIL=LOC]c[ENDN]" in body
    assert mapping == {0: 500, 1: 501, 2: 502}


class _Stub:
    def __init__(self, raw):
        self.raw = raw


def test_collect_text_applies_speaker_and_tail():
    raw = {"npc": [{"name": "V", "dialogue": "Hello.", "speaker": "Vivi", "tail": "UPL"},
                   {"name": "W", "dialogue": "Yo."}]}             # second: defaults
    body, npc_txids, _, _, _, _, _, _, _gw9, _co10, _sp11, _bh12, _ni13 = build.collect_text(_Stub(raw))
    assert "[TAIL=UPL]Vivi\n“Hello.”[ENDN]" in body
    assert "[TAIL=UPR]Yo.[ENDN]" in body                          # no speaker: no name line, no quotes
    assert npc_txids == {0: 500, 1: 501}


def test_collect_text_speaker_on_event_and_cutscene():
    raw = {
        "event": [{"name": "Sign", "message": "It reads...", "speaker": "Sign", "zone": [[0, 0]] * 4}],
        "cutscene": {"steps": [{"say": "I'm here.", "speaker": "[ZDNE]", "tail": "LOR"}]},
    }
    body, _, ev_txids, cs_txids, _, _, _, _, _gw9, _co10, _sp11, _bh12, _ni13 = build.collect_text(_Stub(raw))
    assert "Sign\n“It reads...”[ENDN]" in body
    assert "[TAIL=LOR][ZDNE]\n“I'm here.”[ENDN]" in body
    assert ev_txids and cs_txids                                  # both got txids


# --- the dialogue-less NPC default talk (the fort-condor swarm bug) ----------------------
def test_dialogueless_npc_owns_its_txid_not_the_choice_prompt():
    # THE FORT-CONDOR SWARM BUG: a dialogue-less [[npc]]'s default talk was WindowSync(1,128,500) --
    # 500 is the mes allocation BASE, not a line the NPC owns. The [[choice]] prompt allocated txid 500
    # first, so talking to every silent NPC opened the choice menu, dead rows included, with no
    # GetChoose dispatch behind them. The default talk now allocates its OWN silent line.
    raw = {"npc": [{"name": "Swarm", "pos": [0, -100]}],           # no dialogue, no choice attached
           "choice": [{"zone": [[0, 0]] * 4, "prompt": "Which way?",
                       "options": [{"text": "Left"}, {"text": "Right"}]}]}
    body, npc_txids, _, _, choice_txids, _, _, _, _, _, _, _, _ = build.collect_text(_Stub(raw))
    assert 0 in npc_txids                                          # the silent NPC owns a line now
    assert npc_txids[0] != choice_txids[0]["prompt"]               # ...distinct from the choice prompt
    assert f"[TXID={npc_txids[0]}]" in body                        # and the line actually ships
    assert text.DEFAULT_SILENT_TALK in body
    # the silent line is added LAST: the choice prompt keeps its old txid (500), so a field
    # without a silent NPC keeps the previous layout byte-identical
    assert choice_txids[0]["prompt"] == 500 and npc_txids[0] > choice_txids[0]["prompt"]


def test_silent_default_only_for_npcs_that_keep_the_default_talk():
    # dialogue, an attached [[choice]], opens_shop, and an explicit text_id all opt out of the silent
    # default line -- so every existing field that uses only those stays byte-identical.
    raw = {"npc": [{"name": "Talker", "dialogue": "Hi."},
                   {"name": "Menu"},                               # choice-attached: talk IS the menu
                   {"name": "Shop", "opens_shop": 0},              # talk -> Menu(2, id)
                   {"name": "Donor", "text_id": 42}],              # author-directed txid (donor text)
           "choice": [{"npc": "Menu", "prompt": "?", "options": [{"text": "A"}]}]}
    body, npc_txids, *_ = build.collect_text(_Stub(raw))
    assert npc_txids == {0: 500}                                   # only the voiced NPC allocates
    assert text.DEFAULT_SILENT_TALK not in body


def test_verbatim_silent_npc_rides_the_appended_channel_in_lockstep(tmp_path):
    # the same bug on the verbatim path fell back to txid 500 -- INSIDE the donor's own .mes band (real
    # donor text reaches 863), rendering a random donor line. The silent line now rides the appended-text
    # channel AFTER the voiced block (voiced txids stay byte-stable), and every downstream appender's
    # base counts it (no txid overlap).
    raw = {"npc": [{"name": "Silent", "pos": [0, 0]},
                   {"name": "V", "pos": [1, 1], "dialogue": "Hi."}],
           "event": [{"name": "E", "zone": [[0, 0]] * 4, "message": "Found it."}]}
    proj = build.FieldProject(raw, tmp_path)
    npc_txids, npc_sfx = build._verbatim_npc_messages(proj, ["us"])
    ev_txids, _ = build._verbatim_event_messages(proj, ["us"])
    assert set(npc_txids) == {0, 1}
    assert npc_txids[1] == 1000                        # the voiced NPC keeps the old base (byte-stable)
    assert npc_txids[0] == 1001                        # the silent line appends AFTER the voiced block
    assert text.DEFAULT_SILENT_TALK in npc_sfx["us"]
    assert set(ev_txids.values()).isdisjoint(npc_txids.values())   # the count stayed in lockstep


def test_invalid_tail_code_is_rejected(tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "f.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
        '[walkmesh]\nquad = [[0, 0], [10, 0], [10, 10], [0, 10]]\n\n'
        '[[npc]]\nname = "V"\npos = [0, 0]\ndialogue = "hi"\ntail = "NOPE"\n', encoding="utf-8")
    # validate may flag other things (e.g. the missing borrow file), but the bad tail must be among them
    assert any("tail" in m and "NOPE" in m for m in validate(FieldProject.load(p)))


# --- proportional auto-wrap --------------------------------------------------------------
def test_measure_is_proportional():
    # wide glyphs cost more than narrow ones (the whole point of "accurate" wrapping)
    assert text.measure("WWWW") > text.measure("iiii") * 2
    assert text.measure("[VIVI]") > 0                       # a name tag renders ~a name
    assert text.measure("[C8C8C8]") == 0                    # a color tag renders nothing


def test_wrap_breaks_a_long_line_within_budget():
    line = "This is a very long sentence that clearly does not fit on a single dialogue line at all."
    wrapped, overflow = text.wrap_text(line, 28)
    assert "\n" in wrapped and not overflow
    assert wrapped.replace("\n", " ") == line              # only breaks added; words intact, in order
    assert all(text.measure(ln) <= 28 for ln in wrapped.split("\n"))


def test_wrap_respects_existing_breaks_and_pages():
    t = "short one\nshort two[PAGE]page two"
    wrapped, _ = text.wrap_text(t, 28)
    assert wrapped == t                                     # already fits -> byte-identical, breaks kept


def test_wrap_short_line_is_byte_identical():
    assert text.wrap_text("I miss you Zidane", 28) == ("I miss you Zidane", [])


def test_wrap_reports_unbreakable_overflow_word():
    huge = "Supercalifragilisticexpialidocious!!!!!!!!!!"
    _, overflow = text.wrap_text(huge, 28)
    assert huge in overflow
    assert text.overflow_lines(huge, 28) == [huge]


def test_collect_text_wraps_long_dialogue_but_not_short():
    long_line = ("If you should ever find your way back to this little place, "
                 "know that you are always welcome here, old friend.")
    raw = {"npc": [{"name": "L", "dialogue": long_line}, {"name": "S", "dialogue": "Hi."}]}
    body, _, _, _, _, _, _, _, _gw9, _co10, _sp11, _bh12, _ni13 = build.collect_text(_Stub(raw))
    assert body.count("\n") >= 2          # more than the single entry-separator -> the long line wrapped
    assert long_line not in body          # the long line was broken (not a contiguous run)
    assert "Hi.[ENDN]" in body            # the short line is verbatim, no inserted break


def test_dialogue_wrap_can_be_disabled(tmp_path):
    from ff9mapkit.build import FieldProject, lint_logic
    p = tmp_path / "f.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "X"\narea = 11\n\n[dialogue]\nwrap = false\n\n'
        '[camera]\nborrow = "c.bgx"\n\n[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
        '[[npc]]\nname = "V"\npos = [0, 0]\ndialogue = "' + "word " * 40 + '"\n', encoding="utf-8")
    proj = FieldProject.load(p)
    body, _, _, _, _, _, _, _, _gw9, _co10, _sp11, _bh12, _ni13 = build.collect_text(proj)
    assert "\n" not in body.split("[ENDN]")[0]              # not wrapped (one giant line)
    assert any("wrap is off" in m for m in lint_logic(proj))


# --- fixed low txids (the save-Moogle menus reference text ids 0/3/4/8/11-18) ------------------------
def test_build_mes_fixed_emits_explicit_ids():
    from ff9mapkit.content import text as _t
    body = _t.build_mes_fixed([(3, "menu"), (0, "roster"), (18, "mail")])
    assert "[TXID=0]" in body and "[TXID=3]" in body and "[TXID=18]" in body
    # ...in ascending id order, whatever order they were supplied in
    assert body.index("[TXID=0]") < body.index("[TXID=3]") < body.index("[TXID=18]")
    assert "roster" in body and "menu" in body and "mail" in body


def test_build_mes_fixed_keys_tails_and_strts_by_txid():
    from ff9mapkit.content import text as _t
    body = _t.build_mes_fixed([(0, "a"), (7, "b")], tails={7: ""}, strts={7: (20, 3)})
    assert "[STRT=20,3]" in body
    line7 = [ln for ln in body.split("\n") if "[TXID=7]" in ln][0]
    assert "[TAIL=" not in line7                      # "" = explicit NO tail
    line0 = [ln for ln in body.split("\n") if "[TXID=0]" in ln][0]
    assert f"[TAIL={_t.DEFAULT_TAIL}]" in line0       # unspecified -> the default


def test_build_mes_fixed_empty_is_empty():
    from ff9mapkit.content import text as _t
    assert _t.build_mes_fixed([]) == ""


def test_build_mes_fixed_does_not_disturb_sequential_build_mes():
    """The two must be able to coexist in one block: fixed low ids + the authored 500+ run."""
    from ff9mapkit.content import text as _t
    seq, mapping = _t.build_mes(["x", "y"])
    fixed = _t.build_mes_fixed([(0, "roster"), (3, "menu")])
    assert min(mapping.values()) >= _t.DEFAULT_BASE_TXID
    assert "[TXID=0]" not in seq and "[TXID=500]" not in fixed
