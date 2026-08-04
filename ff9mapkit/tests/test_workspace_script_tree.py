"""The verbatim 'Script' tree PRESENTATION -- the call-site fences for logic_map's semantic layer.

The pure layer (kind labels, flag bands, selectors, battles, warp names) is fenced in test_logic_map.py;
this file proves the SHELL SPENDS it: the tree rows lead with the human name (Talk handler / Field
startup), the group teaches the story-beat lever when Main_Init dispatches on the scenario counter, a
dormant entry is chipped on its row, warps name their campaign-member destination, and the edit panel's
header carries the routine's human name.

Driven over a KIT-AUTHORED synthetic verbatim .eb (raw instruction bytes assembled here -- zero
Square-Enix bytes, no install, no extracted templates), so this runs in every worktree -- unlike the
smoke's ALEX-fixture block, which a fresh worktree skips.

Headless (offscreen), NO_THUMBS; prefs isolated by conftest's autouse ``_isolate_prefs``.
"""
from __future__ import annotations

import os
import struct

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel                             # noqa: E402

from ff9mapkit import campaign as C                                            # noqa: E402
from ff9mapkit.workspace import anim                                           # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    anim.set_enabled(False)
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    app.processEvents()
    yield w
    w.close()


# --------------------------------------------------------------- the synthetic .eb (kit-authored bytes)
RET = b"\x04"                                          # the 0-arg terminator


def _expr_scenario() -> bytes:
    return b"\x05\xDC\x00\x7F"                         # 0x05 expr: push ScenarioCounter (DC 00), end


def _switchex(default_rel: int, pairs) -> bytes:
    """0x06 JMP_SWITCHEX: count byte, then u16 args -- default reloff, (value, reloff) pairs."""
    vals = [default_rel]
    for v, r in pairs:
        vals += [v, r]
    return bytes([0x06, len(pairs)]) + b"".join(struct.pack("<H", x) for x in vals)


def _init_object(slot: int) -> bytes:
    return bytes([0x09, slot, 0])                      # InitObject(slot, arg) -- 1-byte args, no flag byte


def _init_region(slot: int) -> bytes:
    return bytes([0x08, slot, 0])                      # InitRegion(slot, arg) -- same encoding as InitObject


def _set_model(mid: int) -> bytes:
    return bytes([0x2F, 0x00]) + struct.pack("<H", mid) + b"\x00"    # SetModel(model u16, animset u8)


def _window(txid: int) -> bytes:
    return bytes([0x1F, 0x00, 0, 0]) + struct.pack("<H", txid)       # WindowSync(u8, u8, txid u16)


def _add_item(iid: int, count: int = 1) -> bytes:
    return bytes([0x48, 0x00]) + struct.pack("<H", iid) + bytes([count])


def _set_flag_long(idx: int) -> bytes:
    return b"\x05\xE4" + struct.pack("<H", idx) + b"\x7D\x01\x00\x2C\x7F"     # Global.Bit[idx] = 1


def _field_warp(fid: int) -> bytes:
    return bytes([0x2B, 0x00]) + struct.pack("<H", fid)


def _battle(scene: int) -> bytes:
    return bytes([0x2A, 0x00, 0x00]) + struct.pack("<H", scene)      # Battle(rush u8, btlId u16)


def _eb_file(entries) -> bytes:
    """Assemble a multi-entry .eb: per entry a list of (tag, body). Mirrors EbScript's layout (the
    8-byte entry-table slots at 0x80; per entry: etype, fc, (tag, fpos)* table, bodies)."""
    blobs = []
    for funcs in entries:
        fc = len(funcs)
        table, bodies, fpos = b"", b"", fc * 4
        for tag, body in funcs:
            table += struct.pack("<HH", tag, fpos)
            bodies += body
            fpos += len(body)
        blobs.append(bytes([0, fc]) + table + bodies)
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = len(blobs)
    slots, out, off = b"", b"", 8 * len(blobs)
    for b in blobs:
        slots += struct.pack("<HHBBH", off, len(b), 0, 0, 0)
        off += len(b)
        out += b
    return bytes(head) + slots + out


def demo_verbatim_eb(model_id: int = 0) -> bytes:
    """The demo field: Main_Init (spawns + a story-beat SWITCHEX) · a player · a talkable NPC
    (dialogue + reward + a kit-band once-flag) · a DORMANT object (defined, never spawned) · a
    warp+battle trigger entry -- armed by InitRegion, the way real fields arm region entries
    (spawns must count all THREE init ops, not just InitObject). The InitObject(252) is the
    engine's party-slot selector -- it must NOT count as arming an entry."""
    # entry 0 tag 0: spawn 1/2, arm region 4 (entry 3 stays dormant), push SC, dispatch beats 1900/2005
    spawns = _init_object(1) + _init_object(2) + _init_region(4) + _init_object(252)
    sw_off = len(spawns) + len(_expr_scenario())       # the switch's function-relative offset
    sw_len = 2 + 2 * 5                                 # op+count + 5 u16 args (default + 2 pairs)
    anchor = sw_off + 4                                # 0x06 reloffs anchor at O+4
    t0 = sw_off + sw_len                               # three terminators follow the switch
    sw = _switchex(t0 - anchor, [(1900, t0 + 1 - anchor), (2005, t0 + 2 - anchor)])
    main0 = spawns + _expr_scenario() + sw + RET + RET + RET
    return _eb_file([
        [(0, main0), (10, _set_flag_long(8713) + RET)],                # main: startup + after-battle re-arm
        [(0, b"\x2C" + RET), (1, RET)],                                # player: DefinePC + idle loop
        [(0, _set_model(model_id) + RET), (1, RET),                    # NPC: model + loop +
         (3, _window(1) + _add_item(236) + _set_flag_long(8712) + RET)],   # talk: line/reward/kit flag
        [(0, _set_model(model_id) + RET), (3, _window(2) + RET)],      # DORMANT (never InitObject'd)
        [(2, _field_warp(30101) + RET), (3, _battle(67) + RET)],       # invisible trigger: warp + battle
        [(1, _set_flag_long(8714) + RET)],                             # script helper: a loop, no contact
    ])


def demo_mes_body() -> str:
    return ("[TXID=1][STRT=32,1][IMME]Kupo! Have you seen my letter?[TIME=-1]\n"
            "[TXID=2][STRT=32,1][IMME]The old sign is too faded to read.[TIME=-1]")


def make_demo_campaign(root) -> "os.PathLike":
    """A 2-member campaign: GLADE (the verbatim demo) + TRAIL (a plain member, so the Field(30101)
    warp resolves to a NAMED destination). Returns the campaign.toml path."""
    import json
    root.mkdir(parents=True, exist_ok=True)
    mem = [C.Member(100, 30100, "GLADE", "borrow", 11, "", "GLADE/GLADE.field.toml", False),
           C.Member(101, 30101, "TRAIL", "borrow", 11, "", "TRAIL/TRAIL.field.toml", False)]
    plan = C.CampaignPlan(name="Demo", mod_folder="M", id_base=30100, flag_base=C.FIRST_SAFE_FLAG,
                          flags_per_field=64, entry_name="GLADE", entry_entrance=0,
                          members=mem, edges=[], seams=[])
    (root / "campaign.toml").write_text(C.render_campaign_toml(plan), encoding="utf-8")
    (root / "GLADE").mkdir(exist_ok=True)
    (root / "TRAIL").mkdir(exist_ok=True)
    (root / "GLADE" / "GLADE.field.toml").write_text(
        '[field]\nid = 30100\nname = "GLADE"\narea = 11\n\n'
        '[verbatim_eb]\nbin = "GLADE.verbatim_eb.bin"\ntext = "GLADE.text.json"\n', encoding="utf-8")
    (root / "GLADE" / "GLADE.verbatim_eb.bin").write_bytes(demo_verbatim_eb())
    (root / "GLADE" / "GLADE.text.json").write_text(json.dumps({"us": demo_mes_body()}), encoding="utf-8")
    (root / "TRAIL" / "TRAIL.field.toml").write_text(
        '[field]\nid = 30101\nname = "TRAIL"\narea = 11\n', encoding="utf-8")
    return root / "campaign.toml"


def _script_group(win, app):
    win.tree.expandItem(win.tree.topLevelItem(0))
    vitem = win.tree.topLevelItem(0).child(0)
    win.tree.expandItem(vitem)
    app.processEvents()
    grp = next(vitem.child(i) for i in range(vitem.childCount())
               if win._payload(vitem.child(i))[0] == "logic_root")
    win.tree.expandItem(grp)
    app.processEvents()
    return grp


def _rows(grp):
    out = {}
    for i in range(grp.childCount()):
        e = grp.child(i)
        out[e.text(0)] = [e.child(j).text(0) for j in range(e.childCount())]
    return out


def test_script_tree_speaks_the_engines_conventions_in_human_words(win, app, tmp_path):
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    rows = _rows(grp)
    flat = "\n".join(list(rows) + [r for rs in rows.values() for r in rs])
    # the routine rows lead with the HUMAN name; the raw tag stays (edits key on it)
    assert "Field startup · tag 0" in flat, flat
    assert "After-battle re-entry · tag 10" in flat
    assert "Talk handler · tag 3" in flat
    # (the player's DefinePC-only setup routine is EMPTY to the scanners and stays filtered -- by design)
    assert "Contact trigger · tag 2" in flat
    assert "Action trigger · tag 3" in flat
    assert " / tag " not in flat, "no row falls back to the machine 'kind / tag N' form"
    # a defined-but-never-spawned entry is chipped on its ROW, not only in the detail
    assert any("· not spawned" in r for r in rows), rows.keys()


def test_region_armed_trigger_is_not_labeled_dormant(win, app, tmp_path):
    """The demo's invisible trigger is armed by InitRegion (0x08) -- all THREE engine init ops count as
    spawns, not just InitObject (pre-fix, a real fork mislabeled ~77% of region/helper entries dormant).
    The InitObject(252) party-slot selector arms nothing; entry 3 stays the only dormant row."""
    from ff9mapkit.workspace.shell import _DETAIL
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    rows = {grp.child(i).text(0): "\n".join(grp.child(i).data(0, _DETAIL) or [])
            for i in range(grp.childCount())}
    trig = next(k for k in rows if "invisible trigger" in k)
    assert "not spawned" not in trig, trig
    assert "spawned: 1x" in rows[trig], rows[trig]
    dormant = [k for k in rows if "· not spawned" in k]
    assert len(dormant) == 1 and dormant[0].startswith("entry 3"), dormant


def test_script_group_teaches_the_story_beat_lever(win, app, tmp_path):
    from ff9mapkit.workspace.shell import _DETAIL
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    det = "\n".join(grp.data(0, _DETAIL) or [])
    assert "STORY BEAT" in det and "[startup] scenario" in det, det


def test_routine_detail_names_the_warp_and_the_battle(win, app, tmp_path):
    from ff9mapkit.workspace.shell import _DETAIL
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    details = []
    for i in range(grp.childCount()):
        for j in range(grp.child(i).childCount()):
            details += grp.child(i).child(j).data(0, _DETAIL) or []
    txt = "\n".join(details)
    assert "Warps to field 30101 — TRAIL" in txt, txt          # the member name resolves the retarget id
    assert "Starts a battle (scene 67" in txt, txt
    assert "flag 8712 (kit band" in txt, txt                   # the kit-allocated once-flag names its band
    assert "Kupo! Have you seen my letter?" in txt, txt        # dialogue text rides the .mes json


def test_edit_panel_header_carries_the_routines_human_name(win, app, tmp_path):
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    _script_group(win, app)                                    # builds + caches the logic map
    win._open_editor("GLADE", "logic_node", "logic_n:2:3")     # the NPC talk handler
    app.processEvents()
    labels = [w.text() for w in win.findChildren(QLabel)]
    assert any("Talk handler" in t and "entry 2 / tag 3" in t for t in labels), \
        [t for t in labels if "entry 2" in t]


# ------------------------------------------------------- the concepts round: the nouns get taught
def test_entry_rows_split_the_logic_wall_into_trigger_and_helper(win, app, tmp_path):
    """A real fork shows a WALL of 'entry N: logic' rows (Prima Vista: seven in a column). A model-less
    entry with a contact/action handler is an INVISIBLE TRIGGER; one with only loops/helpers is a
    SCRIPT HELPER -- and the word 'logic' appears on no row."""
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    rows = list(_rows(grp))
    assert any("invisible trigger" in r for r in rows), rows
    assert any("script helper" in r for r in rows), rows
    assert not any(": logic" in r for r in rows), rows


def test_script_group_links_the_concept_card(win, app, tmp_path):
    from ff9mapkit.workspace.shell import _DETAIL
    from ff9mapkit.workspace import concepts
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    det = "\n".join(grp.data(0, _DETAIL) or [])
    assert 'href="concept:script-entries"' in det, det
    # the card answers the exact words a user reaches for
    for term in ("entries", "tags", "routines", "cases", "switch"):
        c = concepts.resolve(term)
        assert c is not None and c.term == "script-entries", term


def test_entry_detail_annotates_the_conventional_tags(win, app, tmp_path):
    from ff9mapkit.workspace.shell import _DETAIL
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    grp = _script_group(win, app)
    dets = {grp.child(i).text(0): "\n".join(grp.child(i).data(0, _DETAIL) or [])
            for i in range(grp.childCount())}
    npc = next(v for k, v in dets.items() if k.startswith("entry 2"))
    assert "0 (setup)" in npc and "1 (every frame)" in npc and "3 (action/talk)" in npc, npc
    trig = next(v for k, v in dets.items() if "invisible trigger" in k)
    assert "no model" in trig and "touches or examines" in trig, trig


def test_the_routine_transcript_opens_by_default_and_links_the_card(win, app, tmp_path):
    from PySide6.QtWidgets import QToolButton
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    _script_group(win, app)
    win._open_editor("GLADE", "logic_node", "logic_n:2:3")
    app.processEvents()
    host = win.doc_scroll
    btns = [b for b in host.findChildren(QToolButton) if b.text().startswith("This routine")]
    assert btns and btns[0].isChecked(), "the transcript IS the explanation -- it must start expanded"
    links = [w for w in host.findChildren(QLabel) if 'href="concept:script-entries"' in w.text()]
    assert links, "the panel offers the entries/tags/routines card"


def test_the_transcript_renders_quotes_not_entities(win, app, tmp_path):
    """_collapsible escaped each line and the label rendered PLAIN -- the panel showed
    'Says: &quot;Kupo!…' literally (hidden for a whole round because the block started collapsed;
    the open_=True snap caught it)."""
    assert win.open_campaign(make_demo_campaign(tmp_path / "demo"))
    _script_group(win, app)
    win._open_editor("GLADE", "logic_node", "logic_n:2:3")
    app.processEvents()
    texts = [w.text() for w in win.doc_scroll.findChildren(QLabel)]
    assert any('Says: "Kupo!' in t for t in texts), [t for t in texts if "Kupo" in t]
    assert not any("&quot;" in t for t in texts), "no HTML entity ever reaches a plain-text label"
