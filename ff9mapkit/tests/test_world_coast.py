"""world-coast: place a REAL FF9 coastal block at ocean cells (Path D faithful coast) -- copy the donor's terrain +
write the Donor.txt sidecar that the engine's per-cell divert reads to render the donor's beach/sea/foam.

Hermetic: the copy+sidecar orchestration (right override + sidecar per cell, donor terrain carried verbatim, dry-run
writes nothing, validation) with read_block/deploy stubbed; one game-gated test that real coastal donors are found.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import extract as X, mesh as M, terrain as T


def _fake_block(x, y, tris=4):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    n = tris * 3
    chan = {CH_POS: [[0.0, 0.0, 0.0]] * n, CH_NRM: [[0.0, 1.0, 0.0]] * n,
            CH_UV: [[0.5, 0.5]] * n, CH_TAN: [[236.0, 0.0, 0.0, 1.0]] * n}
    return BlockMesh(name=f"Block[{x}][{y}] Terrain", disc=1, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays=chan, flat_index=list(range(n)),
                     tris=[[i, i + 1, i + 2] for i in range(0, n, 3)], raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


def test_donor_sidecar_relpath():
    assert M.donor_sidecar_relpath(1, 2, 17) == "FF9_Data/WorldMap/Disc1/0_1/r17/Block[2][17] Donor.txt"
    assert M.donor_sidecar_relpath(4, 12, 10) == "FF9_Data/WorldMap/Disc4/0_1/r10/Block[12][10] Donor.txt"


def test_coast_copies_donor_and_writes_sidecar(monkeypatch):
    donor_bm = _fake_block(18, 15, tris=6)
    overrides, sidecars = [], []
    monkeypatch.setattr(X, "read_block", lambda dx, dy, **k: donor_bm if (dx, dy) == (18, 15) else _fake_block(dx, dy))
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: overrides.append((bm.x, bm.y, bm.vcount, k.get("part"))))
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: sidecars.append((dx, dy, k["x"], k["y"])))
    s = T.coast("MOD", cells=[(2, 17), (2, 18)], donor=(18, 15))
    assert s["op"] == "coast" and s["donor"] == [18, 15]
    # donor's 18 verts (6 tris) copied VERBATIM to each target cell as a Terrain override
    assert overrides == [(2, 17, 18, "Terrain"), (2, 18, 18, "Terrain")]
    # each cell gets a Donor.txt naming the donor (18,15)
    assert sidecars == [(18, 15, 2, 17), (18, 15, 2, 18)]
    # the copy does NOT mutate the shared donor mesh
    assert donor_bm.x == 18 and donor_bm.y == 15


def test_coast_dry_run_writes_nothing(monkeypatch):
    overrides = []
    monkeypatch.setattr(X, "read_block", lambda dx, dy, **k: _fake_block(dx, dy))
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: overrides.append(1))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: overrides.append(1))
    s = T.coast("MOD", cells=[(2, 17)], donor=(18, 15), dry_run=True)
    assert s["cells"] and s["dry_run"] is True and overrides == []


def test_coast_validates_grid(monkeypatch):
    monkeypatch.setattr(X, "read_block", lambda dx, dy, **k: _fake_block(dx, dy))
    with pytest.raises(ValueError):
        T.coast("MOD", cells=[(2, 20)], donor=(18, 15), dry_run=True)   # cell off-grid
    with pytest.raises(ValueError):
        T.coast("MOD", cells=[(2, 17)], donor=(24, 15), dry_run=True)   # donor off-grid


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_list_coastal_donors_finds_beaches():
    donors = X.list_coastal_donors(disc=1, beach_only=True)
    assert (18, 15) in donors                                  # the proven beach donor
    assert all(any(s.startswith("beach") for s in subs) for subs in donors.values())
