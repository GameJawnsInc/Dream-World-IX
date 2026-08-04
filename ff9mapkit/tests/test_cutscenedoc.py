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

[[npc]]
name = "Mira"
model = "GEO_SUB_F0_CID"
pos = [-250, -200]

# the altar sits ACROSS the mesh's wall slot from Cid, so the straight walk is blocked and
# the compiler ROUTES it -- the storyboard's straight-to-routed upgrade is real in this fixture
[[marker]]
name = "altar"
pos = [900, 400]

[[cutscene]]
actors = ["Cid"]
requires_scenario = 100
set_scenario = 200
steps = [
  { walk = "altar" },
  { turn = 128, with_prev = true },
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
    assert "scene #0" in doc.rail.item(0).text() and "cast 1" in doc.rail.item(0).text()
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
    assert t["post"] == 1                               # Cid, the cast
    assert t["npc"] == 1                                # Mira, an obstacle
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
