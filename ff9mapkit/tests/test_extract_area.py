"""The custom-scene area-safety rule used by `ff9mapkit import` (offline; no game data needed).

Importing real fields needs UnityPy + p0data (not in CI), so the import writers themselves are
verified live. This pins the one piece of pure logic they share: a single-digit source area (0-9)
black-screens via the engine's 'FBG_N<area>' lookup, so an editable (custom-scene) fork must remap
it to a safe area, while BG-borrow can't express it at all. ``extract`` imports UnityPy lazily, so
importing the module here does not require it.
"""

from __future__ import annotations

import os

from ff9mapkit import extract


def test_safe_custom_area_remaps_low_areas():
    assert extract.MIN_CUSTOM_AREA == 10
    for low in range(0, 10):
        assert extract.safe_custom_area(low) == 11      # 0-9 -> a safe >= 10 area
    for ok in (10, 11, 36, 57):
        assert extract.safe_custom_area(ok) == ok       # >= 10 kept as-is


# --- _load_env: the in-process static-bundle cache (stops the suite re-reading the 68 MB event bundle
#     on every install-gated call -- the cold re-read that amplified under CPU/disk contention). ----------
class _FakeUnityPy:
    """Stand-in for UnityPy: each .load() is a real (counted) parse returning a fresh env object."""

    def __init__(self):
        self.loaded: list[str] = []

    def load(self, p):
        self.loaded.append(p)
        return object()


def test_load_env_memoizes_a_static_bundle(monkeypatch, tmp_path):
    extract._STREAM_ENV_CACHE.clear()
    fake = _FakeUnityPy()
    monkeypatch.setattr(extract, "_unitypy", lambda: fake)
    p = tmp_path / "p0data7.bin"
    e1 = extract._load_env(p)
    e2 = extract._load_env(p)
    e3 = extract._load_env(str(p))                       # str vs Path resolve to the same abspath key
    assert e1 is e2 is e3                                # one parse, reused -> no cold re-read
    assert fake.loaded == [os.path.abspath(str(p))]      # loaded exactly once
    extract._STREAM_ENV_CACHE.clear()


def test_load_env_lru_bounds_memory_and_keeps_the_hot_bundle(monkeypatch, tmp_path):
    extract._STREAM_ENV_CACHE.clear()
    fake = _FakeUnityPy()
    monkeypatch.setattr(extract, "_unitypy", lambda: fake)
    cap = extract._STREAM_ENV_CACHE_MAX
    hot = tmp_path / "p0data7.bin"                        # the constantly-touched event bundle
    extract._load_env(hot)
    for i in range(cap + 3):                              # churn more cold field bundles than the cap
        extract._load_env(hot)                            # re-touch hot first -> recency protects it
        extract._load_env(tmp_path / f"p0data{i}.bin")
    assert len(extract._STREAM_ENV_CACHE) <= cap          # bounded (can't grow unbounded over a long run)
    assert fake.loaded.count(os.path.abspath(str(hot))) == 1   # hot never re-loaded (LRU kept it resident)
    n = len(fake.loaded)
    extract._load_env(hot)
    assert len(fake.loaded) == n                          # still a cache hit, not a reload
    extract._STREAM_ENV_CACHE.clear()
