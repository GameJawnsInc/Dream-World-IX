"""Shared test fixtures.

The one autouse fixture isolates the per-user PREFS STORE: several GUI tests construct a full
``Workspace`` whose Home tab reads (and whose open-project paths write) ``prefs.json`` -- without
isolation the suite would read the developer's real theme/recent-projects file and could write test
paths into it. Redirected per-test to a tmp file; tests that want their own store just monkeypatch
``prefs._path`` again on top.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_prefs(tmp_path, monkeypatch):
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")


@pytest.fixture()
def qt_drain():
    """Deterministically destroy a test's leftover top-level Qt widgets (close + deleteLater +
    drain the deferred deletions). THE GC-CHILD LAW's teardown half: leaving a whole
    view->scene->items graph to a FORCED garbage-collection pass (pytest's unraisable plugin
    runs gc_collect_harder) can double-free in shiboken (VERSION-independent — the root cause
    is the parentItem() ownership flip, studies/pyside-gc-crash/NOTES.md): order-random wrapper
    finalization over an already-dead C++ graph. Qt's own deleteLater path destroys the graph
    with the wrappers still alive, which shiboken handles correctly. Use as an autouse
    per-module teardown ONLY in modules that build widgets per test — never where a
    module-scoped fixture caches one (test_coop_tab's Workspace would die mid-module)."""
    def drain():
        import sys
        qtw = sys.modules.get("PySide6.QtWidgets")
        if qtw is None:
            return
        app = qtw.QApplication.instance()
        if app is None:
            return
        # PARK, do not destroy: destroying (deleteLater OR letting GC take the graph) leaves
        # wrapper finalization order to chance, and shiboken intermittently
        # double-frees there (~1 in 5 suite runs, measured, with every ownership fix in
        # place; gc.freeze made it WORSE — frozen wrappers still finalize at shutdown).
        # Keeping the widgets ALIVE in a process-global list means no Qt C++ graph ever dies
        # under GC: hidden windows idle at ~0 cost and the OS reclaims everything at process
        # end. A bounded leak in a TEST process, traded for a deterministic suite.
        for w in qtw.QApplication.topLevelWidgets():
            if w not in _QT_PARKED:
                w.hide()
                _QT_PARKED.append(w)
        app.processEvents()
    return drain


_QT_PARKED = []                                    # keep-alive: see qt_drain
