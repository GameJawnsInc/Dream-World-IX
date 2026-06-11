"""The dialogue READ spine: parse a .mes, decode an .eb's calls, join them, view a project.

Pure tests run anywhere; the two that need real bytes (scan a real field .eb, the offline JOIN against
the shipped hut) are gated on those files being present, like the golden tests -- they regenerate from
the user's install and may be absent in a clean checkout.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import dialogue as D
from ff9mapkit.content import text as T

REPO = Path(__file__).resolve().parents[2]
HUT_MOD = REPO / "release" / "FF9CustomMap"                 # the kit's own known-good hut (committed)
ALEX_EB = Path(__file__).resolve().parent / "fixtures" / "alex100-us.eb.bytes"   # a REAL field .eb


# --- parse_mes: the missing reader (inverse of content.text) -----------------------------
def test_parse_mes_round_trips_build_mes():
    body, mapping = T.build_mes(["Hello there.", "Line two"], tails=["UPL", None])
    parsed = D.parse_mes(body)
    assert set(parsed) == set(mapping.values()) == {500, 501}
    assert parsed[500].text == "Hello there." and parsed[500].tail == "UPL"
    assert parsed[501].text == "Line two" and parsed[501].tail == "UPR"   # None -> DEFAULT_TAIL


def test_parse_mes_real_format_line():
    # the exact grammar the engine + the kit's shipped 1073.mes use
    parsed = D.parse_mes("_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]")
    assert parsed[500].text == "I miss you Zidane"
    assert parsed[500].tail == "UPR" and parsed[500].strt == "10,1"


def test_parse_mes_multiline_and_pages():
    body = "_[TXID=7][STRT=10,1][TAIL=LOC]line one\nline two[PAGE]page two[ENDN]"
    e = D.parse_mes(body)[7]
    assert e.text == "line one\nline two[PAGE]page two"            # wrapped \n + [PAGE] preserved verbatim


def test_parse_mes_base_game_index_implicit():
    # REAL FF9 field text carries NO [TXID=] tags -- the txid is the entry's 0-based position (the
    # exact form `100.mes` etc. use; this is what makes "import from the game" actually resolve text)
    parsed = D.parse_mes("[STRT=55,1]Dragonfly[ENDN][STRT=40,1]Charge[ENDN]")
    assert parsed[0].text == "Dragonfly" and parsed[1].text == "Charge"
    assert parsed[0].strt == "55,1" and parsed[0].tail is None


def test_parse_mes_txid_reindexes_running_id():
    # a [TXID=n] marker re-indexes; entries increment from there (so a real field's 0..67 then a jump works)
    parsed = D.parse_mes("[STRT=10,1]zero[ENDN][TXID=68][STRT=10,1]sixtyeight[ENDN][STRT=10,1]sixtynine[ENDN]")
    assert parsed[0].text == "zero" and parsed[68].text == "sixtyeight" and parsed[69].text == "sixtynine"


def test_strip_tags_renders_readably():
    assert D.strip_tags("[C8C8C8]hi[ENDN]".replace("[ENDN]", "")) == "hi"   # colour tag drops out
    assert D.strip_tags("[VIVI]: hello") == "Vivi: hello"                    # name tag -> its plain code
    assert "---" in D.strip_tags("a[PAGE]b")                                 # page break -> separator


# --- scan_dialogue: decode an .eb's dialogue calls ---------------------------------------
def test_scan_dialogue_on_synthetic_window_sync():
    # a WindowSync(1, 128, 500) is op 0x1F with txid at operand 2 -> scan must surface txid 500
    from ff9mapkit.eb import opcodes
    code = opcodes.window_sync(1, 128, 500)
    txid = None
    from ff9mapkit.eb.disasm import iter_code
    for ins in iter_code(code, 0, len(code)):
        if ins.op == 0x1F:
            txid = ins.imm(2)
    assert txid == 500                                                       # the operand layout we rely on


@pytest.mark.skipif(not ALEX_EB.is_file(), reason="real alex100 .eb fixture absent (regenerates from install)")
def test_scan_dialogue_on_real_field_eb():
    calls = D.scan_dialogue(ALEX_EB.read_bytes())
    assert calls, "a real populated field has dialogue"
    assert any(c.kind == "npc" for c in calls)                              # tag-3 talk handlers
    assert all(c.txid is None or isinstance(c.txid, int) for c in calls)
    assert {c.op for c in calls} <= set(D.WINDOW_OPS)                       # only window opcodes collected


# --- join: the two read directions meet on txid ------------------------------------------
def test_join_pairs_calls_with_text():
    calls = [D.DialogueCall(2, 3, 500, x=0, z=-700, model=8),               # an NPC talk
             D.DialogueCall(4, 0, 777)]                                     # a scene line, no text
    mes = {500: D.MesEntry(500, "Hello!", tail="UPR")}
    lines = D.join(calls, mes, field_label="HUT")
    assert lines[0].source == "npc" and lines[0].text == "Hello!" and lines[0].pos == (0, -700)
    assert lines[1].source == "scene" and lines[1].text is None            # unresolved txid -> None, kept


# --- the offline plausibility proof: the kit's own hut, no install -----------------------
@pytest.mark.skipif(not HUT_MOD.is_dir(), reason="release/FF9CustomMap absent")
def test_read_local_dialogue_joins_the_hut():
    lines = D.read_local_dialogue(HUT_MOD, "HUT_INT")
    talk = [ln for ln in lines if ln.source == "npc" and ln.text]
    assert talk, "the hut's NPC should resolve to its line"
    assert any(ln.text == "I miss you Zidane" for ln in talk)              # decoded .eb JOIN parsed .mes
    # format_lines renders it
    out = D.format_lines(lines)
    assert "I miss you Zidane" in out and "[npc]" in out


# --- project_dialogue: the authored lines of a field.toml --------------------------------
def _mini_project(tmp_path, dialogue):
    p = tmp_path / "f.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
        '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
        f'[[npc]]\nname = "V"\npos = [0, 0]\ndialogue = "{dialogue}"\n', encoding="utf-8")
    from ff9mapkit.build import FieldProject
    return FieldProject.load(p)


def test_project_dialogue_lists_authored_lines(tmp_path):
    proj = _mini_project(tmp_path, "Hello from the editor.")
    lines = D.project_dialogue(proj)
    assert any(ln.source == "npc" and ln.who == "V" and "Hello from the editor." in (ln.text or "")
               for ln in lines)


def test_collect_text_refs_covers_every_section():
    data = {
        "npc": [{"name": "V", "dialogue": "hi", "speaker": "Vivi"}],
        "event": [{"name": "Sign", "message": "reads..."}],
        "choice": [{"npc": "V", "prompt": "Well?", "options": [{"text": "Yes", "reply": "Good."},
                                                               {"text": "No"}]}],
        "cutscene": {"steps": [{"say": "Once upon a time."}, {"wait": 10}]},
    }
    refs = D.collect_text_refs(data)
    secs = [r.section for r in refs]
    assert secs == ["npc", "event", "choice", "reply", "reply", "cutscene"]      # prompt + 2 replies
    npc = refs[0]
    assert D.get_text(data, npc.path) == "hi" and D.get_text(data, npc.speaker_path) == "Vivi"


def test_set_text_writes_adds_and_removes():
    data = {"npc": [{"name": "V", "dialogue": "old"}],
            "choice": [{"npc": "V", "prompt": "Q", "options": [{"text": "Yes"}]}]}
    assert D.set_text(data, ("npc", 0, "dialogue"), "new") and data["npc"][0]["dialogue"] == "new"
    assert D.set_text(data, ("npc", 0, "speaker"), "Vivi") and data["npc"][0]["speaker"] == "Vivi"
    assert D.set_text(data, ("npc", 0, "speaker"), "")                            # empty -> removed
    assert "speaker" not in data["npc"][0]
    # add a reply to an option that had none
    assert D.set_text(data, ("choice", 0, "options", 0, "reply"), "Great.")
    assert data["choice"][0]["options"][0]["reply"] == "Great."


def test_field_text_id_table():
    # the engine's own field-map-id -> text-block (MES) id table (baked from Memoria's eventIDToMESID).
    # This is how dialogue-import reads the RIGHT block for a real field (txids alone can't pick it).
    from ff9mapkit._fieldtext import EVENT_ID_TO_MES
    assert EVENT_ID_TO_MES[100] == 33        # Alexandria (1)
    assert EVENT_ID_TO_MES[1059] == 44
    assert len(EVENT_ID_TO_MES) > 800


def test_wrap_preview_and_overflow():
    long = "If you should ever find your way back to this little place know that you are welcome."
    assert "\n" in D.wrap_preview(long)                                     # a long line wraps for preview
    assert D.overflow("short enough") == []                                 # nothing overflows
    assert D.overflow("Supercalifragilisticexpialidocious!!!!!!!!!!")       # an unbreakable wide word does
