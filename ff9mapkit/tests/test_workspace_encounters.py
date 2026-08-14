"""The Workspace wiring of the battle-locations pillar (UI design (a)/(b)/(c)), all offline:

  * (a) the Info Hub ``CatalogLibrary`` Encounters section -- a build-free sidebar count, rich rows + rich
    detail (enemies/attacks/places/"Appears in"/the ``[encounter]`` snippet) from an INJECTED warm map, the
    ``_scene_usage`` cold guard (never a GUI-thread build), and the async Build front door.
  * (b) the field-editor Encounter form's ``scene`` field pointing at ``catalog="encounter,scene"``, and a
    ``CatalogPicker`` over those kinds returning the numeric scene id.
  * (c) ``BattleDoc._location_panel`` -- warm-only, best-effort, MAP-node-only, never builds.

Every test injects a synthetic ``BattleMap`` into ``locate._MEMO`` (or leaves it empty for the cold lane),
so nothing here ever runs the ~9s census. The build seam asserted against is ``locate._build_fresh`` (the
actual cold build) -- ``build_map`` on a memo hit must never reach it, exactly as ``test_battle_locate``'s
``cached_map must never build`` fence.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QWidget           # noqa: E402

from ff9mapkit import infohub                                 # noqa: E402
from ff9mapkit.battle import locate as loc                    # noqa: E402
from ff9mapkit.workspace import forms_qt                      # noqa: E402
from ff9mapkit.workspace.battledoc import BattleDoc           # noqa: E402
from ff9mapkit.workspace.forms_qt import CatalogLibrary, CatalogPicker  # noqa: E402
from ff9mapkit.workspace.shell import pick_palette            # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    loc._MEMO.clear()
    forms_qt._locate_mod = None                                # drop the module-level hook memo between tests
    yield
    loc._MEMO.clear()
    forms_qt._locate_mod = None


def _warm_map():
    return loc.BattleMap(
        version=loc.CACHE_VERSION,
        census={250: {"random": [67], "scripted": [], "computed": False}},
        scene_sites={67: [(250, "random")]},
        field_arc={250: "evil_forest"},
        arcs={"evil_forest": {"name": "Evil Forest", "zone": "evft"}},
        classification={67: "placed"},
        names={67: {"typecount": 2, "atkcount": 3,
                    "names": {"us": ["Goblin", "Fang"]},
                    "attacks": {"us": ["Knife", "Goblin Punch", None]}}},
        scene_count=856, field_count=1,
    )


def _inject(bm):
    loc._MEMO[loc._memo_key(None)] = bm


def _select_encounter(lib):
    idx = lib._cat_kinds.index("encounter")                    # raises if the section is missing (the fence)
    lib.cats.setCurrentRow(idx)
    return idx


# ---------------------------------------------------------------- TAILOR: the library hears the dial ---
def _room_the_library(app, lib):
    """Show the library and give it a box that HOLDS the sidebar's ask plus the other panes' floors,
    then re-run the production allocation. Needed because the sidebar-ask fences are claims about a
    ROOMY screen: under offscreen's ~800px fake screen (which any batch importing an offscreen-pinning
    module inherits at collection time) the box clamps too small to hold the detail pane's button-bar
    floor, the allocation lawfully makes the SIDEBAR yield, and an outcome assert measures the squeeze
    instead of the mechanism. WA_DontShowOnScreen means no WM, so the resize is honored anywhere."""
    from PySide6.QtCore import Qt

    lib.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    lib.show()
    app.processEvents()
    assert lib._panes_set, "showEvent never ran the pane allocation"
    need = (lib.cats.maximumWidth() + lib._split.widget(1).minimumSizeHint().width()
            + lib._split.widget(2).minimumSizeHint().width() + 80)
    if lib.width() < need:
        lib.resize(need, lib.height())
        app.processEvents()
        lib._allocate_panes()
        app.processEvents()


def test_the_library_box_is_a_function_of_its_font(app):
    """TAILOR's last deliberate skip, converted: resize(900, 580) was one font at one scale. The box,
    the sidebar cap, and the pane split must now DERIVE from the dialog's own polished font -- asserted
    as formula equality (the same inputs on both sides, so offscreen's inflated advances cancel out).
    The split is asserted SHOWN and ROOMY (see _room_the_library): the panes are allocated at first
    show, where the splitter's width is finally real -- a never-laid-out splitter lies about it, and
    QSplitter settles an oversubscribed request by shaving EVERY pane, which is how the shipped
    ctor-time request opened the library with an h-scrollbar on its own category sidebar."""
    from PySide6.QtGui import QFontMetricsF

    lib = CatalogLibrary(None, None, pick_palette("dark"))
    fm = QFontMetricsF(lib.font())
    screen = lib.screen() or QApplication.primaryScreen()
    avail = screen.availableGeometry()
    assert lib.width() == min(round(fm.averageCharWidth() * 140), int(avail.width() * 0.92))
    assert lib.height() == min(round(fm.height() * 30), int(avail.height() * 0.85))
    _room_the_library(app, lib)
    try:
        frame = 2 * lib.cats.frameWidth()
        want = min(lib.cats.sizeHintForColumn(0) + frame + lib.cats.verticalScrollBar().sizeHint().width() + 8,
                   round(fm.averageCharWidth() * 34))
        assert lib.cats.maximumWidth() == want, "the sidebar asks for its own longest row, ch-capped"
        assert lib._split.sizes()[0] == want, "the splitter must actually GIVE the sidebar its ask"
    finally:
        lib.close()


def test_the_library_sidebar_never_scrolls_sideways_under_the_app_sheet(app):
    """THE REGRESSION FENCE, red on the shipped block: under the real app QSS the ctor-time split
    request (summed to the DIALOG's width, against a never-laid-out splitter, blind to the detail
    pane's ~451px button-bar floor) was settled by a proportional shave of every pane, and the library
    opened with an h-scrollbar on its own category sidebar (viewport 134 vs col hint 156, range 22,
    measured 2026-07-28). The app sheet is restored in a finally so this test never pollutes later
    modules (the round-9 disease)."""
    from ff9mapkit.workspace import style

    inst = QApplication.instance()
    inst.setStyleSheet(style.qss(pick_palette("dark")))
    try:
        lib = CatalogLibrary(None, None, pick_palette("dark"))
        _room_the_library(inst, lib)
        try:
            assert lib.cats.horizontalScrollBar().maximum() == 0, \
                "the category sidebar must fit its own longest row under the app QSS"
            assert lib._split.sizes()[0] == lib.cats.maximumWidth()
        finally:
            lib.close()
    finally:
        inst.setStyleSheet("")


def test_the_help_badge_keeps_its_glyph_at_150(app):
    """THE REGRESSION FENCE, red on the shipped badge: a frozen setFixedSize(30, 30) box + the sheet's
    SCALED button padding (the old widget stylesheet set fill and font, never padding) left the "?" a
    zero-ink empty circle at 150% (measured ink px: 14 at 100 -> 0 at 150). The box now lives in the
    sheet, keyed to badge_box(scale, HELP_HALF) with padding 0 -- so at 150 the box must hear the dial
    and the glyph must actually render. Sheet and module scale are restored in a finally (the round-9
    disease)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton

    from ff9mapkit.editor.theme import derive
    from ff9mapkit.workspace import style

    inst = QApplication.instance()
    inst.setStyleSheet(style.qss(pick_palette("dark"), scale=150))
    forms_qt.set_text_scale(150)
    try:
        lib = CatalogLibrary(None, None, pick_palette("dark"))
        lib.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        lib.show()
        inst.processEvents()
        try:
            helpb = lib.findChild(QPushButton, "libraryHelp")
            assert helpb is not None, "the badge lost its objectName -- the sheet rule reaches nothing"
            assert helpb.width() == style.badge_box(150, style.HELP_HALF), \
                "the badge box must hear the dial (a frozen 30px box is the shipped defect)"
            ink = derive(dict(pick_palette("dark")))["help_fg"].lstrip("#")
            want = tuple(int(ink[i:i + 2], 16) for i in (0, 2, 4))
            img = helpb.grab().toImage()
            n = sum(1 for x in range(img.width()) for y in range(img.height())
                    if all(abs(a - b) <= 60 for a, b in zip(img.pixelColor(x, y).getRgb()[:3], want)))
            assert n > 0, "the ? glyph rendered ZERO ink pixels -- an empty violet circle"
        finally:
            lib.close()
    finally:
        inst.setStyleSheet("")
        forms_qt.set_text_scale(100)


def test_the_library_grows_with_its_font(app):
    """The relationship half: a bigger base font must widen the sidebar's cap. The cap is the proxy on
    purpose -- the outer box hits the screen clamp on offscreen's ~800px fake screen (fit_dialog's own
    documented trap: growth fences need a measure the clamp can't eat). The app font is restored in a
    finally so this test never pollutes the worker's later modules (the round-9 disease)."""
    from PySide6.QtGui import QFont

    inst = QApplication.instance()
    base = QFont(inst.font())
    small = CatalogLibrary(None, None, pick_palette("dark")).cats.maximumWidth()
    big_font = QFont(base)
    ps = base.pointSize()
    big_font.setPointSize((ps if ps > 0 else 12) * 2)
    inst.setFont(big_font)
    try:
        big = CatalogLibrary(None, None, pick_palette("dark")).cats.maximumWidth()
    finally:
        inst.setFont(base)
    assert big > small, "the sidebar cap must hear the font it caps"


# ------------------------------------------------------------------------- (a) the Encounters section ---
def test_library_has_an_encounters_section_even_cold(app):
    # picker-only kind -> the sidebar count comes from the build-free encounter_entries(), so the section is
    # present (baked fallback is never empty) WITHOUT triggering a census at dialog-open.
    lib = CatalogLibrary(None, None, pick_palette("dark"))
    assert "encounter" in lib._cat_kinds, "the Encounters section shows even on a cold cache"


def test_library_encounters_warm_rows_and_rich_detail(app):
    _inject(_warm_map())
    lib = CatalogLibrary(None, None, pick_palette("dark"))
    _select_encounter(lib)                                      # -> _refresh_list over kind='encounter'
    assert [e.ident for e in lib._entries] == [67]
    assert "Goblin" in lib._entries[0].name and "Evil Forest" in lib._entries[0].name
    lib.lst.setCurrentRow(0)                                    # -> _describe -> infohub.detail(scene_usage_fn)
    html = lib.detail.toPlainText()
    assert "Goblin" in html and "Knife" in html and "Evil Forest" in html
    assert "[encounter]" in html                                # the ready-to-paste snippet
    # Copy snippet puts the [encounter] block on the clipboard
    lib._copy_snippet()
    assert QApplication.clipboard().text().startswith("[encounter]\nscene = 67")


def test_build_button_shown_only_on_the_encounters_section(app):
    _inject(_warm_map())
    lib = CatalogLibrary(None, None, pick_palette("dark"))
    lib.cats.setCurrentRow(0)                                   # 'All'
    # the dialog is never shown headlessly, so isVisible() is always False -- isHidden() reflects the
    # explicit setVisible() toggle this section makes.
    assert lib.build_btn.isHidden()
    _select_encounter(lib)
    assert not lib.build_btn.isHidden(), "the Build button appears on the Encounters section"


def test_scene_usage_cold_returns_none_without_building(app, monkeypatch):
    # the load-bearing fix: opening a scene/encounter detail on a COLD cache must NOT run the census on the
    # GUI thread. _scene_usage probes cached_map() and bails to None -- _build_fresh is never reached.
    def _boom(*a, **k):
        raise AssertionError("_scene_usage must never trigger a cold build on the GUI thread")
    monkeypatch.setattr(loc, "_build_fresh", _boom)
    assert forms_qt._scene_usage(67) is None


def test_scene_usage_warm_carries_attacks(app):
    _inject(_warm_map())
    info = forms_qt._scene_usage(67)
    assert info is not None
    assert info["enemies"] == ["Goblin", "Fang"]
    assert info["attacks"] == ["Knife", "Goblin Punch"]        # the dead None slot dropped
    assert info["classification"] == "placed"


def test_build_index_warm_just_refreshes_no_thread(app, monkeypatch):
    # already warm -> _build_index refreshes the section and does NOT enter the busy/thread path.
    _inject(_warm_map())
    monkeypatch.setattr(loc, "_build_fresh",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not build when warm")))
    lib = CatalogLibrary(None, None, pick_palette("dark"))
    _select_encounter(lib)
    lib._build_index()
    assert lib._index_busy is False
    assert [e.ident for e in lib._entries] == [67]


def test_build_index_runs_off_thread_then_refreshes(app, monkeypatch):
    warm = _warm_map()

    def _stub_build(*a, **k):
        loc._MEMO[loc._memo_key(None)] = warm                  # the worker warms the memo
        return warm
    monkeypatch.setattr(loc, "build_map", _stub_build)

    class _SyncThread:                                         # run the "worker" synchronously on this thread
        def __init__(self, target=None, **k):
            self._t = target

        def start(self):
            self._t()
    monkeypatch.setattr(forms_qt.threading, "Thread", _SyncThread)

    lib = CatalogLibrary(None, None, pick_palette("dark"))
    _select_encounter(lib)
    assert [e.ident for e in lib._entries] != [67] or not lib._entries  # cold: baked fallback (not the warm row)
    lib._build_index()                                         # cold -> worker builds -> _on_index_ready(None)
    assert lib._index_busy is False
    assert lib.build_btn.text() == "Rebuild battle index"
    assert [e.ident for e in lib._entries] == [67]             # now warm: the single rich row


def test_on_index_ready_error_warns_without_crashing(app, monkeypatch):
    seen = []
    # Swap forms_qt's QMessageBox NAME for a stub -- never a patch of the live Qt class (the
    # shiboken override-cache poison, studies/pyside-gc-crash); _on_index_ready resolves
    # `QMessageBox.warning` through the module global at call time.
    monkeypatch.setattr(forms_qt, "QMessageBox", SimpleNamespace(
        warning=lambda *a, **k: seen.append(a) or None))
    lib = CatalogLibrary(None, None, pick_palette("dark"))
    lib._index_busy = True
    lib.build_btn.setEnabled(False)
    lib._on_index_ready(RuntimeError("no install"))
    assert seen, "a build error is surfaced, not swallowed"
    assert lib._index_busy is False and lib.build_btn.isEnabled()


# ------------------------------------------------------------------ (b) the Encounter form pick-and-fill ---
def test_encounter_spec_scene_field_points_at_the_rich_picker():
    from ff9mapkit.editor.forms import ENCOUNTER_SPEC
    scene_f = next(f for f in ENCOUNTER_SPEC if f.key == "scene")
    assert scene_f.catalog == "encounter,scene", "encounter (rich) first, scene (baked) as the fallback"


def test_catalog_picker_over_encounter_scene_returns_the_scene_id(app):
    _inject(_warm_map())
    dlg = CatalogPicker(None, ["encounter", "scene"], "", None, pick_palette("dark"), want_id=True)
    assert dlg._entries, "the picker lists rows for encounter+scene"
    assert dlg._entries[0].kind == "encounter", "the rich encounter row sorts first (it's in `extra`)"
    dlg.lst.setCurrentRow(0)
    dlg._ok()
    assert dlg.result == "67", "want_id returns the numeric scene id string"


# --------------------------------------------------------------------- (c) battledoc location panel ---
def test_location_panel_warm_returns_a_panel(app, monkeypatch):
    _inject(_warm_map())
    monkeypatch.setattr(loc, "_build_fresh",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not build")))
    doc = BattleDoc(pick_palette("dark"))
    panel = doc._location_panel({"scene_id": 67})
    assert isinstance(panel, QWidget), "a warm map yields a 'Fought in the real game' facts panel"


def test_location_panel_cold_and_absent_return_none(app, monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("_location_panel must never build")
    monkeypatch.setattr(loc, "_build_fresh", _boom)
    doc = BattleDoc(pick_palette("dark"))
    assert doc._location_panel({"scene_id": 67}) is None       # cold cache -> no panel, no build
    assert doc._location_panel({}) is None                     # no scene id -> no panel
