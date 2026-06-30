"""GUI wiring for the opt-in update check: the status-bar version chip + the result handler.

Skips cleanly without PySide6 (the optional `gui` extra). Headless (offscreen); never touches the network
(the result handler is driven with canned dicts) and never opens the modal dialog/prompt."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication            # noqa: E402

from ff9mapkit import __version__                     # noqa: E402
from ff9mapkit.editor.theme import pick_palette       # noqa: E402
from ff9mapkit.workspace import shell                 # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _win(app):
    return shell.Workspace(pick_palette("dark"))


def test_version_chip_shows_running_version(app):
    w = _win(app)
    assert f"v{__version__}" in w.version_label.text()
    assert w._update_result is None                    # no check has run


def test_newer_result_lights_the_chip(app):
    w = _win(app)
    w._on_update_result({"current": __version__, "latest": "9.9.9", "ok": True, "newer": True}, manual=False)
    assert "update" in w.version_label.text().lower()  # chip changed to signal an update
    assert "9.9.9" in w.version_label.toolTip()
    assert w._update_result["latest"] == "9.9.9"


def test_uptodate_result_leaves_chip_plain(app):
    w = _win(app)
    w._on_update_result({"current": __version__, "latest": __version__, "ok": True, "newer": False}, manual=False)
    assert w.version_label.text() == f"v{__version__}"


def test_offline_result_leaves_chip_plain(app):
    w = _win(app)
    w._on_update_result({"current": __version__, "latest": None, "ok": False, "newer": False}, manual=False)
    assert w.version_label.text() == f"v{__version__}"
