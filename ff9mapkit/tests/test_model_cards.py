"""Fences for the model-preview performance pass + the card-grid picker + the no-geometry filter.

Three mechanisms, each fenced against the no-op:

  * the WARM DISK FAST PATH -- both thumb services answer from the on-disk cache with one stat,
    without spawning the worker (before: every prior session's renders re-queued through the worker
    before a single icon showed);
  * the NO-GEOMETRY filter -- `thumbcache.absent_ids()` reads the render worker's `absent` sidecars,
    the Models tab / card picker hide those rows on request (count reported, never silent), and the
    set grows LIVE off the service's `missed` signal;
  * the CARD PICKER -- `modelcards.ModelCardPicker` browses the same catalog as thumbnail cards and
    returns the GEO name; the Models tab and the catalog picker both open it.

Headless (offscreen); FF9MAPKIT_NO_THUMBS=1 except where a test flips it, and EVERY cache read is
pinned to a scratch FF9MAPKIT_DATA -- the recurring disease is a test that reads the developer's
real machine (here: the real preview cache). Doc tests use a stub service so nothing can reach an
install even if a guard regresses.
"""
from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Qt, Signal                       # noqa: E402
from PySide6.QtGui import QPixmap                                    # noqa: E402
from PySide6.QtWidgets import QApplication                           # noqa: E402

from ff9mapkit.editor.theme import pick_palette                      # noqa: E402
from ff9mapkit.models import thumbcache                              # noqa: E402
from ff9mapkit.workspace import modelcards, thumbs as thumbs_mod     # noqa: E402
from ff9mapkit.workspace.forms_qt import CatalogPicker               # noqa: E402
from ff9mapkit.workspace.modelcards import ModelCardPicker           # noqa: E402
from ff9mapkit.workspace.modelsdoc import ModelsDoc                  # noqa: E402

_VIV = "GEO_MAIN_F0_VIV"                                             # model id 8 -- the catalog's anchor


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pin_cache(tmp_path, monkeypatch):
    """Every provision.cache_dir() read/write lands in a scratch dir -- never the developer's cache."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
def thumbs_on(monkeypatch):
    """Flip the NO_THUMBS gate for tests exercising the cache-read paths it guards."""
    monkeypatch.setenv("FF9MAPKIT_NO_THUMBS", "0")


def _write_absent_sidecar(cache_root, gid):
    d = cache_root / "model_thumbs"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{gid}_v{thumbcache._MODEL_RENDER_V}.json").write_text(
        json.dumps({"geo": "X", "id": gid, "absent": True}), encoding="utf-8")


def _write_cached_png(cache_root, sub, stem):
    d = cache_root / sub
    d.mkdir(parents=True, exist_ok=True)
    pm = QPixmap(4, 4)
    pm.fill(Qt.GlobalColor.white)
    p = d / f"{stem}.png"
    pm.save(str(p), "PNG")
    return p


class _StubThumbs(QObject):
    """A service double with the real signal surface but NO worker and NO install reach -- so a doc
    test can assert what was REQUESTED without any chance of touching this machine."""
    ready = Signal(str, str)
    missed = Signal(str)

    def __init__(self):
        super().__init__()
        self.requests = []
        self._cached = {}

    def cached(self, name):
        return self._cached.get(name)

    def request(self, name):
        self.requests.append(name)
        return self._cached.get(name)


# ------------------------------------------------------------------ absent_ids (the sidecar scan)
def test_absent_ids_reads_only_the_absent_sidecars(pin_cache):
    _write_absent_sidecar(pin_cache, 8)
    d = pin_cache / "model_thumbs"
    (d / f"9_v{thumbcache._MODEL_RENDER_V}.json").write_text(json.dumps({"id": 9, "bones": 3}),
                                                             encoding="utf-8")   # a real render's sidecar
    (d / f"10_v{thumbcache._MODEL_RENDER_V}.json").write_text("{corrupt", encoding="utf-8")
    (d / "11_v0.json").write_text(json.dumps({"id": 11, "absent": True}), encoding="utf-8")  # old renderer
    assert thumbcache.absent_ids() == {8}


def test_absent_ids_is_empty_on_a_fresh_cache(pin_cache):
    assert thumbcache.absent_ids() == set()


# ------------------------------------------------------------------ the warm disk fast path
def test_model_service_answers_from_the_disk_cache_without_a_worker(app, pin_cache, thumbs_on,
                                                                    monkeypatch):
    # a broken fast path must FAIL here, not fall through to a real render on this machine
    monkeypatch.setattr(thumbs_mod, "build_model_thumb",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("worker path taken")))
    png = _write_cached_png(pin_cache, "model_thumbs", f"8_v{thumbcache._MODEL_RENDER_V}")
    svc = thumbs_mod.ModelThumbService()
    got = svc.cached(_VIV)
    assert got == str(png)
    assert svc._worker is None, "a warm cache read must not spawn the worker"
    # memoized both ways: a hit sticks (in-memory), and a probe-miss never re-stats
    png.unlink()
    assert svc.cached(_VIV) == str(png)
    other = "GEO_MAIN_F0_ZID"
    assert svc.cached(other) is None
    assert other in svc._disk_miss, "a negative disk probe must be remembered (refill re-stats otherwise)"
    svc.invalidate()
    assert svc._disk_miss == set() and svc.cached(_VIV) is None


def test_model_service_disk_reads_are_gated_by_the_no_thumbs_flag(app, pin_cache):
    _write_cached_png(pin_cache, "model_thumbs", f"8_v{thumbcache._MODEL_RENDER_V}")
    svc = thumbs_mod.ModelThumbService()
    assert svc.cached(_VIV) is None, "NO_THUMBS must gate the disk read too (headless isolation)"


def test_field_service_answers_from_the_disk_cache_without_a_worker(app, pin_cache, thumbs_on,
                                                                    monkeypatch):
    monkeypatch.setattr(thumbs_mod, "build_thumb",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("worker path taken")))
    png = _write_cached_png(pin_cache, "thumbs", "real_4003")
    svc = thumbs_mod.ThumbService()
    got = svc.request("my_room", None, 4003)
    assert got == str(png)
    assert svc._worker is None, "a warm cache read must not spawn the worker"
    assert svc.cached("my_room") == str(png)


def test_field_fast_path_keys_on_the_project_art_when_present(app, pin_cache, thumbs_on, tmp_path):
    proj = tmp_path / "proj" / "field.toml"
    proj.parent.mkdir(parents=True)
    proj.write_text("", encoding="utf-8")
    (proj.parent / "background.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    key = thumbs_mod._key_for(proj.parent / "background.png", None)
    png = _write_cached_png(pin_cache, "thumbs", key)
    assert thumbs_mod.cached_thumb_fast(proj, 4003) == png   # tier 1 (project art) outranks the id
    assert thumbs_mod.cached_thumb_fast(None, 9999) is None  # nothing cached -> the worker's job


# ------------------------------------------------------------------ the shared filter
def test_filter_models_reports_what_it_hid():
    entries, hidden = modelcards.filter_models("GEO_MAIN_F0_VIV", None)
    assert len(entries) == 1 and hidden == 0
    kept, hidden = modelcards.filter_models("GEO_MAIN_F0_VIV", None, hide_absent=True, absent={8})
    assert kept == [] and hidden == 1, "hiding must COUNT what it dropped, never vanish rows silently"


# ------------------------------------------------------------------ the card picker
def test_card_picker_populates_searches_and_returns_the_geo_name(app, pin_cache):
    dlg = ModelCardPicker(None, pick_palette("dark"), _StubThumbs())
    assert dlg.listw.count() > 500, "card grid under-populated"
    dlg.q.setText(_VIV)
    assert dlg.listw.count() == 1
    dlg.listw.setCurrentRow(0)
    dlg._ok()
    assert dlg.result == _VIV


def test_card_picker_hides_probed_no_geometry_models(app, pin_cache, thumbs_on):
    _write_absent_sidecar(pin_cache, 8)
    dlg = ModelCardPicker(None, pick_palette("dark"), _StubThumbs())
    dlg.q.setText(_VIV)
    assert dlg.listw.count() == 0, "the probed-absent id must be hidden while the toggle is on"
    assert "hidden" in dlg.info.text()
    dlg.no_geo.setChecked(False)
    assert dlg.listw.count() == 1, "unchecking the toggle must bring the row back"


def test_card_picker_grows_the_absent_set_live_off_the_missed_signal(app, pin_cache, thumbs_on):
    svc = _StubThumbs()
    dlg = ModelCardPicker(None, pick_palette("dark"), svc)
    dlg.q.setText(_VIV)
    assert dlg.listw.count() == 1
    _write_absent_sidecar(pin_cache, 8)          # the render worker just probed it absent...
    svc.missed.emit(_VIV)                        # ...and the service reported the miss
    assert 8 in dlg._absent
    assert dlg.listw.count() == 0, "a live absent probe must drop the card while the toggle is on"


def test_card_picker_missed_without_a_sidecar_changes_nothing(app, pin_cache, thumbs_on):
    svc = _StubThumbs()
    dlg = ModelCardPicker(None, pick_palette("dark"), svc)
    dlg.q.setText(_VIV)
    svc.missed.emit(_VIV)                        # a no-install miss writes no sidecar
    assert 8 not in dlg._absent and dlg.listw.count() == 1


def test_card_picker_requests_only_the_visible_cards(app, pin_cache, thumbs_on):
    svc = _StubThumbs()
    dlg = ModelCardPicker(None, pick_palette("dark"), svc)
    dlg.show()                                   # the icon grid lays out on show -- visualItemRect needs it
    app.processEvents()
    svc.requests.clear()
    dlg._request_visible()
    uniq = set(svc.requests)
    assert 0 < len(uniq) <= modelcards._VISIBLE_BATCH, \
        "the card grid must never flood the render queue with the whole catalog"
    assert len(uniq) < dlg.listw.count(), "only the viewport's cards are requested, not the list"
    dlg.close()


def test_card_picker_keeps_the_selection_across_a_refill(app, pin_cache):
    dlg = ModelCardPicker(None, pick_palette("dark"), _StubThumbs())
    dlg.q.setText("GEO_MAIN_F0")
    dlg.listw.setCurrentItem(dlg._items[_VIV])
    dlg._refill()
    cur = dlg.listw.currentItem()
    assert cur is not None and cur.data(Qt.ItemDataRole.UserRole) == _VIV


# ------------------------------------------------------------------ the Models tab wiring
@pytest.fixture
def doc(app, pin_cache, monkeypatch):
    from ff9mapkit.editor import jobs
    monkeypatch.setattr(jobs, "detect_game_mod", lambda: None)   # never read this machine's install
    svc = _StubThumbs()
    d = ModelsDoc(pick_palette("dark"), ".", run=lambda *a, **k: True, model_thumbs=svc)
    d._svc = svc
    return d


def test_models_tab_has_the_cards_button_and_the_hide_toggle(doc):
    assert doc.cards_btn is not None
    assert doc.no_geo is not None and not doc.no_geo.isChecked(), \
        "the tab browses/explains unshipped ids -- hiding is opt-in here"


def test_models_tab_hide_toggle_filters_and_reports(doc, pin_cache):
    doc._absent = {8}
    doc.search.setText(_VIV)
    assert doc.listw.count() == 1
    doc.no_geo.setChecked(True)
    assert doc.listw.count() == 0
    assert "hidden" in doc.count_lbl.text()


def test_models_tab_missed_signal_updates_the_filter_live(doc, pin_cache, thumbs_on):
    doc.no_geo.setChecked(True)
    doc.search.setText(_VIV)
    assert doc.listw.count() == 1
    _write_absent_sidecar(pin_cache, 8)
    doc._svc.missed.emit(_VIV)
    assert 8 in doc._absent and doc.listw.count() == 0


def test_models_tab_memoizes_row_icons(doc, tmp_path):
    png = _write_cached_png(tmp_path, "art", "thumb")
    doc._thumb_ready(_VIV, str(png))
    assert _VIV in doc._icons
    assert doc._icon_for(_VIV) is doc._icons[_VIV], \
        "a refill must reuse the decoded icon, not re-load the PNG per keystroke"


def test_models_tab_warm_batch_skips_known_absent_ids(app, pin_cache, thumbs_on, monkeypatch):
    from ff9mapkit.editor import jobs
    monkeypatch.setattr(jobs, "detect_game_mod", lambda: None)
    _write_absent_sidecar(pin_cache, 8)
    svc = _StubThumbs()
    d = ModelsDoc(pick_palette("dark"), ".", run=lambda *a, **k: True, model_thumbs=svc)
    d.search.setText("GEO_MAIN_F0_VIV")          # narrows the warm batch to the one (absent) row
    assert _VIV not in svc.requests, "a known no-geometry id is a guaranteed miss -- never re-probe it"


def test_models_tab_warm_startup_defers_the_sidecar_scan(app, pin_cache, thumbs_on, monkeypatch):
    """The tab is built at Workspace construction. When the warm disk cache answers every visible row,
    the startup refill must not pay the absent-sidecar sweep (hundreds of small-file reads on a real
    machine) -- the scan belongs to the hide-toggle / cold-render paths, on first NEED."""
    from ff9mapkit.editor import jobs
    monkeypatch.setattr(jobs, "detect_game_mod", lambda: None)
    _write_absent_sidecar(pin_cache, 8)

    class _AllWarm(_StubThumbs):
        def cached(self, name):
            return "warm.png"                    # every row answers from "disk" -- nothing needs a render

    d = ModelsDoc(pick_palette("dark"), ".", run=lambda *a, **k: True, model_thumbs=_AllWarm())
    assert d._absent is None, "a fully-warm startup refill must defer the absent-sidecar scan"
    d.no_geo.setChecked(True)                    # the hide toggle is the first real NEED...
    assert d._absent == {8}, "...and it scans (and applies) the sidecars on demand"


def test_models_tab_cards_pick_lands_on_the_row(doc, monkeypatch):
    def _fake_exec(self):
        self.result = _VIV
        return 1
    monkeypatch.setattr(ModelCardPicker, "exec", _fake_exec)
    doc.on_cards()
    assert doc.search.text() == _VIV
    cur = doc.listw.currentItem()
    assert cur is not None and cur.data(Qt.ItemDataRole.UserRole) == _VIV
    assert doc._current is not None and doc._current.id == 8


# ------------------------------------------------------------------ the shell's warm-open redraw
def test_open_campaign_kicks_the_map_redraw_for_warm_thumbs(app, pin_cache, tmp_path, monkeypatch):
    """The fast path answers request() WITHOUT a ready() emit, and open_campaign renders the Map
    BEFORE the prefetch loop -- so a warm cache must kick the coalesced redraw itself, or the art
    that is finally instant would never reach the Map at all."""
    from ff9mapkit import campaign as C, prefs
    from ff9mapkit.workspace import shell
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    d = tmp_path / "camp"
    plan = C.new_campaign("Warm", "FF9CustomMap", d)
    C.add_field(plan, d, name="room_a")
    win = shell.Workspace(pick_palette("dark"))
    monkeypatch.setattr(win.thumbs, "request", lambda *a, **k: str(tmp_path / "warm.png"))
    assert win.open_campaign(d / "campaign.toml")
    assert win._thumb_rerender.isActive(), \
        "a warm-cache open must start the coalesced Map redraw (no ready() will arrive)"


def test_scene_refresh_re_resolves_the_thumbs_it_invalidated(app, pin_cache, tmp_path, monkeypatch):
    """F5's analogue invalidates the thumb cache 'to re-resolve' -- and for two rounds NOBODY
    re-resolved: the next Map redraw probed an empty in-memory cache and found nothing, and no call
    site was left holding a request. The refresh must spend the prefetch loop itself."""
    from ff9mapkit import campaign as C, prefs
    from ff9mapkit.workspace import shell
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    d = tmp_path / "camp"
    plan = C.new_campaign("Warm", "FF9CustomMap", d)
    C.add_field(plan, d, name="room_a")
    win = shell.Workspace(pick_palette("dark"))
    requested = []
    monkeypatch.setattr(win.thumbs, "request",
                        lambda name, *a, **k: (requested.append(name), str(tmp_path / "warm.png"))[1])
    assert win.open_campaign(d / "campaign.toml")
    requested.clear()
    win._thumb_rerender.stop()
    win.on_refresh_scene()
    assert requested, "the scene refresh invalidated the thumbs and must RE-REQUEST them"
    assert win._thumb_rerender.isActive(), "warm re-answers must kick the coalesced Map redraw"


def test_adding_a_field_requests_its_thumb(app, pin_cache, tmp_path, monkeypatch):
    """Add-field re-renders the Map -- so the NEW member needs a thumb request of its own, or its
    card keeps the placeholder band until the campaign is next reopened."""
    from ff9mapkit import campaign as C, prefs
    from ff9mapkit.workspace import shell
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    d = tmp_path / "camp"
    plan = C.new_campaign("Warm", "FF9CustomMap", d)
    C.add_field(plan, d, name="room_a")
    win = shell.Workspace(pick_palette("dark"))
    requested = []
    monkeypatch.setattr(win.thumbs, "request",
                        lambda name, *a, **k: (requested.append(name), None)[1])
    assert win.open_campaign(d / "campaign.toml")
    requested.clear()
    win._add_field_to_campaign("room_b")
    assert "room_b" in requested, "the freshly added member's art must be requested, not orphaned"


# ------------------------------------------------------------------ the catalog picker doorway
def test_the_model_fields_actually_reach_the_picker():
    """THE CALL-SITE LAW: the card view lives behind the `model` catalog kind, so a model field
    without a catalog= never shows Browse at all (the NPC Model id shipped exactly that way)."""
    from ff9mapkit.editor import forms
    npc_model = next(f for f in forms.NPC_SPEC if f.key == "model")
    assert npc_model.catalog == "model"
    walk_as = next(f for f in forms.PLAYER_SPEC if f.key == "model")
    assert "model" in walk_as.catalog.split(","), "walk-as accepts an exact GEO name -- cards apply"


def test_catalog_picker_offers_cards_only_for_the_model_kind(app, pin_cache):
    pal = pick_palette("dark")
    svc = _StubThumbs()
    with_cards = CatalogPicker(None, ["model"], "", None, pal, model_thumbs=svc)
    assert with_cards.cards_btn is not None
    no_service = CatalogPicker(None, ["model"], "", None, pal)
    assert no_service.cards_btn is None, "no preview service -> no card view (cache reads only)"
    other_kind = CatalogPicker(None, ["item"], "", None, pal, model_thumbs=svc)
    assert other_kind.cards_btn is None, "a GEO name is only a valid answer for the model kind"


def test_catalog_picker_card_pick_answers_the_dialog(app, pin_cache, monkeypatch):
    def _fake_exec(self):
        self.result = _VIV
        return 1
    monkeypatch.setattr(ModelCardPicker, "exec", _fake_exec)
    pal = pick_palette("dark")
    pk = CatalogPicker(None, ["model"], "", None, pal, model_thumbs=_StubThumbs())
    accepted = []
    monkeypatch.setattr(pk, "accept", lambda: accepted.append(True))
    pk._open_cards()
    assert pk.result == _VIV and accepted


# ------------------------------------------------------------------ the right pane never clips silently
def test_models_right_pane_scrolls_instead_of_clipping(doc, app):
    """At the default window the one-row filter strip put a ~450px floor under the LEFT pane, the split
    starved the right editor pane below its own content width, and its h-bar was forced off -- which
    under widgetResizable means CLIP, not scroll ('Copy [[npc]] snip', 'Deploy r' cut mid-glyph).
    Filters now stack two rows; the bar is AsNeeded and must actually appear in a squeeze."""
    from PySide6.QtWidgets import QScrollArea, QSplitter
    right = doc.findChildren(QScrollArea)[0]
    assert right.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded, \
        "AlwaysOff under widgetResizable is a silent clip, not a policy"
    doc.show()
    app.processEvents()
    assert doc.group.y() < doc.field_only.y(), \
        "the group combo sits on its own row above the checkboxes (the left pane's width floor)"
    split = doc.findChildren(QSplitter)[0]
    split.setSizes([900, 120])                       # starve the right pane below its content minimum
    app.processEvents()
    assert right.horizontalScrollBar().isVisible(), \
        "below its content minimum the pane scrolls -- it never clips silently"


def test_single_kind_picker_rows_drop_the_chip_and_realfield_rows_carry_the_id(app):
    """Every row of the realfield picker repeated '[realfield]' (noise in a single-kind list) while
    twin names ('Cargo Room' x2, 'Interior' x4) were indistinguishable -- the id, the very value the
    pick fills in, was nowhere on the row."""
    from ff9mapkit.infohub import Entry
    ents = [Entry("realfield", "Prima Vista/Interior", None, "field #58 -- pv_int", 58),
            Entry("realfield", "Prima Vista/Interior", None, "field #59 -- pv_int2", 59)]
    dlg = CatalogPicker(None, ["realfield"], "", None, pick_palette("dark"), entries=ents, want_id=True)
    try:
        rows = [dlg.lst.item(i).text() for i in range(dlg.lst.count())]
        assert all("[realfield]" not in r for r in rows), "a single-kind picker repeats no kind chip"
        assert "58" in rows[0] and "59" in rows[1] and rows[0] != rows[1], \
            "twin names are told apart by the id the pick fills in"
        assert "2 matches" in dlg.info.text(), "a real plural, not 'match(es)'"
        dlg.q.setText("58")
        assert "1 match " in dlg.info.text() or dlg.info.text().startswith("1 match"), \
            "the singular reads as prose too"
    finally:
        dlg.deleteLater()
