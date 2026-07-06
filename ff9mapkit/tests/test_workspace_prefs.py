"""GUI wiring for Preferences/About + the live theme switch. Headless (offscreen); no network, no modal
dialogs are opened (those .exec() — we drive the underlying state/handlers directly)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

import shutil                                         # noqa: E402
import subprocess                                      # noqa: E402

from PySide6.QtWidgets import (                         # noqa: E402
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox)

from ff9mapkit.editor import theme                    # noqa: E402
from ff9mapkit.editor.theme import pick_palette       # noqa: E402
from ff9mapkit.workspace import shell                 # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _win(app):
    return shell.Workspace(pick_palette("dark"))


def test_retheme_swaps_palette_for_every_theme(app):
    w = _win(app)
    for mode, pal in theme.THEMES.items():
        w.retheme(pick_palette(mode))
        assert w.pal is pal, mode
        # the global stylesheet tracks the new palette (its bg colour appears in the QSS)
        assert pal["bg"] in w.styleSheet(), mode


def test_retheme_retints_the_version_chip(app):
    w = _win(app)
    w.retheme(pick_palette("nord"))
    assert theme.NORD["muted"] in w.version_label.styleSheet()      # plain chip = muted, in the new palette
    # once an update is known, the chip goes accent — and a later retheme keeps it accent in the new palette
    w._on_update_result({"current": "0.0.0", "latest": "9.9.9", "ok": True, "newer": True}, manual=False)
    w.retheme(pick_palette("gruvbox-dark"))
    assert theme.GRUVBOX_DARK["accent"] in w.version_label.styleSheet()


def test_retheme_retints_persistent_chrome(app):
    # the inline-styled always-alive chrome (Info Hub button + breadcrumb bar) must follow a theme switch
    w = _win(app)
    w.retheme(pick_palette("gruvbox-dark"))
    assert theme.GRUVBOX_DARK["help"] in w._hub_btn.styleSheet()        # violet tint tracks pal['help']
    assert theme.GRUVBOX_DARK["surface"] in w.crumb.styleSheet()        # breadcrumb bar bg re-applied


def test_run_upgrade_without_uv_shows_manual_command(app, monkeypatch):
    # the path CI/non-Windows takes: no detached PowerShell spawn, just the manual command.
    w = _win(app)
    monkeypatch.setattr(shutil, "which", lambda _n: None)
    info, popen = [], []
    monkeypatch.setattr(shell.QMessageBox, "information", lambda *a, **k: info.append(a))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: popen.append(a))
    w._run_upgrade()
    assert info and not popen
    assert any(shell.update_check.UPGRADE_COMMAND in str(a) for a in info)


def test_run_upgrade_non_windows_shows_manual_command(app, monkeypatch):
    w = _win(app)
    monkeypatch.setattr(shutil, "which", lambda _n: "/usr/bin/uv")      # uv present...
    monkeypatch.setattr(shell.os, "name", "posix")                      # ...but not Windows
    info, popen = [], []
    monkeypatch.setattr(shell.QMessageBox, "information", lambda *a, **k: info.append(a))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: popen.append(a))
    w._run_upgrade()
    assert info and not popen


def test_preferences_cancel_reverts_live_preview(app, monkeypatch):
    w = _win(app)
    w.retheme(pick_palette("dark"))
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")           # combo opens on Dark
    monkeypatch.setattr(shell.prefs, "set_theme", lambda *_: None)

    def fake_exec(dlg):
        combo = dlg.findChild(QComboBox)
        combo.setCurrentIndex(combo.findData("gruvbox-dark"))           # live preview fires
        assert w.pal is theme.GRUVBOX_DARK                             # ...and is applied
        dlg.reject()                                                   # Cancel -> finished -> revert
        return 0

    monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
    w._open_preferences()
    assert w.pal is theme.DARK                                         # reverted to the pre-dialog palette


def test_preferences_ok_keeps_preview_and_persists(app, monkeypatch):
    w = _win(app)
    w.retheme(pick_palette("dark"))
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")
    saved = []
    monkeypatch.setattr(shell.prefs, "set_theme", lambda m: saved.append(m))
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: False)   # skip update-state write here

    def fake_exec(dlg):
        combo = dlg.findChild(QComboBox)
        combo.setCurrentIndex(combo.findData("gruvbox-dark"))
        dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
        return 1

    monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
    w._open_preferences()
    assert w.pal is theme.GRUVBOX_DARK                                 # kept (not reverted)
    assert saved == ["gruvbox-dark"]                                   # persisted


def test_preferences_writes_update_optin_only_when_installed(app, monkeypatch):
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")
    monkeypatch.setattr(shell.prefs, "set_theme", lambda *_: None)
    monkeypatch.setattr(shell.update_check, "is_enabled", lambda: False)

    def run_ok(installed):
        w = _win(app)
        monkeypatch.setattr(shell.update_check, "is_installed", lambda: installed)
        calls = []
        monkeypatch.setattr(shell.update_check, "set_preference", lambda v: calls.append(v))

        def fake_exec(dlg):
            chk = dlg.findChild(QCheckBox)               # only present on an installed copy
            if chk is not None:
                chk.setChecked(True)
            dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            return 1

        monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
        w._open_preferences()
        return calls

    assert run_ok(True) == [True]      # installed copy persists the opt-in
    assert run_ok(False) == []         # source checkout never writes update-check state


def test_preferences_update_toggle_only_on_installed(app, monkeypatch):
    # installed -> a real clickable checkbox; source checkout -> NO dead/disabled checkbox (a note instead)
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")
    seen = {}

    def fake_exec(dlg):
        seen["chk"] = dlg.findChild(QCheckBox)
        dlg.reject()
        return 0

    monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: True)
    _win(app)._open_preferences()
    assert seen["chk"] is not None
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: False)
    _win(app)._open_preferences()
    assert seen["chk"] is None


def test_upgrade_ps1_is_parameterized():
    # the detached helper takes its inputs as params (no interpolation) and uses each one.
    ps1 = shell._UPGRADE_PS1
    assert "param([int]$AppPid, [string]$Uv, [string]$Launcher)" in ps1
    assert "Wait-Process -Id $AppPid" in ps1       # waits on the app PID (lock-safety)
    assert "$Uv tool upgrade ff9mapkit" in ps1     # upgrades via the passed uv path
    assert "Start-Process $Launcher" in ps1        # relaunches the passed launcher


def test_settings_menu_and_palette_commands_exist(app):
    w = _win(app)
    assert w._settings_btn is not None
    labels = {c[0] for c in w._command_index()}
    assert {"Preferences…", "About Dream World IX", "Check for updates…"} <= labels


def test_startup_uses_the_saved_theme(app, monkeypatch):
    # main() resolves the palette from prefs.theme(); a saved "nord" must drive the window's palette.
    monkeypatch.setattr(shell.prefs, "theme", lambda: "nord")
    monkeypatch.setattr(shell.update_check, "auto_check_allowed", lambda: False)   # no network/prompt
    monkeypatch.setattr(shell.sys, "exit", lambda *_a, **_k: None)                 # don't kill the test run
    monkeypatch.setattr(shell.QApplication, "exec", lambda *_a, **_k: 0)
    created = {}
    real_init = shell.Workspace.__init__

    def _spy(self, pal):
        created["pal"] = pal
        real_init(self, pal)

    monkeypatch.setattr(shell.Workspace, "__init__", _spy)
    monkeypatch.setattr(shell.Workspace, "show", lambda self: None)
    shell.main(["ff9_workspace"])
    assert created["pal"] is theme.NORD


# ---- recent projects (MRU) — prefs-level, no Qt needed beyond the module import above ----

@pytest.fixture()
def prefs_file(tmp_path, monkeypatch):
    """Point the prefs store at a throwaway file so MRU tests never touch the real prefs.json."""
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    return prefs


def test_recent_round_trip_dedupes_and_caps(prefs_file, tmp_path):
    p = prefs_file
    for i in range(p.RECENT_LIMIT + 3):
        p.add_recent("field", tmp_path / f"f{i}.field.toml")
    rows = p.recent()
    assert len(rows) == p.RECENT_LIMIT                       # capped
    assert rows[0]["path"].endswith(f"f{p.RECENT_LIMIT + 2}.field.toml")   # most recent first
    p.add_recent("field", tmp_path / f"f{p.RECENT_LIMIT}.field.toml")      # re-open -> moves to front, no dup
    rows = p.recent()
    assert rows[0]["path"].endswith(f"f{p.RECENT_LIMIT}.field.toml")
    assert len({e["path"] for e in rows}) == len(rows)


def test_recent_survives_garbage_and_unknown_kinds(prefs_file, tmp_path):
    p = prefs_file
    p.add_recent("overworld", tmp_path / "nope.toml")        # unknown kind -> ignored
    assert p.recent() == []
    (tmp_path / "prefs.json").write_text(
        '{"recent": ["junk", {"kind": "field"}, {"kind": "campaign", "path": "C:/x/campaign.toml"},'
        ' {"kind": "field", "path": 7}], "theme": "dark"}', encoding="utf-8")
    rows = p.recent()                                        # only the one well-formed entry survives
    assert rows == [{"kind": "campaign", "path": "C:/x/campaign.toml"}]
    assert p.theme() == "dark"                               # unrelated keys untouched


def test_remove_recent(prefs_file, tmp_path):
    p = prefs_file
    p.add_recent("save", tmp_path / "SavedData_ww.dat")
    p.add_recent("journey", tmp_path / "journeys.toml")
    gone = p.recent()[1]["path"]
    p.remove_recent(gone)
    assert [e["kind"] for e in p.recent()] == ["journey"]
