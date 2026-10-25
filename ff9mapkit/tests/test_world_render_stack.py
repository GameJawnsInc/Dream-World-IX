"""world.render resolving a block's files through the whole FolderNames stack, the way the engine does.

``WorldMeshOverride`` (Memoria/World/WorldMeshOverride.cs) walks ``AssetManager.FolderHighToLow`` -- FolderNames in
order, then the base game -- per FILE: each mesh part, the divert's Terrain-exists check (``HasLandOverride``: any
folder) and ``Donor.txt`` (``TryReadDonorPath``: the first folder holding one) are three independent lookups, and a
file the engine cannot read means STOCK, not the next folder's file. Hermetic: tmp folders, real ``.ff9mesh`` bytes,
``extract.block_parts`` pinned (no install).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from ff9mapkit.world import extract as X
from ff9mapkit.world import mesh as M
from ff9mapkit.world import render as R
from ff9mapkit.world.extract import CH_NRM, CH_POS, CH_TAN, CH_UV, BlockMesh, encode_id


def _tri_mesh(y, bx=1, by=1, part="Terrain"):
    pos = [[0.0, y, 0.0], [8.0, y, 0.0], [0.0, y, -8.0]]
    return BlockMesh(name=f"Block[{bx}][{by}] {part}", disc=1, x=bx, y=by, lod="0_1", vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * 3, CH_UV: [[0.0, 0.0]] * 3,
                                  CH_TAN: [[float(encode_id(topograph=0)), 0.0, 0.0, 1.0]] * 3},
                     flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _put(root, name, data, bx=1, by=1):
    p = root / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {name}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def _mesh(y, part="Terrain"):
    return M.ff9mesh_bytes(_tri_mesh(y, part=part))


@pytest.fixture
def stack(tmp_path):
    hi, lo = tmp_path / "HIGH", tmp_path / "LOW"
    hi.mkdir()
    lo.mkdir()
    return tmp_path, hi, lo


def _site(game, roots, parts=("Terrain", "Sea4")):
    return R.RenderSite(cells=((1, 1),), disc=1, game=game, stack=tuple(roots), parts=parts)


def test_the_first_folder_holding_a_file_wins_and_each_file_resolves_alone(stack):
    game, hi, lo = stack
    _put(hi, "Terrain.ff9mesh", _mesh(7.0))
    _put(lo, "Terrain.ff9mesh", _mesh(2.0))
    _put(lo, "Sea4.ff9mesh", _mesh(0.0, "Sea4"))            # only the lower folder has a Sea4
    site = _site(game, (hi, lo))
    assert R.resolve_file(site, 1, 1, "Terrain.ff9mesh").parents[5] == hi
    assert R.resolve_file(site, 1, 1, "Sea4.ff9mesh").parents[5] == lo
    src = {}
    got = dict(R.cell_meshes(site, 1, 1, sources=src))
    assert got["Terrain"].verts[0][1] == 7.0 and got["Sea4"].verts[0][1] == 0.0
    assert src["Terrain"].parents[5] == hi and src["Sea4"].parents[5] == lo
    flipped = dict(R.cell_meshes(_site(game, (lo, hi)), 1, 1))  # the order IS the rule
    assert flipped["Terrain"].verts[0][1] == 2.0


def test_a_refused_file_hides_the_good_one_below_it(stack):
    """TryLoad returns null on a read failure instead of trying the next folder: the engine keeps the STOCK mesh."""
    game, hi, lo = stack
    bad_bytes = _mesh(7.0)[:-8]                               # truncated: its header promises more indices
    _put(hi, "Terrain.ff9mesh", bad_bytes)
    _put(lo, "Terrain.ff9mesh", _mesh(2.0))
    bad = []
    got = dict(R.cell_meshes(_site(game, (hi, lo)), 1, 1, bad=bad))
    assert "Terrain" not in got                               # stock=False: no stock part, and NOT the LOW file
    assert len(bad) == 1 and bad[0][0].parents[5] == hi and "truncated" in bad[0][1]


@pytest.mark.parametrize("mutate, why", [
    (lambda b: b"XXXX" + b[4:], "bad magic"),
    (lambda b: b[:4] + (2).to_bytes(4, "little") + b[8:], "unsupported version"),
    (lambda b: b[:8] + (0).to_bytes(4, "little") + b[12:], "vertex count"),
    (lambda b: b[:8] + (70000).to_bytes(4, "little") + b[12:], "vertex count"),
    (lambda b: b[:12] + (10).to_bytes(4, "little") + b[16:], "index count"),
    (lambda b: b[:-4], "truncated"),
], ids=["magic", "version", "no-verts", "too-many-verts", "too-many-indices", "short"])
def test_engine_read_error_mirrors_readmesh(tmp_path, mutate, why):
    good = _put(tmp_path, "Terrain.ff9mesh", _mesh(1.0))
    assert R.engine_read_error(good) is None
    bad = _put(tmp_path, "Object.ff9mesh", mutate(_mesh(1.0)))
    assert why in R.engine_read_error(bad)


def test_the_divert_reads_terrain_from_any_folder_and_donor_from_the_first(stack, monkeypatch):
    """A prefab-less (sea) cell diverts when ANY folder has its Terrain (HasLandOverride); the donor is the FIRST
    folder's Donor.txt (TryReadDonorPath), independent of which folder supplied the Terrain."""
    game, hi, lo = stack
    monkeypatch.setattr(X, "block_parts", lambda disc=1, game=None: {(5, 15): ("terrain",), (6, 15): ("terrain",)})
    site = _site(game, (hi, lo))
    assert R.effective_prefab(site, 1, 1) == (None, "SeaBlockPrefab")
    _put(lo, "Terrain.ff9mesh", _mesh(2.0))
    assert R.effective_prefab(site, 1, 1)[0] == R.LAND_DONOR_FALLBACK      # diverted, no Donor.txt yet
    _put(lo, "Donor.txt", b"6,15")
    _put(hi, "Donor.txt", b"5,15")
    assert R.effective_prefab(site, 1, 1) == ((5, 15), "Donor.txt -> 5,15")


def test_one_folder_as_a_stack_draws_exactly_what_the_one_folder_site_draws(stack):
    game, hi, lo = stack
    _put(lo, "Terrain.ff9mesh", _mesh(2.0))
    _put(lo, "Sea4.ff9mesh", _mesh(0.0, "Sea4"))
    one = R.load_batches(R.RenderSite(cells=((1, 1),), disc=1, game=game, mod_root=lo, parts=("Terrain", "Sea4")))
    as_stack = R.load_batches(_site(game, (lo,)))
    assert len(one) == len(as_stack) == 2
    for (pa, va, ua, ta), (pb, vb, ub, tb) in zip(one, as_stack):
        assert pa == pb and np.array_equal(va, vb) and np.array_equal(ua, ub) and np.array_equal(ta, tb)


def test_the_load_scope_listing_answers_as_the_disk_does(stack):
    """load_batches lists each folder once instead of a stat per part per folder per cell; outside the scope the
    same calls stat the disk -- both must resolve the same files."""
    game, hi, lo = stack
    _put(hi, "Sea4.ff9mesh", _mesh(0.5, "Sea4"))
    _put(lo, "Terrain.ff9mesh", _mesh(2.0))
    site = _site(game, (hi, lo))
    scoped = R.load_batches(site)
    direct = [(p, bm.verts[0][1]) for p, bm in R.cell_meshes(site, 1, 1)]
    assert [(p, float(v[0][1])) for p, v, _u, _t in scoped] == direct == [("Terrain", 2.0), ("Sea4", 0.5)]
    assert R._LISTING is None                                   # the scope never leaks into later lookups


def test_game_stack_reads_foldernames_in_priority_order(tmp_path):
    (tmp_path / "Memoria.ini").write_text('[Mod]\nFolderNames = "A", "B-world", "C"\n', encoding="utf-8")
    assert [p.name for p in R.game_stack(tmp_path)] == ["A", "B-world", "C"]
    assert R.game_stack(tmp_path / "nowhere") is None


def test_an_empty_stack_is_stock_everywhere(stack):
    game, hi, lo = stack
    _put(lo, "Terrain.ff9mesh", _mesh(2.0))
    site = _site(game, ())
    assert not R.live_path(site, 1, 1, "Terrain").is_file() and R.cell_meshes(site, 1, 1) == []
