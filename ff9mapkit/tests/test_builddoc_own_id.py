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
    could undo a different id's later deploy.

    Driven against a SCRATCH repo root, never the developer's own: this used to plant a stub in the real
    checkout's tools/scroll_out (a test that reports on the machine it runs on), and that dir is now
    shared by every concurrent worktree, so the stub would race other sessions."""
    scroll = tmp_path / "tools" / "scroll_out"
    scroll.mkdir(parents=True)
    (scroll / "revert_deploy_4008.py").write_text("# test stub\n", encoding="utf-8")
    assert jobs.scroll_out_dir(tmp_path) == scroll, "a repo with no resolver must answer itself"
    assert jobs.revert_field_argv(tmp_path, 4008)[-1].endswith("revert_deploy_4008.py")
    # ...and an id with no script falls back to the latest-deploy revert
    assert jobs.revert_field_argv(tmp_path, 999999)[-1].endswith("revert_deploy.py")
    assert jobs.revert_field_argv(tmp_path)[-1].endswith("revert_deploy.py")


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

# ------------------------------------- the undo home is the MAIN repo, even launched from a worktree
# THE CALL-SITE LAW: jobs.scroll_out_dir / install_backups_dir exist and answer correctly (fenced in
# test_editor_jobs.py); these pin that the Build tab actually SPENDS them. Launched from an agent
# worktree the tab used to look in its own tools/scroll_out -- empty, because the deploy scripts write
# into the main repo -- so the "Deployed here" ledger listed no undo scripts and Revert missed every
# one, while Install-to-game parked the live install's ONLY backup in a tree that gets cleaned.


def _worktree_doc(app, monkeypatch, tmp_path):
    """A BuildDoc rooted at a REAL linked git worktree of a synthetic main repo. The install is pinned
    OUT (no read of the developer's game folder) and $FF9_REPO cleared, or resolve_dev_repo would
    redirect the doc at whatever checkout that names."""
    import shutil as sh, subprocess
    from ff9mapkit.workspace import builddoc
    resolver = _REPO / "tools" / "repo_root.py"
    if not resolver.is_file() or sh.which("git") is None:
        pytest.skip("needs git + the repo-only tools/repo_root.py")

    def git(*a, cwd):
        return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True)

    main = tmp_path / "main"; main.mkdir()
    if git("init", cwd=main).returncode:
        pytest.skip("git init failed in tmp_path")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-m", "i", cwd=main)
    wt = tmp_path / "wt"
    if git("worktree", "add", "--detach", str(wt), cwd=main).returncode:
        pytest.skip("git worktree add failed")
    for root in (main, wt):
        (root / "tools").mkdir()
        sh.copyfile(resolver, root / "tools" / "repo_root.py")
        (root / "tools" / "deploy_field.py").write_text("# stub\n", encoding="utf-8")
    if jobs.main_repo_root(wt) != main:
        pytest.skip("this git cannot answer --git-common-dir --path-format=absolute")
    monkeypatch.delenv("FF9_REPO", raising=False)
    monkeypatch.setattr(builddoc.jobs, "detect_game_mod", lambda: None)
    doc = BuildDoc(pick_palette("dark"), wt, run=lambda *a, **k: True, problems=lambda *a, **k: None)
    assert doc.repo == wt and doc.has_tools, "the doc must stay rooted at the checkout it was launched from"
    return doc, main, wt


def test_the_deployed_ledger_scans_the_main_repos_scroll_out(app, tmp_path, monkeypatch):
    from ff9mapkit.workspace import builddoc
    doc, main, wt = _worktree_doc(app, monkeypatch, tmp_path)
    seen = []
    monkeypatch.setattr(builddoc.jobs, "scan_deployed_reverts",
                        lambda dp, scroll: seen.append(scroll) or [])
    doc._refresh_deployed()
    assert seen and seen[-1] == main / "tools" / "scroll_out"
    assert seen[-1] != wt / "tools" / "scroll_out", "the ledger is reading the ephemeral worktree again"


def test_install_to_game_snapshots_into_the_main_repo(app, tmp_path, monkeypatch):
    """Hard-Constraint §2's backup of live install state must outlive the worktree that took it."""
    doc, main, wt = _worktree_doc(app, monkeypatch, tmp_path)
    backups, reverts = doc._revert_dirs()
    assert (backups, reverts) == (main / "backups", main / "tools" / "scroll_out")
    assert wt not in backups.parents and backups != wt / "backups"


def test_the_ledger_hint_never_points_at_a_disabled_revert(app, tmp_path, monkeypatch):
    """A hint that says "select one and Revert selected" while Revert is DISABLED is a dead instruction.
    Three situations (nothing registered / registered but no undo / some undo), three messages -- the
    no-undo one is what a worktree launch showed for every row before the scroll_out fix."""
    from ff9mapkit.workspace import builddoc
    doc = _doc(app)
    rows = {"none": [],
            "orphaned": [{"kind": "field", "id": "4003", "name": "T", "script": None, "mtime": None}],
            "mixed": [{"kind": "field", "id": "4003", "name": "T", "script": None, "mtime": None},
                      {"kind": "field", "id": "4100", "name": "B", "script": "x.py", "mtime": 1.0}]}
    seen = {}
    for state, rs in rows.items():
        monkeypatch.setattr(builddoc.jobs, "scan_deployed_reverts", lambda dp, s, _r=rs: _r)
        doc._refresh_deployed()
        seen[state] = doc.dep_hint.text()
        assert doc.dep_revert.isEnabled() == (state == "mixed")
        if not doc.dep_revert.isEnabled():
            assert "Revert selected" not in seen[state], \
                f"{state}: the hint sends the user to a button this method just disabled"
    assert "Revert selected" in seen["mixed"], "the reachable case must still teach the button"
    assert len(set(seen.values())) == 3, "each situation needs its own message, not a shared near-miss"
