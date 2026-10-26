"""extract._worldmap_env on a root with no bundles (PERF.md 5, K4): every world-* job into a draft attempts the
disc-4 mirror, whose game root (the draft's parent) has no StreamingAssets bundles -- and it imported UnityPy first
(about 1 s of attrs codegen) only to log that the mirror did NOT RUN. A root with no p0data*.bin refuses with the
same error, memoized the same way, without importing it."""
from __future__ import annotations

import pytest

from ff9mapkit.world import extract as X


def test_a_root_with_no_bundles_refuses_without_importing_unitypy(tmp_path, monkeypatch):
    (tmp_path / "StreamingAssets").mkdir()
    imported = []
    monkeypatch.setattr(X, "_unitypy", lambda: imported.append(1))
    monkeypatch.setattr(X, "_WM_ENV_MEMO", {})
    for _ in range(2):                                    # the second answer is the memo's
        with pytest.raises(ValueError, match=r"no worldmap terrain meshes \(container 'worldmap/disc4/0_1/'\)"):
            X._worldmap_env(4, game=tmp_path)
    assert imported == [] and len(X._WM_ENV_MEMO) == 1
