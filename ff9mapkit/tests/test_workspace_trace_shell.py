"""SHELL-side fences for the Trace lane: what a Trace regenerate does to the project that is
OPEN in the Editor (review finding T38).

The first Trace Generate hands the project to the shell (``open_field``). Every later Generate
rewrote the same ``field.toml`` in place and told the shell nothing, so the open buffer went
stale: any edit in another tab followed by Save All wrote the OLD buffer over the regenerated
file — the session's new doors, events and camera gone, while the regenerated walkmesh stayed.
And the reverse: the regenerate merges from DISK, so edits not yet saved were left out of it.

These drive the REAL wiring (``win.trace_doc`` and the hooks the shell gave it), not the hook
methods by name, so a fence cannot pass by the hook merely existing.

Behaviour + data only — no geometry or font claim — so offscreen is sound here.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")
pytest.importorskip("PIL")

from PySide6.QtWidgets import QApplication                               # noqa: E402

from ff9mapkit import imagefield as IF                                   # noqa: E402
from ff9mapkit.editor.theme import pick_palette                          # noqa: E402
from ff9mapkit.workspace import placedoc, shell                          # noqa: E402

_NAME = "HALL"
_FLOOR = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
_DOOR = "4005@60,300;140,300;140,330;60,330"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    w = shell.Workspace(pick_palette("dark"))
    yield w
    w.hide()


class _Run:
    """The run_job seam: records the argv + kwargs, reports 'started'."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        return True


def _project(tmp_path, **regions):
    """A generated image-field project on disk: (photo, its field.toml)."""
    from PIL import Image
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    man = IF.build_image_field(photo, _FLOOR, tmp_path / "proj", name=_NAME, field_id=30790,
                               **regions)
    return photo, Path(man["toml"])


def _regenerate(photo, toml, floor=_FLOOR, **regions):
    """What the Trace tab's job does on disk for an in-place regenerate — the same backend the
    CLI it launches calls, without the subprocess."""
    return IF.build_image_field(photo, floor, toml.parent, name=_NAME, field_id=30790, **regions)


def _disk(toml):
    return tomllib.loads(toml.read_text(encoding="utf-8"))


def _place_an_npc(win):
    """An edit in ANOTHER tab, through the shell's own edit hook (the Place tab's path)."""
    data = win._doc(_NAME).data
    placedoc.place_npc(data, 0, 1500)
    win._on_place_edit(_NAME, "place NPC")


# --------------------------------------------------------------- the regenerate reloads the buffer
def test_a_regenerate_reloads_the_open_project_so_save_all_cannot_undo_it(win, tmp_path):
    """THE FLOW THAT LOST IT: generate (the project opens), draw a door in Trace and regenerate,
    place something in another tab, Save All. The door was written over by the stale buffer."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    win._open_editor(_NAME, "field", "field")          # a form is mounted over the old buffer
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(0, False, str(toml))  # the job's clean finish, a REGENERATE
    assert [g["name"] for g in win._doc(_NAME).data["gateway"]] == ["traced_door0"]
    assert _NAME not in win._unsaved()                 # a reload is not an edit
    _place_an_npc(win)
    win._save_all()
    data = _disk(toml)
    assert [g["name"] for g in data["gateway"]] == ["traced_door0"]   # the regenerate survived
    assert len(data["npc"]) == 1                                       # and so did the new edit


def test_a_regenerate_that_wrote_the_file_but_reported_failure_still_reloads(win, tmp_path):
    """The job writes its files and THEN prints its report; a console that cannot encode a
    character in that report (review finding E10) makes a complete regenerate exit non-zero.
    Whether the file moved is the disk's to say, not the exit code's."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(1, False, str(toml))
    assert [g["name"] for g in win._doc(_NAME).data["gateway"]] == ["traced_door0"]


def test_a_regenerate_that_changed_nothing_keeps_the_buffer_and_its_history(win, tmp_path):
    """A failed job that wrote nothing — or a regenerate whose toml came out identical — is not
    a reason to throw the undo history away."""
    _photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _place_an_npc(win)
    win._save_all()
    buffer = win._doc(_NAME)
    steps = [r for r in win._undo_stack if r.member == _NAME]
    assert steps
    for code in (1, 0):
        win.trace_doc._after_generate(code, False, str(toml))
        assert win._doc(_NAME) is buffer
        assert [r for r in win._undo_stack if r.member == _NAME] == steps


def test_a_regenerate_of_a_file_that_is_not_open_changes_nothing_here(win, tmp_path):
    photo, toml = _project(tmp_path)
    (tmp_path / "other").mkdir()
    _photo2, other = _project(tmp_path / "other")
    assert win.open_field(other)
    before = win._doc(_NAME).data
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(0, False, str(toml))
    assert win._doc(_NAME).data is before              # another project's buffer is left alone
    assert win.member_paths[_NAME] == other.resolve()


def test_the_reload_drops_undo_steps_that_would_resurrect_the_old_file(win, tmp_path):
    """An undo snapshot is the WHOLE pre-regenerate document: Undo then Save All would write the
    old file back as surely as the stale buffer did."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _place_an_npc(win)
    win._save_all()
    assert any(r.member == _NAME for r in win._undo_stack)
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(0, False, str(toml))
    assert not any(r.member == _NAME for r in win._undo_stack)
    assert not any(r.member == _NAME for r in win._redo_stack)
    win._undo()                                        # nothing to undo: the buffer stays regenerated
    assert [g["name"] for g in win._doc(_NAME).data["gateway"]] == ["traced_door0"]
    assert len(win._doc(_NAME).data["npc"]) == 1       # the saved NPC is in the regenerated file


def test_the_reload_drops_places_cached_surface_of_that_project(win, tmp_path):
    """The Place tab caches a project's surface (camera + walkmesh + art) for the session and
    reads it from disk; after a regenerate that cache is the OLD floor."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    key = (("project", str(win.member_paths[_NAME])), 0)
    win.place_doc._bundles[key] = {"stale": True}
    win.place_doc._bundles[(("real", 351), 0)] = {"unrelated": True}
    _regenerate(photo, toml, floor=[(100.0, 220.0), (280.0, 220.0), (340.0, 430.0), (40.0, 430.0)])
    win.trace_doc._after_generate(0, False, str(toml))
    assert key not in win.place_doc._bundles
    assert (("real", 351), 0) in win.place_doc._bundles   # a donor room's surface is not this file's


# --------------------------------------------------------------- unsaved edits and the regenerate
def test_generate_is_refused_while_the_open_project_has_unsaved_edits(win, tmp_path, monkeypatch):
    """The regenerate merges from the file on DISK: unsaved edits would be left out of it, and
    the next save would then write them back over it. So it says so and starts nothing."""
    _photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    td = win.trace_doc
    td.load_project(toml)                              # armed: the next Generate goes in place
    run = _Run()
    monkeypatch.setattr(td, "_run", run)
    _place_an_npc(win)                                 # unsaved
    td.on_generate()
    assert run.calls == []
    assert "unsaved" in td.status.text() and "Save All" in td.status.text()
    win._save_all()
    td.on_generate()
    assert len(run.calls) == 1                         # saved -> it runs


def test_generate_is_not_held_up_by_unsaved_edits_in_another_project(win, tmp_path, monkeypatch):
    (tmp_path / "other").mkdir()
    _photo2, other = _project(tmp_path / "other")
    _photo, toml = _project(tmp_path)
    assert win.open_field(other)
    _place_an_npc(win)                                 # the OPEN project (not the traced one) is dirty
    td = win.trace_doc
    td.load_project(toml)
    run = _Run()
    monkeypatch.setattr(td, "_run", run)
    td.on_generate()
    assert len(run.calls) == 1


@pytest.mark.parametrize("take_disk", [True, False], ids=["reload", "keep-mine"])
def test_edits_made_while_the_job_ran_are_never_dropped_without_asking(win, tmp_path, monkeypatch,
                                                                       take_disk):
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _regenerate(photo, toml, gateways=[_DOOR])
    _place_an_npc(win)                                 # typed after the job launched
    asked = []
    monkeypatch.setattr(win, "_confirm", lambda title, text: asked.append(text) or take_disk)
    win.trace_doc._after_generate(0, False, str(toml))
    assert len(asked) == 1 and _NAME in asked[0]
    data = win._doc(_NAME).data
    if take_disk:
        assert [g["name"] for g in data["gateway"]] == ["traced_door0"] and "npc" not in data
        assert _NAME not in win._unsaved()
    else:
        assert len(data["npc"]) == 1 and "gateway" not in data     # theirs, untouched
        assert _NAME in win._unsaved()


# --------------------------------------------------------------- the adversarial pass over the fix
# Each of these is a way the first cut of the T38 fix could still lose work, found by reviewers
# told to break it (or a line of it that no test noticed being removed).

def _moved_floor():
    return [(100.0, 220.0), (280.0, 220.0), (340.0, 430.0), (40.0, 430.0)]


def test_the_reload_drops_redo_steps_too(win, tmp_path):
    """Edit then Undo: the buffer is clean again, and the edit waits on the REDO stack as a whole
    pre-regenerate document. A Redo after the reload would bring the old file back."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _place_an_npc(win)
    win._undo()
    assert any(r.member == _NAME for r in win._redo_stack) and _NAME not in win._dirty_members()
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(0, False, str(toml))
    assert not any(r.member == _NAME for r in win._redo_stack)
    win._redo()
    assert [g["name"] for g in win._doc(_NAME).data["gateway"]] == ["traced_door0"]
    assert "npc" not in win._doc(_NAME).data


def test_the_reload_rebuilds_the_form_that_was_mounted_over_the_old_buffer(win, tmp_path):
    """A single-section form resolves its target by NAME, so one left mounted over the old
    document would write its old values into the new one the next time it folded."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    win.tree.setCurrentItem(win._member_items[_NAME])
    win._open_editor(_NAME, "object", "player")
    old_ctx = win._save_ctx
    old_spawn = win._doc(_NAME).data["player"]["spawn"]
    _regenerate(photo, toml, floor=_moved_floor())
    win.trace_doc._after_generate(0, False, str(toml))
    new_spawn = _disk(toml)["player"]["spawn"]
    assert new_spawn != old_spawn                      # the premise: the regenerate moved it
    assert win._save_ctx is not old_ctx                # not the form built from the old rows
    win._save_all()                                    # nothing mounted can write the old spawn back
    assert _disk(toml)["player"]["spawn"] == new_spawn


def test_unsaved_edits_are_not_questioned_when_the_disk_did_not_move(win, tmp_path, monkeypatch):
    """'Did the file move' is judged against the last SAVE, not against the live buffer: a
    failed job that wrote nothing must not offer to drop the author's unsaved edits."""
    _photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _place_an_npc(win)                                 # unsaved; the disk is untouched
    asked = []
    monkeypatch.setattr(win, "_confirm", lambda title, text: asked.append(text) or True)
    win.trace_doc._after_generate(1, False, str(toml))
    assert asked == [] and len(win._doc(_NAME).data["npc"]) == 1


def test_text_typed_into_the_projects_form_counts_as_an_unsaved_edit(win, tmp_path, monkeypatch):
    """Typed but not yet folded: the refusal folds it first (as Save All does) and then sees it."""
    _photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    td = win.trace_doc
    td.load_project(toml)
    run = _Run()
    monkeypatch.setattr(td, "_run", run)
    win._open_editor(_NAME, "object", "player")
    win._save_ctx["getters"]["spawn"].__self__.setText("11, 22")
    td.on_generate()
    assert run.calls == [] and "unsaved" in td.status.text()
    assert win._doc(_NAME).data["player"]["spawn"] == [11, 22]     # folded, not thrown away


def test_another_fields_open_form_is_none_of_this_fields_business(win, tmp_path, monkeypatch):
    """The mounted form may belong to ANOTHER member. Folding it here blamed a clean field for
    that form's bad value, and a 'No' to the false question kept this field's stale buffer."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    win._open_editor(_NAME, "field", "field")
    win._save_ctx["member"] = "SOMEONE_ELSE"           # a form on a different member, mid-edit
    folds = []
    monkeypatch.setattr(win, "_commit_active_ck", lambda: folds.append(1) or False)
    asked = []
    monkeypatch.setattr(win, "_confirm", lambda title, text: asked.append(text) or False)
    assert win._trace_can_generate(str(toml)) is None and folds == []   # not folded, not blamed
    _regenerate(photo, toml, gateways=[_DOOR])
    win._trace_regenerated(str(toml))
    assert asked == []                                 # ...and no false "unsaved edits" question
    assert [g["name"] for g in win._doc(_NAME).data["gateway"]] == ["traced_door0"]


def test_a_field_touched_and_put_back_does_not_block_generate_forever(win, tmp_path, monkeypatch):
    """Touched-but-identical is not an unsaved edit: Save All writes only real differences, so a
    refusal that counted the touch could never be cleared."""
    _photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    win._touch(_NAME)
    assert _NAME in win._unsaved() and _NAME not in win._dirty_members()
    td = win.trace_doc
    td.load_project(toml)
    run = _Run()
    monkeypatch.setattr(td, "_run", run)
    td.on_generate()
    assert len(run.calls) == 1


def test_the_tabs_drop_the_old_floor_even_when_the_toml_came_out_identical(win, tmp_path):
    """The job replaces walkmesh.obj and the art beside the toml. Place's armed surface and the
    staging mesh are read from THOSE, so an unchanged toml is no reason to keep them."""
    from ff9mapkit.scene import guide
    _photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    win.tabs.setCurrentWidget(win.place_doc)
    pd = win.place_doc
    floor = [((-1000.0, 0.0, 500.0), (1000.0, 0.0, 500.0), (1000.0, 0.0, 2500.0))]
    bundle = {"donor": None, "source": pd._source, "cam_index": 0, "n_cams": 1,
              "cam": guide.make_camera(26.0, 3000.0, fov_x_deg=42.0), "png": None,
              "tris": floor, "floors": [0]}
    pd._bundles[(pd._source, 0)] = bundle
    pd._apply_bundle(bundle, refit=True)
    assert pd.canvas._surface_tris
    buffer = win._doc(_NAME)
    win.trace_doc._after_generate(0, False, str(toml))  # nothing in the toml moved
    assert win._doc(_NAME) is buffer                   # so the buffer stays...
    assert pd.canvas._surface_tris == [] and pd._bundles == {}   # ...and the old floor does not


def test_a_save_during_the_job_is_never_silently_the_winner(win, tmp_path, monkeypatch):
    """Nothing stops a Save All while the job runs. Whichever write landed last, the other is
    gone, and the two cases look identical afterwards -- so the window reloads what is on disk
    and SAYS the two raced, instead of quietly trusting either."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    assert win._trace_can_generate(str(toml)) is None   # the job is let go
    _place_an_npc(win)
    win._save_all()                                    # ...and a save lands while it runs
    said = []
    monkeypatch.setattr(win, "_show_problems", lambda verdict, problems: said.append(verdict))
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(0, False, str(toml))
    assert win._doc(_NAME).data == _disk(toml)         # the buffer is exactly the file
    assert any("saved while Trace was regenerating" in v.headline for v in said)


# --------------------------------------------------------------- the second adversarial pass
def test_an_unchanged_document_keeps_what_the_author_was_typing(win, tmp_path):
    """The first follow-up reset all three tabs on EVERY finish, so a failed job or an identical
    toml closed the Cutscene step editor and threw away the line being typed. When the document
    did not move, only what was read from the replaced walkmesh and art is dropped."""
    _photo, toml = _project(tmp_path)
    toml.write_text(toml.read_text(encoding="utf-8")
                    + '\n[cutscene]\nsteps = [ { say = "first" } ]\n', encoding="utf-8")
    assert win.open_field(toml)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    cd = win.cutscene_doc
    cd._edit_step(0)
    assert cd.editor.step_i == 0
    cd._wmesh = object()                               # a warm staging mesh, read from walkmesh.obj
    for code in (1, 0):
        win.trace_doc._after_generate(code, False, str(toml))
        assert cd.editor.step_i == 0                   # the open step editor is untouched ...
    assert cd._wmesh is None                           # ... and the old floor is not kept


def test_a_second_generate_click_does_not_lose_the_first_jobs_launch_record(win, tmp_path, monkeypatch):
    """Generate stays clickable while a job runs. The second click starts nothing, but it used to
    re-record the launch baseline AFTER a mid-job save, hiding the very race it exists to report."""
    from types import SimpleNamespace
    from PySide6.QtCore import QProcess
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    assert win._trace_can_generate(str(toml)) is None  # job 1 is let go
    _place_an_npc(win)
    win._save_all()                                    # a save lands while it runs ...
    monkeypatch.setattr(win, "proc", SimpleNamespace(state=lambda: QProcess.ProcessState.Running),
                        raising=False)
    assert win._trace_can_generate(str(toml)) is None  # ... and the author clicks Generate again
    monkeypatch.setattr(win, "proc", None, raising=False)
    said = []
    monkeypatch.setattr(win, "_show_problems", lambda verdict, problems: said.append(verdict))
    _regenerate(photo, toml, gateways=[_DOOR])
    win.trace_doc._after_generate(0, False, str(toml))
    assert any("saved while Trace was regenerating" in v.headline for v in said)


# ------------------------------------------------------------- Ctrl+Z on the Trace tab (T26)
def _trace_with_a_field_edit_behind_it(win, app, tmp_path):
    """An open field with one committed edit on the shell's stack, then the Trace tab with two
    vertices clicked -- the review's path: edit elsewhere, go to Trace, click a wrong vertex."""
    photo, toml = _project(tmp_path)
    assert win.open_field(toml)
    _place_an_npc(win)
    _place_an_npc(win)
    win._undo()                                        # one step on EACH stack: both must stay put
    assert win._undo_stack and win._redo_stack
    win.show()
    win.activateWindow()
    win.tabs.setCurrentWidget(win.trace_doc)
    td = win.trace_doc
    td.load_image(photo)
    td.canvas._commit_floor([(100, 300)])
    td.canvas._commit_floor([(100, 300), (280, 300)])
    td.canvas.setFocus()
    app.processEvents()
    return td


def test_ctrl_z_on_the_trace_tab_undoes_the_trace_not_another_tabs_edit(win, app, tmp_path):
    """Finding T26: a REAL Ctrl+Z (through the window's shortcut map) on the Trace canvas undid
    the open field's last edit and jumped to its tab, leaving the wrong vertex in place."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    td = _trace_with_a_field_edit_behind_it(win, app, tmp_path)
    stack, redo = list(win._undo_stack), list(win._redo_stack)
    npcs = len(win._doc(_NAME).data.get("npc") or [])
    QTest.keyClick(td.canvas, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    assert td._floor == [(100, 300)]                   # the trace gesture is taken back ...
    assert win.tabs.currentWidget() is td              # ... on the tab the author is looking at
    assert win._undo_stack == stack and win._redo_stack == redo
    assert len(win._doc(_NAME).data.get("npc") or []) == npcs   # the field edit is untouched
    QTest.keyClick(td.canvas, Qt.Key.Key_Z,
                   Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    app.processEvents()                                # Trace has no redo: nothing else moves
    assert td._floor == [(100, 300)] and win._undo_stack == stack and win._redo_stack == redo
    assert len(win._doc(_NAME).data.get("npc") or []) == npcs
    assert win.tabs.currentWidget() is td


def test_the_toolbar_undo_on_the_trace_tab_acts_on_the_trace(win, app, tmp_path):
    """The toolbar Undo is the same rule as the key, and says so: on Trace it names the trace,
    never the other tab's edit it would no longer touch."""
    td = _trace_with_a_field_edit_behind_it(win, app, tmp_path)
    stack = list(win._undo_stack)
    assert "trace" in win.act_undo.toolTip().lower() and win.act_undo.isEnabled()
    assert not win.act_redo.isEnabled()
    win.act_undo.trigger()
    win.act_redo.trigger()
    assert td._floor == [(100, 300)] and win._undo_stack == stack
    assert win.tabs.currentWidget() is td
    win.tabs.setCurrentWidget(win.doc_scroll)          # off Trace, the app-level labels come back
    assert win.act_undo.toolTip().startswith("Undo place NPC")


# ------------------------------------------------------------- the job pipe speaks UTF-8 (E10)
def _run_real_job(win, app, code):
    """A REAL run_job: a Python child through the shell's own QProcess, waited out."""
    import sys
    import time
    done = []
    assert win.run_job([sys.executable, "-c", code], subject="Pipe probe", on_finished=done.append)
    deadline = time.monotonic() + 60
    while not done and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert done, "the job never finished"
    return done[0]


def test_a_job_that_prints_beyond_cp1252_is_not_a_failure(win, app, monkeypatch):
    """Finding E10, every verb at once: the shell's child wrote its stdout in the locale codepage
    (cp1252 on a Western Windows -- forced here so a UTF-8 host reproduces it), so an arrow made
    a finished job exit 1, and a plain e-acute came back as a replacement mark because the shell
    decodes UTF-8. The child is told to write UTF-8, the encoding the shell reads."""
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    code = _run_real_job(win, app, "print('caf\\u00e9 \\u2192 north')")
    assert code == 0, win.output.toPlainText()[-400:]
    assert "café → north" in win.output.toPlainText()


def test_a_character_split_across_two_reads_is_not_mangled(win, app):
    """A pipe read can end inside a multi-byte character; decoding each read on its own turned
    one arrow into two replacement marks."""
    code = _run_real_job(win, app, (
        "import sys, time; o = sys.stdout.buffer; o.write(b'A \\xe2'); o.flush(); "
        "time.sleep(0.5); o.write(b'\\x86\\x92 B\\n'); o.flush()"))
    assert code == 0
    assert "A → B" in "".join(win._job_out)      # the verbatim record the failure anchor scans
    assert "→ B" in win.output.toPlainText() and "�" not in win.output.toPlainText()
