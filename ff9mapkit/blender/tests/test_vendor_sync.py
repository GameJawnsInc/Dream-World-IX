"""Drift guard: the vendored scene math must stay byte-identical to the canonical source.

The add-on vendors cam/bgi/bgx so it is self-contained in Blender. This test fails if they
drift from `ff9mapkit/scene/*` — run `python build_addon.py` (sync_vendor) to re-sync.
"""

from __future__ import annotations

from pathlib import Path

import pytest

BLENDER = Path(__file__).resolve().parents[1]          # .../ff9mapkit/blender
VENDOR = BLENDER / "ff9mapkit_blender" / "vendor"
SCENE = BLENDER.parent / "ff9mapkit" / "scene"         # .../ff9mapkit/ff9mapkit/scene


@pytest.mark.parametrize("name", ["cam.py", "bgi.py", "bgx.py", "guide.py"])
def test_vendor_matches_source(name):
    assert (VENDOR / name).read_bytes() == (SCENE / name).read_bytes(), \
        f"vendor/{name} drifted from ff9mapkit/scene/{name}; run build_addon.py to re-sync"
