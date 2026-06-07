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
    body, npc_txids, _, _ = build.collect_text(_Stub(raw))
    assert "[TAIL=UPL]Vivi: Hello.[ENDN]" in body
    assert "[TAIL=UPR]Yo.[ENDN]" in body
    assert npc_txids == {0: 500, 1: 501}


def test_collect_text_speaker_on_event_and_cutscene():
    raw = {
        "event": [{"name": "Sign", "message": "It reads...", "speaker": "Sign", "zone": [[0, 0]] * 4}],
        "cutscene": {"steps": [{"say": "I'm here.", "speaker": "[ZDNE]", "tail": "LOR"}]},
    }
    body, _, ev_txids, cs_txids = build.collect_text(_Stub(raw))
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
