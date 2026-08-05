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


# ---- THE ONE-WAY WALL GATE (audit rec 9 step 4, recalibrated) -------------------------------------------------------
# The audit's letter (interior.GATE_CLIMB per edge) was WRONG for a smooth reshape: a
# displaced continuous mesh never makes a step discontinuity, and per-edge 2.30 would have
# refused a 43-deg hill the engine walks happily (per-tick model: ground may rise 2.34375
# per 0.4375u step -> the true ceiling is rise/run ~5.36, ~79.4 deg). Above it a face is
# descendable but UNCLIMBABLE -- the soft-lock pit class. 28.6 deg (grass-look p99) warns.

def _flat_block(n=16, cell=4.0, y=3.0):
    from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    grass = float(encode_id(topograph=0))
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    for i in range(n):
        for j in range(n):
            x0, x1, z0, z1 = i * cell, (i + 1) * cell, -j * cell, -(j + 1) * cell
            for corners in ([(x0, y, z0), (x1, y, z0), (x0, y, z1)],
                            [(x1, y, z0), (x1, y, z1), (x0, y, z1)]):
                base = len(pos)
                for c in corners:
                    pos.append(list(c)); nrm.append([0.0, 1.0, 0.0]); uv.append([0.5, 0.5])
                    tan.append([grass, 0.0, 0.0, 1.0]); flat.append(len(pos) - 1)
                tris.append([base, base + 1, base + 2])
    return BlockMesh(name="Block[16][14] Terrain", disc=1, x=16, y=14, lod="0_1",
                     vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def _real_reshape(monkeypatch, **kw):
    """reshape() with a REAL mesh + REAL deform; only IO stubbed."""
    from ff9mapkit.world import discmirror as DM
    monkeypatch.setattr(X, "read_block", lambda bx, by, **k: _flat_block())
    monkeypatch.setattr(M, "deploy_override", lambda ter, **k: f"stub/{ter.name}")
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    return T.reshape("MOD", **kw)


def test_walk_gate_gentle_hill_reports_and_passes(monkeypatch):
    s = _real_reshape(monkeypatch, at=(1054.0, -951.0), radius=12.0, amount=2.0)
    walk = s["walkability"][str([16, 14])]
    assert not walk["one_way_wall"] and not walk["flank_warn"]
    assert 0 < walk["max_slope_deg"] < 28.6


def test_walk_gate_steep_but_walkable_warns_not_refuses(monkeypatch):
    """The reload-test hill class (~43 deg): the engine walks it (0.41u rise per tick),
    so it must PASS with the look warning -- the audit's per-edge letter refused it."""
    s = _real_reshape(monkeypatch, at=(1054.0, -951.0), radius=10.0, amount=6.0)
    walk = s["walkability"][str([16, 14])]
    assert not walk["one_way_wall"] and walk["flank_warn"]
    assert 28.6 < walk["max_slope_deg"] < 79.0


def test_walk_gate_refuses_the_one_way_wall_and_allow_steep_escapes(monkeypatch):
    """A spike (30u over a ~2u footprint) is a one-way wall: descendable, unclimbable --
    refuse without the explicit escape; record honestly with it."""
    with pytest.raises(ValueError, match="ONE-WAY WALL"):
        _real_reshape(monkeypatch, at=(1052.0, -952.0), radius=2.0, amount=30.0)
    s = _real_reshape(monkeypatch, at=(1052.0, -952.0), radius=2.0, amount=30.0,
                      allow_steep=True)
    walk = s["walkability"][str([16, 14])]
    assert walk["one_way_wall"] and walk["max_slope_deg"] > 79.0
