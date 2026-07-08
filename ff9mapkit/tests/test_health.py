"""The Setup & Health engine: pure, never-raises report rows + the cheap Home-banner summary.
Qt-free (health.py is importable headless); the dialog itself gets one offscreen construction test."""

import os

import pytest

from ff9mapkit import config, health, provision


def test_report_unconfigured_is_bad_but_never_raises(monkeypatch):
    def boom():
        raise config.ConfigError("no install")
    monkeypatch.setattr(config, "find_game_path", boom)
    rows = health.health_report()
    assert health.worst_level(rows) == "bad"
    row = next(r for r in rows if r["label"] == "FF9 install")
    assert row["level"] == "bad" and "Locate game" in row["advice"]
    assert health.quick_issues() == ["FF9 install not configured"]


def test_report_fake_install_flags_missing_pieces(monkeypatch, tmp_path):
    (tmp_path / "StreamingAssets").mkdir()             # a folder that half-looks like FF9
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    rows = health.health_report()
    launcher = next(r for r in rows if r["label"] == "FF9_Launcher.exe")
    sa = next(r for r in rows if r["label"] == "StreamingAssets")
    assert launcher["level"] == "bad" and sa["level"] == "ok"


def test_quick_issues_reports_missing_templates(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    monkeypatch.setattr(provision, "templates_present", lambda: False)
    assert health.quick_issues() == ["base templates not extracted"]
    monkeypatch.setattr(provision, "templates_present", lambda: True)
    assert health.quick_issues() == []


def test_health_flags_scripts_dll_engine_drift(monkeypatch, tmp_path):
    """A live custom battle-formula DLL built against a different engine surfaces as a WARN row (the drift
    detector after a Memoria update); a matching one is a plain OK row naming the engine it was built against."""
    (tmp_path / "StreamingAssets").mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    layout = config.ModLayout(tmp_path / "FF9CustomMap")
    dll = layout.scripts_dll("FF9CustomMap")
    dll.parent.mkdir(parents=True, exist_ok=True)
    dll.write_bytes(b"MZ")

    from ff9mapkit.battle import scriptcompile
    monkeypatch.setattr(scriptcompile, "read_engine_stamp", lambda d: {"engine_file_version": "1.1.1.1"})
    monkeypatch.setattr(scriptcompile, "engine_drift_warning",
                        lambda d, game=None: "built against 1.1.1.1, installed is 1.1.2.2")
    row = next(r for r in health.health_report() if r["label"] == "Custom battle formula DLL")
    assert row["level"] == "warn" and "1.1.1.1" in row["advice"]

    monkeypatch.setattr(scriptcompile, "engine_drift_warning", lambda d, game=None: None)
    row = next(r for r in health.health_report() if r["label"] == "Custom battle formula DLL")
    assert row["level"] == "ok" and "1.1.1.1" in row["value"]


def test_health_no_scripts_dll_row_when_absent(monkeypatch, tmp_path):
    """No custom battle-formula DLL deployed -> no drift row at all (don't clutter installs without one)."""
    (tmp_path / "StreamingAssets").mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    labels = {r["label"] for r in health.health_report()}
    assert "Custom battle formula DLL" not in labels


def test_worst_level_ordering():
    assert health.worst_level([{"level": "ok"}]) == "ok"
    assert health.worst_level([{"level": "ok"}, {"level": "warn"}]) == "warn"
    assert health.worst_level([{"level": "warn"}, {"level": "bad"}]) == "bad"


def test_setup_dialog_constructs_offscreen(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.setupdialog import SetupHealthDialog
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    dlg = SetupHealthDialog(None, pick_palette("dark"), kit_cwd=tmp_path)
    assert dlg._worst in ("ok", "warn", "bad")         # the report rendered
    dlg.refresh()                                      # re-render is safe (grid rebuild)


def test_setup_dialog_refresh_never_stacks_grids(monkeypatch, tmp_path):
    """The doubled-report regression: refresh() before exec() queues the old grid's deferred delete
    OUTSIDE the dialog's nested event loop, so it must be DETACHED immediately — WITHOUT processing
    any deferred deletes, exactly one grid may be parented to the host."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QWidget
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.setupdialog import SetupHealthDialog
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    dlg = SetupHealthDialog(None, pick_palette("dark"), kit_cwd=tmp_path)
    dlg.refresh()                                      # the _open_setup-before-exec() sequence
    dlg.refresh()
    kids = [c for c in dlg.grid_host.findChildren(QWidget) if c.parent() is dlg.grid_host]
    assert len(kids) == 1, f"stale report grids still parented: {len(kids)}"
