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


def test_a_root_with_brackets_in_its_path_still_finds_its_bundles(tmp_path, monkeypatch):
    """The no-bundles check globbed StreamingAssets/p0data*.bin, and a glob reads '[...]' in the path as a set: an
    install under such a path, with its bundles, was refused as having none (review of the perf commits)."""
    game = tmp_path / "Games [Steam]"
    (game / "StreamingAssets").mkdir(parents=True)
    (game / "StreamingAssets" / "p0data3.bin").write_bytes(b"a bundle")
    reached = []
    monkeypatch.setattr(X, "_unitypy", lambda: reached.append(1) or (_ for _ in ()).throw(RuntimeError("stop")))
    monkeypatch.setattr(X, "_WM_ENV_MEMO", {})
    with pytest.raises(RuntimeError, match="stop"):
        X._worldmap_env(1, game=game)                                    # past the check, to the bundle load
    assert reached == [1]
