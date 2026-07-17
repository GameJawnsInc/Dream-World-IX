"""TuningDialog (workspace/tuningdialog.py): a malformed ``[journey.tuning.<block>]`` entry (a bare value
coerced by ``journey._tuning_from`` into a 1-element non-dict list, instead of an array-of-tables) must be
preserved verbatim through the OK path, not silently dropped.

Headless (offscreen).
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication          # noqa: E402

from ff9mapkit.editor.theme import pick_palette     # noqa: E402
from ff9mapkit.workspace.tuningdialog import TuningDialog   # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_malformed_block_survives_ok_untouched(app):
    # "character" is malformed (a bare str, not a list-of-tables); "status" is well-formed.
    tuning = {"character": ["Vivi"], "status": [{"status": "Poison"}]}
    dlg = TuningDialog(None, pick_palette("dark"), "j1", tuning)
    assert dlg._malformed == ["character"]
    assert "character" not in dlg.tuning              # not offered to the form
    assert dlg._untouched["character"] == ["Vivi"]     # carried verbatim
    dlg._accept()
    assert dlg.result_tuning["character"] == ["Vivi"]  # OK did not drop it
    assert dlg.result_tuning["status"] == [{"status": "Poison"}]


def test_malformed_block_shows_a_warning(app):
    dlg = TuningDialog(None, pick_palette("dark"), "j1", {"character": ["Vivi"]})
    from PySide6.QtWidgets import QLabel
    texts = [w.text() for w in dlg.findChildren(QLabel)]
    assert any("character" in t.lower() and "left as-is" in t for t in texts)


def test_well_formed_tuning_is_unaffected(app):
    tuning = {"status": [{"status": "Poison"}]}
    dlg = TuningDialog(None, pick_palette("dark"), "j1", tuning)
    assert dlg._malformed == []
    assert dlg.tuning["status"] == tuning["status"]
    dlg._accept()
    assert dlg.result_tuning == tuning
