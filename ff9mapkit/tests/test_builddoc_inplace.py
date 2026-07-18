"""The Build & Deploy tab's IN-PLACE deploy option (a verbatim fork of a real field deploys under the
donor's own id, keeping its HUD/entry -- e.g. a Chocobo forest fork on 2950/2951/2952).

Headless (offscreen). Drives the real BuildDoc: loading a fork of a real field shows + defaults the
In-place radio with the donor id + text block, and Build/Deploy runs the in-place argv; a novel field or
a fork of a custom id hides it.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication          # noqa: E402

from ff9mapkit.editor import jobs                   # noqa: E402
from ff9mapkit.editor.theme import pick_palette     # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc   # noqa: E402

_REPO = Path(__file__).resolve().parents[2]         # the worktree root (has tools/deploy_field.py)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _doc(app):
    calls = []
    doc = BuildDoc(pick_palette("dark"), _REPO,
                   run=lambda argv, **kw: calls.append((argv, kw)) or True,
                   problems=lambda *a, **k: None)
    doc._confirm = lambda *a, **k: True             # auto-accept the modal confirm
    doc._calls = calls
    return doc


def _write(tmp, body):
    p = tmp / "F.field.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_inplace_shown_and_defaulted_for_a_forest_fork(app, tmp_path):
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    p = _write(tmp_path, '[field]\nid = 4003\nname = "CHFORK"\narea = 14\n'
                         'text_block = 1073\n\n[verbatim_eb]\nbin = "x.bin"\ndonor = 2952\n')
    doc.path.setText(str(p))                          # triggers _on_path -> _sync_inplace
    assert doc.inplace_target == {"donor": 2952, "name": "CHFORK", "text_block": 945, "is_forest": True}
    assert doc._inplace_available and doc.rb_inplace.isChecked(), "in-place shown + defaulted"
    assert "2952" in doc.rb_inplace.text() and "HUD" in doc.rb_inplace.text()
    assert "in place" in doc.dest.text().lower() and "2952" in doc.dest.text()

    doc._go_field(str(p))                             # Build/Deploy with in-place selected
    assert doc._calls, "a deploy job was started"
    argv = doc._calls[-1][0]
    assert "--id" in argv and "2952" in argv and "--text-block" in argv and "945" in argv
    assert "deploy_field.py" in " ".join(argv)


def test_inplace_shown_for_a_non_forest_fork_without_hud_note(app, tmp_path):
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    p = _write(tmp_path, '[field]\nid = 4010\nname = "INNFORK"\narea = 11\n\n'
                         '[verbatim_eb]\nbin = "x.bin"\ndonor = 351\n')       # Dali Inn -> text block 47
    doc.path.setText(str(p))
    assert doc.inplace_target["donor"] == 351 and doc.inplace_target["text_block"] == 47
    assert doc._inplace_available and doc.rb_inplace.isChecked()
    assert "HUD" not in doc.rb_inplace.text() or "Chocobo" not in doc.rb_inplace.text()


def test_inplace_hidden_for_a_novel_field(app, tmp_path):
    doc = _doc(app)
    p = _write(tmp_path, '[field]\nid = 4020\nname = "NOVEL"\narea = 11\n')
    doc.path.setText(str(p))
    assert doc.inplace_target is None
    assert not doc._inplace_available
    assert not doc.rb_inplace.isChecked(), "a hidden in-place radio must not stay the checked option"


def test_inplace_hidden_for_a_fork_of_a_custom_id(app, tmp_path):
    doc = _doc(app)
    p = _write(tmp_path, '[field]\nid = 4030\nname = "F"\narea = 11\n\n'
                         '[verbatim_eb]\nbin = "x.bin"\ndonor = 5000\n')       # a custom-slot donor
    doc.path.setText(str(p))
    assert doc.inplace_target is None and not doc._inplace_available


def test_refresh_picks_up_an_edit_and_save_without_re_browsing(app, tmp_path):
    # Same bug the shell hits: the Author form edits + saves the SAME path (`self.path` text never
    # changes, so `_on_path`'s textChanged trigger never fires) -- `refresh()` is the shell's fix,
    # called on every Build & Deploy tab-show.
    doc = _doc(app)
    p = _write(tmp_path, '[field]\nid = 4006\nname = "AC_FTI"\narea = 11\n')
    doc.path.setText(str(p))
    assert doc.field_id == 4006 and doc.field_name == "AC_FTI"
    assert "4006" in doc.status.text()
    p.write_text('[field]\nid = 7006\nname = "AC_FTI"\narea = 11\n', encoding="utf-8")   # id bumped on disk
    assert doc.field_id == 4006, "unchanged before refresh -- same path text never re-triggers _on_path"
    doc.refresh()
    assert doc.field_id == 7006 and "7006" in doc.status.text(), "refresh() re-reads the same path from disk"


def test_refresh_does_not_clobber_a_manual_deploy_target_pick(app, tmp_path):
    # _sync_inplace used to force-check In-place on EVERY render; refresh() now runs on every tab-show,
    # so that would have silently reverted a deliberate "Install to game" pick back to In-place each time
    # the user merely revisited the Build & Deploy tab (the donor doesn't change across the edit).
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    p = _write(tmp_path, '[field]\nid = 4006\nname = "AC_FTI"\narea = 11\n\n'
                         '[verbatim_eb]\nbin = "x.bin"\ndonor = 1807\n')
    doc.path.setText(str(p))
    assert doc.rb_inplace.isChecked(), "defaults to In-place for a verbatim fork"
    doc.rb_game.setChecked(True)                       # the user manually picks Install to game
    assert not doc.rb_inplace.isChecked()
    p.write_text('[field]\nid = 7006\nname = "AC_FTI"\narea = 11\n\n'
                '[verbatim_eb]\nbin = "x.bin"\ndonor = 1807\n', encoding="utf-8")   # id edited, same donor
    doc.refresh()
    assert doc.field_id == 7006, "the id edit is still picked up"
    assert doc.rb_game.isChecked() and not doc.rb_inplace.isChecked(), \
        "a manual pick survives a refresh of the same donor"
