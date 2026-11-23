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
