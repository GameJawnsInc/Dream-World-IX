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
