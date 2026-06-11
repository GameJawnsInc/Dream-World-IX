"""Dialogue text: speaker-name prefix + per-line window TAIL. Pure (no game install needed).

FF9 has no name-box; a speaker name is just prefixed onto the line (optionally via a renameable
name tag like [VIVI]), and the dialogue window's TAIL pointer says who's talking. These check the
text layer + the collect_text integration (speaker prefix, per-line tail, txid mapping).
"""
from __future__ import annotations

from ff9mapkit import build
from ff9mapkit.content import text


def test_with_speaker_prefixes_or_passes_through():
    assert text.with_speaker("Vivi", "Hello.") == "Vivi: Hello."
    assert text.with_speaker(None, "Hello.") == "Hello."          # no speaker -> unchanged
    assert text.with_speaker("[VIVI]", "Hi.") == "[VIVI]: Hi."    # name tag passes through verbatim


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
    body, npc_txids, _, _, _, _ = build.collect_text(_Stub(raw))
    assert "[TAIL=UPL]Vivi: Hello.[ENDN]" in body
    assert "[TAIL=UPR]Yo.[ENDN]" in body
    assert npc_txids == {0: 500, 1: 501}


def test_collect_text_speaker_on_event_and_cutscene():
    raw = {
        "event": [{"name": "Sign", "message": "It reads...", "speaker": "Sign", "zone": [[0, 0]] * 4}],
        "cutscene": {"steps": [{"say": "I'm here.", "speaker": "[ZDNE]", "tail": "LOR"}]},
    }
    body, _, ev_txids, cs_txids, _, _ = build.collect_text(_Stub(raw))
    assert "Sign: It reads...[ENDN]" in body
    assert "[TAIL=LOR][ZDNE]: I'm here.[ENDN]" in body
    assert ev_txids and cs_txids                                  # both got txids


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
    body, _, _, _, _, _ = build.collect_text(_Stub(raw))
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
    body, _, _, _, _, _ = build.collect_text(proj)
    assert "\n" not in body.split("[ENDN]")[0]              # not wrapped (one giant line)
    assert any("wrap is off" in m for m in lint_logic(proj))
