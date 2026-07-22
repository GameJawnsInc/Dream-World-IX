"""UX wave: the Import tab's Walk-as disclosure + pick-and-fill for real FF9 fields.

Two items, sharing the picker: (1) the player-swap row folds behind a collapsed disclosure with a
comes-back rule; (2) Find… and 'Suggest a test room…' become interactive CatalogPickers (the new
``realfield`` Info-Hub kind) that fill the source id, instead of console dumps."""
import pytest
from types import SimpleNamespace

pytest.importorskip("PySide6")

from pathlib import Path                                              # noqa: E402

from PySide6.QtWidgets import (QApplication, QComboBox, QDialog,      # noqa: E402
                               QCheckBox, QPushButton)

from ff9mapkit import infohub                                        # noqa: E402
from ff9mapkit.workspace import forms_qt, widgets                    # noqa: E402
from ff9mapkit.workspace.importdoc import ImportDoc                  # noqa: E402
from ff9mapkit.workspace.shell import pick_palette                   # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_KIT = _REPO / "ff9mapkit"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _pin_guided():
    # ImportDoc reads forms_qt._GUIDED at construction to set the swap drawer's expansion, and the
    # collapsed-by-default assertions here only hold at the module default (Guided). A sibling test that
    # flips this process global without restoring it would leak into this file, so -- like
    # test_gui_mode_lever._pin_prefs -- pin it True for the test and restore the caller's value after.
    # (importdoc/conceptmap reference no prefs.*, so this touches nothing on disk.)
    _saved = forms_qt._GUIDED
    forms_qt.set_guided(True)
    yield
    forms_qt.set_guided(_saved)


def _stub_run(*a, **k):
    return True


def _doc():
    return ImportDoc(pick_palette("dark"), _KIT, run=_stub_run, problems=lambda *a, **k: None)


# ---------------------------------------------------------------- infohub: the realfield kind ---
def test_realfield_kind_lists_real_fields_with_ids():
    hits = infohub.browse("", kinds=["realfield"])
    assert hits, "the realfield kind lists real FF9 fields"
    assert all(e.kind == "realfield" and isinstance(e.ident, int) for e in hits)


def test_realfield_matches_a_numeric_id_query():
    # the id lives in the SUMMARY so a numeric-id search resolves the field, not just an FBG-name search
    assert any(e.ident == 50 for e in infohub.browse("50", kinds=["realfield"]))


def test_realfield_is_picker_only_not_in_the_kitchen_sink():
    # NOT a member of KINDS: a whole-catalog browse must not be flooded with 674 fields
    assert "realfield" not in infohub.KINDS
    assert not any(e.kind == "realfield" for e in infohub.browse("", kinds=None, limit=None))


def test_realfield_entries_subset_preserves_order():
    sub = infohub.realfield_entries(ids=[52, 50])
    assert [e.ident for e in sub] == [52, 50], "the subset is the given ids, in the given order"


# ---------------------------------------------------------------- item 1: the Walk-as disclosure ---
def test_walk_as_swap_is_behind_a_collapsed_disclosure(app):
    doc = _doc()
    assert isinstance(doc.swap_drawer, type(widgets.disclosure("x"))) or hasattr(doc.swap_drawer, "toggle_button")
    assert not doc.swap_drawer.toggle_button.isChecked(), "the advanced swap drawer is collapsed by default"
    # the swap combo + Neutralize live INSIDE the drawer
    assert doc.swap_player in doc.swap_drawer.findChildren(QComboBox)
    assert doc.neutralize in doc.swap_drawer.findChildren(QCheckBox)


def test_suggest_button_stays_out_of_the_swap_drawer(app):
    # chair ruling: 'Suggest a test room…' is a newcomer aid -- it does NOT go into the advanced drawer
    doc = _doc()
    assert doc.rooms_btn not in doc.swap_drawer.findChildren(QPushButton)
    assert doc.rooms_btn.text() == "Suggest a test room…"


def test_walk_as_drawer_comes_back_when_a_swap_is_set(app):
    doc = _doc()
    assert not doc.swap_drawer.toggle_button.isChecked()   # a no-op would leave it here (the fence)
    doc.swap_player.setCurrentText("vivi")
    assert doc.swap_drawer.toggle_button.isChecked(), "setting a swap reveals the drawer (comes-back rule)"
    # OPEN-ONLY: clearing the swap does not force the drawer shut
    doc.swap_player.setCurrentText("")
    assert doc.swap_drawer.toggle_button.isChecked(), "a revealed drawer is never forced closed"


# ---------------------------------------------------------------- item 2: pick-and-fill ---
def _accept_first_row(monkeypatch):
    """Patch QDialog.exec to pick the first row of the CatalogPicker and accept -- the headless analogue of
    a user double-clicking a row."""
    captured = []

    def _fake_exec(self):
        captured.append(self)
        if getattr(self, "lst", None) is not None and self.lst.count():
            self.lst.setCurrentRow(0)
            self._ok()                                     # sets self.result (want_id -> the id string)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", _fake_exec)
    return captured


def test_find_opens_a_picker_and_fills_the_source_id(app, monkeypatch):
    doc = _doc()
    captured = _accept_first_row(monkeypatch)
    doc.on_find()
    assert captured, "Find… opens the catalog picker (no console dump)"
    dlg = captured[0]
    assert dlg._fixed_entries is None, "Find… browses ALL real fields (not a pre-scoped subset)"
    # the chosen row's id landed in the source box
    assert doc.field.text().isdigit(), "the picked field id filled the source box"


def test_suggest_rooms_cache_hit_opens_a_prescoped_picker(app, monkeypatch):
    doc = _doc()
    # prime the cache so on_suggest_rooms takes the instant path (no 45s sweep, no worker thread)
    sweep = SimpleNamespace(rooms=[SimpleNamespace(field_id=50), SimpleNamespace(field_id=52)])
    doc._rooms_cache = sweep
    doc._rooms_cache_key = doc._game_key()
    captured = _accept_first_row(monkeypatch)
    doc.on_suggest_rooms()
    assert captured, "a cached sweep opens the picker immediately"
    dlg = captured[0]
    assert dlg._fixed_entries is not None, "the suggested-rooms picker is PRE-SCOPED to the sweep's rooms"
    assert {e.ident for e in dlg._fixed_entries} == {50, 52}, "only the swept rooms are offered"
    assert doc.field.text() == "50", "picking the top room fills its id"


def test_open_rooms_picker_warns_when_the_sweep_is_empty(app):
    doc = _doc()
    warned = []
    doc._warn = lambda title, text: warned.append((title, text))
    doc._open_rooms_picker(SimpleNamespace(rooms=[]))
    assert warned and "room" in warned[-1][1].lower()


def test_rooms_ready_error_warns_and_restores_the_button(app):
    doc = _doc()
    warned = []
    doc._warn = lambda title, text: warned.append((title, text))
    doc._rooms_busy = True
    doc.rooms_btn.setEnabled(False)
    doc.rooms_btn.setText("Sweeping fields… (~45 s)")
    doc._on_rooms_ready(RuntimeError("no install"))
    assert warned, "a sweep error is surfaced, not swallowed"
    assert doc.rooms_btn.isEnabled() and doc.rooms_btn.text() == "Suggest a test room…", "the button is restored"
    assert doc._rooms_cache is None, "a failed sweep is not cached"
