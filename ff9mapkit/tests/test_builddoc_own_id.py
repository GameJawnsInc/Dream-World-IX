"""The Build & Deploy tab's OWN-ID deploy option -- reversible, at the id the field declares.

The gap it fills (and the incident that motivated it, 2026-07-18): the other three modes are donor-id +
reversible (in-place), test-slot + reversible (overrides the id), and own-id + a wholesale `build` with
NO undo ("Install to game"). A user wanting "deploy this at its own id" reached for the install, which
rewrote the shared folder's whole DictionaryPatch and silently unregistered every other field. This mode
is own-id AND reversible: it shells out to tools/deploy_field.py, which merges the DictionaryPatch and
writes a per-id revert script.

Headless (offscreen). Drives the real BuildDoc.
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

_REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _doc(app):
    calls = []
    doc = BuildDoc(pick_palette("dark"), _REPO,
                   run=lambda argv, **kw: calls.append((argv, kw)) or True,
                   problems=lambda *a, **k: None)
    doc._confirm = lambda *a, **k: True
    doc._calls = calls
    return doc


def _field(tmp, fid=4008, name="AC_FTI"):
    p = tmp / "F.field.toml"
    p.write_text(f'[field]\nid = {fid}\nname = "{name}"\narea = 11\ntext_block = 88\n', encoding="utf-8")
    return p


def test_own_id_option_labels_itself_with_the_declared_id(app, tmp_path):
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    doc.path.setText(str(_field(tmp_path)))
    assert doc.rb_own.isEnabled() and "4008" in doc.rb_own.text()
    assert "reversible" in doc.rb_own.text().lower()


def test_own_id_deploy_runs_deploy_field_with_id_and_name(app, tmp_path):
    """The --name matters: without it deploy_field sandboxes the name to TEST<id>, which is right for a
    throwaway slot and wrong for a field installed under its own identity."""
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    p = _field(tmp_path)
    doc.path.setText(str(p))
    doc.rb_own.setChecked(True)
    assert "4008" in doc.dest.text() and "reversible" in doc.dest.text()
    assert doc.rev.isEnabled(), "an own-id deploy has an undo"
    doc._go_field(str(p))
    argv = " ".join(str(x) for x in doc._calls[-1][0])
    assert "deploy_field.py" in argv
    assert "--id 4008" in argv and "--name AC_FTI" in argv
    assert "build" not in argv.split("deploy_field.py")[-1]      # a DEPLOY, not a build


def test_own_id_disabled_without_a_readable_id(app, tmp_path):
    """An unknown id would deploy nowhere meaningful -- the option must not be selectable, and must not
    strand the selection if it was already checked."""
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    doc.path.setText(str(_field(tmp_path)))
    doc.rb_own.setChecked(True)
    bad = tmp_path / "B.field.toml"
    bad.write_text('[field]\nname = "NOID"\narea = 11\n', encoding="utf-8")
    doc.path.setText(str(bad))
    assert not doc.rb_own.isEnabled() and not doc.rb_own.isChecked()
    assert doc.rb_test.isChecked() or doc.rb_game.isChecked() or doc.rb_other.isChecked()


def test_own_id_revert_targets_that_id(app, tmp_path):
    """Revert must use the per-id script, not the generic 'latest' one -- otherwise reverting field 4008
    could undo a different id's later deploy."""
    scroll = _REPO / "tools" / "scroll_out"
    if not scroll.is_dir():
        pytest.skip("no scroll_out in this checkout")
    per_id = scroll / "revert_deploy_4008.py"
    made = not per_id.exists()
    if made:
        per_id.write_text("# test stub\n", encoding="utf-8")
    try:
        argv = jobs.revert_field_argv(_REPO, 4008)
        assert argv[-1].endswith("revert_deploy_4008.py")
        # ...and an id with no script falls back to the latest-deploy revert
        assert jobs.revert_field_argv(_REPO, 999999)[-1].endswith("revert_deploy.py")
        assert jobs.revert_field_argv(_REPO)[-1].endswith("revert_deploy.py")
    finally:
        if made:
            per_id.unlink()


def test_install_to_game_preserves_other_fields(app, tmp_path, monkeypatch):
    """The mode that caused the incident now passes --preserve-existing, so installing one field leaves
    the folder's other fields registered -- AND it honours the §2 backup law: the whole mod folder is
    snapshotted before the write (jobs.snapshot_mod_folder stubbed here so the test never copies the real
    live folder). The stub returns a path -> Install-to-game reports itself reversible."""
    from ff9mapkit.workspace import builddoc
    snapped = []
    monkeypatch.setattr(builddoc.jobs, "snapshot_mod_folder",
                        lambda mod, b, r: snapped.append(mod) or (tmp_path / "revert_install.py"))
    doc = _doc(app)
    p = _field(tmp_path)
    doc.path.setText(str(p))
    if not doc.game_mod:
        pytest.skip("no game install detected")
    doc.rb_game.setChecked(True)
    # the dest line + Revert now read as reversible (checked BEFORE the deploy: _busy disables rev while a
    # job streams, and the stub `run` never fires on_finished to re-enable it)
    assert doc.rev.isEnabled() and "no undo" not in doc.dest.text().lower()
    doc._go_field(str(p))
    argv = " ".join(str(x) for x in doc._calls[-1][0])
    assert "--preserve-existing" in argv
    assert snapped == [doc.game_mod], "Install-to-game must snapshot the mod folder before the write (§2)"
