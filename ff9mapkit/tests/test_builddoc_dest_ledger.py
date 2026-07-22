"""Build & Deploy: the remembered destination choice + the 'Deployed here' ledger.

Two Workspace-UX build items live here:
  * the destination radio is PERSISTED across sessions (the squeeze law -- only a radio the USER clicked is
    a preference; a programmatic fallback / restore is not), and
  * a 'Deployed here' ledger lists every field registered in the reversible test mod folder paired with its
    per-id undo script, with a confirm-first per-entry revert.

Headless (offscreen). Drives the real BuildDoc. Every test pins prefs._path (THE RECURRING DISEASE: a test
that touches prefs must never read or write the developer's real prefs.json) -- function-scoped, for the
whole fixture life.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt                           # noqa: E402
from PySide6.QtWidgets import QApplication             # noqa: E402

from ff9mapkit import prefs                             # noqa: E402
from ff9mapkit.editor import jobs                       # noqa: E402
from ff9mapkit.editor.theme import pick_palette         # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc       # noqa: E402

_REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def isolated_prefs(tmp_path, monkeypatch):
    """Pin prefs._path at a throwaway file for the WHOLE test -- BuildDoc reads/writes deploy_dest, so it
    must never touch the real prefs.json. Function-scoped on purpose (a module-scoped pin would be finalized
    AFTER function-scoped monkeypatches and leak)."""
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    return prefs


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


# ---------------------------------------------------------------- destination persistence (the squeeze law)
def test_a_user_click_on_a_destination_persists(app, isolated_prefs, tmp_path):
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    doc.path.setText(str(_field(tmp_path)))
    doc.rb_own.setChecked(True)                          # a user picking the own-id destination
    assert isolated_prefs.deploy_dest() == "own", "a clicked destination was not remembered"


def test_a_forced_fallback_is_not_a_preference(app, isolated_prefs, tmp_path):
    """A value computed under duress is not a value the user chose: when own-id becomes unusable the radio
    is force-moved to the test slot, and that MUST NOT overwrite the saved 'own'."""
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    doc.path.setText(str(_field(tmp_path, fid=4008)))
    doc.rb_own.setChecked(True)                          # a real pick -> persisted
    assert isolated_prefs.deploy_dest() == "own"
    bad = tmp_path / "B.field.toml"
    bad.write_text('[field]\nname = "NOID"\narea = 11\n', encoding="utf-8")
    doc.path.setText(str(bad))                           # own-id unusable -> forced fallback off rb_own
    assert not doc.rb_own.isChecked()
    assert isolated_prefs.deploy_dest() == "own", "a forced fallback clobbered the saved preference"


def test_the_saved_destination_is_restored_on_a_field_load(app, isolated_prefs, tmp_path):
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    isolated_prefs.set_deploy_dest("own")               # the veteran's workflow, saved last session
    doc.path.setText(str(_field(tmp_path)))             # a field with a known id -> own-id is legal
    assert doc.rb_own.isChecked(), "the saved own-id destination was not restored on load"


def test_a_disabled_saved_mode_falls_back_legally(app, isolated_prefs, tmp_path, monkeypatch):
    """When the saved mode's radio is not legal (e.g. an installed copy where the test slot is disabled),
    restore leaves the current default in place rather than checking a dead radio."""
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    doc.path.setText(str(_field(tmp_path)))
    isolated_prefs.set_deploy_dest("own")
    doc.rb_own.setEnabled(False)                         # simulate the mode being unavailable this session
    doc.rb_test.setChecked(True)
    doc._apply_saved_dest()
    assert not doc.rb_own.isChecked() and doc.rb_test.isChecked(), "restore checked an illegal radio"


def test_inplace_autoselect_beats_the_saved_destination(app, isolated_prefs, tmp_path):
    """In-place is donor-driven and auto-selects for a verbatim fork of a real field; the saved mode must
    not override that route (and prefs never stores 'inplace' in the first place)."""
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    isolated_prefs.set_deploy_dest("own")
    p = tmp_path / "V.field.toml"
    p.write_text('[field]\nid = 4100\nname = "VFORK"\narea = 11\n\n[verbatim_eb]\ndonor = 100\n',
                 encoding="utf-8")
    doc.path.setText(str(p))
    assert doc.rb_inplace.isChecked(), "In-place did not auto-select for a verbatim fork of a real field"
    assert not doc.rb_own.isChecked(), "the saved 'own' overrode the donor-driven In-place route"
    assert isolated_prefs.deploy_dest() == "own", "auto-selecting In-place must not persist as a preference"


# ------------------------------------------------------------------------------- the 'Deployed here' ledger
def test_the_ledger_marks_scriptless_rows_read_only(app, isolated_prefs, tmp_path, monkeypatch):
    doc = _doc(app)
    rows = [
        {"kind": "field", "id": "4003", "name": "TESTROOM", "script": None, "mtime": None},
        {"kind": "field", "id": "4100", "name": "MYFORK", "script": str(tmp_path / "r.py"), "mtime": 1.0},
        {"kind": "campaign", "id": None, "name": "campaign deploy",
         "script": str(tmp_path / "c.py"), "mtime": 2.0},
    ]
    monkeypatch.setattr(jobs, "scan_deployed_reverts", lambda *a: rows)
    doc._refresh_deployed()
    assert doc.dep_list.count() == 3
    it0 = doc.dep_list.item(0)
    assert not (it0.flags() & Qt.ItemFlag.ItemIsSelectable), "a scriptless row must be read-only informational"
    assert "no undo script" in it0.text()
    assert doc.dep_list.item(1).flags() & Qt.ItemFlag.ItemIsSelectable
    assert doc.dep_revert.isEnabled(), "with revertable rows present, Revert selected must be live"


def test_the_ledger_disables_revert_when_nothing_is_undoable(app, isolated_prefs, tmp_path, monkeypatch):
    doc = _doc(app)
    rows = [{"kind": "field", "id": "4003", "name": "TESTROOM", "script": None, "mtime": None}]
    monkeypatch.setattr(jobs, "scan_deployed_reverts", lambda *a: rows)
    doc._refresh_deployed()
    assert not doc.dep_revert.isEnabled(), "no undo script anywhere -> Revert selected must be disabled"


def test_revert_selected_runs_that_entrys_script(app, isolated_prefs, tmp_path, monkeypatch):
    doc = _doc(app)
    script = tmp_path / "revert_deploy_4100.py"
    script.write_text("# undo\n", encoding="utf-8")
    rows = [{"kind": "field", "id": "4100", "name": "MYFORK", "script": str(script), "mtime": 1.0}]
    monkeypatch.setattr(jobs, "scan_deployed_reverts", lambda *a: rows)
    doc._refresh_deployed()
    doc.dep_list.setCurrentRow(0)
    doc.on_deployed_revert()
    argv = [str(x) for x in doc._calls[-1][0]]
    assert str(script) in argv, "Revert selected did not run the entry's own undo script"


def test_revert_with_nothing_selected_warns(app, isolated_prefs, monkeypatch):
    doc = _doc(app)
    monkeypatch.setattr(jobs, "scan_deployed_reverts", lambda *a: [])
    doc._refresh_deployed()
    warned = []
    doc._warn = lambda *a, **k: warned.append(a)
    doc.on_deployed_revert()
    assert warned, "reverting with no selection must warn, not run a script"
    assert not doc._calls, "nothing should have been run"
