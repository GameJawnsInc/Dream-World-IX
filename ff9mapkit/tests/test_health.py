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
