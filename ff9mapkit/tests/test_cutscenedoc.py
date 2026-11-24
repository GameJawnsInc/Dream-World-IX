"""Fences for the Cutscene DOC TAB (:mod:`workspace.cutscenedoc`) — the redesigned surface.

THIS FILE OWNS THE FIXTURE (`FIELD_TOML` + :func:`make_cutscene_field`) — gui_snap loads it by
path, the test_behaviordoc ownership pattern, so the snap surfaces and these fences can never
render different fields.

Behaviour + data only — no geometry or font claim — so offscreen is sound here (the pixel
truth lives in the `cutscene:*` snap surfaces).
"""
from __future__ import annotations

import copy
import os
import tomllib

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt                        # noqa: E402
from PySide6.QtWidgets import QApplication          # noqa: E402

from ff9mapkit.editor import forms                   # noqa: E402
from ff9mapkit.editor.theme import pick_palette      # noqa: E402
from ff9mapkit.workspace import cutscenescan         # noqa: E402
from ff9mapkit.workspace import shell                # noqa: E402
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc   # noqa: E402

# ------------------------------------------------------------------ THE FIXTURE (one owner)
# The behaviour suite's synthetic floor: x[-300,1000] z[-300,600] with a vertical SLOT
# x[640,680] z[60,600] missing from the upper band — a wall a straight walk can cross.
# Scene #0 is the CAST scene (a routed walk + a parallel turn + an attributed line);
# scene #1 is NARRATION — together they exercise the dispatch, both flavours, and the
# storyboard's beat grouping. Positions sit > ~192u apart (stacked content is itself a
# staging warning and would poison every other assertion).
FIELD_TOML = """\
[field]
id = 4003
name = "GLEN"
area = 11

[camera]
borrow = "c.bgx"

[walkmesh]
bgi = "walkmesh.bgi"

[player]
spawn = [-200, 500]

[[npc]]
name = "Cid"
model = "GEO_SUB_F0_CID"
pos = [0, 400]

# Mira is CAST (the parallel beat needs a second actor: the compiler rejects one actor doing
# two things at once); she stands clear of Cid's route through the lower band.
[[npc]]
name = "Mira"
model = "GEO_SUB_F0_CID"
pos = [-250, -200]

# Tam is NOT cast -- the stage's obstacle row.
[[npc]]
name = "Tam"
model = "GEO_SUB_F0_CID"
pos = [250, 520]

# the altar sits ACROSS the mesh's wall slot from Cid, so the straight walk is blocked and
# the compiler ROUTES it -- the storyboard's straight-to-routed upgrade is real in this fixture
[[marker]]
name = "altar"
pos = [900, 400]

[[cutscene]]
actors = ["Cid", "Mira"]
requires_scenario = 100
set_scenario = 200
steps = [
  { walk = "altar", actor = "Cid" },
  { turn = 128, actor = "Mira", with_prev = true },
  { say = "Made it to the altar.", speaker = "Cid" },
]

[[cutscene]]
requires_scenario = 300
steps = [
  { say = "Dusk falls over the glen." },
  { wait = 30 },
]
"""


def _mesh_bytes() -> bytes:
    from ff9mapkit.scene import bgi
    xs = (-300, 640, 680, 1000)
    verts = [(x, 0, z) for z in (600, 60, -300) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    return bgi.build(verts, tris).to_bytes()


def make_cutscene_field(root):
    """Write the fixture field (+ its walkmesh sidecar) under ``root``; returns the toml path.
    gui_snap imports THIS function by path — one owner for what the surfaces render."""
    root.mkdir(parents=True, exist_ok=True)
    p = root / "GLEN.field.toml"
    p.write_text(FIELD_TOML, encoding="utf-8")
    (root / "walkmesh.bgi").write_bytes(_mesh_bytes())
    return p


def _raw():
    return tomllib.loads(FIELD_TOML)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def doc(app):
    d = CutsceneDoc(pick_palette("dark"))
    yield d
    d.hide()
    d.instruments.setParent(None)


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    w = shell.Workspace(pick_palette("dark"))
    yield w
    w.hide()


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die parked, not under a forced GC pass (THE GC-CHILD LAW's teardown half).

    This module was the LAST per-test-widget GUI module without the drain: its unparked
    doc/win graphs died under GC mid-way through whichever module ran NEXT, and the pair
    `test_cutscenedoc.py test_workspace_floorplan.py` carried an intermittent 0xC0000005 in
    the neighbour's drain (studies/pyside-gc-crash/NOTES.md — the unparked-module flavor).
    The restage debounce is disarmed first: a test may end with the 500ms timer armed
    (`test_the_stage_drop_rewrites_the_selected_target` asserts exactly that), and a PARKED doc
    firing it inside somebody else's teardown starts a staging worker thread — the floorplan
    module's judge-debounce lesson, same disease."""
    yield
    for w in QApplication.topLevelWidgets():
        try:
            t = getattr(w, "_restage_timer", None)
            if t is not None:
                t.stop()
        except RuntimeError:                           # a wrapper whose C++ side already went
            pass
    qt_drain()


def _fed(doc, tmp_path, toml_text=FIELD_TOML):
    p = tmp_path / "GLEN.field.toml"
    p.write_text(toml_text, encoding="utf-8")
    (tmp_path / "walkmesh.bgi").write_bytes(_mesh_bytes())
    raw = tomllib.loads(toml_text)
    doc.show_field("GLEN", raw, p)
    return raw, p


def _tags(canvas):
    """Census the stage by item tag (data slot 0) — the snap harness's own idiom."""
    from collections import Counter
    return Counter(it.data(0) for it in canvas._scene.items() if it.data(0))


# ------------------------------------------------------------------ guide / feed / render
def test_the_doc_opens_on_the_guide_and_show_none_returns_there(doc, tmp_path):
    assert doc._stack.currentWidget() is doc._guide_page
    _fed(doc, tmp_path)
    assert doc._stack.currentWidget() is doc._content
    doc.show_none()
    assert doc._stack.currentWidget() is doc._guide_page


def test_a_field_without_scenes_shows_the_noscene_guide(doc, tmp_path):
    head = FIELD_TOML.split("[[cutscene]]")[0]
    _fed(doc, tmp_path, head)
    assert doc._stack.currentWidget() is doc._guide_page
    assert doc._guide_state == "noscene"


def test_the_rail_renders_the_whole_dispatch(doc, tmp_path):
    raw, _ = _fed(doc, tmp_path)
    rows = cutscenescan.scene_rows(raw)
    assert doc.rail.count() == len(rows) == 2
    assert "scene #0" in doc.rail.item(0).text() and "cast 2" in doc.rail.item(0).text()
    assert "narration" in doc.rail.item(1).text()
    assert "plays at beat 100" in doc.rail.item(0).text()


def test_the_rail_leads_with_what_tells_scenes_apart_and_elides_instead_of_scrolling(doc,
                                                                                      tmp_path):
    """C21: rows were cut mid-glyph over a permanent horizontal scrollbar (a list that scrolls
    sideways never elides), and the step count and cast -- what tells scenes apart -- sat at
    the far end. Pixels: tools/gui_snap.py cutscene:doc at 100 and 150."""
    _fed(doc, tmp_path)
    assert doc.rail.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert doc.rail.textElideMode() == Qt.TextElideMode.ElideRight
    t0, t1 = doc.rail.item(0).text(), doc.rail.item(1).text()
    assert t0 == "scene #0 · 3 steps\ncast 2 · plays at beat 100", t0   # two lines, each elides
    assert t1 == "scene #1 · 2 steps\nnarration · plays at beat 300", t1
    assert doc.rail.item(0).toolTip().startswith(t0), "the tooltip keeps the whole line"


def test_scene_select_switches_the_ladder_and_the_stage(doc, tmp_path):
    _fed(doc, tmp_path)
    assert len(doc.ladder._idx_chips) == 3              # the cast scene's steps
    doc.rail.setCurrentRow(1)
    assert doc._scene == 1
    assert len(doc.ladder._idx_chips) == 2              # the narration scene's steps
    t = _tags(doc.canvas)
    assert t["leg"] == 0                                # narration moves nobody


def test_the_canvas_draws_markers_cast_obstacles_and_legs(doc, tmp_path):
    _fed(doc, tmp_path)
    t = _tags(doc.canvas)
    assert t["marker"] == 1                             # altar — review B5, finally on a canvas
    assert t["post"] == 2                               # Cid + Mira, the cast
    assert t["npc"] == 1                                # Tam, an obstacle
    assert t["player"] == 1                             # the spawn (player not in the cast)
    assert t["leg"] >= 1 and t["target"] == 1           # the walk to the altar


def test_step_select_accents_the_leg_and_tolerates_reselect(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._on_step_select(0)
    assert doc._selected_step == 0 and doc.canvas._selected_step == 0
    doc._on_step_select(0)                              # click again = deselect
    assert doc._selected_step is None


def test_the_scene_bar_spills_its_buttons_instead_of_flooring_the_window(doc, tmp_path):
    """The scene bar was one non-wrapping row (title + gate + five buttons): the widest page in
    the stack, so it set the WHOLE window floor -- natively 1228 at 150% with no field, 1290 with
    one open, over a 1280 window. Now the bar's floor is the wider HALF, never the sum: the buttons
    drop under the title at the doc's floor (all in full, never elided) and rejoin it on one line
    when the column is wide. Relative widths only -- offscreen fonts are fiction."""
    _fed(doc, tmp_path)
    bar, lead, tail = doc.scene_bar, doc.scene_bar._lead, doc.scene_bar._tail
    m = bar.layout().contentsMargins()
    pad = m.left() + m.right()
    one_line = pad + lead.minimumSizeHint().width() + bar.ROW_GAP + tail.sizeHint().width()
    floor = pad + max(lead.minimumSizeHint().width(), tail.minimumSizeHint().width())
    assert bar.minimumSizeHint().width() == floor < one_line, "the floor is the wider half"
    buttons = (doc.add_step_btn, doc.settings_btn, doc.dup_scene_btn, doc.del_scene_btn,
               doc.board_btn)
    assert all(b.parentWidget() is tail for b in buttons), "every scene button rides the tail"

    doc.show()
    doc.resize(doc.minimumSizeHint().width(), 700)
    QApplication.processEvents()
    assert bar.width() < one_line and bar.spilled(), "at the doc's floor the buttons spill"
    assert tail.geometry().top() > lead.geometry().bottom(), "spilled = a second line"
    assert all(b.text() == b.accessibleName() for b in buttons), "spilled, never elided"

    doc.resize(doc.minimumSizeHint().width() + one_line + 400, 700)
    QApplication.processEvents()
    assert bar.width() >= one_line and not bar.spilled(), "wide: one line again"
    assert tail.geometry().top() == lead.geometry().top()


# ------------------------------------------------------------------ the storyboard strip
def test_the_storyboard_scrubs_beats_and_wraps_the_say_line(doc, tmp_path):
    raw, _ = _fed(doc, tmp_path)
    assert not doc.board_bar.isVisible() and doc.board_btn.isChecked() is False
    doc.board_btn.setChecked(True)
    assert doc._board is not None and doc._board["error"] == ""
    beats = doc._board["beats"]
    assert len(beats) == 2                              # [walk + turn] then [say]
    assert doc.board_slider.maximum() == 1
    doc._show_beat(1)
    assert "beat 2 of 2" in doc.board_pos.text()
    # E1: the strip shows the line the BUILD emits (name line, quotes, the build's wrap) --
    # not an invented "Cid:" prefix
    assert doc.board_say.text() == _as_built("Cid", "Made it to the altar.")
    assert doc.ladder._beat_marks == {2}                # ▶ sweeps the ladder
    t = _tags(doc.canvas)
    assert t["beatpos"] >= 1                            # storyboard mode draws positions
    doc.board_btn.setChecked(False)
    assert doc.ladder._beat_marks == set()


def test_the_storyboard_never_names_an_actor_the_game_leaves_unattributed(doc, tmp_path):
    """C14 (already fixed by E1, proven here): the strip wrote 'Mira:' over a line tagged only
    with actor = "Mira". The build attributes a line through `speaker` alone, so the game shows
    the bare line -- and so must the strip."""
    from ff9mapkit import build as _build
    toml = FIELD_TOML.replace('{ say = "Made it to the altar.", speaker = "Cid" }',
                              '{ say = "Quiet now.", actor = "Mira" }')
    _fed(doc, tmp_path, toml)
    doc.board_btn.setChecked(True)
    doc._show_beat(1)
    assert doc.board_say.text() == _as_built(None, "Quiet now.", tomllib.loads(toml))
    assert "Mira" not in doc.board_say.text()
    assert not [p for p in _build.validate(_build.FieldProject(tomllib.loads(toml), tmp_path))
                if "[cutscene]" in p], "the fixture builds"


def test_the_storyboard_clears_when_the_scene_loses_its_last_step(doc, tmp_path):
    """C12: deleting every step left the old beat on the strip, the ladder and the stage."""
    _fed(doc, tmp_path)
    doc.board_btn.setChecked(True)
    doc._show_beat(1)
    for _ in range(3):
        _rowtool(doc, "Remove this step (Ctrl+Z undoes)", 0).click()
    assert doc._steps() == []
    assert "Made it" not in doc.board_say.text() and "no steps" in doc.board_say.text().lower()
    assert doc.board_pos.text() == ""
    assert doc.ladder._beat_marks == set()
    assert doc.canvas._board is None and _tags(doc.canvas)["beatpos"] == 0


def _preview(doc):
    from PySide6.QtWidgets import QPlainTextEdit
    return doc.editor.say_preview.findChild(QPlainTextEdit).toPlainText()


def _as_built(speaker, text, raw=None):
    """What the BUILD puts in the window for a say step: build._add's own two calls."""
    from ff9mapkit.content import text as _text
    from ff9mapkit import dialogue as _dlg
    return _dlg.wrap_preview(_text.with_speaker(speaker, text),
                             cutscenescan.wrap_width(raw or _raw()))


def test_the_editor_preview_shows_what_the_build_emits(doc, tmp_path):
    """E1: the preview wrapped the RAW typed text -- no speaker name line, no quotes, {colour}
    markup measured as visible text, a typed \\n shown literally -- so it broke lines where the
    game does not, and its 'fits' note judged a different line."""
    _fed(doc, tmp_path)
    doc._edit_step(2)                                  # say "Made it to the altar.", speaker Cid
    assert _preview(doc) == _as_built("Cid", "Made it to the altar.")
    long = "We crossed the whole glen before the dusk light faded out over the {item}hills{/}"
    doc.editor.value_text.setPlainText(long)
    assert _preview(doc) == _as_built("Cid", long)
    doc.editor.x_speaker.setText("Mira")               # the speaker alone changed: re-run
    assert _preview(doc) == _as_built("Mira", long), "the preview ignored a speaker change"
    doc.editor.x_speaker.clear()
    doc.editor.value_text.setPlainText("First line here\\nSecond line")   # a TYPED backslash-n
    assert _preview(doc) == "First line here\nSecond line"
    doc._apply_step()
    assert doc._steps()[2]["say"] == "First line here\nSecond line", "read_step agrees"


def test_the_storyboard_error_lane_renders_instead_of_raising(doc, tmp_path):
    bad = FIELD_TOML.replace('walk = "altar"', 'walk = "no_such_marker"')
    _fed(doc, tmp_path, bad)
    doc.board_btn.setChecked(True)
    assert "no_such_marker" in doc.board_say.text()
    assert not doc.board_slider.isEnabled()


# ------------------------------------------------------------------ the staging lane
def test_stage_now_sync_paints_the_summary_and_the_verdicts(doc, tmp_path):
    bad = FIELD_TOML.replace('walk = "altar"', "walk = [2000, 2000]")
    _fed(doc, tmp_path, bad)
    doc.stage_now(sync=True)
    assert "staging problem" in doc.stage_note.text()
    assert doc.stage_list.count() >= 1
    assert doc.stage_list.item(0).text().startswith("⚠")
    assert _tags(doc.canvas)["verdict"] >= 1            # painted at the failing leg
    assert doc._wmesh is not None and doc._stage_armed


_TWO_CAST = FIELD_TOML.replace(
    '[[cutscene]]\nrequires_scenario = 300\nsteps = [\n  { say = "Dusk falls over the glen." },\n'
    '  { wait = 30 },\n]',
    '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 300\n'
    'steps = [ { walk = [2000, 2000], actor = "Cid" } ]')


def test_a_stall_paints_only_on_its_own_scene(doc, tmp_path):
    """C1: the verdict rows cover EVERY cast scene; the stage shows ONE. A stall in scene #1 must
    not paint 'step 0 stalls here' on scene #0's stage (a different, fine step), and switching
    scenes re-filters."""
    assert "walk = [2000, 2000]" in _TWO_CAST, "the fixture edit must land"
    _fed(doc, tmp_path, _TWO_CAST)
    doc.stage_now(sync=True)
    assert "1 staging problem" in doc.stage_note.text()
    assert doc._scene == 0
    assert _tags(doc.canvas)["verdict"] == 0, "scene #1's stall painted on scene #0's stage"
    doc.rail.setCurrentRow(1)
    assert _tags(doc.canvas)["verdict"] >= 1, "its own scene paints it"
    doc.rail.setCurrentRow(0)
    assert _tags(doc.canvas)["verdict"] == 0, "switching back re-filters"


def test_a_clean_staging_says_so_and_paints_nothing(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.stage_now(sync=True)
    assert "✓" in doc.stage_note.text()
    assert _tags(doc.canvas)["verdict"] == 0
    # the warm mesh upgrades the storyboard's straight legs to the compiler's routes
    doc.board_btn.setChecked(True)
    (leg,) = doc._board["beats"][0]["legs"]
    assert leg["kind"] == "path" and len(leg["points"]) > 2


def test_the_flag_names_seam_is_spent_by_the_mesh_load(app, tmp_path, monkeypatch):
    """The campaign's [[flag]] table must reach the walkmesh load, or a campaign member dies
    in flag resolution before any mesh is read (the stolen-ember lesson)."""
    seen = {}

    def fake_load(path, flag_names=None):
        seen["flags"] = flag_names
        return None, "stubbed"

    monkeypatch.setattr(cutscenescan, "load_walkmesh", fake_load)
    d = CutsceneDoc(pick_palette("dark"), flag_names_fn=lambda: {"chapel_open": 8712})
    try:
        _fed(d, tmp_path)
        d.stage_now(sync=True)
        assert seen["flags"] == {"chapel_open": 8712}
        assert "stubbed" in d.stage_note.text()         # the load failure is SAID, not eaten
    finally:
        d.hide()
        d.instruments.setParent(None)


def test_a_stale_staging_result_never_paints(doc, tmp_path):
    _fed(doc, tmp_path)
    res = cutscenescan.StagingResult(error="STALE — must never paint")
    doc._finish_stage((doc._stage_gen - 1, res, [], None))
    assert "STALE" not in doc.stage_note.text()


def test_a_narration_only_field_says_there_is_nothing_to_stage(doc, tmp_path):
    only_narr = FIELD_TOML.split("[[cutscene]]")[0] + (
        '[[cutscene]]\nsteps = [ { say = "alone" } ]\n')
    _fed(doc, tmp_path, only_narr)
    doc.stage_now(sync=True)
    assert "No cast scene to stage" in doc.stage_note.text()


# ------------------------------------------------------------------ live problems
def test_live_problems_show_a_dispatch_collision_and_a_bad_target(doc, tmp_path):
    bad = FIELD_TOML.replace("requires_scenario = 300", "requires_scenario = 100")
    _fed(doc, tmp_path, bad)
    assert "the same gate" in doc.problems_lbl.text()
    bad2 = FIELD_TOML.replace('walk = "altar"', 'walk = "ghost"')
    _fed(doc, tmp_path, bad2)
    assert "step 0: movement target 'ghost'" in doc.problems_lbl.text()   # the build's sentence
    _fed(doc, tmp_path)
    assert doc.problems_lbl.text() == "No structural problems."


# ------------------------------------------------------------------ shell integration
def test_the_tab_show_feeds_the_doc_and_docks_the_instruments(win, tmp_path):
    p = make_cutscene_field(tmp_path)
    assert win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    assert win.cutscene_doc._member == "GLEN"
    assert win.cutscene_doc.rail.count() == 2
    assert win.cutscene_doc.instruments.parent() is not None    # docked into the inspector
    win.tabs.setCurrentWidget(win.behavior_doc)
    assert win.cutscene_doc.instruments.parent() is None        # ...and undocked on leave
    assert win.behavior_doc.instruments.parent() is not None


def test_the_feed_is_by_reference_and_merged_is_live(win, tmp_path):
    p = make_cutscene_field(tmp_path)
    win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    fd = win._doc("GLEN")
    assert win.cutscene_doc._raw is fd.data                     # the feed contract
    assert win.cutscene_doc._merged()["field"]["name"] == "GLEN"


def test_the_cutscene_tab_focus_token_lands_on_the_tab(win, tmp_path):
    """`cutscene_tab`, never `cutscene`: the bare token is in _SINGLE, so _goto_focus would
    yank an undo back to the Editor tree instead of this tab."""
    p = make_cutscene_field(tmp_path)
    win.open_field(p)
    win.tabs.setCurrentWidget(win.doc_scroll)
    win._goto_focus("GLEN", "cutscene_tab")
    assert win.tabs.currentWidget() is win.cutscene_doc


def test_the_open_toml_door_reaches_the_member_file(win, tmp_path, monkeypatch):
    p = make_cutscene_field(tmp_path)
    win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    opened = {}
    # Swap the NAME shell resolves openUrl through (_open_member_toml), never the Qt class itself
    # (the shiboken override-cache poison, studies/pyside-gc-crash).
    from types import SimpleNamespace
    monkeypatch.setattr(shell, "QDesktopServices", SimpleNamespace(
        openUrl=lambda url: opened.setdefault("path", url.toLocalFile()) or True))
    win.cutscene_doc.toml_btn.click()
    assert opened["path"].endswith("GLEN.field.toml")


# ------------------------------------------------------------------ THE WRITE SURFACE (the flip)
def _apply_say(doc, text):
    doc.editor.value_text.setPlainText(text)
    doc._apply_step()


def test_three_consecutive_say_steps_all_survive(doc, tmp_path):
    """THE SAME-KIND OVERWRITE, retired for good: the add lane inserts then ADVANCES, so a
    conversation types straight through — three lines in, three out."""
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)                          # the narration scene: 2 steps
    doc._selected_step = None
    doc._add_step()                                    # add mode, at the end
    for line in ("Cid: Well now.", "Cid: That's torn it.", "Cid: Rubbish!"):
        _apply_say(doc, line)
    says = [s.get("say") for s in doc._steps() if "say" in s]
    assert says[-3:] == ["Cid: Well now.", "Cid: That's torn it.", "Cid: Rubbish!"]


def test_add_step_inserts_after_the_selection(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._on_step_select(0)                             # select the first narration line
    doc._add_step()
    assert doc.editor.insert_at == 1
    _apply_say(doc, "slotted in")
    assert doc._steps()[1]["say"] == "slotted in"
    assert "wait" in doc._steps()[2], "the old tail moved down, nothing overwritten"


def test_update_can_change_a_steps_kind_in_place_and_preserves_unknown_keys(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._steps()[0]["mystery"] = 7                     # a key the editor does not know
    doc._edit_step(0)                                  # the say line
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("wait"))
    doc.editor.value_line.setText("45")
    doc._apply_step()
    s = doc._steps()[0]
    assert s.get("wait") == 45 and "say" not in s, "the kind changed IN PLACE"
    assert s.get("mystery") == 7, "unknown keys survive the editor (the extras rule)"


def test_clearing_a_managed_key_in_the_editor_pops_it(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._edit_step(2)                                  # the attributed say (speaker = Cid)
    assert doc.editor.x_speaker.text() == "Cid"
    doc.editor.x_speaker.clear()
    doc._apply_step()
    assert "speaker" not in doc._steps()[2], "a cleared managed key must POP, not linger"


def test_the_pacing_extras_round_trip_and_validate_clean(doc, tmp_path):
    """The message-box vocabulary the compiler already reads off a text step — now writable.
    The written step must round-trip AND pass the build's own window-attribute sweep."""
    import copy as _copy
    from ff9mapkit import build as _build
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._edit_step(0)
    doc.editor.x_speaker.setText("Narrator")
    doc.editor.x_duration.setText("90")
    doc.editor.x_speed.setText("4")
    doc.editor.x_instant.setChecked(True)
    doc._apply_step()
    s = doc._steps()[0]
    assert s["speaker"] == "Narrator" and s["duration"] == 90
    assert s["speed"] == 4 and s["instant"] is True
    problems = _build.validate(_build.FieldProject(_copy.deepcopy(doc._raw), tmp_path))
    assert not [p for p in problems if "[cutscene]" in p], problems
    # and a bad number is refused with the field NAMED, before any op fires
    doc._edit_step(0)
    doc.editor.x_duration.setText("soon")
    n = len(doc._steps())
    doc._apply_step()
    assert "duration" in doc.editor.note.text()
    assert len(doc._steps()) == n and doc._steps()[0]["duration"] == 90, "no op fired"


def test_a_raw_window_style_byte_round_trips_as_an_int(doc, tmp_path):
    """C5: style = 128 is the documented raw-flags-byte form. The build reads a STRING as a style
    NAME, so an Apply that wrote '128' back broke a valid step (even an Apply that only fixed a
    typo in the line). A name stays a name."""
    from ff9mapkit.content import text as _text
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._steps()[0]["style"] = 128
    doc._edit_step(0)
    assert doc.editor.x_style.text() == "128"
    doc.editor.value_text.setPlainText("Dusk falls over the glen!")   # a typo fix, nothing else
    doc._apply_step()
    assert doc._steps()[0]["style"] == 128, doc._steps()[0]
    _text.resolve_style(doc._steps()[0]["style"])          # the build accepts what was written
    assert doc.editor.step_i == 0, "the editor stays on its row after Apply"
    doc.editor.x_style.setText("notail")
    doc._apply_step()
    assert doc._steps()[0]["style"] == "notail", "a style NAME stays a name"


@pytest.mark.parametrize("stored, shown, back", [
    ("+", "+", "+"),           # the form the build's own wait_signal lint recommends
    (True, "+", True),         # the build reads true exactly like "+": shown "+", kept true
    (3, "3", 3),
    (-1, "-1", -1),
])
def test_a_say_signal_opens_and_applies_in_every_form_the_build_accepts(doc, tmp_path,
                                                                        stored, shown, back):
    """C6: the editor read signal with int(), so a line carrying signal = "+" (or true) could not
    be applied at all -- not even to fix a typo in the line."""
    import copy as _copy
    from ff9mapkit import build as _build
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._steps()[0]["signal"] = stored
    doc._edit_step(0)
    assert doc.editor.x_signal.text() == shown
    doc.editor.value_text.setPlainText("Dusk falls over the glen!")   # a typo fix, nothing else
    doc._apply_step()
    assert doc.editor.note.text() == "", doc.editor.note.text()
    s = doc._steps()[0]
    assert s["say"] == "Dusk falls over the glen!" and s["signal"] == back
    assert type(s["signal"]) is type(back)
    problems = _build.validate(_build.FieldProject(_copy.deepcopy(doc._raw), tmp_path))
    assert not [p for p in problems if "signal" in p], problems


def test_a_signal_the_build_refuses_is_refused_with_its_forms_named(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._edit_step(0)
    assert "+" in doc.editor._extra_rows["signal"][0].text(), "the label must say + is allowed"
    assert '"+"' in doc.editor.x_signal.toolTip()
    doc.editor.x_signal.setText("soon")
    doc._apply_step()
    assert "signal" in doc.editor.note.text() and "+" in doc.editor.note.text()
    assert "signal" not in doc._steps()[0], "no op fired"
    doc.editor.x_signal.setText("")
    doc._apply_step()
    assert "signal" not in doc._steps()[0], "blank clears"


def test_a_window_step_round_trips_and_the_valueless_kind_hides_its_value(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._add_step()
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("open"))
    assert not doc.editor.value_text.isHidden(), "open is a TEXT step: the dialogue box"
    assert not doc.editor.say_preview.isHidden(), "…and the wrap preview"
    doc.editor.value_text.setPlainText("The window stays up")
    doc.editor.x_window.setText("2")
    doc._apply_step()
    added = doc._steps()[doc.editor.insert_at - 1]
    assert added == {"open": "The window stays up", "window": 2}
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("raise"))
    assert doc.editor.value_line.isHidden() and doc.editor.value_label.isHidden(), \
        "a valueless step hides the value row"
    doc._apply_step()
    assert doc._steps()[doc.editor.insert_at - 1] == {"raise": True}


def test_set_flag_takes_a_flag_name_and_problems_flags_a_reserved_index(doc, tmp_path):
    """C19: 'Set flag' took only two integers -- it refused a [[flag]] NAME the build resolves --
    and accepted 8600, a save-corrupting reserved bit, with every GUI readout green.
    After review: a name the field does not define (a typo) is a PROBLEM -- the build refuses
    the whole field on it, so the tab must not say 'No structural problems'."""
    _fed(doc, tmp_path, FIELD_TOML + '\n[[flag]]\nname = "glen_done"\nindex = 8712\n')
    doc.rail.setCurrentRow(1)
    doc._add_step()
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("set_flag"))
    doc.editor.value_line.setText("glen_done, 1")
    doc._apply_step()
    assert doc.editor.note.text() == "", doc.editor.note.text()
    added = doc._steps()[doc.editor.insert_at - 1]
    assert added == {"set_flag": ["glen_done", 1]}
    assert forms.step_value_text(added) == "glen_done, 1", "the name reopens as typed"
    assert "No structural problems." in doc.problems_lbl.text()
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("set_flag"))
    doc.editor.value_line.setText("glen_dnoe, 1")      # the typo
    doc._apply_step()
    assert "unknown flag name 'glen_dnoe'" in doc.problems_lbl.text(), \
        f"PROBLEMS stayed green over a name the build refuses: {doc.problems_lbl.text()!r}"
    doc._del_step(doc.editor.insert_at - 1 if doc.editor.insert_at else len(doc._steps()) - 1)
    doc._add_step()
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("set_flag"))
    doc.editor.value_line.setText("8600, 1")
    doc._apply_step()
    assert "8600" in doc.problems_lbl.text() and "reserved" in doc.problems_lbl.text(), \
        f"PROBLEMS stayed green over a reserved flag: {doc.problems_lbl.text()!r}"


def test_with_prev_is_gated_by_the_compilers_rule_and_row_position(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._edit_step(1)                                  # the turn step, row 1
    assert doc.editor.with_prev.isEnabled(), "turn on row 1 may run in parallel"
    doc._edit_step(0)                                  # row 0: nothing to run with
    assert not doc.editor.with_prev.isEnabled()
    doc._edit_step(2)                                  # a say can never parallelize
    assert not doc.editor.with_prev.isEnabled()


def test_an_add_lane_started_at_row_0_re_enables_with_prev_after_apply(doc, tmp_path):
    """C13: the checkbox was judged only on a kind change, so after the first Apply advanced the
    lane to row 1 it stayed disabled for a turn until the author toggled the type."""
    _fed(doc, tmp_path)
    for _ in range(3):
        _rowtool(doc, "Remove this step (Ctrl+Z undoes)", 0).click()
    doc.add_step_btn.click()
    assert doc.editor.insert_at == 0
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("turn"))
    assert not doc.editor.with_prev.isEnabled(), "row 0 has nothing to run with"
    doc.editor.value_line.setText("128")
    doc.editor.actor.setEditText("Cid")
    doc.editor.apply_btn.click()
    assert doc.editor.insert_at == 1 and forms.step_key(doc._steps()[0]) == "turn"
    assert doc.editor.with_prev.isEnabled(), "row 1 may run with row 0"


def test_ladder_rowtools_reorder_duplicate_and_delete(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    says = lambda: [forms.step_key(s) for s in doc._steps()]      # noqa: E731
    assert says() == ["say", "wait"]
    doc._move_step(1, -1)
    assert says() == ["wait", "say"], "Up must move the step EARLIER"
    doc._move_step(0, -1)                              # boundary: a no-op, never a raise
    assert says() == ["wait", "say"]
    doc._dup_step(0)
    assert says() == ["wait", "wait", "say"], "the copy sits directly AFTER its source"
    doc._steps()[1]["wait"] = 99
    assert doc._steps()[0]["wait"] == 30, "the duplicate is a DEEP copy"
    doc._del_step(1)
    assert says() == ["wait", "say"]


def test_scene_ops_add_duplicate_delete(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._add_scene()
    assert doc.rail.count() == 3 and doc._scene == 2, "add lands ON the new scene"
    doc._dup_scene()
    assert doc.rail.count() == 4 and doc._scene == 3
    assert "the same gate" in doc.problems_lbl.text() or "UNGATED" in doc.problems_lbl.text(), \
        "duplicating a scene collides its gate — PROBLEMS must say so LIVE"
    doc._del_scene()
    doc._del_scene()
    assert doc.rail.count() == 2 and len(doc._raw["cutscene"]) == 2


def test_the_noscene_guide_action_authors_the_first_scene(doc, tmp_path):
    head = FIELD_TOML.split("[[cutscene]]")[0]
    _fed(doc, tmp_path, head)
    assert doc._guide_state == "noscene"
    doc._add_scene()
    assert doc._stack.currentWidget() is doc._content
    assert isinstance(doc._raw["cutscene"], list) and len(doc._raw["cutscene"]) == 1


def test_scene_settings_apply_writes_the_gate_and_keeps_the_steps(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.settings_btn.setChecked(True)
    g = doc._settings_getters
    assert g is not None
    g["requires_scenario"].__self__.setText("777")     # the getter is the widget's bound .text
    steps_before = list(doc._raw["cutscene"][0]["steps"])
    doc._apply_settings()
    b = doc._raw["cutscene"][0]
    assert b["requires_scenario"] == 777
    assert b["steps"] == steps_before, "settings must never touch the steps"
    assert "plays at beat 777" in doc.rail.item(0).text(), "the rail follows the applied gate"


def _gate_box(doc):
    return doc._settings_getters["requires_scenario"].__self__


def test_unapplied_scene_settings_survive_every_re_render(doc, tmp_path):
    """C10: with Scene settings open, every re-render rebuilt the form from the document and
    threw away what was typed but not applied -- a tab show, a tree select, a stage drag, an
    undo of something else, a retheme."""
    raw, p = _fed(doc, tmp_path)
    doc.settings_btn.setChecked(True)
    _gate_box(doc).setText("150")
    doc.show_field("GLEN", raw, p)                     # the tab show / tree select re-feed
    assert _gate_box(doc).text() == "150", "a same-field re-feed wiped the typed gate"
    doc.show_field("GLEN", copy.deepcopy(raw), p)      # undo/redo of another edit: an equal buffer
    assert _gate_box(doc).text() == "150"
    doc._selected_step = 0                             # a stage drag of the selected walk
    doc._on_stage_move(("target", 0, 0), 100, 100)
    assert doc._raw["cutscene"][0]["steps"][0]["walk"] == [100, 100]
    assert _gate_box(doc).text() == "150", "a stage drag wiped the typed gate"
    doc.retheme(pick_palette("light"))
    assert _gate_box(doc).text() == "150"
    assert doc._raw["cutscene"][0]["requires_scenario"] == 100, "nothing was applied"
    # ...but what the form was built from really changing DOES rebuild it
    doc._raw["cutscene"][0]["requires_scenario"] = 120    # the Editor tree, in place
    doc.show_field("GLEN", doc._raw, p)
    assert _gate_box(doc).text() == "120"
    doc.rail.setCurrentRow(1)                          # another scene
    assert _gate_box(doc).text() == "300"
    doc.rail.setCurrentRow(0)
    doc._dup_scene()                                   # scene #1 is now a look-alike of #0
    _gate_box(doc).setText("555")
    doc.rail.setCurrentRow(0)                          # typing on #1 must not follow to #0
    assert _gate_box(doc).text() == "120"
    other = tmp_path / "other"
    other.mkdir()
    q = make_cutscene_field(other)                     # the same name, another file
    doc.show_field("GLEN", tomllib.loads(q.read_text(encoding="utf-8")), q)
    doc.settings_btn.setChecked(True)
    assert _gate_box(doc).text() == "100"


def test_the_stage_drop_rewrites_the_selected_target(doc, tmp_path):
    """One drop = one op = one label — through the INHERITED drag machinery, driven at the
    world-frame seam the behavior suite uses."""
    _fed(doc, tmp_path)
    doc._on_step_select(0)                             # the walk step -> its target grows a handle
    assert doc.canvas._edit and len(doc.canvas._move_items) == 1
    labels = []
    doc.on_edit = lambda m, lbl: labels.append(lbl)
    doc._member = doc._member                          # (unchanged; on_edit now captures)
    assert doc.canvas._begin_drag(("handle", 0))
    doc.canvas._drag_world(500, 250)
    doc.canvas._end_drag()
    assert doc._raw["cutscene"][0]["steps"][0]["walk"] == [500, 250]
    assert len(labels) == 1 and 'was "altar"' in labels[0], \
        "dragging a NAMED target must SAY the meaning changed"


def test_pick_on_the_stage_fills_the_value(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._edit_step(0)
    doc.editor.pick_btn.click()
    assert doc.canvas.on_sim_click is not None, "the one-shot click lane is armed"
    doc.canvas.on_sim_click(123.4, -56.6)
    assert doc.editor.value_line.text() == "123, -57"
    assert doc.canvas.on_sim_click is None, "one shot only"


def _wait_stage(doc, timeout=20):
    """Let the async worker a REAL gesture started (button / debounce) land."""
    import time
    deadline = time.time() + timeout
    while doc._stage_busy and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.02)
    QApplication.processEvents()
    assert not doc._stage_busy, "the staging worker never landed"


def _small_mesh_bytes() -> bytes:
    """A floor that ends at x=300: the altar (x=900) is OFF it, so Cid's walk stalls."""
    from ff9mapkit.scene import bgi
    verts = [(-300, 0, 600), (300, 0, 600), (300, 0, -300), (-300, 0, -300)]
    return bgi.build(verts, [(0, 1, 2), (0, 2, 3)]).to_bytes()


def test_pick_on_the_stage_shows_it_is_armed_and_never_outlives_its_step(doc, tmp_path):
    """E2: the pick stayed armed after Apply, after Edit on another row and after a kind change,
    with no sign -- and silently stole the next stage press (a handle drag, a pan) into the
    editor's value."""
    from PySide6.QtCore import Qt as _Qt

    def armed():
        return doc.canvas.on_sim_click is not None

    def crosshair():
        return doc.canvas.viewport().cursor().shape() == _Qt.CursorShape.CrossCursor

    _fed(doc, tmp_path)
    doc._edit_step(0)                                  # the walk
    doc.editor.pick_btn.click()
    assert armed() and doc.editor.pick_btn.isChecked() and crosshair(), "armed must SHOW"
    doc.editor.pick_btn.click()                        # a second press cancels
    assert not armed() and not doc.editor.pick_btn.isChecked() and not crosshair()
    doc.editor.pick_btn.click()
    doc._apply_step()
    assert not armed() and not doc.editor.pick_btn.isChecked() and not crosshair(), \
        "Apply left the pick armed"
    doc.editor.pick_btn.click()
    doc._edit_step(2)                                  # another row (a say)
    assert not armed() and not doc.editor.pick_btn.isChecked(), "Edit on another row left it armed"
    doc._edit_step(0)
    doc.editor.pick_btn.click()
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("teleport"))
    assert not armed(), "a kind change left it armed"
    doc.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("walk"))   # clean again (C11:
    doc.editor.pick_btn.click()                        # a changed step refuses Add instead)
    doc._add_step()
    assert not armed(), "Add step left it armed"


def test_a_warm_mesh_rejudges_without_touching_disk(doc, tmp_path, monkeypatch):
    _fed(doc, tmp_path)
    doc.stage_now(sync=True)
    assert doc._stage_armed and doc._wmesh is not None
    monkeypatch.setattr(cutscenescan, "load_walkmesh",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("disk touched")))
    doc._steps()[0]["walk"] = [2000, 2000]             # an edit that now stalls
    doc._last_stage = None
    doc._restage()                                     # the AUTOMATIC lane rides the WARM mesh
    _wait_stage(doc)
    assert doc._last_stage.error == "", doc._last_stage.error
    assert doc._last_stage.warnings, "the warm re-judge must catch the new stall"
    # and a committed edit ARMS the debounced re-judge
    doc._after_edit("test edit")
    assert doc._restage_timer.isActive()


def test_the_check_button_reloads_the_walkmesh_from_disk(doc, tmp_path):
    """C4: the button's tooltip promises the SAVED walkmesh. After a regenerate / re-export
    replaced it, a click judged the old warm copy and said every walk reaches its target."""
    _, p = _fed(doc, tmp_path)
    doc.stage_now(sync=True)
    assert "✓" in doc.stage_note.text() and doc._wmesh is not None
    (tmp_path / "walkmesh.bgi").write_bytes(_small_mesh_bytes())    # the floor changed on disk
    doc._last_stage = None
    doc.stage_btn.click()                              # the real gesture (async worker)
    _wait_stage(doc)
    assert doc._last_stage is not None, "the click produced no result"
    assert doc._last_stage.warnings, \
        f"the click judged the stale warm mesh: {doc.stage_note.text()!r}"


def test_a_same_named_field_at_another_path_drops_the_warm_staging(doc, tmp_path):
    """C4/E3: a copied field or a re-imported fork keeps the member NAME. Its walks must not be
    judged (or its storyboard routed) on the previous file's floor, nor wear its verdict."""
    (tmp_path / "a").mkdir()
    _fed(doc, tmp_path / "a")
    doc.stage_now(sync=True)
    assert doc._stage_armed and "✓" in doc.stage_note.text()
    p_b = make_cutscene_field(tmp_path / "b")
    doc.show_field("GLEN", tomllib.loads(FIELD_TOML), p_b)
    assert doc._wmesh is None and not doc._stage_armed, "the old file's mesh survived"
    assert doc.stage_note.text() == "", "the old file's verdict survived"


# ------------------------------------------------------------------ the accordion (declutter round)
def test_the_accordion_unfolds_the_editor_under_its_row(doc, tmp_path):
    """Playtest feedback: separate bands for list/settings/editor cluttered the column. The
    editor now unfolds INSIDE the ladder, directly under the row it edits."""
    _fed(doc, tmp_path)
    doc._edit_step(1)
    assert doc.editor.parent() is doc.ladder
    assert doc.ladder._lay.indexOf(doc.editor) == 2          # row 1 + 1
    doc._edit_step(0)
    assert doc.ladder._lay.indexOf(doc.editor) == 1


def test_the_add_panel_follows_the_typing_point(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._on_step_select(0)
    doc._add_step()
    assert doc.ladder._lay.indexOf(doc.editor) == 1          # AT the landing row
    _apply_say(doc, "first")
    assert doc.ladder._lay.indexOf(doc.editor) == 2          # ...and it advances with insert_at


def test_set_rows_lifts_the_accordion_panel_instead_of_deleting_it(doc, tmp_path):
    """(M) THE LIFT LAW: the ladder refills on every render; if a refill deleteLater'd the ONE
    StepEditor instance, the next Apply would drive a dead widget. The fence must DELIVER
    DeferredDelete (the harness's own lesson): without the spin, a deleteLater'd widget still
    answers, and the first cut of this test stayed green under the exact mutation it fences."""
    from PySide6.QtCore import QEvent
    _fed(doc, tmp_path)
    doc._edit_step(2)                                        # the say row
    doc._render()                                            # a full refill cycle over the open panel
    QApplication.instance().sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert doc.editor.parent() is doc.ladder, "the refill must LIFT the editor, never delete it"
    doc.editor.value_text.setPlainText("still editable after a refill")
    doc._apply_step()
    assert doc._steps()[2]["say"] == "still editable after a refill"


def test_nothing_shows_the_accordion_panels_while_parentless(doc, tmp_path):
    """(M) THE PHANTOM-WINDOW FENCE, entry side: showing a PARENTLESS widget makes it a
    top-level OS window for an instant (playtest-caught: the editor flickered as its own
    window on the first ✎ of a scene). Only set_inset may show — AFTER seating.

    Observed through an EVENT FILTER, never by patching a Qt class: this fence's second cut
    monkeypatched QFrame.show/setVisible while live widgets dispatched through them, and
    shiboken's per-type override cache kept a dangling pointer to the undone patch — the
    NEXT module's teardown hide() then segfaulted (0xC0000005) or misdispatched a stale
    lambda as a "Python override of QFrame::2:setVisible" (deterministic, bisected:
    studies/pyside-gc-crash/NOTES.md, the class-patch flavor). QEvent.Show is delivered
    synchronously inside BOTH show() and setVisible(True) — including C++-side shows the
    first (vacuous) QWidget.setVisible-only cut could never see — and only on the
    hidden→visible transition, which is exactly the instant the phantom window exists.
    A parentless widget can only BE visible by crossing that transition parentless
    (setParent(None) hides), so the filter misses nothing the patch spy caught."""
    from PySide6.QtCore import QEvent, QObject

    _fed(doc, tmp_path)
    assert doc.editor.parent() is None                       # the exact first-edit state
    flashes = []

    class ParentlessShowSpy(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Type.Show and obj.parent() is None:
                flashes.append(f"{type(obj).__name__}.Show")
            return False                                     # observe, never swallow

    spy = ParentlessShowSpy(doc)                             # doc-owned: no GC-orphaned QObject
    doc.editor.installEventFilter(spy)
    doc.settings_card.installEventFilter(spy)
    doc._edit_step(2)                                        # the flicker's exact gesture
    doc.settings_btn.setChecked(True)                        # ...and the latent settings half
    doc.editor.removeEventFilter(spy)
    doc.settings_card.removeEventFilter(spy)
    assert not flashes, f"shown while parentless (a top-level flash): {flashes}"
    assert doc.settings_card.parent() is doc.ladder          # still seated + shown the right way


def test_reclicking_edit_folds_the_open_row(doc, tmp_path):
    """Playtest ask: the row's Edit is a TOGGLE — reclicking the open row folds the panel;
    clicking another row switches to it (never folds)."""
    _fed(doc, tmp_path)
    doc._edit_step(2)
    assert doc.editor.scene is not None
    doc._edit_step(2)                                        # same row again -> fold
    assert doc.editor.scene is None
    doc._edit_step(2)
    doc._edit_step(1)                                        # a DIFFERENT row -> switch, not fold
    assert doc.editor.scene is not None and doc.editor.step_i == 1


def test_the_edit_affordances_wear_the_svg_pencil_not_the_codepoint(doc, tmp_path):
    """Playtest ask: U+270E falls back to a pixelly legacy glyph on Windows. The Settings
    toggle and the per-row Edit wear the authored SVG (the call-site law: an icon nobody
    sets is a glyph that never improved)."""
    from PySide6.QtWidgets import QPushButton
    _fed(doc, tmp_path)
    assert not doc.settings_btn.icon().isNull()
    assert "✎" not in doc.settings_btn.text()
    edit_btn = next(b for b in doc.ladder.findChildren(QPushButton)
                    if b.accessibleName().startswith("Edit this step") and " step 0" in b.accessibleName())
    assert not edit_btn.icon().isNull() and edit_btn.text() == ""
    from ff9mapkit.workspace import icons
    assert "pencil" in icons.names()                         # the family owns it (parity census)


def test_settings_and_the_editor_are_mutually_exclusive(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._edit_step(2)
    assert doc.editor.scene is not None
    doc.settings_btn.setChecked(True)
    assert doc.editor.scene is None, "opening settings closes the step editor"
    assert doc.ladder._lay.indexOf(doc.settings_card) == 0, "settings seats above row 0"
    doc._edit_step(2)
    assert not doc.settings_btn.isChecked(), "opening a step closes settings"
    assert doc.ladder._lay.indexOf(doc.editor) == 3


# ------------------------------------------------------------------ shell: undo + one-writer
def _glen_on_tab(win, tmp_path):
    win.open_field(make_cutscene_field(tmp_path))
    win.tabs.setCurrentWidget(win.cutscene_doc)
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(1)                          # narration: [say "Dusk…", wait 30]
    return doc


def _scene1(win):
    return win._doc("GLEN").data["cutscene"][1]["steps"]


def test_undo_under_an_open_editor_never_overwrites_another_step(win, tmp_path):
    """C2: Ctrl+Z swaps in a NEW buffer. The editor stayed aimed at its old (scene, row), so the
    next Apply wrote its stale content over whichever step now held that row -- one step lost,
    another duplicated -- with no sign anything had changed."""
    doc = _glen_on_tab(win, tmp_path)
    doc._move_step(0, +1)                              # [wait, say] -- one undo step
    doc._edit_step(0)                                  # the editor holds the WAIT
    assert doc.editor.value_line.text() == "30"
    win._undo()                                        # Ctrl+Z: [say, wait] again
    assert win.tabs.currentWidget() is doc
    assert [forms.step_key(s) for s in _scene1(win)] == ["say", "wait"]
    assert doc.editor.scene is None, "the editor still claims row 0, which is now another step"
    doc._apply_step()                                  # a stray Apply must not write anything
    assert [forms.step_key(s) for s in _scene1(win)] == ["say", "wait"]


def test_undo_that_removes_the_edited_row_closes_the_editor(win, tmp_path):
    """C2: the row the editor is on no longer exists -- Apply raised IndexError out of the slot
    and the user saw nothing happen."""
    doc = _glen_on_tab(win, tmp_path)
    doc._add_step()
    doc.editor.value_text.setPlainText("a third line")
    doc._apply_step()                                  # lands at row 2 (one undo step)
    doc._close_editor()
    doc._edit_step(2)
    win._undo()                                        # row 2 is gone
    assert len(_scene1(win)) == 2
    assert doc.editor.scene is None
    doc._apply_step()                                  # no IndexError out of the slot


def test_an_undo_that_leaves_the_edited_step_alone_keeps_the_editor(win, tmp_path):
    """The other half of C2: a buffer swap that did not touch the editor's step (here an undo
    of a Behavior-tab edit) must not throw the author's half-typed line away."""
    doc = _glen_on_tab(win, tmp_path)
    doc._edit_step(0)
    doc.editor.value_text.setPlainText("half-typed rewrite")
    data = win._doc("GLEN").data
    data.setdefault("marker", []).append({"name": "well", "pos": [-100, -100]})
    win._on_behavior_edit("GLEN", "add a marker")      # a real checkpointed edit elsewhere
    win._undo()
    win.tabs.setCurrentWidget(doc)                     # back on the tab: the feed sees the swap
    assert doc._raw is win._doc("GLEN").data, "the doc follows the restored buffer"
    assert doc.editor.scene == 1 and doc.editor.step_i == 0, "the editor was closed needlessly"
    assert doc.editor.value_text.toPlainText() == "half-typed rewrite"
    doc._apply_step()
    assert _scene1(win)[0]["say"] == "half-typed rewrite", "Apply lands in the RESTORED buffer"
    assert "wait" in _scene1(win)[1]


def test_undo_re_judges_an_armed_staging(win, tmp_path):
    """C3: once the staging is armed, Ctrl+Z brought the stalling walk back while the inspector
    still said every walk reaches its target -- a same-field re-feed never re-judged."""
    p = make_cutscene_field(tmp_path)
    p.write_text(FIELD_TOML.replace('walk = "altar"', "walk = [2000, 2000]"), encoding="utf-8")
    win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    doc = win.cutscene_doc
    doc.stage_now(sync=True)
    assert "staging problem" in doc.stage_note.text()
    doc._edit_step(0)
    doc.editor.value_line.setText("altar")             # the fix, through the editor
    doc._apply_step()
    doc._restage_timer.stop()
    doc.stage_now(sync=True, warm=True)
    assert "✓" in doc.stage_note.text()
    win._undo()                                        # the stall is back in the document
    assert win._doc("GLEN").data["cutscene"][0]["steps"][0]["walk"] == [2000, 2000]
    assert doc._restage_timer.isActive(), "the undo did not re-judge the armed staging"
    doc._restage_timer.stop()
    doc._restage()                                     # what the debounce fires
    _wait_stage(doc)
    assert "staging problem" in doc.stage_note.text()


def test_apply_refuses_when_an_in_place_writer_removed_its_row(doc, tmp_path):
    """C2's last guard: a writer that edits the SAME buffer in place (the Editor tree's delete)
    gives show_field no buffer swap to notice; Apply itself must refuse, and say so."""
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._edit_step(1)                                  # the wait
    cutscenescan.remove_step(doc._raw, 1, 1)           # the in-place writer
    doc._apply_step()                                  # must not raise IndexError
    assert len(doc._steps()) == 1 and "say" in doc._steps()[0]
    assert doc.editor.note.text(), "the refusal is SAID"


_THREE_SCENES = FIELD_TOML + """
[[cutscene]]
requires_scenario = 400
steps = [
  { say = "Scene two line A" },
  { say = "Scene two line B" },
]
"""


def _says(win):
    return [[s.get("say") or forms.step_key(s) for s in b.get("steps", [])]
            for b in win._doc("GLEN").data["cutscene"]]


def test_an_editor_tree_scene_delete_never_aims_apply_at_another_scene(win, tmp_path):
    """C2 (after review): the Editor tree's 'Remove cutscene' pops scene #0 IN PLACE -- the same
    buffer, so no swap to notice -- and every later scene shifts down one. An editor open on scene
    1 row 0 then pointed at the old scene 2 row 0, and Apply overwrote 'Scene two line A'."""
    p = make_cutscene_field(tmp_path)
    p.write_text(_THREE_SCENES, encoding="utf-8")
    win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(1)
    doc._edit_step(0)                                  # "Dusk falls over the glen."
    doc.editor.value_text.setPlainText("Dusk falls, rewritten")
    win._confirm = lambda *a, **k: True
    win._delete_object("GLEN", "cutscene", single=True, label="cutscene")   # the tree's Remove
    win.tabs.setCurrentWidget(doc)
    win._feed_cutscene()
    doc._apply_step()
    assert _says(win) == [["Dusk falls, rewritten", "wait"],
                          ["Scene two line A", "Scene two line B"]], \
        "Apply wrote into a scene the author never opened"


def test_an_add_editor_never_inserts_into_the_scene_an_undo_put_at_its_index(win, tmp_path):
    """C2 (after review): ADD mode was exempt from the survival rule. Delete scene #0, Add on the
    narration scene (now #0), type, Ctrl+Z: the cast scene came back at #0 and Apply inserted the
    narration line between its turn and its say."""
    win.open_field(make_cutscene_field(tmp_path))
    win.tabs.setCurrentWidget(win.cutscene_doc)
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(0)
    doc._del_scene()                                   # one undo step
    doc._add_step()                                    # ADD on the narration scene, now #0
    doc.editor.value_text.setPlainText("Narration line 3")
    win._undo()
    win.tabs.setCurrentWidget(doc)
    doc._apply_step()
    says = _says(win)
    assert says[0] == ["walk", "turn", "Made it to the altar."], f"the cast scene was written: {says}"
    assert says[1] == ["Dusk falls over the glen.", "wait", "Narration line 3"], \
        f"the typed line must land in the scene it was typed for: {says}"


def test_a_stage_drag_of_the_open_step_shows_in_the_editor_and_survives_apply(doc, tmp_path):
    """C2 (after review): dragging the open walk step's target rewrote the step, but the editor
    kept 'altar'; the next Apply (here: only a speed change) silently reverted the drag."""
    _fed(doc, tmp_path)
    doc._edit_step(0)                                  # walk "altar", actor Cid
    assert doc._stage_handles(), "the open step's target is a stage handle"
    doc._on_stage_move(("target", 0, 0), 120, 300)     # the drag
    assert doc.editor.value_line.text() == "120, 300", "the editor still shows the old target"
    doc.editor.x_speed.setText("12")
    doc._apply_step()
    assert doc._raw["cutscene"][0]["steps"][0] == {"walk": [120, 300], "actor": "Cid", "speed": 12}


def test_apply_writes_to_the_scene_the_editor_opened_not_the_selected_one(doc, tmp_path):
    """C2: the editor addresses ITS scene. If the tab's selected scene ever differs from the
    editor's, Apply must still land in the scene the step was opened from."""
    raw, _ = _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc._edit_step(0)
    doc._scene = 0                                     # the selection moved without a close
    doc.editor.value_text.setPlainText("Night falls")
    doc._apply_step()
    assert raw["cutscene"][1]["steps"][0]["say"] == "Night falls"
    assert [forms.step_key(s) for s in raw["cutscene"][0]["steps"]] == ["walk", "turn", "say"]
    assert raw["cutscene"][0]["steps"][2]["say"] == "Made it to the altar."


def test_a_field_switch_drops_the_doc_held_verdict_rows(doc, tmp_path):
    """C1: the verdicts live on the doc and every render repaints them, so a field switch that
    kept the rows would paint the old field's stall on the new field's stage."""
    (tmp_path / "a").mkdir()
    _fed(doc, tmp_path / "a", FIELD_TOML.replace('walk = "altar"', "walk = [2000, 2000]"))
    doc.stage_now(sync=True)
    assert doc._verdicts and _tags(doc.canvas)["verdict"] >= 1
    doc.show_field("GLEN", tomllib.loads(FIELD_TOML), make_cutscene_field(tmp_path / "b"))
    assert doc._verdicts == []
    assert _tags(doc.canvas)["verdict"] == 0, "the old field's stall painted on the new field"


def test_a_failed_explicit_reload_drops_the_warm_mesh_and_the_auto_rejudge(doc, tmp_path):
    """C4 (after review): the button's reload failed (a broken .bgi) and said so, but the OLD warm
    mesh stayed armed -- the next edit's automatic re-judge painted the old floor's checkmark
    over the error."""
    _fed(doc, tmp_path)
    doc.stage_now(sync=True)
    assert "✓" in doc.stage_note.text()
    (tmp_path / "walkmesh.bgi").write_bytes(b"garbage")
    doc.stage_now(sync=True)                           # the explicit press
    assert "No walkmesh" in doc.stage_note.text()
    assert doc._wmesh is None and not doc._stage_armed
    doc._steps()[2]["say"] = "Made it."
    doc._after_edit("edit")
    assert not doc._restage_timer.isActive(), "an edit re-armed a judge on the old floor"
    doc._restage()                                     # even if fired, it must read disk again
    _wait_stage(doc)
    assert "✓" not in doc.stage_note.text(), doc.stage_note.text()


def test_a_doc_edit_lands_by_reference_dirty_and_one_undo_step(win, tmp_path):
    p = make_cutscene_field(tmp_path)
    win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    doc = win.cutscene_doc
    n = len(win._undo_stack)
    doc.rail.setCurrentRow(1)
    doc._add_step()
    doc.editor.value_text.setPlainText("an undoable line")
    doc._apply_step()
    assert any(s.get("say") == "an undoable line"
               for s in win._doc("GLEN").data["cutscene"][1]["steps"]), \
        "the op mutated the OPEN doc (by reference)"
    assert "GLEN" in win._dirty_members()
    assert len(win._undo_stack) == n + 1, "exactly one undo step per Apply"
    win.tabs.setCurrentWidget(win.doc_scroll)
    win._undo()
    assert win.tabs.currentWidget() is win.cutscene_doc, \
        "undo focus lands back on the TAB (the cutscene_tab token)"
    assert not any(s.get("say") == "an undoable line"
                   for s in win._doc("GLEN").data["cutscene"][1]["steps"])


def test_the_editor_tree_summary_has_no_write_path(win, tmp_path):
    """THE ONE-WRITE-SURFACE FENCE: the summary carries no _save_ctx, so no nav/undo/save
    boundary can fold stale widget values back over a doc edit."""
    p = make_cutscene_field(tmp_path)
    win.open_field(p)
    win._goto_tree_section("GLEN", "cutscene")
    assert win._save_ctx is None
    win.tabs.setCurrentWidget(win.cutscene_doc)
    win.cutscene_doc._add_scene()                      # a doc edit while the summary was mounted
    assert win._commit_active() is True                # the old fold boundary: now a no-op
    assert len(win._doc("GLEN").data["cutscene"]) == 3, "nothing folded back over the edit"


# ------------------------------------------------------------------ chrome
def test_a11y_names_on_every_interactive_control(doc, tmp_path):
    _fed(doc, tmp_path)
    assert doc.rail.accessibleName() == "Cutscene scenes"
    assert doc.canvas.accessibleName() == "Cutscene stage"
    assert doc.board_slider.accessibleName() == "Storyboard beat"
    assert doc.stage_btn.accessibleName()
    assert doc.stage_list.accessibleName() == "Cutscene staging problems"
    assert doc.ladder.accessibleName() == "Cutscene steps"


def test_retheme_and_set_scale_survive_both_pages(doc, tmp_path):
    doc.retheme(pick_palette("mist"))                   # on the guide: rebuilds the glyph
    _fed(doc, tmp_path)
    doc.board_btn.setChecked(True)
    doc.retheme(pick_palette("dark"))                   # on content: repaints canvas + chips
    doc.set_scale(150)
    assert doc.board_slider.minimumWidth() == 180
    assert doc.crumb_label() == "Cutscene — GLEN"


# --------------------------------------------------------------- batch 2, the final review
def test_a_swapped_buffer_never_carries_the_editor_into_a_look_alike_scene(doc, tmp_path):
    """After an undo the editor's scene must be re-found by its contents -- its OWN index first.
    'Some scene equal to the one it opened on' carried it into a duplicate (Duplicate scene makes
    those routine) whenever its own scene had changed under it, and Apply wrote the author's
    line into a scene they never opened. Also fences the own-row fallback: without it the open
    step's typed text is dropped by every undo of an edit elsewhere in its scene."""
    import copy
    raw, path = _fed(doc, tmp_path)
    raw["cutscene"][1] = copy.deepcopy(raw["cutscene"][0])        # scene #1 is now a twin of #0
    doc.show_field("GLEN", raw, path)
    doc.rail.setCurrentRow(0)
    doc._edit_step(2)                                  # the say "Made it to the altar." of scene #0
    doc.editor.value_text.setPlainText("typed, not yet applied")
    swapped = copy.deepcopy(raw)                       # an undo: a NEW buffer in which a SIBLING step
    swapped["cutscene"][0]["steps"][0]["walk"] = [5, 5]            # of scene #0 differs
    doc.show_field("GLEN", swapped, path)
    assert doc.editor.scene == 0 and doc.editor.step_i == 2, "the editor left its own scene"
    assert doc.editor.value_text.toPlainText() == "typed, not yet applied"
    doc._apply_step()
    assert swapped["cutscene"][0]["steps"][2]["say"] == "typed, not yet applied"
    assert swapped["cutscene"][1]["steps"][2]["say"] == "Made it to the altar."   # the twin: untouched


def test_a_waypoint_added_or_removed_on_the_open_route_survives_apply(doc, tmp_path):
    """The stage's insert / delete of a path point rewrote the step, but the open editor kept the
    old route in its box; the next Apply (even a speed-only change) wrote it back."""
    raw, path = _fed(doc, tmp_path)
    raw["cutscene"][0]["steps"][0] = {"path": [[0, 400], [200, 400]], "actor": "Cid"}
    doc.show_field("GLEN", raw, path)
    doc.rail.setCurrentRow(0)
    doc._edit_step(0)
    doc._on_stage_insert(("leg", 0, 0, 0))             # a point after the first
    assert len(raw["cutscene"][0]["steps"][0]["path"]) == 3
    doc.editor.x_speed.setText("12")
    doc._apply_step()
    step = raw["cutscene"][0]["steps"][0]
    assert step["path"] == [[0, 400], [100, 400], [200, 400]] and step["speed"] == 12
    doc._on_stage_delete(("leg", 0, 0, 1))             # and take it out again
    doc.editor.x_speed.setText("14")
    doc._apply_step()
    step = raw["cutscene"][0]["steps"][0]
    assert step["path"] == [[0, 400], [200, 400]] and step["speed"] == 14


def test_a_flag_the_campaign_owns_is_not_called_unknown(app, tmp_path):
    """A member's scene may set a flag its CAMPAIGN defines. The tab's unknown-name check must be
    handed the campaign's names, or every shared flag is a false problem."""
    for names, clean in (({"bridge_out": 8713}, True), ({}, False)):
        d = CutsceneDoc(pick_palette("dark"), flag_names_fn=lambda n=names: n)
        try:
            raw, path = _fed(d, tmp_path)
            assert "No structural problems." in d.problems_lbl.text()      # the premise: clean before
            raw["cutscene"][0]["steps"].append({"set_flag": ["bridge_out", 1]})
            d.show_field("GLEN", raw, path)
            assert ("No structural problems." in d.problems_lbl.text()) is clean, d.problems_lbl.text()
        finally:
            d.hide()
            d.instruments.setParent(None)


def test_adding_or_duplicating_a_scene_closes_the_step_editor(doc, tmp_path):
    """The selection moves to the new scene; an editor left open would still be aimed at a step
    of the old one while the ladder shows another."""
    _fed(doc, tmp_path)
    for act in (doc._add_scene, doc._dup_scene):
        doc.rail.setCurrentRow(0)
        doc._edit_step(0)
        assert doc.editor.scene is not None
        act()
        assert doc.editor.scene is None, f"{act.__name__} left the step editor open"


def _rowtool(doc, glyph_tip, i):
    """The real ladder button (rowtools are named '<tip> — step <i>')."""
    from PySide6.QtWidgets import QPushButton
    name = f"{glyph_tip} — step {i}"
    hits = [b for b in doc.ladder.findChildren(QPushButton) if b.accessibleName() == name]
    assert len(hits) == 1, name
    return hits[0]


_GESTURES = {
    "move up": lambda doc: _rowtool(doc, "Move this step up", 1).click(),
    "duplicate": lambda doc: _rowtool(doc, "Duplicate this step", 1).click(),
    "delete": lambda doc: _rowtool(doc, "Remove this step (Ctrl+Z undoes)", 1).click(),
    "pencil on another row": lambda doc: _rowtool(doc, "Edit this step (click again to fold)",
                                                  1).click(),
    "add a step": lambda doc: doc.add_step_btn.click(),
    "another scene": lambda doc: doc.rail.setCurrentRow(0),
    "delete the scene": lambda doc: doc.del_scene_btn.click(),
    "add a scene": lambda doc: doc.add_scene_btn.click(),
    "duplicate the scene": lambda doc: doc.dup_scene_btn.click(),
}


@pytest.mark.parametrize("gesture", list(_GESTURES))
def test_a_gesture_never_throws_away_an_unapplied_line(doc, tmp_path, gesture):
    """C11: the row tools, a scene switch, a scene delete and the pencil on another row closed
    the step editor (or loaded another step over it) and the half-typed line was gone. A DIRTY
    editor now refuses the gesture and says how to go on; nothing changes."""
    raw, _ = _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)                          # [say "Dusk…", wait 30]
    doc._edit_step(0)
    doc.editor.value_text.setPlainText("Dusk falls, half-typed")
    before = copy.deepcopy(doc._raw)
    _GESTURES[gesture](doc)
    assert doc._raw == before, f"{gesture} changed the document under a dirty editor"
    assert doc._scene == 1 and doc.rail.currentRow() == 1
    assert doc.editor.scene == 1 and doc.editor.step_i == 0, f"{gesture} closed the editor"
    assert doc.editor.value_text.toPlainText() == "Dusk falls, half-typed"
    assert "Apply" in doc.editor.note.text() and "Close" in doc.editor.note.text()
    doc._apply_step()                                  # the line was kept for this
    assert doc._steps()[0]["say"] == "Dusk falls, half-typed"


def _in_view(doc, w):
    from PySide6.QtCore import QPoint
    vp = doc._lscroll.viewport()
    y = w.mapTo(vp, QPoint(0, 0)).y()
    return 0 <= y and y + min(w.height(), 30) <= vp.height()


def test_opening_a_step_shows_the_editors_header_and_the_row_it_edits(doc, tmp_path):
    """C18: the editor (taller than the ladder pane) was CENTRED, so Apply/Close and the row
    being edited scrolled away. A relation, not a pixel claim: the row above the editor and the
    Apply button must both lie inside the viewport (pixels: tools/gui_snap.py cutscene:editor)."""
    from PySide6.QtCore import Qt as _Qt
    toml = FIELD_TOML.replace('  { say = "Made it to the altar.", speaker = "Cid" },\n',
                              '  { say = "Made it to the altar.", speaker = "Cid" },\n'
                              + "".join(f'  {{ say = "line {n}" }},\n' for n in range(10)))
    doc.setAttribute(_Qt.WidgetAttribute.WA_DontShowOnScreen)
    doc.resize(1000, 520)
    doc.show()
    _fed(doc, tmp_path, toml)
    QApplication.processEvents()
    for i in (9, 2, 12):
        _rowtool(doc, "Edit this step (click again to fold)", i).click()
        QApplication.processEvents()
        lay = doc.ladder._lay
        row = lay.itemAt(lay.indexOf(doc.editor) - 1).widget()
        assert _in_view(doc, row), f"step {i}: the row being edited scrolled away"
        assert _in_view(doc, doc.editor.apply_btn), f"step {i}: Apply is off screen"
    doc.editor.value_text.setPlainText("half-typed")   # C11's refusal brings the editor back too
    doc._lscroll.verticalScrollBar().setValue(0)
    _rowtool(doc, "Remove this step (Ctrl+Z undoes)", 0).click()
    QApplication.processEvents()
    assert "Apply" in doc.editor.note.text() and _in_view(doc, doc.editor.apply_btn)


def test_a_clean_editor_still_closes_for_a_structural_edit(doc, tmp_path):
    _fed(doc, tmp_path)
    for i in range(3):                                 # every fixture step opens CLEAN
        doc._edit_step(i)
        assert not doc._editor_dirty(), doc._steps()[i]
    _rowtool(doc, "Move this step down", 0).click()
    assert doc.editor.scene is None, "a clean editor closes, as before"
    assert forms.step_key(doc._steps()[1]) == "walk"


def test_an_add_lane_with_typing_or_an_unreadable_value_counts_as_unapplied(doc, tmp_path):
    _fed(doc, tmp_path)
    doc.rail.setCurrentRow(1)
    doc.add_step_btn.click()
    assert not doc._editor_dirty(), "an empty add lane is clean"
    doc.editor.value_text.setPlainText("a")
    _rowtool(doc, "Move this step down", 0).click()
    assert forms.step_key(doc._steps()[0]) == "say", "refused"
    doc.editor.value_text.clear()
    doc._close_editor()
    doc._edit_step(0)
    doc.editor.x_duration.setText("soon")               # read_step raises: still the author's typing
    _rowtool(doc, "Move this step down", 0).click()
    assert forms.step_key(doc._steps()[0]) == "say" and doc.editor.scene == 1


def test_a_check_that_was_running_while_the_scenes_changed_paints_nothing(doc, tmp_path):
    """Its rows are numbered by the scenes as they WERE: after a scene is deleted mid-check, the
    stall would paint on whichever scene now has that number. They are dropped and the document
    is judged again as it is."""
    _fed(doc, tmp_path)
    doc.stage_now(sync=True)                           # arms the lane: a warm mesh, a real result
    assert doc._stage_armed and doc._wmesh is not None
    doc._stage_busy = True                             # a check is in flight ...
    doc._stage_moved = False
    doc.rail.setCurrentRow(1)
    doc._del_scene()                                   # ... and the author deletes a scene
    stale_rows = [{"scene": 0, "step": 0, "kind": "stall", "pts": [(0, 0), (1, 1)], "label": "x"}]
    doc._restage_timer.stop()
    doc._finish_stage((doc._stage_gen, doc._last_stage, stale_rows, doc._wmesh))
    assert doc._verdicts == [], "rows judged against the old scene layout were painted"
    assert doc._restage_timer.isActive(), "the document must be judged again as it now is"
