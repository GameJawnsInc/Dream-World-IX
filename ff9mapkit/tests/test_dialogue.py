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


# --- viewer polish: hide system windows, de-dupe, drop the kit-only position heuristic ----
def test_dialogue_call_is_system_by_flags():
    assert D.DialogueCall(0, 0, 68, flags=0).is_system          # flags=0 -> a system/notification window
    assert not D.DialogueCall(1, 3, 500, flags=128).is_system   # 0x80 set -> a real dialogue box
    assert not D.DialogueCall(1, 3, 500, flags=None).is_system  # unknown flags -> shown (not marked system)


def test_join_marks_system_and_can_drop_positions():
    calls = [D.DialogueCall(0, 0, 68, x=0, z=-700, flags=0),     # a system window
             D.DialogueCall(1, 3, 500, x=10, z=20, flags=128)]   # real dialogue
    mes = {68: D.MesEntry(68, "Error"), 500: D.MesEntry(500, "Hi")}
    full = D.join(calls, mes, field_label="F")                   # trust_positions defaults True
    assert full[0].system and not full[1].system
    assert full[1].pos == (10, 20)
    dropped = D.join(calls, mes, field_label="F", trust_positions=False)
    assert dropped[1].pos is None                                # real-field reads suppress the heuristic


def test_present_hides_system_and_dedupes_preferring_npc():
    lines = [
        D.ViewedLine("scene", "F (entry 0, func 0)", 68, "Error", system=True, entry=0),
        D.ViewedLine("scene", "F (entry 1, func 18)", 155, "Hi", entry=1),
        D.ViewedLine("npc", "NPC (entry 1)", 155, "Hi", entry=1),    # same line, from the talk handler
    ]
    clean = D.present(lines)
    assert len(clean) == 1                                       # system hidden; (entry1, 155, "Hi") collapsed
    assert clean[0].source == "npc"                             # ...preferring the NPC-talk representative
    assert len(D.present(lines, show_system=True, dedupe=False)) == 3   # the --all view keeps everything
    # two DIFFERENT objects sharing a txid are NOT collapsed (two NPCs may speak the same line)
    two = [D.ViewedLine("npc", "A", 9, "Yo", entry=1), D.ViewedLine("npc", "B", 9, "Yo", entry=2)]
    assert len(D.present(two)) == 2


# --- editable [[npc]] stubs (import --dialogue) ------------------------------------------
def test_npc_stub_toml_editable_blocks():
    import tomllib
    lines = [
        D.ViewedLine("npc", "NPC (entry 1)", 155, "Hi there, traveler!", entry=1),
        D.ViewedLine("npc", "NPC (entry 1)", 155, "Hi there, traveler!", entry=1),   # dup -> collapsed
        D.ViewedLine("scene", "F (entry 0)", 68, "Error", system=True, entry=0),      # system -> excluded
    ]
    commented = D.npc_stub_toml(lines, field_ref="alex")
    assert commented.count("# [[npc]]") == 1 and "Error" not in commented            # 1 npc; system skipped
    assert "dialogue-import alex" in commented                                       # points at the full script
    assert tomllib.loads(commented).get("npc") is None                              # commented -> nothing live
    # the live form parses as valid TOML with the editable block
    doc = tomllib.loads(D.npc_stub_toml(lines, commented=False))
    assert len(doc["npc"]) == 1
    npc = doc["npc"][0]
    assert npc["dialogue"] == "Hi there, traveler!" and npc["pos"] == [0, 0] and npc["preset"] == "vivi"


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


# --- polish: campaign-wide review + the live-text resolver diagnostic --------------------
def test_flag_overflow_picks_only_overflowing_lines():
    wide = D.ViewedLine("npc", "X", 1, "Supercalifragilisticexpialidocious!!!!!!!!!!")
    fine = D.ViewedLine("npc", "Y", 2, "a short line that fits")
    assert D.flag_overflow([wide, fine]) == [wide]


def test_campaign_dialogue_runs_each_member_and_survives_a_bad_one(tmp_path):
    """campaign_dialogue runs project_dialogue per member; a load failure becomes an error row, not an abort."""
    proj = _mini_project(tmp_path, "Member line.")
    fields = D.campaign_dialogue([("A", proj, None), ("B", None, "boom")])
    assert [f.label for f in fields] == ["A", "B"]
    assert any("Member line." in (ln.text or "") for ln in fields[0].lines)
    assert fields[1].error == "boom" and fields[1].lines == []


def test_text_source_status_reports_missing_unitypy(monkeypatch):
    """When UnityPy can't be imported, the status says so (not a bare 'unresolved')."""
    import ff9mapkit.extract as X

    def _boom():
        raise RuntimeError("UnityPy missing")
    monkeypatch.setattr(X, "_unitypy", _boom)
    assert "UnityPy" in D.text_source_status()


def test_text_source_status_reports_missing_install(monkeypatch):
    """With UnityPy present but no game install, the status points at resources.assets / --game."""
    import ff9mapkit.extract as X
    monkeypatch.setattr(X, "_unitypy", lambda: object())          # pretend UnityPy is importable
    monkeypatch.setattr(D, "_resources_assets", lambda game=None: None)
    s = D.text_source_status()
    assert s != "ok" and "resources.assets" in s


def test_dialogue_cli_reviews_a_whole_campaign(tmp_path, capsys):
    """`ff9mapkit dialogue <campaign.toml>` auto-detects the manifest and reviews every member field."""
    import argparse
    from ff9mapkit import cli
    (tmp_path / "ROOM_A").mkdir()
    (tmp_path / "ROOM_A" / "ROOM_A.field.toml").write_text(
        '[field]\nid = 4000\nname = "ROOM_A"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
        '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
        '[[npc]]\nname = "Guard"\npos = [0, 0]\ndialogue = "Halt, who goes there?"\n', encoding="utf-8")
    camp = tmp_path / "campaign.toml"
    camp.write_text(
        '[campaign]\nname = "TESTCAMP"\nmod_folder = "FF9CustomMap-t"\nid_base = 4000\n\n'
        '[[field]]\nname = "ROOM_A"\nid = 4000\nsource = 100\nmode = "borrow"\n'
        'toml = "ROOM_A/ROOM_A.field.toml"\n', encoding="utf-8")
    rc = cli._cmd_dialogue(argparse.Namespace(field=str(camp), clean=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "dialogue (campaign): TESTCAMP" in out
    assert "ROOM_A (id 4000)" in out and "Halt, who goes there?" in out


def test_dialogue_campaign_survives_a_broken_member(tmp_path, capsys):
    """A member whose field.toml is malformed is noted + skipped -- it must not abort the whole review."""
    import argparse
    from ff9mapkit import cli
    (tmp_path / "GOOD").mkdir()
    (tmp_path / "GOOD" / "GOOD.field.toml").write_text(
        '[field]\nid = 4000\nname = "GOOD"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
        '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
        '[[npc]]\nname = "G"\npos = [0, 0]\ndialogue = "I load fine."\n', encoding="utf-8")
    (tmp_path / "BAD").mkdir()
    (tmp_path / "BAD" / "BAD.field.toml").write_text("this is not valid toml = = =\n", encoding="utf-8")
    camp = tmp_path / "campaign.toml"
    camp.write_text(
        '[campaign]\nname = "C"\nmod_folder = "m"\nid_base = 4000\n\n'
        '[[field]]\nname = "GOOD"\nid = 4000\nsource = 1\nmode = "borrow"\ntoml = "GOOD/GOOD.field.toml"\n\n'
        '[[field]]\nname = "BAD"\nid = 4001\nsource = 2\nmode = "borrow"\ntoml = "BAD/BAD.field.toml"\n',
        encoding="utf-8")
    rc = cli._cmd_dialogue(argparse.Namespace(field=str(camp), clean=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "I load fine." in out                       # the good member still rendered
    assert "BAD (id 4001)" in out and "skipped" in out  # the broken member noted, not a crash


def test_dialogue_field_with_stray_campaign_key_is_not_misrouted(tmp_path, capsys):
    """A single field.toml carries a [field] TABLE -- even with a stray [campaign] key it stays single-field
    (a campaign manifest uses [[field]] = a list), so the auto-detect can't misroute it."""
    import argparse
    from ff9mapkit import cli
    p = tmp_path / "f.field.toml"
    p.write_text(
        '[campaign]\nname = "oops typo"\n\n'                # a stray [campaign] table, but...
        '[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'   # ...a real [field] TABLE
        '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
        '[[npc]]\nname = "V"\npos = [0, 0]\ndialogue = "single field still."\n', encoding="utf-8")
    rc = cli._cmd_dialogue(argparse.Namespace(field=str(p), clean=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "dialogue (campaign)" not in out and "single field still." in out
