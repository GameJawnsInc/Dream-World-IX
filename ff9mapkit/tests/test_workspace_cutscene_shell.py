"""SHELL-side fences for the Cutscene tab's history (review finding E6).

History restores the whole buffer. The Cutscene doc kept its scene INDEX across the restore, so
after "undo delete scene #1" the rail showed #0, redo of a duplicate left the original selected,
and redo of "add scene" showed the scene before the re-added one: the author had to go looking
for what the history step had just changed.

Driven the way a user does it: the doc's own scene buttons, then the shell's Undo / Redo.
Behaviour + data only -- no geometry or font claim -- so offscreen is sound here.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication                               # noqa: E402

from ff9mapkit.editor.theme import pick_palette                          # noqa: E402
from ff9mapkit.workspace import shell                                    # noqa: E402

_M = "X"                                              # open_field keys the member by its [field] NAME

_TOML = ('[field]\nid = 30999\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
         + "".join(f'[[cutscene]]\nrequires_scenario = {100 * (i + 1)}\n'
                   f'steps = [ {{ say = "scene {i}" }} ]\n\n' for i in range(3)))


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    w = shell.Workspace(pick_palette("dark"))
    p = tmp_path / "X.field.toml"
    p.write_text(_TOML, encoding="utf-8")
    assert w.open_field(p)
    w.toml = p
    w.tabs.setCurrentWidget(w.cutscene_doc)            # the shell feed runs on tab show
    yield w
    w.hide()


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die parked, not under a forced GC pass (test_cutscenedoc's own teardown)."""
    yield
    for w in QApplication.topLevelWidgets():
        try:
            t = getattr(w, "_restage_timer", None)
            if t is not None:
                t.stop()
        except RuntimeError:
            pass
    qt_drain()


def _shown(win):
    """The scene the tab shows: the doc's index, the rail's row and the scene bar must agree."""
    doc = win.cutscene_doc
    assert doc.rail.currentRow() == doc._scene
    assert doc.scene_title.text() == f"scene #{doc._scene}"
    return doc._scene


def _says(win):
    return [b["steps"][0]["say"] for b in win._doc(_M).data["cutscene"]]


def test_undo_of_a_scene_delete_selects_the_restored_scene(win):
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(1)
    doc.del_scene_btn.click()
    assert _says(win) == ["scene 0", "scene 2"] and _shown(win) == 0
    win._undo()
    assert _says(win) == ["scene 0", "scene 1", "scene 2"]
    assert win.tabs.currentWidget() is doc
    assert _shown(win) == 1, "undo restored scene #1 but the tab shows another"
    win._redo()
    assert _says(win) == ["scene 0", "scene 2"] and _shown(win) == 0


def test_undo_and_redo_of_a_duplicate_select_the_original_then_the_copy(win):
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(1)
    doc.dup_scene_btn.click()
    assert _shown(win) == 2
    win._undo()
    assert len(_says(win)) == 3 and _shown(win) == 1, "undo of a copy lands on its original"
    win._redo()
    assert _says(win) == ["scene 0", "scene 1", "scene 1", "scene 2"]
    assert _shown(win) == 2, "redo of a duplicate selects the copy"


def test_redo_of_an_added_scene_selects_it(win):
    doc = win.cutscene_doc
    doc.add_scene_btn.click()
    assert _shown(win) == 3
    win._undo()
    assert len(_says(win)) == 3 and _shown(win) == 2
    win._redo()
    assert len(win._doc(_M).data["cutscene"]) == 4
    assert _shown(win) == 3, "redo of 'add scene' shows the re-added scene"


def test_undo_of_a_step_edit_in_another_scene_goes_to_that_scene(win):
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(2)
    doc._edit_step(0)
    doc.editor.value_text.setPlainText("scene 2, rewritten")
    doc.editor.apply_btn.click()
    doc._close_editor()
    doc.rail.setCurrentRow(0)
    win._undo()
    assert _says(win)[2] == "scene 2" and _shown(win) == 2


def test_the_first_run_banner_calls_a_standalone_field_a_field(win, monkeypatch):
    """C32: the first-run banner said 'Your fork is ready' for every field, beside a status bar
    reading '<name> — standalone field'. 'Field' is true of a fork and of an authored field."""
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "has_deployed", lambda: False)
    text, _acts = win._next_actions()
    assert text == "Your field is ready — press Deploy to put it in your game.", text


def test_a_scene_delete_says_what_went_and_how_to_get_it_back(win):
    """C25: '− Scene' deletes at once (undo-first, no confirm, like the step delete) and said
    nothing: the scene just vanished from the rail. It says what went and that Ctrl+Z restores
    it -- through the shell's own re-feed, which re-renders the doc -- also for the last scene."""
    from PySide6.QtWidgets import QLabel
    doc = win.cutscene_doc
    doc.rail.setCurrentRow(1)
    doc.del_scene_btn.click()
    assert doc.head_sum.fullText() == "Deleted scene #1 (1 step) — Ctrl+Z restores it."
    doc.rail.setCurrentRow(1)                          # the next render puts the summary back
    assert "Deleted" not in doc.head_sum.fullText()
    for _ in range(2):
        doc.del_scene_btn.click()
    said = [lab.text() for lab in doc._guide_page.findChildren(QLabel)]
    assert any(t.startswith("Deleted scene #0 (1 step) — Ctrl+Z restores it.") for t in said), said
    win._undo()
    assert len(_says(win)) == 1
