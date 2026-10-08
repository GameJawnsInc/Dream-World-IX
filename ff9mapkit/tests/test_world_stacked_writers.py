"""THE STACKED READ + THE FRESH-RESET GATE (terrain study defects 3-4).

Four in-place writers -- ``terrain.reshape`` (world-terrain), world-deploy, world-retarget and
``transplant.morph_in_place`` (world-transplant --in-place) -- read pristine stock, so a second edit of a block erased
the first, and a reshape or retarget silently killed a world-entrance (its ``.eb`` trigger left with no tile). The
study's S3 probe measured 8/8 cross-writer pairs last-writer-wins. They now read the mod folder's deployed override
first, like world-entrance always did; ``fresh`` re-reads stock, names what it discards, and refuses to erase kit
entrance tiles without ``allow_overwrite``. A morph's tweaks are built from stock, so a morph may change only tris
still identical to stock. Re-run against the install: ``studies/.../gap_inplace_stitch_composition/composition_postfix.py``.

Hermetic: every game root is ``tmp_path``; stock reads are stubbed.
"""
from __future__ import annotations

import argparse

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, mesh as M, terrain as T, transplant as TR

BLK = (16, 14)
AT = (1054.0, -951.0)                      # inside BLK: local (30, -55)
OX, OZ = X.block_world_origin(*BLK)


def _flat_block(y=3.0, raise_at=None, dy=2.0, event_near=None):
    """Block[16][14] Terrain: a 16x16 grid of 4u cells at height ``y`` (unindexed, up-facing). ``raise_at`` = a
    block-local (x, z) grid node lifted by ``dy`` in every corner instance; ``event_near`` = a block-local (x, z):
    tris whose centroid is within 6u carry event 1 (a kit entrance's trigger tiles)."""
    from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, nrm, uv, tan, tris = [], [], [], [], []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            for corners in ([(x0, z0), (x0, z1), (x1, z0)], [(x1, z0), (x0, z1), (x1, z1)]):
                cx, cz = sum(c[0] for c in corners) / 3, sum(c[1] for c in corners) / 3
                ev = 1 if event_near and (cx - event_near[0]) ** 2 + (cz - event_near[1]) ** 2 < 36 else 0
                idall = float(encode_id(ev, 14, 0))
                base = len(pos)
                for (x, z) in corners:
                    yy = y + (dy if raise_at and (x, z) == tuple(raise_at) else 0.0)
                    pos.append([x, yy, z]); nrm.append([0.0, 1.0, 0.0]); uv.append([0.5, 0.5])
                    tan.append([idall, 0.0, 0.0, 1.0])
                tris.append([base, base + 1, base + 2])
    n = len(pos)
    return BlockMesh(name="Block[16][14] Terrain", disc=1, x=BLK[0], y=BLK[1], lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}, flat_index=list(range(n)),
                     tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A tmp game root; stock = a flat Block[16][14] (every other block is sea); no mirror."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def stock(bx, by, **k):
        if (bx, by) != BLK:
            raise ValueError("mesh not found")
        return _flat_block()
    monkeypatch.setattr(X, "read_block", stock)
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: None)
    return tmp_path


def _deploy(bm):
    return M.deploy_override(bm, mod_folder="MOD", part="Terrain")


def _ys(path):
    return [v[1] for v in M.read_ff9mesh(path)["verts"]]


def _events(path):
    d = M.read_ff9mesh(path)
    return sum(1 for i in range(0, len(d["indices"]), 3)
               if X.decode_id(int(round(d["tangents"][d["indices"][i]][0])))["event"])


def test_deployed_override_is_none_without_an_install(monkeypatch):
    def nope(game=None):
        raise config.ConfigError("no install")
    monkeypatch.setattr(config, "find_game_path", nope)
    assert M.deployed_override("MOD", *BLK, disc=1) is None
    assert M.fresh_reset_gate([BLK], "MOD", disc=1) == {}


def test_reshape_stacks_on_the_deployed_override_and_a_rerun_compounds(world):
    dep = _deploy(_flat_block(raise_at=(8.0, -8.0), dy=5.0))       # an earlier edit, away from the hill
    s1 = T.reshape("MOD", at=AT, radius=12.0, amount=2.0)
    assert [b["block"] for b in s1["blocks"]] == [list(BLK)] and s1["stacked_on"] == [str(dep)]
    y1 = _ys(dep)
    assert max(y1) == 8.0                                           # the earlier edit survived (pre-fix: erased)
    hill1 = max(y for y in y1 if y < 8.0) - 3.0
    T.reshape("MOD", at=AT, radius=12.0, amount=2.0)
    hill2 = max(y for y in _ys(dep) if y < 8.0) - 3.0
    assert hill1 > 0.5 and abs(hill2 - 2 * hill1) < 1e-4            # stacked: the re-run compounds


def test_reshape_fresh_reads_stock_and_names_the_discard(world):
    dep = _deploy(_flat_block(raise_at=(8.0, -8.0), dy=5.0))
    s = T.reshape("MOD", at=AT, radius=12.0, amount=2.0, fresh=True)
    assert s["fresh_discards"] == [str(dep)] and "DISCARDING 1" in s["fresh_warning"] and not s["stacked_on"]
    assert max(_ys(dep)) < 8.0                                      # the earlier edit is gone, as asked


def test_fresh_refuses_to_erase_kit_entrance_tiles(world):
    dep = _deploy(_flat_block(event_near=(30.0, -30.0)))
    n = _events(dep)
    with pytest.raises(ValueError, match="refusing --fresh: it would erase entrance trigger tiles"):
        T.reshape("MOD", at=AT, radius=12.0, amount=2.0, fresh=True)
    assert _events(dep) == n > 0                                    # refused before any write
    s = T.reshape("MOD", at=AT, radius=12.0, amount=2.0, fresh=True, allow_overwrite=True)
    assert list(s["fresh_lost_entrances"]) == ["16,14"] and _events(dep) == 0
    # the default (stacked) path keeps them: the hill is position-based, the IDALLs ride along
    dep2 = _deploy(_flat_block(event_near=(30.0, -30.0)))
    T.reshape("MOD", at=AT, radius=12.0, amount=2.0)
    assert _events(dep2) == n


def test_reshape_fresh_has_no_stock_on_a_synthetic_world(world):
    with pytest.raises(ValueError, match="synthetic world"):
        T.reshape("MOD", at=AT, radius=12.0, amount=2.0, fresh=True, target_disc=9)


def _deploy_ns(**kw):
    ns = dict(block=None, cluster=None, disc=1, lod="0_1", mod_folder="MOD", hill=2.0, crater=0.0, flatten=False,
              height=None, radius=12.0, center=list(AT), falloff="smooth", no_normals=False, allow_entrances=False,
              spike=0.0, lift=0.0, skip_mirror=True, game=None, fresh=False, allow_overwrite=False)
    ns.update(kw)
    return argparse.Namespace(**ns)


def test_world_deploy_stacks(world, monkeypatch, capsys):
    monkeypatch.setattr(X, "list_blocks", lambda **k: [BLK])
    dep = _deploy(_flat_block(raise_at=(8.0, -8.0), dy=5.0))
    assert cli._cmd_world_deploy(_deploy_ns()) == 0
    assert max(_ys(dep)) == 8.0 and "stacked on 1 deployed override" in capsys.readouterr().out
    assert cli._cmd_world_deploy(_deploy_ns(fresh=True)) == 0
    assert max(_ys(dep)) < 8.0 and "DISCARDING 1" in capsys.readouterr().out


def _retarget_ns(**kw):
    ns = dict(block=list(BLK), disc=1, lod="0_1", game=None, mod_folder="MOD", event=None, area=None, topograph=17,
              center=list(AT), radius=8.0, only_entrances=False, skip_mirror=True, fresh=False, allow_overwrite=False)
    ns.update(kw)
    return argparse.Namespace(**ns)


def test_world_retarget_stacks_and_its_fresh_is_gated(world, capsys):
    dep = _deploy(_flat_block(raise_at=(8.0, -8.0), dy=5.0))
    assert cli._cmd_world_retarget(_retarget_ns()) == 0
    d = M.read_ff9mesh(dep)
    topos = {X.decode_id(int(round(t[0])))["topograph"] for t in d["tangents"]}
    assert max(_ys(dep)) == 8.0 and topos == {0, 17}                # the earlier hill kept, the retype applied
    assert "stacked on 1" in capsys.readouterr().out
    _deploy(_flat_block(event_near=(30.0, -30.0)))
    assert cli._cmd_world_retarget(_retarget_ns(fresh=True)) == 2
    assert "refusing --fresh" in capsys.readouterr().err


@pytest.fixture
def morph_world(world, monkeypatch):
    stock = TR._soup(_flat_block(), *BLK)
    monkeypatch.setattr(TR, "world_tris", lambda bx, by, part, **k: list(stock) if (bx, by, part) == (*BLK, "terrain")
                        else [])
    return world


def _displace(local_xz, y, dy=1.0):
    pos = (local_xz[0] + OX, y, local_xz[1] + OZ)
    return TR.VertexDisplace(moves={pos: (0.0, dy, 0.0)}, expected=6, part=None)   # an interior node: 6 corners


def test_morph_stacks_where_it_touches_only_stock_tris(morph_world):
    dep = _deploy(_flat_block(raise_at=(8.0, -8.0), dy=5.0))
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((44.0, -44.0), 3.0)], parts=("terrain",))
    assert s["clean"] and s["stacked_on"] == [str(dep)] and "stack_conflicts" not in s
    ys = _ys(dep)
    assert max(ys) == 8.0 and ys.count(4.0) == 6                    # the earlier edit kept + the morph applied


def test_morph_refuses_to_rework_a_deployed_edit_with_stock_built_tweaks(morph_world):
    dep = _deploy(_flat_block(raise_at=(20.0, -20.0), dy=2.0))
    before = dep.read_bytes()
    tw = _displace((20.0, -20.0), 5.0)                              # keyed on the DEPLOYED (raised) node
    with pytest.raises(ValueError, match="would change tris a deployed edit already changed"):
        TR.morph_in_place("MOD", cell=BLK, tweaks=[tw], parts=("terrain",))
    assert dep.read_bytes() == before
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((20.0, -20.0), 5.0)], parts=("terrain",),
                          allow_overwrite=True)
    assert s["stack_conflicts"] == {"terrain": 6} and max(_ys(dep)) == 6.0


def test_morph_fresh_reads_stock(morph_world):
    dep = _deploy(_flat_block(raise_at=(8.0, -8.0), dy=5.0))
    s = TR.morph_in_place("MOD", cell=BLK, tweaks=[_displace((44.0, -44.0), 3.0)], parts=("terrain",), fresh=True)
    assert s["fresh_discards"] == [str(dep)] and not s["stacked_on"] and max(_ys(dep)) == 4.0


def test_world_transplant_fresh_needs_in_place(capsys):
    rc = cli.main(["world-transplant", "--cell", "3,4", "--donor", "5,6", "--mod-folder", "X", "--fresh",
                   "--dry-run"])
    assert rc == 2 and "--in-place only" in capsys.readouterr().err
