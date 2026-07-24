"""Fences for :mod:`ff9mapkit.workspace.worldscan` -- the deployed-overworld census the World tab reads.

Every tree here is SYNTHETIC (tmp_path): the census must never need -- and these tests must never
touch -- a real install. The blank-part law is calibrated against the kit's own writers
(``stub_terrain_mesh`` / ``hidden_block_mesh``), not against hand-typed constants.
"""

from __future__ import annotations

import json
import struct

import pytest

from ff9mapkit import config
from ff9mapkit.workspace import worldscan


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _mesh_bytes(vcount=12, icount=12, *, salt=0):
    """A minimal valid ``.ff9mesh`` (write_ff9mesh's exact header + verts + indices, flags=0)."""
    out = bytearray(b"F9WM")
    out += struct.pack("<iiii", 1, vcount, icount, 0)
    for i in range(vcount):
        out += struct.pack("<3f", float(i + salt), 0.0, float(i))
    out += struct.pack("<%di" % icount, *([0] * icount))
    return bytes(out)


def _put(root, bx, by, name, data, disc=1):
    d = root / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"Block[{bx}][{by}] {name}"
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8")
    return p


def test_the_filename_parser_is_the_mirrors_own():
    """One regex owns the cell-file grammar: the census parses with discmirror's exact object, so the
    two can never disagree about what counts as a deployed part."""
    from ff9mapkit.world import discmirror
    assert worldscan.BLOCK_RE is discmirror._BLOCK_RE


def test_a_tree_censuses_cells_parts_and_donor(tmp_path):
    _put(tmp_path, 3, 17, "Terrain.ff9mesh", _mesh_bytes(vcount=300, icount=2139))
    _put(tmp_path, 3, 17, "Sea4.ff9mesh", _mesh_bytes(vcount=4, icount=6))
    _put(tmp_path, 3, 17, "Sea1.ff9mesh", _mesh_bytes(vcount=3, icount=3))   # a blanked part
    _put(tmp_path, 3, 17, "Donor.txt", "0,0")
    census = worldscan.scan_tree(tmp_path)
    assert set(census.cells) == {(3, 17)}
    c = census.cells[(3, 17)]
    assert c.kind == "land"
    assert c.parts["Terrain"].tris == 713 and not c.parts["Terrain"].blank
    assert c.parts["Sea4"].tris == 2 and not c.parts["Sea4"].blank
    assert c.parts["Sea1"].blank
    assert c.donor == (0, 0) and c.donor_raw == "0,0"
    assert c.dirpath is not None and c.dirpath.name == "r17"
    assert census.total_bytes > 0


def test_the_blank_law_is_calibrated_against_the_writers(tmp_path):
    """``vcount <= 3`` is not a guess: the divert-arm stub and the part blanker -- the only two blank
    idioms the kit writes -- must classify blank THROUGH THEIR OWN OUTPUT, and a water cell built the
    way the writers build one (arming stub + real sea) must read as water."""
    from ff9mapkit.world.mesh import hidden_block_mesh, stub_terrain_mesh, write_ff9mesh
    d = tmp_path / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r19"
    d.mkdir(parents=True)
    write_ff9mesh(stub_terrain_mesh(x=11, y=19), d / "Block[11][19] Terrain.ff9mesh")
    write_ff9mesh(hidden_block_mesh(name="Block[11][19] Sea1", x=11, y=19),
                  d / "Block[11][19] Sea1.ff9mesh")
    (d / "Block[11][19] Sea4.ff9mesh").write_bytes(_mesh_bytes(vcount=8, icount=12))
    census = worldscan.scan_tree(tmp_path)
    c = census.cells[(11, 19)]
    assert c.parts["Terrain"].blank, "the divert-arm stub must read as blank"
    assert c.parts["Sea1"].blank, "the hidden-part blanker must read as blank"
    assert not c.parts["Sea4"].blank
    assert c.kind == "water"


def test_bak_siblings_are_counted_never_parts(tmp_path):
    _put(tmp_path, 6, 18, "Terrain.ff9mesh", _mesh_bytes())
    _put(tmp_path, 6, 18, "Terrain.ff9mesh.bak-20260719-093929", _mesh_bytes(salt=9))
    census = worldscan.scan_tree(tmp_path)
    c = census.cells[(6, 18)]
    assert set(c.parts) == {"Terrain"}
    assert c.backups == 1
    assert not census.strays


def test_off_grid_overrides_are_strays(tmp_path):
    """The grid-bounds law: the engine never streams beyond 24x20, so an off-grid override is a DEAD
    file -- the census surfaces it instead of drawing a block that cannot exist."""
    _put(tmp_path, 30, 5, "Terrain.ff9mesh", _mesh_bytes())
    census = worldscan.scan_tree(tmp_path)
    assert not census.cells
    assert any("Block[30][5]" in s for s in census.strays)


def test_mirror_byte_compares_not_size(tmp_path):
    """A pure-Y terrain displacement changes bytes WITHOUT changing length -- exactly the edit a
    size-compare would call 'current'. The verdict must come from bytes."""
    data = _mesh_bytes(vcount=60, icount=90)
    _put(tmp_path, 5, 9, "Terrain.ff9mesh", data)
    _put(tmp_path, 5, 9, "Terrain.ff9mesh", data, disc=4)
    census = worldscan.scan_tree(tmp_path)
    assert census.has_disc4 and census.cells[(5, 9)].mirror == "current"

    stale = bytearray(data)
    stale[-1] ^= 0xFF                                        # same length, different bytes
    _put(tmp_path, 5, 9, "Terrain.ff9mesh", bytes(stale), disc=4)
    assert worldscan.scan_tree(tmp_path).cells[(5, 9)].mirror == "stale"

    _put(tmp_path, 5, 9, "Terrain.ff9mesh", data, disc=4)    # restore; add a free-ride pin
    _put(tmp_path, 5, 9, "Beach1.ff9mesh", _mesh_bytes(vcount=6, icount=6), disc=4)
    c = worldscan.scan_tree(tmp_path).cells[(5, 9)]
    assert c.mirror == "current" and c.pins == 1, "Disc4-only pins are expected, not stale"

    d4 = tmp_path / "FF9_Data" / "WorldMap" / "Disc4" / "0_1" / "r9" / "Block[5][9] Terrain.ff9mesh"
    d4.unlink()
    assert worldscan.scan_tree(tmp_path).cells[(5, 9)].mirror == "missing"


def test_no_disc4_tree_reads_as_unmirrored(tmp_path):
    _put(tmp_path, 5, 9, "Terrain.ff9mesh", _mesh_bytes())
    census = worldscan.scan_tree(tmp_path)
    assert not census.has_disc4
    assert census.cells[(5, 9)].mirror == ""


def test_disc4_only_cells_are_surfaced(tmp_path):
    _put(tmp_path, 2, 2, "Terrain.ff9mesh", _mesh_bytes())
    _put(tmp_path, 9, 9, "Terrain.ff9mesh", _mesh_bytes(), disc=4)
    _put(tmp_path, 2, 2, "Terrain.ff9mesh", _mesh_bytes(), disc=4)
    census = worldscan.scan_tree(tmp_path)
    assert census.disc4_only == [(9, 9)]


def test_block_centre_matches_the_islands_documented_deploy():
    """Island F's recorded placement: block (3,17) at world (224, -1120) -- the study's own numbers."""
    assert worldscan.block_center(3, 17) == (224.0, -1120.0)
    (x0, x1), (z0, z1) = worldscan.block_span(3, 17)
    assert (x0, x1) == (192.0, 256.0) and (z0, z1) == (-1152.0, -1088.0)


def test_donor_junk_is_kept_raw_never_parsed(tmp_path):
    _put(tmp_path, 4, 4, "Terrain.ff9mesh", _mesh_bytes())
    _put(tmp_path, 4, 4, "Donor.txt", "banana")
    c = worldscan.scan_tree(tmp_path).cells[(4, 4)]
    assert c.donor is None and c.donor_raw == "banana"


def test_a_corrupt_mesh_is_an_unreadable_part_not_a_crash(tmp_path):
    _put(tmp_path, 4, 4, "Terrain.ff9mesh", b"NOPE" + b"\x00" * 40)
    c = worldscan.scan_tree(tmp_path).cells[(4, 4)]
    assert c.parts["Terrain"].vcount is None
    assert c.kind == "stub"                                  # unreadable never masquerades as land


def test_landmasses_are_four_adjacency_components(tmp_path):
    for bx, by in ((3, 17), (4, 17), (11, 19)):
        _put(tmp_path, bx, by, "Terrain.ff9mesh", _mesh_bytes())
    census = worldscan.scan_tree(tmp_path)
    assert census.landmasses == 2


def test_stock_context_is_cache_first_and_keyed_to_the_install(tmp_path, monkeypatch):
    """One derive per install: the first call reads the bundles and writes the JSON, every later call
    answers from it -- and a cache written for a DIFFERENT game path re-derives instead of serving
    another install's geography."""
    calls = []

    def _fake_derive(game_path, disc=1):
        calls.append(str(game_path))
        return {(0, 0): "L", (1, 0): "~", (5, 9): "L"}
    monkeypatch.setattr(worldscan, "derive_stock_grid", _fake_derive)
    cache = tmp_path / "cache"
    g1 = worldscan.stock_context(tmp_path / "gameA", cache_root=cache)
    assert g1 == {(0, 0): "L", (1, 0): "~", (5, 9): "L"} and len(calls) == 1
    assert (cache / worldscan.STOCK_CACHE_NAME).is_file()
    g2 = worldscan.stock_context(tmp_path / "gameA", cache_root=cache)
    assert g2 == g1 and len(calls) == 1, "the second call must answer from the cache"
    worldscan.stock_context(tmp_path / "gameB", cache_root=cache)
    assert len(calls) == 2, "another install's cache is not this install's geography"
    worldscan.stock_context(tmp_path / "gameA", cache_root=cache, refresh=True)
    assert len(calls) == 3


def test_stock_context_underivable_is_none_and_writes_nothing(tmp_path, monkeypatch):
    def _boom(game_path, disc=1):
        raise RuntimeError("no UnityPy / no install")
    monkeypatch.setattr(worldscan, "derive_stock_grid", _boom)
    cache = tmp_path / "cache"
    assert worldscan.stock_context(tmp_path / "game", cache_root=cache) is None
    assert not (cache / worldscan.STOCK_CACHE_NAME).exists()


def test_stock_rows_round_trip_and_reject_a_wrong_shape():
    grid = {(0, 0): "L", (23, 19): "~", (11, 8): "L"}
    rows = worldscan._rows_encode(grid)
    assert len(rows) == 20 and all(len(r) == 24 for r in rows)
    assert worldscan._rows_decode(rows) == grid
    with pytest.raises(ValueError):
        worldscan._rows_decode(rows[:-1])                    # 19 rows is not the engine's grid


def test_a_malformed_stock_cache_falls_through_to_derive(tmp_path, monkeypatch):
    monkeypatch.setattr(worldscan, "derive_stock_grid", lambda g, disc=1: {(2, 2): "L"})
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / worldscan.STOCK_CACHE_NAME).write_text(json.dumps({"version": 1, "rows": ["xx"]}),
                                                    encoding="utf-8")
    assert worldscan.stock_context(tmp_path / "game", cache_root=cache) == {(2, 2): "L"}


# ---------------------------------------------------------------------------------------- game-gated ---
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_the_real_installs_stock_grid_reads_sane(tmp_path):
    """Derived from the actual install (read-only, cached to a TMP root -- never the dev's cache):
    Uaho island (0,0) -- the kit's DEFAULT_DONOR -- must be land, every key on the 24x20 grid, and
    the land count in a plausible continent range."""
    grid = worldscan.stock_context(config.find_game_path(None), cache_root=tmp_path / "c")
    assert grid is not None
    assert grid.get((0, 0)) == "L", "Uaho island is the kit's default donor -- it had better be land"
    assert all(worldscan.block_in_grid(*k) for k in grid)
    land = sum(1 for v in grid.values() if v == "L")
    assert 50 <= land <= 400, f"implausible stock land count {land}"


def test_landmass_names_write_resolve_and_never_accumulate(tmp_path):
    for bx, by in ((3, 17), (4, 17), (11, 19)):
        _put(tmp_path, bx, by, "Terrain.ff9mesh", _mesh_bytes())
    census = worldscan.scan_tree(tmp_path)
    assert census.name_for((3, 17)) is None
    worldscan.set_landmass_name(census, (4, 17), "Twin Isles")
    assert census.name_for((3, 17)) == "Twin Isles", "any member of the component resolves the name"
    assert census.name_for((11, 19)) is None, "the other landmass is untouched"
    census2 = worldscan.scan_tree(tmp_path)                  # the FILE round-trips through a rescan
    assert census2.name_for((4, 17)) == "Twin Isles"
    worldscan.set_landmass_name(census2, (3, 17), "Ember Isles")   # rename via the OTHER member
    raw = json.loads((tmp_path / worldscan.NAMES_FILE).read_text(encoding="utf-8"))
    assert list(raw["names"].values()) == ["Ember Isles"], "one entry per component, updated in place"
    worldscan.set_landmass_name(census2, (4, 17), "")         # empty = un-name
    assert worldscan.scan_tree(tmp_path).names == {}


def test_a_gone_landmasss_name_stays_in_the_file_never_the_census(tmp_path):
    """A name whose blocks were reverted keeps its file entry (the island may come back) but never
    draws over empty water -- and a later save of ANOTHER landmass preserves it."""
    _put(tmp_path, 2, 2, "Terrain.ff9mesh", _mesh_bytes())
    (tmp_path / worldscan.NAMES_FILE).write_text(
        json.dumps({"version": 1, "names": {"2,2": "Here", "9,9": "Ghost Isle"}}), encoding="utf-8")
    census = worldscan.scan_tree(tmp_path)
    assert census.names == {(2, 2): "Here"}
    worldscan.set_landmass_name(census, (2, 2), "Renamed")
    raw = json.loads((tmp_path / worldscan.NAMES_FILE).read_text(encoding="utf-8"))
    assert raw["names"] == {"2,2": "Renamed", "9,9": "Ghost Isle"}


def test_malformed_names_json_never_fails_a_scan(tmp_path):
    _put(tmp_path, 2, 2, "Terrain.ff9mesh", _mesh_bytes())
    (tmp_path / worldscan.NAMES_FILE).write_text("{not json", encoding="utf-8")
    assert worldscan.scan_tree(tmp_path).names == {}


def test_find_world_trees_prefers_the_world_folder(tmp_path):
    for name, has_tree in (("FF9CustomMap", True), ("FF9CustomMap-world", True),
                           ("SomeOtherMod", False), ("x64", False)):
        d = tmp_path / name
        (d / "FF9_Data" / "WorldMap" / "Disc1").mkdir(parents=True) if has_tree \
            else d.mkdir(parents=True)
    trees = worldscan.find_world_trees(tmp_path)
    assert [t.name for t in trees] == ["FF9CustomMap-world", "FF9CustomMap"]
