"""Fences for the region-divided FIELD card picker (the sibling of the model cards).

The data is baked and offline (the ``realfield`` Info-Hub kind + the place prefix of each field's
human name); the ART rides the shared field ThumbService under a namespaced member key, requested
only for the viewport (a cold composite is seconds EACH — flooding the queue is the failure mode).
Entry points: the Import tab's Cards… and the realfield picker's Card view….

Headless (offscreen), FF9MAPKIT_NO_THUMBS=1 throughout — the picker itself is pure over baked data;
every service here is a stub with the real signal surface and NO install reach.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from pathlib import Path                                              # noqa: E402

from PySide6.QtCore import QObject, Qt, Signal                        # noqa: E402
from PySide6.QtGui import QPixmap                                     # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog                   # noqa: E402

from ff9mapkit.editor.theme import pick_palette                       # noqa: E402
from ff9mapkit.workspace import fieldcards                            # noqa: E402
from ff9mapkit.workspace.fieldcards import FieldCardPicker            # noqa: E402
from ff9mapkit.workspace.forms_qt import CatalogPicker                # noqa: E402
from ff9mapkit.workspace.importdoc import ImportDoc                   # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_KIT = _REPO / "ff9mapkit"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _StubFieldThumbs(QObject):
    """The field ThumbService's signal surface with NO worker and NO install reach."""
    ready = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.requests = []

    def cached(self, member):
        return None

    def request(self, member, project_toml, real_id):
        self.requests.append((member, real_id))
        return None


def _png(tmp_path):
    pm = QPixmap(4, 4)
    pm.fill(Qt.GlobalColor.white)
    p = tmp_path / "art.png"
    pm.save(str(p), "PNG")
    return str(p)


# ------------------------------------------------------------------ the data (baked, offline)
def test_field_entries_cover_every_real_field_with_a_region():
    es = fieldcards.field_entries()
    assert len(es) > 800
    assert len({e.id for e in es}) == len(es), "field ids must be unique"
    assert all(e.region for e in es), "every field lands in a region (a no-slash name IS its region)"


def test_regions_are_story_ordered_and_account_for_everything():
    es = fieldcards.field_entries()
    regs = fieldcards.regions_of(es)
    assert regs[0][0] == "Prima Vista", "the first region by first-field-id is the opening airship"
    assert sum(c for _r, c in regs) == len(es), "region counts must partition the catalog"


# ------------------------------------------------------------------ the picker
def test_picker_populates_and_a_region_row_filters(app):
    dlg = FieldCardPicker(None, pick_palette("dark"), _StubFieldThumbs())
    total = dlg.listw.count()
    assert total > 800
    # row 1 = the first real region (row 0 is All); its label carries the same count the grid shows
    dlg.regions.setCurrentRow(1)
    label = dlg.regions.item(1).text()
    assert dlg.listw.count() < total
    assert str(dlg.listw.count()) in label, "the region row's count must match what the grid shows"
    assert f" in {label.split('  ·  ')[0]}" in dlg.info.text()


def test_picker_search_and_exact_id(app):
    dlg = FieldCardPicker(None, pick_palette("dark"), _StubFieldThumbs())
    dlg.q.setText("cargo")
    assert 0 < dlg.listw.count() < 100
    dlg.q.setText("50")
    assert 50 in dlg._items, "an exact id query must surface that field"


def test_picker_returns_the_field_id_as_a_string(app):
    dlg = FieldCardPicker(None, pick_palette("dark"), _StubFieldThumbs())
    dlg.q.setText("50")
    dlg.listw.setCurrentItem(dlg._items[50])
    dlg._ok()
    assert dlg.result == "50"


def test_picker_requests_only_the_visible_cards(app, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_NO_THUMBS", "0")
    svc = _StubFieldThumbs()
    dlg = FieldCardPicker(None, pick_palette("dark"), svc)
    dlg.show()
    app.processEvents()
    svc.requests.clear()
    dlg._request_visible()
    uniq = {m for m, _rid in svc.requests}
    assert 0 < len(uniq) <= fieldcards._VISIBLE_BATCH, \
        "a cold composite is seconds each -- the grid must never flood the queue"
    assert len(uniq) < dlg.listw.count()
    assert all(m.startswith(fieldcards._KEY) for m in uniq), "requests ride the namespaced key"
    dlg.close()


def test_ready_routes_by_the_namespaced_key(app, tmp_path):
    svc = _StubFieldThumbs()
    dlg = FieldCardPicker(None, pick_palette("dark"), svc)
    png = _png(tmp_path)
    svc.ready.emit("some_campaign_member", png)      # the SHARED service also serves the Map/Inspector
    assert 50 not in dlg._icons, "a foreign member key must not paint a card"
    svc.ready.emit(f"{fieldcards._KEY}50", png)
    assert 50 in dlg._icons
    assert not dlg._items[50].icon().isNull()


# ------------------------------------------------------------------ the doorways
def test_realfield_picker_offers_the_card_view(app):
    pal = pick_palette("dark")
    with_cards = CatalogPicker(None, ["realfield"], "", None, pal, want_id=True,
                               field_thumbs=_StubFieldThumbs())
    assert with_cards.cards_btn is not None
    no_service = CatalogPicker(None, ["realfield"], "", None, pal, want_id=True)
    assert no_service.cards_btn is None, "no field art service -> no card view"


def test_realfield_card_pick_answers_the_picker(app, monkeypatch):
    def _fake_exec(self):
        self.result = "300"
        return 1
    monkeypatch.setattr(FieldCardPicker, "exec", _fake_exec)
    pal = pick_palette("dark")
    pk = CatalogPicker(None, ["realfield"], "", None, pal, want_id=True,
                       field_thumbs=_StubFieldThumbs())
    accepted = []
    monkeypatch.setattr(pk, "accept", lambda: accepted.append(True))
    pk._open_field_cards()
    assert pk.result == "300" and accepted


def test_import_tab_cards_button_fills_the_source_box(app, monkeypatch):
    def _fake_exec(self):
        self.result = "300"
        return 1
    monkeypatch.setattr(FieldCardPicker, "exec", _fake_exec)
    doc = ImportDoc(pick_palette("dark"), _KIT, run=lambda *a, **k: True,
                    problems=lambda *a, **k: None, thumbs=_StubFieldThumbs())
    assert doc.field_cards_btn is not None
    doc.on_field_cards()
    assert doc.field.text() == "300"


def test_import_tab_realfield_picker_carries_the_art_service(app, monkeypatch):
    """THE CALL-SITE LAW fence: the Card view lives behind field_thumbs= -- an Import picker opened
    without it silently ships no card button."""
    carried = []

    def _fake_exec(self):
        carried.append(self.field_thumbs)
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(CatalogPicker, "exec", _fake_exec)
    svc = _StubFieldThumbs()
    doc = ImportDoc(pick_palette("dark"), _KIT, run=lambda *a, **k: True,
                    problems=lambda *a, **k: None, thumbs=svc)
    doc._pick_realfield()
    assert carried and carried[0] is svc
