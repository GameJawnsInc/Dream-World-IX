"""Coast-nav stamp plumbing: the synthetic-namespace loader guard + the worldmap-env negative memo.

THE 928-LOAD PROFILE (2026-07-30): a coast-nav stamp on Disc9 spent 97% of its 169s/cell inside
UnityPy, because ``_Loader.parts`` fell through ``read_block_stacked``'s stock fallback on a disc no
bundle serves, and ``_worldmap_env`` memoized only WINNERS -- every miss rescanned all ~50 p0data
bundles. Two guards fixed it (169s/cell -> ~0.2s/cell, results byte-identical per the Disc9 gate
probe); these tests pin both so neither silently regresses.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.world import coastnav as CN
from ff9mapkit.world import extract as WX


def _mesh_bytes(topo: int = 57) -> bytes:
    """A minimal F9WM sea mesh: 3 verts, 1 tri, tangents present (flags=4)."""
    verts = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 0.0, -8.0)]
    out = bytearray()
    out += b"F9WM" + struct.pack("<iiii", 1, 3, 3, 4)
    for v in verts:
        out += struct.pack("<3f", *v)
    for _ in verts:
        out += struct.pack("<4f", float(topo << 2), 0.0, 0.0, 0.0)
    out += struct.pack("<3i", 0, 1, 2)
    return bytes(out)


def test_synthetic_loader_never_touches_the_stock_fallback(monkeypatch, tmp_path):
    """On a synthetic disc the loader reads deployed overrides ONLY -- the stacked read's stock
    fallback (a full p0data rescan per missing part) must be unreachable."""
    from ff9mapkit import config
    from ff9mapkit.world import entrance as EN
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def _boom(*a, **k):
        raise AssertionError("stock fallback reached on a synthetic namespace")

    monkeypatch.setattr(EN, "read_block_stacked", _boom)
    monkeypatch.setattr(WX, "read_block", _boom)
    p = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1" / "r10" / "Block[12][10] Sea4.ff9mesh"
    p.parent.mkdir(parents=True)
    p.write_bytes(_mesh_bytes())
    loader = CN._Loader("MOD", 9)
    parts = loader.parts(12, 10)
    assert [nm for nm, _, _ in parts] == ["Sea4"], "the deployed override must load, nothing else"
    assert loader.parts(11, 10) == [], "a cell with no override is empty, not a stock read"


def test_real_disc_loader_still_uses_the_stacked_read(monkeypatch):
    """Disc 1/4 keep the override-over-stock stacked semantics -- and scan exactly the
    engine's one registration order (audit rec 11: the local PARTS_ORDER copy is gone)."""
    from ff9mapkit.world import entrance as EN
    from ff9mapkit.world import placement as P
    calls = []
    monkeypatch.setattr(EN, "read_block_stacked",
                        lambda mod, x, y, **k: calls.append((x, y, k["part"], k["disc"])) or None)
    assert CN._Loader("MOD", 1).parts(5, 5) == []
    assert [c[2] for c in calls] == [p.lower() for p in P.REGISTRATION_ORDER]
    assert all(c[3] == 1 for c in calls)


def test_worldmap_env_memoizes_the_negative(monkeypatch, tmp_path):
    """A disc with no winning bundle pays the full bundle scan ONCE per process, not per call."""
    monkeypatch.setattr(WX, "_streaming_assets", lambda game=None: tmp_path)
    monkeypatch.setattr(WX, "_unitypy", lambda: None)
    scans = []
    monkeypatch.setattr(WX, "_bundles", lambda game=None: scans.append(1) or [])
    WX._WM_ENV_MEMO.clear()
    with pytest.raises(ValueError):
        WX._worldmap_env(disc=9)
    with pytest.raises(ValueError):
        WX._worldmap_env(disc=9)
    assert len(scans) == 1, "the second miss must come from the memo, not another rescan"
    WX._WM_ENV_MEMO.clear()
