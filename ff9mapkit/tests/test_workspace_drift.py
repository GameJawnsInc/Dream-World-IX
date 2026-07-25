"""The drift chip + the "Since your last deploy" list (shell.py's wiring of editor/deploysnap).

The arithmetic is fenced in test_tomldiff.py. This fences the WIRING, which is where the interesting
mistakes were:

  * the snapshot is captured at LAUNCH from DISK, and the live comparison reads the OPEN DOC -- conflating
    the two either hides unsaved work from the count or records edits that never reached the game;
  * the chip is gated on something being OPEN, not on the Build tab's path box (which deliberately survives
    a close), or it goes on reporting "in sync" about a project the user just closed;
  * a failed deploy must not move the baseline;
  * a snapshot write failure must not break the deploy it decorates.

Prefs are isolated by conftest's autouse _isolate_prefs; the snapshot dir is patched per test so nothing
here can write the developer's real cache.
"""

from __future__ import annotations

import copy
import os
import shutil
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication                                   # noqa: E402

from ff9mapkit.editor import deploysnap                                      # noqa: E402
from ff9mapkit.editor.theme import pick_palette                              # noqa: E402
from ff9mapkit.workspace import anim                                         # noqa: E402

KIT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def snapdir(tmp_path, monkeypatch):
    """Patched at deploysnap's own accessor -- NOT via FF9MAPKIT_DATA, which also redirects the TEMPLATES
    dir and (measured, in gui_snap) hangs the whole app when pointed at an empty directory. One env var,
    two meanings: patch the narrow thing."""
    monkeypatch.setattr(deploysnap, "snap_dir", lambda: tmp_path / "deploysnap")
    return tmp_path


@pytest.fixture
def project(tmp_path):
    """A WRITABLE copy of a bundled example. Never the example itself: a Save rewrites the byte-exact
    golden oracle (the standing rule in CLAUDE.md §7)."""
    dst = tmp_path / "proj"
    shutil.copytree(KIT / "examples/boletta", dst)
    return dst / "boletta.field.toml"


@pytest.fixture
def win(app, snapdir, project):
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    anim.set_enabled(False)
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    w.open_field(project)
    w.build_deploy.set_target(str(project))
    app.processEvents()
    yield w
    w.close()


def _doc(win):
    return win._docs[sorted(win._docs)[0]]


def _deploy(win, app, ok=True):
    """Drive a deploy through the REAL hooks (capture at launch, commit on success)."""
    win._capture_deploy_snapshot()
    win._deployed_field_id = 4004
    if ok:
        win._commit_deploy_snapshot()
    app.processEvents()


# ------------------------------------------------------------------ the chip's states
def test_before_the_first_deploy_the_chip_is_ABSENT(win, app):
    """THE GOES-AWAY LAW. A chip reading "0 changes" would imply the game is running this project; it is not.
    Nothing true to say -> nothing shown."""
    win._refresh_drift_chip()
    assert not win.drift_chip.isVisible()
    snap, changes = win._drift_changes()
    assert snap is None and changes == []


def test_after_a_deploy_it_says_in_sync_then_counts_edits(win, app):
    _deploy(win, app)
    assert win.drift_chip.isVisible()
    assert win.drift_chip.text() == "game: in sync"

    _doc(win).data["camera"]["pitch"] = 45.0
    win._refresh_drift_chip()
    assert win.drift_chip.text() == "game: 1 ahead"

    _doc(win).data["field"]["title"] = "Colder"
    win._refresh_drift_chip()
    assert win.drift_chip.text() == "game: 2 ahead"


def test_the_chip_names_its_referent(win, app):
    """"3 ahead" does not say ahead of WHAT. The `game:` label is the same key-then-value idiom kv() uses."""
    _deploy(win, app)
    assert win.drift_chip.text().startswith("game:")
    assert "deploy" in win.drift_chip.toolTip().lower()


def test_more_than_one_change_states_the_projects_own_rule(win, app):
    """The law is *"One change per in-game test"*. One change: no scolding. Two: say it, once, in the tooltip.

    NO NEW MODAL, and that is a deliberate constraint rather than an omission -- ASK #1 removed the F9 confirm
    on purpose ("make F9 a true one-key loop"), so a warning dialog here would undo a ratified decision."""
    _deploy(win, app)
    _doc(win).data["camera"]["pitch"] = 45.0
    win._refresh_drift_chip()
    assert "⚠" not in win.drift_chip.toolTip(), "one change is the RULE being followed, not a problem"

    _doc(win).data["field"]["title"] = "Colder"
    win._refresh_drift_chip()
    tip = win.drift_chip.toolTip()
    assert "⚠" in tip and "which edit" in tip


def test_closing_the_project_hides_the_chip(win, app):
    """The Build tab's path box deliberately SURVIVES a close (round 10 persists the destination), so a chip
    keyed on it alone went on reporting "in sync" about a project the user had just closed."""
    _deploy(win, app)
    assert win.drift_chip.isVisible()
    win._close_project()
    app.processEvents()
    win._refresh_drift_chip()
    assert not win.drift_chip.isVisible()
    assert win._deploy_target(), "...and the Build tab still HAS a target -- which is why the gate is elsewhere"


def test_an_edit_schedules_a_coalesced_refresh(win, app):
    """_refresh_dirty_marks is documented "free to call per keystroke", and recomputing means parsing the
    project's tomls -- so the chip is coalesced behind a timer rather than computed inline."""
    _deploy(win, app)
    win._drift_timer.stop()
    win._refresh_dirty_marks()
    assert win._drift_timer.isActive(), "the edit funnel must ASK for a refresh, not perform one"


# ------------------------------------------------------------------ disk vs. the open doc
def test_the_snapshot_records_DISK_while_the_count_reads_the_OPEN_DOC(win, app):
    """The pairing that makes both numbers true. An UNSAVED edit is what F9 will save and deploy, so it must
    count; but it is not what the last deploy sent, so capturing it as deployed would erase the very edit
    under test from the next comparison."""
    _deploy(win, app)
    _doc(win).data["camera"]["pitch"] = 45.0            # edited, NOT saved
    win._refresh_drift_chip()
    assert win.drift_chip.text() == "game: 1 ahead"
    assert win._dirty_members(), "the doc really is dirty"

    _deploy(win, app)                                    # deploy again WITHOUT saving
    win._refresh_drift_chip()
    assert win.drift_chip.text() == "game: 1 ahead", \
        "the unsaved edit never reached disk, so it is still ahead of the game"

    win._save_all()
    _deploy(win, app)
    win._refresh_drift_chip()
    assert win.drift_chip.text() == "game: in sync", "saved then deployed -> in sync"


def test_a_capture_at_LAUNCH_survives_an_edit_during_the_build(win, app, project):
    """A build takes seconds and the user keeps working. Reading the files after the subprocess returns would
    record a mid-run save as "already deployed", so the edit under test would vanish from the comparison."""
    _deploy(win, app)
    win._capture_deploy_snapshot()                       # the deploy launches...
    data = copy.deepcopy(_doc(win).data)
    data["camera"]["pitch"] = 45.0
    from ff9mapkit.editor import model
    project.write_text(model.dumps(data), encoding="utf-8")   # ...and a save lands mid-build
    win._commit_deploy_snapshot()                        # ...then it succeeds
    _doc(win).data["camera"]["pitch"] = 45.0             # the editor holds the new value
    win._refresh_drift_chip()
    assert win.drift_chip.text() == "game: 1 ahead", \
        "the mid-build save is AHEAD of what was deployed, not part of it"


def test_a_failed_deploy_does_not_move_the_baseline(win, app):
    """_commit_deploy_snapshot is called only from _proc_done's success branch. A red deploy leaves the last
    GOOD deploy as the comparison point -- which is the one you want to reason from."""
    _deploy(win, app)
    _doc(win).data["camera"]["pitch"] = 45.0
    win._refresh_drift_chip()
    before = win.drift_chip.text()
    win._capture_deploy_snapshot()                       # launched...
    win._pending_snapshot = None                         # ...and _proc_done never promoted it (non-zero exit)
    win._refresh_drift_chip()
    assert win.drift_chip.text() == before == "game: 1 ahead"


def test_a_snapshot_write_failure_never_breaks_the_deploy(win, app, monkeypatch):
    """NEVER LOAD-BEARING. The chip is diagnostics; a read-only cache must cost the deploy nothing."""
    monkeypatch.setattr(deploysnap, "write", lambda *a, **k: None)
    _deploy(win, app)                                    # must not raise
    win._refresh_drift_chip()
    assert not win.drift_chip.isVisible(), "no snapshot -> nothing to compare -> no chip (not a lie)"


# ------------------------------------------------------------------ the list
def test_the_dialog_lists_the_changes_and_groups_by_file(win, app, monkeypatch):
    shown = {}
    monkeypatch.setattr("PySide6.QtWidgets.QDialog.exec", lambda dlg: shown.setdefault("dlg", dlg) and 0)
    _deploy(win, app)
    _doc(win).data["camera"]["pitch"] = 45.0
    _doc(win).data["npc"][0]["dialogue"] = "Changed!"
    win._open_drift()
    dlg = shown["dlg"]
    from PySide6.QtWidgets import QListWidget
    lst = dlg.findChild(QListWidget)
    assert lst is not None, "the rows live in a LIST -- fit_dialog sizes those from real content"
    rows = [lst.item(i).text() for i in range(lst.count())]
    assert any("camera.pitch" in r for r in rows), rows
    assert any("dialogue" in r for r in rows), rows
    assert all(c.file == "" for c in win._drift_changes()[1]), "a single-file project tags no file"


def test_the_dialog_teaches_before_the_first_deploy(win, app, monkeypatch):
    """With no baseline the honest answer is "nothing to compare", plus how to get one."""
    shown = {}
    monkeypatch.setattr("PySide6.QtWidgets.QDialog.exec", lambda dlg: shown.setdefault("dlg", dlg) and 0)
    win._open_drift()
    from PySide6.QtWidgets import QLabel
    text = " ".join(w.text() for w in shown["dlg"].findChildren(QLabel))
    assert "nothing to compare" in text.lower()
    assert "F9" in text, "say how to get a baseline"


def test_a_destination_reads_as_english_not_as_a_tuple(win):
    """deploy_dest_key() returns ("test",) / ("inplace", donor) -- readable to the code, not to a reader."""
    assert win._dest_phrase(("test",)) == "the shared test slot"
    assert "in place" in win._dest_phrase(("inplace", "IC_ENT"))
    assert "IC_ENT" in win._dest_phrase(("inplace", "IC_ENT"))
    assert win._dest_phrase(("inplace", None)) == "in place, over its donor", "no empty parentheses"
    assert win._dest_phrase(None) == "an unknown destination"
    assert win._dest_phrase(("something-new",)) == "something-new", "an unmapped kind degrades to itself"


def test_the_command_palette_carries_the_question(win):
    assert any("changed since my last deploy" in lbl.lower() for lbl, _k, _cb in win._command_index())
