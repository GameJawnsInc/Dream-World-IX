"""THE STITCH PINS + THE STITCH GATE (terrain study defect 5).

world-terrain and world-deploy write Terrain only, but stock is ONE conforming mesh across every part and block:
11.4% of Terrain positions are welded to a sea, beach, river, Object or volcano vertex. A Terrain-only Y edit tore
exactly the welds it moved -- a +3 reshape at a beach left a 3u slit and a one-way wall (in-game proven), and the
study's sweep measured a wall in 149-154 of 154 beach-centred +-3 edits. The writers now HOLD every Terrain vertex
welded to another part (``mesh.stitch_pins``), fading the field in over ``terrain.SEAM_TAPER``, and
``mesh.stitch_gate`` refuses any tear before the first write. Re-run on the real sweep:
``studies/.../gap_inplace_stitch_composition/stitch_postfix.py``.
"""
from __future__ import annotations

import argparse
import math

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, mesh as M, terrain as T

BLK = (16, 14)
OX, OZ = X.block_world_origin(*BLK)
SEAM_Z = -32.0                              # block-local z of the Terrain|Beach1 seam


def _mesh(tris, name, idall=0.0, x=BLK[0], y=BLK[1]):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos = [list(c) for t in tris for c in t]
    n = len(pos)
    return BlockMesh(name=name, disc=1, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: [[0.5, 0.5]] * n,
                                  CH_TAN: [[idall, 0.0, 0.0, 1.0]] * n},
                     flat_index=list(range(n)), tris=[[i, i + 1, i + 2] for i in range(0, n, 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _terrain(y=3.0, x=BLK[0], yb=BLK[1], heights=None):
    tris = []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            h = (lambda px, pz: heights(px, pz)) if heights else (lambda px, pz: y)
            for corners in ([(x0, z0), (x0, z1), (x1, z0)], [(x1, z0), (x0, z1), (x1, z1)]):
                tris.append([(px, h(px, pz), pz) for px, pz in corners])
    return _mesh(tris, f"Block[{x}][{yb}] Terrain", x=x, y=yb)


def _beach():
    """A Beach1 strip welded to the Terrain along the local row z = -32 (its other corners sit below the ground)."""
    tris = []
    for i in range(16):
        a, b = (i * 4.0, 3.0, SEAM_Z), ((i + 1) * 4.0, 3.0, SEAM_Z)
        tris.append([a, (i * 4.0 + 2.0, 2.0, SEAM_Z + 2.0), b])
    return _mesh(tris, "Block[16][14] Beach1")


@pytest.fixture
def seam(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def stock(bx, by, part="terrain", **k):
        if (bx, by) == BLK and part == "terrain":
            return _terrain()
        if (bx, by) == BLK and part == "beach1":
            return _beach()
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append(bm) or tmp_path / bm.name)
    return written


AT = (OX + 30.0, OZ + SEAM_Z)                # on the seam


def _row(bm, z):
    return sorted({round(v[1], 6) for v in bm.verts if abs(v[2] - z) < 1e-9})


def test_stitch_gate_finds_a_split_weld_and_only_that():
    a = [(0.0, 3.0, 0.0), (4.0, 3.0, 0.0)]
    b = [(0.0, 3.0, 0.0), (9.0, 1.0, 9.0)]
    assert M.stitch_gate([("A", a, a), ("B", b, b)]) == {"welds": 1, "torn": 0, "rewelded": 0, "max_sep": 0.0,
                                                         "by_mesh": {}, "sample": []}
    moved = [(0.0, 3.06, 0.0), (4.0, 3.0, 0.0)]
    g = M.stitch_gate([("A", a, moved), ("B", b, b)])
    assert g["torn"] == 1 and g["by_mesh"] == {"A": 1, "B": 1} and g["max_sep"] == 0.06
    hair = [(0.0, 3.04, 0.0), (4.0, 3.0, 0.0)]                       # inside weld_audit's tolerance: not a tear
    assert M.stitch_gate([("A", a, hair), ("B", b, b)])["torn"] == 0
    both = [(0.0, 5.0, 0.0), (4.0, 3.0, 0.0)], [(0.0, 5.0, 0.0), (9.0, 1.0, 9.0)]
    assert M.stitch_gate([("A", a, both[0]), ("B", b, both[1])])["torn"] == 0     # moved as one: intact


def test_stitch_pins_hold_only_true_welds_and_taper_in():
    ter, beach = _terrain(), _beach()
    pins = M.stitch_pins([("b", beach, (OX, OZ))], [(ter, (OX, OZ))], taper=4.0)
    assert len(pins) == 17                                          # the 17 seam nodes; the beach's low corners are not welds
    assert pins.scale(OX + 8.0, OZ + SEAM_Z) == 0.0
    assert pins.scale(OX + 8.0, OZ + SEAM_Z + 2.0) == 0.5            # halfway through the taper
    assert pins.scale(OX + 8.0, OZ + SEAM_Z + 4.0) == 1.0
    assert M.StitchPins(pins.keys).scale(OX, OZ) == 1.0             # no taper


def test_reshape_holds_the_seam_and_the_gate_passes(seam):
    s = T.reshape("MOD", at=AT, radius=12.0, amount=3.0, seam_taper=0.0)
    ter = seam[0]
    assert _row(ter, SEAM_Z) == [3.0]                              # the welded row never moved
    assert max(_row(ter, SEAM_Z + 4.0)) > 5.0                       # the land beside it rose
    assert s["stitch"]["torn"] == 0 and s["stitch"]["welds"] > 0 and s["pinned"] > 0
    assert [type(b).__name__ for b in seam] == ["BlockMesh"] and seam[0].name.endswith("Terrain")   # Terrain only


def test_without_the_pins_the_gate_refuses_before_any_write(seam, monkeypatch):
    monkeypatch.setattr(M, "stitch_pins", lambda *a, **k: M.StitchPins(set()))
    with pytest.raises(ValueError, match="STITCH GATE: this reshape would tear"):
        T.reshape("MOD", at=AT, radius=12.0, amount=3.0)
    assert seam == []


def test_the_taper_ramps_from_the_seam(seam, monkeypatch):
    def stock(bx, by, part="terrain", **k):                         # a Terrain row 2u off the seam
        if (bx, by) != BLK:
            raise ValueError("mesh not found")
        if part == "beach1":
            return _beach()
        if part != "terrain":
            raise ValueError("mesh not found")
        t = _terrain()
        extra = [[(28.0, 3.0, SEAM_Z), (28.0, 3.0, SEAM_Z + 2.0), (32.0, 3.0, SEAM_Z)]]
        return _mesh([[tuple(t.verts[i]) for i in tri] for tri in t.tris] + extra, t.name)
    monkeypatch.setattr(X, "read_block", stock)
    T.reshape("MOD", at=AT, radius=12.0, amount=3.0, seam_taper=4.0)
    ter = seam[0]
    near = [v[1] for v in ter.verts if (v[0], v[2]) == (28.0, SEAM_Z + 2.0)]
    far = [v[1] for v in ter.verts if (v[0], v[2]) == (28.0, SEAM_Z + 4.0)]
    w = M._falloff(math.hypot(-2.0, 2.0) / 12.0)
    assert near == [pytest.approx(3.0 + 3.0 * w * 0.5)]              # half the field, 2u into a 4u taper
    assert min(far) > near[0]


def test_a_multi_block_flatten_shares_one_height(tmp_path, monkeypatch):
    """Per-block means pulled the shared border to two heights; one mean keeps it welded."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    ramp = {16: lambda px, pz: 2.0, 17: lambda px, pz: 2.0 + px / 8.0}

    def stock(bx, by, part="terrain", **k):
        if part != "terrain" or by != 14 or bx not in ramp:
            raise ValueError("mesh not found")
        return _terrain(x=bx, yb=14, heights=ramp[bx])
    monkeypatch.setattr(X, "read_block", stock)
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append(bm) or tmp_path / bm.name)
    at = (17 * 64.0, OZ - 32.0)                                    # on the 16|17 border
    a, b = _terrain(x=16, yb=14, heights=ramp[16]), _terrain(x=17, yb=14, heights=ramp[17])
    pre = [(a.name, M.world_positions(a, X.block_world_origin(16, 14)), None),
           (b.name, M.world_positions(b, X.block_world_origin(17, 14)), None)]
    M.flatten_region(a, radius=20.0, center=at, world_origin=X.block_world_origin(16, 14))
    M.flatten_region(b, radius=20.0, center=at, world_origin=X.block_world_origin(17, 14))
    old = M.stitch_gate([(n, p, M.world_positions(m, X.block_world_origin(m.x, m.y)))
                         for (n, p, _), m in zip(pre, (a, b))])
    assert old["torn"] > 0                                          # the latent bug: each block flattened to its own mean
    s = T.reshape("MOD", at=at, radius=20.0, flatten=True)
    assert s["stitch"]["torn"] == 0 and "flatten_height" in s and len(written) == 2


def _deploy_ns(**kw):
    ns = dict(block=None, cluster=None, disc=1, lod="0_1", mod_folder="MOD", hill=3.0, crater=0.0, flatten=False,
              height=None, radius=12.0, center=list(AT), falloff="smooth", no_normals=True, allow_entrances=False,
              spike=0.0, lift=0.0, skip_mirror=True, game=None, fresh=False, allow_overwrite=False, allow_tear=False, form=1)
    ns.update(kw)
    return argparse.Namespace(**ns)


def test_world_deploy_holds_the_seam_and_refuses_a_tearing_lift(seam, monkeypatch, capsys):
    """The [diag] --lift holds no seam. Round a town's walkable Object plate an unpinned raise builds a shaft the
    player cannot climb out of (the July Dali freeze, terrain study in-game round 4), so a tear refuses before any
    write unless --allow-tear; allowed, it still warns."""
    monkeypatch.setattr(X, "list_blocks", lambda **k: [BLK])
    assert cli._cmd_world_deploy(_deploy_ns()) == 0
    assert _row(seam[-1], SEAM_Z) == [3.0] and "held " in capsys.readouterr().out
    n = len(seam)
    assert cli._cmd_world_deploy(_deploy_ns(hill=0.0, lift=2.0, block=list(BLK))) == 2
    err = capsys.readouterr().err
    assert "REFUSED: this --lift tears 17 seam weld(s)" in err and "Nothing was written" in err
    assert len(seam) == n
    assert cli._cmd_world_deploy(_deploy_ns(hill=0.0, lift=2.0, block=list(BLK), allow_tear=True)) == 0
    assert "seam weld(s) torn" in capsys.readouterr().out and len(seam) == n + 1


@pytest.fixture
def inland(tmp_path, monkeypatch):
    """Two Terrain blocks side by side, (16,14)|(17,14), welded along x = 1088 and to nothing else."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    blocks = {BLK: _terrain, (17, 14): lambda: _terrain(x=17, yb=14)}

    def stock(bx, by, part="terrain", **k):
        if part == "terrain" and (bx, by) in blocks:
            return blocks[(bx, by)]()
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append(bm) or tmp_path / bm.name)
    return blocks, written


def test_a_lift_is_judged_against_the_neighbour_blocks_terrain(inland, capsys):
    """A lift splits its block's border with every unedited neighbour: a cliff with a slit under it. The neighbours'
    Terrain is no stitch partner (a reshape moves every block its radius reaches as one field), so the [diag] gate
    reads it itself."""
    blocks, written = inland
    assert cli._cmd_world_deploy(_deploy_ns(hill=0.0, lift=2.0, block=list(BLK))) == 2
    err = capsys.readouterr().err
    assert "REFUSED: this --lift tears 17 seam weld(s)" in err and "Block[17][14] Terrain" in err and written == []
    del blocks[(17, 14)]                                           # alone, the block lifts as one: nothing to tear
    assert cli._cmd_world_deploy(_deploy_ns(hill=0.0, lift=2.0, block=list(BLK))) == 0 and len(written) == 1


def test_a_spike_tears_its_own_unindexed_mesh_and_is_refused(inland, capsys):
    blocks, written = inland
    del blocks[(17, 14)]
    assert cli._cmd_world_deploy(_deploy_ns(hill=0.0, spike=2.0, block=list(BLK))) == 2
    assert "REFUSED: this --spike tears 1 seam weld(s), up to 2.0u" in capsys.readouterr().err and written == []
    assert cli._cmd_world_deploy(_deploy_ns(hill=0.0, spike=2.0, block=list(BLK), allow_tear=True)) == 0


def test_allow_tear_is_only_for_the_diag(seam, capsys):
    """A reshape's tear is a kit bug the gate always refuses; --allow-tear on one is a usage error, not a waiver."""
    ns = cli.build_parser().parse_args(["world-deploy", "--mod-folder", "MOD", "--block", "16", "14", "--lift", "2",
                                        "--allow-tear"])
    assert ns.allow_tear is True
    assert cli._cmd_world_deploy(_deploy_ns(allow_tear=True)) == 2
    assert "waives only the [diag] --lift/--spike tear" in capsys.readouterr().err and seam == []


def _game_ready() -> bool:
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_the_in_game_beach_seam_edit_no_longer_tears(monkeypatch):
    """Rank 3 of the study, in game: world-terrain --at 480 -1120 --radius 16 --raise 3 on (7,17) left a 3u slit and
    a one-way wall. The gate, with the pins off, counts the same 10 torn welds the study measured from the real
    writer; with them on, 0, and the edit passes the one-way-wall gate."""
    mod = "FF9CustomMap_test_nonexistent"
    s = T.reshape(mod, at=(480.0, -1120.0), radius=16.0, amount=3.0, dry_run=True)
    assert s["stitch"]["torn"] == 0 and s["pinned"] == 40 and s["blocks"][0]["block"] == [7, 17]
    assert not s["walkability"]["[7, 17]"]["one_way_wall"]
    monkeypatch.setattr(M, "stitch_pins", lambda *a, **k: M.StitchPins(set()))
    with pytest.raises(ValueError, match="would tear 10 weld"):
        T.reshape(mod, at=(480.0, -1120.0), radius=16.0, amount=3.0, dry_run=True, allow_steep=True)
