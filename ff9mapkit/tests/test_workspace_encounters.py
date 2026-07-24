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
def test_the_library_box_is_a_function_of_its_font(app):
    """TAILOR's last deliberate skip, converted: resize(900, 580) was one font at one scale. The box,
    the sidebar cap, and the pane split must now DERIVE from the dialog's own polished font -- asserted
    as formula equality (the same inputs on both sides, so offscreen's inflated advances cancel out)."""
    from PySide6.QtGui import QFontMetricsF

    lib = CatalogLibrary(None, None, pick_palette("dark"))
    fm = QFontMetricsF(lib.font())
    screen = lib.screen() or QApplication.primaryScreen()
    avail = screen.availableGeometry()
    assert lib.width() == min(round(fm.averageCharWidth() * 140), int(avail.width() * 0.92))
    assert lib.height() == min(round(fm.height() * 30), int(avail.height() * 0.85))
    frame = 2 * lib.cats.frameWidth()
    want = min(lib.cats.sizeHintForColumn(0) + frame + lib.cats.verticalScrollBar().sizeHint().width() + 8,
               round(fm.averageCharWidth() * 34))
    assert lib.cats.maximumWidth() == want, "the sidebar asks for its own longest row, ch-capped"


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
    monkeypatch.setattr(forms_qt.QMessageBox, "warning",
                        lambda *a, **k: seen.append(a) or None)
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
