"""world-terrain: reshape walkable overworld terrain across every block a deform touches (seamless, world-space).

Hermetic: the block-index math, and the orchestration (which blocks get read/deformed/deployed, sea skipped, the
right deform op dispatched, dry-run writes nothing) with the extract/mesh calls stubbed.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from ff9mapkit.world import terrain as T, extract as X, mesh as M


def test_block_index_range():
    # a hill at world (1054,-951) r16 spans blocks bx=16, by=14..15 (Z negated: by = floor(-z/64))
    assert T._block_index_range(1054 - 16, 1054 + 16, -951 - 16, -951 + 16) == (16, 16, 14, 15)
    # a point at a block interior -> a single block
    assert T._block_index_range(1030, 1030, -910, -910) == (16, 16, 14, 14)


def _stub(monkeypatch, sea=(), moved_for=None):
    """Stub extract/mesh so reshape() runs offline. `sea` blocks raise (no terrain); `moved_for` maps block->moved."""
    calls = {"deform": [], "deploy": []}

    def fake_read(bx, by, **k):
        if (bx, by) in sea:
            raise ValueError("sea")
        return SimpleNamespace(block=(bx, by))

    def fake_deform(name):
        def f(ter, **k):
            n = (moved_for or {}).get(ter.block, 5)
            calls["deform"].append((name, ter.block))
            return n
        return f

    monkeypatch.setattr(X, "read_block", fake_read)
    monkeypatch.setattr(X, "block_world_origin", lambda bx, by: (bx * 64, -by * 64))
    monkeypatch.setattr(M, "deform_radial", fake_deform("radial"))
    monkeypatch.setattr(M, "deform_ridge", fake_deform("ridge"))
    monkeypatch.setattr(M, "flatten_region", fake_deform("flatten"))
    monkeypatch.setattr(M, "deploy_override", lambda ter, **k: calls["deploy"].append(ter.block))
    return calls


def test_reshape_multiblock_skips_sea_and_zero(monkeypatch):
    # (16,15) is sea; (16,14) moves 259; imagine a 3rd in-range block that moves 0 -> not deployed
    calls = _stub(monkeypatch, sea={(16, 15)}, moved_for={(16, 14): 259})
    s = T.reshape("MOD", at=(1054.0, -951.0), radius=16.0, amount=6.0)
    assert [b["block"] for b in s["blocks"]] == [[16, 14]] and s["blocks"][0]["moved"] == 259
    assert s["skipped_sea"] == [[16, 15]]
    assert calls["deploy"] == [(16, 14)] and calls["deform"][0] == ("radial", (16, 14))
    assert s["op"] == "raise"


def test_reshape_dispatch_and_signs(monkeypatch):
    calls = _stub(monkeypatch)
    assert T.reshape("MOD", at=(1030, -910), radius=8, amount=-4)["op"] == "lower"       # negative -> crater
    assert T.reshape("MOD", at=(1030, -910), radius=8, flatten=True)["op"] == "flatten"
    assert T.reshape("MOD", seg=((1030, -910), (1050, -930)), radius=6, amount=5)["op"] == "ridge+"
    ops = {c[0] for c in calls["deform"]}
    assert ops == {"radial", "flatten", "ridge"}                                          # each op dispatched


def test_reshape_dry_run_writes_nothing(monkeypatch):
    calls = _stub(monkeypatch)
    s = T.reshape("MOD", at=(1030, -910), radius=8, amount=6, dry_run=True)
    assert s["blocks"] and s["dry_run"] is True and calls["deploy"] == []                 # deformed but not deployed


def test_reshape_validation(monkeypatch):
    _stub(monkeypatch)
    with pytest.raises(ValueError):                                                        # no shape
        T.reshape("MOD", radius=8, amount=6)
    with pytest.raises(ValueError):                                                        # both shapes
        T.reshape("MOD", at=(1, -1), seg=((1, -1), (2, -2)), radius=8, amount=6)
    with pytest.raises(ValueError):                                                        # no op
        T.reshape("MOD", at=(1, -1), radius=8)
    with pytest.raises(ValueError):                                                        # ridge + flatten
        T.reshape("MOD", seg=((1, -1), (2, -2)), radius=8, flatten=True)


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_reshape_real_block_moves_verts(monkeypatch):
    from pathlib import Path
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda ter, **k: written.append(1) or Path("x"))
    s = T.reshape("FF9CustomMap", at=(1054.0, -951.0), radius=16.0, amount=6.0)
    assert any(b["block"] == [16, 14] for b in s["blocks"])       # the real Alexandria-area block reshapes
    assert sum(b["moved"] for b in s["blocks"]) > 100 and written
