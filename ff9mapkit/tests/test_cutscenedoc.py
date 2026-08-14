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
    assert "Cid:" in doc.board_say.text()               # the speaker attribution
    assert "Made it to the altar." in doc.board_say.text()
    assert doc.ladder._beat_marks == {2}                # ▶ sweeps the ladder
    t = _tags(doc.canvas)
    assert t["beatpos"] >= 1                            # storyboard mode draws positions
    doc.board_btn.setChecked(False)
    assert doc.ladder._beat_marks == set()


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
    assert 'walk target "ghost"' in doc.problems_lbl.text()
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
    from PySide6.QtGui import QDesktopServices
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.setdefault(
        "path", url.toLocalFile()) or True)
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


def test_with_prev_is_gated_by_the_compilers_rule_and_row_position(doc, tmp_path):
    _fed(doc, tmp_path)
    doc._edit_step(1)                                  # the turn step, row 1
    assert doc.editor.with_prev.isEnabled(), "turn on row 1 may run in parallel"
    doc._edit_step(0)                                  # row 0: nothing to run with
    assert not doc.editor.with_prev.isEnabled()
    doc._edit_step(2)                                  # a say can never parallelize
    assert not doc.editor.with_prev.isEnabled()


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


def test_a_warm_mesh_rejudges_without_touching_disk(doc, tmp_path, monkeypatch):
    _fed(doc, tmp_path)
    doc.stage_now(sync=True)
    assert doc._stage_armed and doc._wmesh is not None
    monkeypatch.setattr(cutscenescan, "load_walkmesh",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("disk touched")))
    doc._steps()[0]["walk"] = [2000, 2000]             # an edit that now stalls
    doc.stage_now(sync=True)                           # the re-judge rides the WARM mesh
    assert doc._last_stage.warnings, "the warm re-judge must catch the new stall"
    # and a committed edit ARMS the debounced re-judge
    doc._after_edit("test edit")
    assert doc._restage_timer.isActive()


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
