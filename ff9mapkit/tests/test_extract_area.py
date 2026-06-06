"""The custom-scene area-safety rule used by `ff9mapkit import` (offline; no game data needed).

Importing real fields needs UnityPy + p0data (not in CI), so the import writers themselves are
verified live. This pins the one piece of pure logic they share: a single-digit source area (0-9)
black-screens via the engine's 'FBG_N<area>' lookup, so an editable (custom-scene) fork must remap
it to a safe area, while BG-borrow can't express it at all. ``extract`` imports UnityPy lazily, so
importing the module here does not require it.
"""

from __future__ import annotations

from ff9mapkit import extract


def test_safe_custom_area_remaps_low_areas():
    assert extract.MIN_CUSTOM_AREA == 10
    for low in range(0, 10):
        assert extract.safe_custom_area(low) == 11      # 0-9 -> a safe >= 10 area
    for ok in (10, 11, 36, 57):
        assert extract.safe_custom_area(ok) == ok       # >= 10 kept as-is
