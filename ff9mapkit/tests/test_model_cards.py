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
        self.bulk = []
        self.invalidated = []

    def cached(self, name):
        return self._cached.get(name)

    def request(self, name):
        self.requests.append(name)
        return self._cached.get(name)

    # the bulk lane + invalidate -- no worker here, so "queued" is just a list a test can read
    def request_many(self, names):
        fresh = [n for n in names if self.cached(n) is None and n not in self.bulk]
        self.bulk.extend(fresh)
        return len(fresh)

    def bulk_pending(self):
        return len(self.bulk)

    def cancel_bulk(self):
        n = len(self.bulk)
        self.bulk.clear()
        return n

    def invalidate(self, name=None):
        self.invalidated.append(name)
        if name is None:
            self._cached.clear()
        else:
            self._cached.pop(name, None)

    def hold(self):
        pass

    def release(self):
        pass


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
    monkeypatch.setattr(jobs, "detect_game_mod", lambda repo_root=None: None)   # never read this machine's install
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
    monkeypatch.setattr(jobs, "detect_game_mod", lambda repo_root=None: None)
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
    monkeypatch.setattr(jobs, "detect_game_mod", lambda repo_root=None: None)
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


def test_models_tab_keys_its_install_target_on_its_checkout(app, pin_cache, monkeypatch, tmp_path):
    """The Build tab passes its checkout to detect_game_mod (the pin lives there); the Models tab passed
    nothing, so the two tabs in ONE Workspace could name different install folders whenever the launch CWD
    was not the checkout. Both key on the checkout now."""
    from pathlib import Path
    from ff9mapkit.editor import jobs
    seen = []
    monkeypatch.setattr(jobs, "detect_game_mod", lambda repo_root=None: seen.append(repo_root) or None)
    kit = tmp_path / "repo" / "ff9mapkit"
    kit.mkdir(parents=True)
    ModelsDoc(pick_palette("dark"), str(kit), run=lambda *a, **k: True, model_thumbs=_StubThumbs())
    assert seen == [Path(kit).parent]


# ------------------------------------------------------------------ the service double stays honest
def test_the_thumb_double_covers_the_whole_model_service_surface():
    """THE CALL-SITE LAW's mirror (the anim double has had this since Stage B): every public member
    the real service ships must exist on the double, or a doc fence proves nothing about it."""
    real = {n for n in dir(thumbs_mod.ModelThumbService)
            if not n.startswith("_") and n not in dir(QObject)}
    stub = {n for n in dir(_StubThumbs) if not n.startswith("_")}
    assert real <= stub, f"the double is missing {sorted(real - stub)}"


# ------------------------------------------------------------------ what the still shows
def test_the_pose_fact_says_what_the_picture_shows():
    f = ModelsDoc._pose_fact
    assert "idle" in f({"bones": 48, "pose": "ANH_X_IDLE", "pose_action": "idle", "pose_rank": 0})
    assert "battle idle" in f({"bones": 27, "pose": "ANH_X_000", "pose_action": "000", "pose_rank": 2})
    rest = f({"bones": 27, "pose": None, "pose_action": None, "pose_rank": None})
    assert "REST pose" in rest
    bind = f({"bones": 27, "pose": "ANH_X_B", "pose_action": "b", "pose_rank": 9})
    assert "bind pose" in bind and "'b'" in bind.replace("‘", "'").replace("’", "'")


def test_the_pose_fact_does_not_caution_about_a_prop():
    """A barrel has 2 bones and a weapon 1. 'This may be a bind pose' is a caution about a character
    standing in a T; under a treasure chest it is noise."""
    f = ModelsDoc._pose_fact
    assert f({"bones": 2, "pose": "ANH_X_B", "pose_action": "b", "pose_rank": 9}) == ""
    assert f({"bones": 1, "pose": None, "pose_action": None, "pose_rank": None}) == ""
    assert f({"bones": 2, "pose": "ANH_X_IDLE", "pose_action": "idle", "pose_rank": 0}) != "",         "a prop genuinely posed from an idle clip may still say so"
    assert f({"bones": 48, "meshes": 3}) == "", "a sidecar from before the field says nothing"
    assert f(None) == ""


def _write_sidecar(gid, **fields):
    _png, meta = thumbcache.model_thumb_paths(gid)
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps({"id": gid, **fields}), encoding="utf-8")


def test_selecting_a_model_shows_its_pose_line(doc, pin_cache):
    _write_sidecar(8, bones=48, meshes=3, verts=1284, textures=["a", "b"],
                   pose="ANH_MAIN_F0_VIV_IDLE", pose_action="idle", pose_rank=0)
    doc.search.setText(_VIV)
    doc.listw.setCurrentRow(0)
    assert "idle" in doc.d_pose.text() and not doc.d_pose.isHidden()
    assert "48 bones" in doc.d_facts.text()


def test_a_still_that_lands_late_fills_the_facts_without_touching_the_clip_filter(doc, pin_cache):
    """The sidecar is written WITH the still, so a first-time selection used to show no counts until
    the model was re-selected. And the refresh must not reset what the author typed."""
    doc.search.setText(_VIV)
    doc.listw.setCurrentRow(0)
    assert "bones" not in doc.d_facts.text() and doc.d_pose.isHidden()
    doc.clip_filter.setText("walk")
    shown = doc.clip_list.count()
    _write_sidecar(8, bones=48, meshes=3, verts=1284, textures=[], pose=None, pose_action=None,
                   pose_rank=None)
    png = _write_cached_png(pin_cache, "art", "late")
    doc._thumb_ready(_VIV, str(png))
    assert "48 bones" in doc.d_facts.text() and "REST pose" in doc.d_pose.text()
    assert doc.clip_filter.text() == "walk" and doc.clip_list.count() == shown


# ------------------------------------------------------------------ renders follow the viewport
def test_scrolling_the_list_renders_what_came_into_view(doc, app, thumbs_on):
    """Only the first _THUMB_BATCH rows were ever requested; the other two thirds of the catalog was a
    text list until a row was SELECTED."""
    from ff9mapkit.workspace import modelsdoc
    doc.resize(900, 600)
    doc.show()
    try:
        app.processEvents()
        n = doc.listw.count()
        assert n > modelsdoc._THUMB_BATCH * 2, "the fence needs a list longer than the warm batch"
        doc._svc.requests.clear()
        doc.listw.scrollToBottom()
        app.processEvents()
        doc._request_visible()
        asked = doc._svc.requests
        last = doc.listw.item(n - 1).data(Qt.ItemDataRole.UserRole)
        assert last in asked, "the row at the bottom of the viewport was not rendered"
        tail = {doc.listw.item(i).data(Qt.ItemDataRole.UserRole) for i in range(n - 40, n)}
        assert 0 < len(asked) <= modelsdoc._VISIBLE_BATCH and set(asked) <= tail,             "it must ask for the VIEWPORT, never the whole list"
    finally:
        doc.hide()


def test_the_viewport_pass_skips_warm_rows_and_known_no_geometry_ids(doc, app, thumbs_on):
    doc.search.setText("GEO_MAIN_F0")
    doc.resize(900, 600)
    doc.show()
    try:
        app.processEvents()
        names = [doc.listw.item(i).data(Qt.ItemDataRole.UserRole) for i in range(doc.listw.count())]
        warm, gone = names[0], names[1]
        doc._svc._cached[warm] = "warm.png"
        doc._absent = {thumbs_mod._geo_id(gone)}
        doc._svc.requests.clear()
        doc._request_visible()
        assert warm not in doc._svc.requests and gone not in doc._svc.requests
        assert names[2] in doc._svc.requests
    finally:
        doc.hide()


def test_a_hidden_tabs_refill_arms_no_timer(doc):
    """The tab is built (and refilled) at Workspace construction. A single-shot armed there fires in
    whichever later test next runs an event loop."""
    doc.search.setText("GEO_NPC")
    doc.listw.verticalScrollBar().valueChanged.emit(3)
    assert not doc._scroll_timer.isActive()


def test_leaving_the_tab_stops_the_scroll_timer(doc, app):
    doc.show()
    app.processEvents()
    doc._scroll_timer.start()
    doc.hide()
    app.processEvents()
    assert not doc._scroll_timer.isActive()


def test_showing_the_tab_does_not_read_the_mod_folder(doc, app, monkeypatch, tmp_path):
    """SNAP-CAUGHT. A first-show scan painted THIS MACHINE's deployed models into a picture; any
    harness that shows the tab would have reported on its developer."""
    from ff9mapkit.models import deployed

    def _boom(_mod):
        raise AssertionError("showing the Models tab must not scan the mod folder")
    monkeypatch.setattr(deployed, "scan_mod", _boom)
    doc.mdl_mod.setText(str(tmp_path))
    doc.show()
    app.processEvents()
    doc.hide()
    assert doc.dep_list.count() == 0


# ------------------------------------------------------------------ the preview cache menu
def test_the_cache_menu_reads_its_status_only_when_it_opens(doc, pin_cache, monkeypatch):
    calls = []
    real = thumbcache.still_cache_stats
    monkeypatch.setattr(thumbcache, "still_cache_stats", lambda: calls.append(1) or real())
    d2 = ModelsDoc(pick_palette("dark"), ".", run=lambda *a, **k: True, model_thumbs=_StubThumbs())
    assert calls == [], "the directory scan belongs to aboutToShow, never to construction"
    d2.cache_menu.aboutToShow.emit()
    assert calls == [1]


def test_the_cache_menu_status_lines_read_cleanly(doc, pin_cache):
    """SNAP-CAUGHT: the first cut said '0 of 256 MB MB'."""
    _write_cached_png(pin_cache, "model_thumbs", f"8_v{thumbcache._MODEL_RENDER_V}")
    _write_absent_sidecar(pin_cache, 9)
    doc._refresh_cache_menu()
    stills, clips = doc.cache_status_act.text(), doc.cache_clips_act.text()
    assert stills.startswith("1 of ") and "previews rendered" in stills and "1 have no geometry" in stills
    assert "MB MB" not in stills + clips and "0 MB" not in stills, (stills, clips)
    assert "256 MB budget" in clips
    assert not doc.cache_status_act.isEnabled(), "a status line is not a command"
    assert doc.cache_render_act.text() == "Render all previews"


def test_render_all_queues_every_unrendered_model_and_toggles_to_stop(doc, pin_cache, thumbs_on):
    from ff9mapkit import catalog
    doc._svc._cached[_VIV] = "warm.png"
    doc._absent = {9}
    doc.on_render_all()
    every = [m for m in catalog.all_models()]
    assert _VIV not in doc._svc.bulk and catalog.model(9).name not in doc._svc.bulk
    assert len(doc._svc.bulk) == len(every) - 2
    assert "rendering previews" in doc.count_lbl.text() and str(len(doc._svc.bulk)) in doc.count_lbl.text()
    doc._refresh_cache_menu()
    assert doc.cache_render_act.text().startswith("Stop rendering")
    doc.on_render_all()                                          # the SAME verb stops it
    assert doc._svc.bulk == [] and "rendering previews" not in doc.count_lbl.text()


def test_the_count_line_ticks_down_as_the_warm_up_lands(doc, pin_cache, thumbs_on):
    doc._svc.bulk = ["GEO_A", "GEO_B"]
    doc._update_count()
    assert "2 to go" in doc.count_lbl.text()
    doc._svc.bulk = ["GEO_B"]
    doc._svc.missed.emit("GEO_A")                                # a plain miss still ticks it
    assert "1 to go" in doc.count_lbl.text()
    doc._svc.bulk = []
    png = _write_cached_png(pin_cache, "art", "b")
    doc._svc.ready.emit("GEO_B", str(png))
    assert "to go" not in doc.count_lbl.text(), "the last arrival must clear the progress text"


def test_clearing_the_cache_asks_first_then_forgets_everything(doc, pin_cache, thumbs_on, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    still = _write_cached_png(pin_cache, "model_thumbs", f"8_v{thumbcache._MODEL_RENDER_V}")
    frame = _write_cached_png(pin_cache, "anim_frames", "8_148_f0_v1a1")
    doc._icons[_VIV] = object()
    doc._absent = {9}
    answers = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: (asked.append(a[2]), answers.pop(0))[1])
    doc.on_clear_cache()
    assert still.exists() and frame.exists() and doc._svc.invalidated == [], "No means no"
    doc.on_clear_cache()
    assert not still.exists() and not frame.exists()
    assert doc._svc.invalidated == [None] and doc._icons == {}
    assert 9 not in doc._absent_ids(),         "the no-geometry set is rebuilt from the sidecars -- and the sidecars just went"
    assert "cleared" in doc.count_lbl.text()
    assert "Nothing of yours is lost" in asked[0], "the prompt must say the cache is re-derivable"


# ------------------------------------------------------------------ the mint id
def _mod_with_mints(tmp_path, *ids):
    mod = tmp_path / "mod"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text(
        "".join(f"3DModel {i} GEO_NPC_F0_M{i % 1000:03d}\n" for i in ids), encoding="utf-8")
    return mod


def test_refresh_moves_the_mint_id_off_a_taken_one(doc, tmp_path):
    """The constant 6000 meant the SECOND mint into a folder silently replaced the first."""
    mod = _mod_with_mints(tmp_path, 6000, 6001)
    assert doc.mdl_mint_id.text() == "6000"
    doc.mdl_mod.setText(str(mod))
    doc.on_deployed_refresh()
    assert doc.mdl_mint_id.text() == "6002"


def test_refresh_never_moves_a_free_id_the_author_typed(doc, tmp_path):
    mod = _mod_with_mints(tmp_path, 6000, 6100)
    doc.mdl_mod.setText(str(mod))
    doc.mdl_mint_id.setText("6500")
    doc.on_deployed_refresh()
    assert doc.mdl_mint_id.text() == "6500", "a free id is the author's choice -- leave it alone"
    doc.mdl_mint_id.setText("6100")
    doc.on_deployed_refresh()
    assert doc.mdl_mint_id.text() == "6101", "a TAKEN id advances from where the author was, not to 6000"


def _recording_doc(monkeypatch):
    from ff9mapkit.editor import jobs
    monkeypatch.setattr(jobs, "detect_game_mod", lambda repo_root=None: None)
    runs = []

    def _run(argv, **kw):
        runs.append((argv, kw))
        return True
    d = ModelsDoc(pick_palette("dark"), ".", run=_run, model_thumbs=_StubThumbs())
    d.search.setText(_VIV)
    d.listw.setCurrentRow(0)
    return d, runs


def test_minting_onto_a_taken_id_asks_before_it_replaces(app, pin_cache, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    d, runs = _recording_doc(monkeypatch)
    mod = _mod_with_mints(tmp_path, 6000)
    d.mdl_mod.setText(str(mod))
    answers = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]
    prompts = []
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: (prompts.append(a[2]), answers.pop(0))[1])
    d.on_model_mint()
    assert runs == [], "No must not start the job"
    assert "REPLACES" in prompts[0] and "6001" in prompts[0], "the prompt names the next free id"
    d.on_model_mint()
    assert len(runs) == 1 and runs[0][0][-6:] == ["model-mint", _VIV, "--id", "6000", "--deploy", str(mod)]
    d.mdl_mint_id.setText("6001")                                # a FREE id never prompts
    d._busy(False)
    d.on_model_mint()
    assert len(runs) == 2 and len(prompts) == 2


def test_a_finished_deploy_refreshes_the_deployed_list(app, pin_cache, tmp_path, monkeypatch):
    """The list went stale the instant a deploy landed, and said so only if you clicked Refresh."""
    d, runs = _recording_doc(monkeypatch)
    mod = _mod_with_mints(tmp_path, 6000)
    d.mdl_mod.setText(str(mod))
    d._kit(["model-anim", _VIV, "--out", "x"], subject="t")      # not a deploy: no refresh on success
    runs[-1][1]["on_finished"](0)
    assert d.dep_list.count() == 0
    d._kit(["model-mint", _VIV, "--id", "6000", "--deploy", str(mod)], subject="t")
    runs[-1][1]["on_finished"](1)                                # a FAILED deploy changed nothing
    assert d.dep_list.count() == 0
    d._kit(["model-mint", _VIV, "--id", "6000", "--deploy", str(mod)], subject="t")
    runs[-1][1]["on_finished"](0)
    assert d.dep_list.count() == 1, "the dangling 3DModel line is the folder's one entry"
    assert d.mdl_mint_id.text() == "6001", "...and the id that was just minted is no longer offered"


def test_the_mint_id_box_is_sized_by_its_font_not_by_a_pixel_constant(doc, app):
    """SNAP-CAUGHT at the 150% rung: a fixed 70px showed ';000' for 6000. A px constant cannot hear
    the text-size dial; a hint measured in the box's own font can. Offscreen metrics are fiction, but
    this COMPARISON is not -- both sides are measured in the same font."""
    from PySide6.QtGui import QFont
    box = doc.mdl_mint_id
    assert box.minimumWidth() != box.maximumWidth() or box.maximumWidth() > 10000, \
        "a fixed pixel width is back on the mint id"
    small = QFont(box.font())
    small.setPixelSize(12)
    big = QFont(box.font())
    big.setPixelSize(24)
    box.setFont(small)
    w_small = box.sizeHint().width()
    assert w_small >= box.fontMetrics().horizontalAdvance("65535"), "the box must fit its widest id"
    box.setFont(big)
    w_big = box.sizeHint().width()
    assert w_big >= box.fontMetrics().horizontalAdvance("65535")
    assert w_big > w_small, "the hint did not grow with the font -- the box is deaf to the dial"
    assert box.minimumSizeHint().width() == w_big, "it may not be squeezed under its own digits"
