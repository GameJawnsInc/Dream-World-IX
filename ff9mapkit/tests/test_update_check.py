"""update_check: the opt-in PyPI update check (offline-tolerant, stdlib-only)."""

import json

import pytest

from ff9mapkit import update_check as uc


@pytest.fixture
def state(tmp_path, monkeypatch):
    """Point the persistent state at a throwaway file."""
    p = tmp_path / "update_check.json"
    monkeypatch.setattr(uc, "_state_path", lambda: p)
    return p


# ---- version ordering ----
@pytest.mark.parametrize("latest,current,expect", [
    ("1.0.0b9", "1.0.0b8", True),
    ("1.0.0b10", "1.0.0b8", True),          # not a string compare ("b10" < "b8" lexically)
    ("1.0.0", "1.0.0b8", True),             # a final release beats its own prereleases
    ("1.0.1", "1.0.0", True),
    ("1.0.0b8", "1.0.0b8", False),          # same
    ("1.0.0b7", "1.0.0b8", False),          # older
    ("1.0.0b8", "1.0.0", False),            # prerelease is older than the final
    ("", "1.0.0b8", False),                 # missing latest
    ("garbage", "1.0.0b8", False),          # unparseable -> conservative False
])
def test_is_newer(latest, current, expect):
    assert uc.is_newer(latest, current) is expect


def test_vkey_orders_prerelease_below_final():
    assert uc._vkey("1.0.0b8") < uc._vkey("1.0.0")
    assert uc._vkey("1.0.0a9") < uc._vkey("1.0.0b1") < uc._vkey("1.0.0rc1") < uc._vkey("1.0.0")
    assert uc._vkey("not-a-version") is None


# ---- network fetch (mocked) ----
def test_fetch_latest_parses_pypi_json(monkeypatch):
    class _Resp:
        def __init__(self, b): self._b = b
        def read(self, *a): return self._b
        def __enter__(self): return self
        def __exit__(self, *a): return False
    payload = json.dumps({"info": {"version": "1.2.3"}}).encode()
    monkeypatch.setattr(uc.urllib.request, "urlopen", lambda req, timeout=None: _Resp(payload))
    assert uc.fetch_latest() == "1.2.3"


def test_fetch_latest_offline_is_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")
    monkeypatch.setattr(uc.urllib.request, "urlopen", boom)
    assert uc.fetch_latest() is None        # degrades, never raises


# ---- preferences + the daily gate ----
def test_preference_roundtrip(state):
    assert uc.was_prompted() is False
    assert uc.is_enabled() is False
    uc.set_preference(True)
    assert uc.was_prompted() is True
    assert uc.is_enabled() is True
    uc.set_preference(False)
    assert uc.was_prompted() is True        # still prompted
    assert uc.is_enabled() is False


def test_should_check_now_gates_on_optin_and_interval(state):
    assert uc.should_check_now(now=1000) is False           # not enabled
    uc.set_preference(True)
    assert uc.should_check_now(now=1000) is True            # enabled, never checked
    uc.record_check("1.0.0b8", now=1000)
    assert uc.should_check_now(now=1000 + 60) is False      # checked a minute ago
    assert uc.should_check_now(now=1000 + uc.CHECK_INTERVAL_S + 1) is True   # a day later


def test_check_records_and_reports(state, monkeypatch):
    monkeypatch.setattr(uc, "fetch_latest", lambda *a, **k: "9.9.9")
    res = uc.check(now=5000)
    assert res == {"current": uc.INSTALLED, "latest": "9.9.9", "ok": True, "newer": True}
    assert json.loads(state.read_text())["last_check"] == 5000
    assert json.loads(state.read_text())["last_seen_latest"] == "9.9.9"


def test_check_offline_is_safe(state, monkeypatch):
    monkeypatch.setattr(uc, "fetch_latest", lambda *a, **k: None)
    res = uc.check(now=5000)
    assert res["ok"] is False and res["newer"] is False
    assert json.loads(state.read_text())["last_check"] == 5000   # still stamps the attempt
