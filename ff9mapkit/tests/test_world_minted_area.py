"""THE MINTED-LAND AREA (terrain study policy R1).

world-reclaim and world-island stamped every minted tri with area 0: zone 0, so their grass (topograph 0) rolled
Mist Continent battles and the title read "Gunitas Basin". The Southern Ring needed a post-hoc 112-file restamp.
Now an explicit ``--area`` wins; land that joins stock ground inherits that ground's area (its camera place, battles
and label continue: stock has no walkable camera seam); land out at open sea gets the safe road, area 14 (no random
battles on kit ground under the s60 patch; the owner's pick).
"""
from __future__ import annotations

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import extract as X, mesh as M, palette as PAL, terrain as T


def _grid(bx, by, idall_at, step=4.0):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, tan, tris = [], [], []
    n = int(64 / step)
    for i in range(n):
        for j in range(n):
            x0, z0 = i * step, -j * step
            x1, z1 = x0 + step, z0 - step
            for corners in (((x0, z0), (x0, z1), (x1, z0)), ((x1, z0), (x0, z1), (x1, z1))):
                cx, cz = sum(c[0] for c in corners) / 3, sum(c[1] for c in corners) / 3
                idall = float(idall_at(cx, cz))
                base = len(pos)
                for (x, z) in corners:
                    pos.append([x, 0.0, z])
                    tan.append([idall, 0.0, 0.0, 1.0])
                tris.append([base, base + 1, base + 2])
    nv = len(pos)
    return BlockMesh(name=f"Block[{bx}][{by}] Terrain", disc=1, x=bx, y=by, lod="0_1", vcount=nv, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * nv, CH_UV: [[0.5, 0.5]] * nv,
                                  CH_TAN: tan},
                     flat_index=list(range(nv)), tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _areas(bm):
    return sorted({X.decode_id(int(round(bm.tangents[t[0]][0])))["area"] for t in bm.tris})


def test_stamp_area_leaves_entrances_and_walk_skips_alone():
    def at(x, z):
        if x < 8:
            return X.encode_id(1, 30, 0)                            # an entrance tile
        if x < 16:
            return 4078                                             # walk-skip (decodes as area 15)
        return X.encode_id(0, 0, 31, 2)
    bm = _grid(5, 5, at)
    assert M.stamp_area(bm, 14) == 384                                         # 512 tris less 64 + 64
    kept = [X.decode_id(int(round(bm.tangents[t[0]][0]))) for t in bm.tris]
    assert {"event": 0, "area": 14, "topograph": 31, "flags": 2} in kept      # topograph and flags kept
    assert {"event": 1, "area": 30, "topograph": 0, "flags": 0} in kept      # the entrance untouched
    assert M.stamp_area(bm, 14) == 0                                          # idempotent


def test_minted_area_policy():
    assert T.minted_area(None)["area"] == M.SAFE_ROAD_AREA == 14
    assert T.minted_area(None)["source"] == "open-sea" and T.minted_area(None)["zone"] == 6
    assert T.minted_area(None, host={"area": 41, "votes": {41: 9.0}})["source"] == "host"
    assert T.minted_area(5, host={"area": 41, "votes": {}})["area"] == 5
    for bad in (64, -1, "14", 14.0, True):
        with pytest.raises(ValueError, match="area must be"):
            T.minted_area(bad)


@pytest.fixture
def no_install(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    return tmp_path


@pytest.mark.parametrize("nb, near", [((6, 5), lambda x, z: x < 8), ((4, 5), lambda x, z: x > 56),
                                      ((5, 6), lambda x, z: z > -8), ((5, 4), lambda x, z: z < -56)])
def test_host_area_reads_only_the_strip_along_the_shared_edge(no_install, monkeypatch, nb, near):
    """Each neighbour votes with the 8u strip that touches the cell; the rest of the block (a bigger area 7) does not."""
    def stock(bx, by, part="terrain", **k):
        if (bx, by) != nb or part != "terrain":
            raise ValueError("mesh not found")
        return _grid(bx, by, lambda x, z: X.encode_id(0, 41 if near(x, z) else 7, 0))
    monkeypatch.setattr(X, "read_block", stock)
    h = T.host_area_for_cells([(5, 5)], "MOD")
    assert h["area"] == 41 and set(h["votes"]) == {41}


def test_host_area_ignores_water_canopy_entrances_and_reclaimed_neighbours(no_install, monkeypatch):
    def stock(bx, by, part="terrain", **k):
        if part != "terrain":
            raise ValueError("mesh not found")
        if (bx, by) == (6, 5):
            return _grid(bx, by, lambda x, z: X.encode_id(0, 41, 57))   # sea topograph: not walkable
        if (bx, by) == (4, 5):
            return _grid(bx, by, lambda x, z: X.encode_id(0, 7, 37))    # canopy
        if (bx, by) == (5, 6):
            return _grid(bx, by, lambda x, z: X.encode_id(1, 9, 0))     # all entrance tiles
        if (bx, by) == (5, 4):
            return _grid(bx, by, lambda x, z: X.encode_id(0, 22, 0))    # reclaimed in the same call: excluded
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    assert T.host_area_for_cells([(5, 5), (5, 4)], "MOD")["area"] is None


def _open_sea(*a, **k):
    raise ValueError("mesh not found")


@pytest.fixture
def reclaim_env(no_install, monkeypatch):
    seen = []
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)
    monkeypatch.setattr(X, "list_blocks", lambda **k: [])
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: seen.append((k["part"], bm)) or no_install / "x")
    return seen


def _terrain_areas(seen):
    return sorted({a for part, bm in seen if part == "Terrain" for a in _areas(bm)})


@pytest.mark.parametrize("profile", ["island", "cliff", "flat"])
def test_reclaim_at_open_sea_stamps_the_safe_road(reclaim_env, monkeypatch, profile):
    monkeypatch.setattr(X, "read_block", _open_sea)
    s = T.reclaim("MOD", cells=[(5, 5)], profile=profile, skip_mirror=True)
    assert s["area"]["area"] == 14 and s["area"]["source"] == "open-sea"
    assert _terrain_areas(reclaim_env) == [14]


def test_reclaim_joining_land_inherits_its_area_and_area_overrides(reclaim_env, monkeypatch):
    def stock(bx, by, part="terrain", **k):
        if (bx, by) == (6, 5) and part == "terrain":
            return _grid(bx, by, lambda x, z: X.encode_id(0, 41, 0))
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    s = T.reclaim("MOD", cells=[(5, 5)], profile="flat", skip_mirror=True)
    assert s["area"]["source"] == "host" and s["area"]["camera_place"] == 1 and _terrain_areas(reclaim_env) == [41]
    reclaim_env.clear()
    s = T.reclaim("MOD", cells=[(5, 5)], profile="flat", area=3, skip_mirror=True)
    assert s["area"]["source"] == "explicit" and _terrain_areas(reclaim_env) == [3]
    reclaim_env.clear()
    with pytest.raises(ValueError, match="area must be"):
        T.reclaim("MOD", cells=[(5, 5)], profile="flat", area=99, skip_mirror=True)
    assert reclaim_env == []                                      # refused before any write


def test_cli_reclaim_area_flag_and_receipt(reclaim_env, monkeypatch, capsys):
    monkeypatch.setattr(X, "read_block", _open_sea)
    assert cli.main(["world-reclaim", "--mod-folder", "MOD", "--cells", "5,5", "--profile", "flat", "--dry-run"]) == 0
    assert "ground area 14 (open sea: the safe road" in capsys.readouterr().out
    assert cli.main(["world-reclaim", "--mod-folder", "MOD", "--cells", "5,5", "--profile", "flat", "--dry-run",
                     "--area", "12"]) == 0
    out = capsys.readouterr().out
    assert "ground area 12 (--area)" in out and "the area-12 camera LOCK" in out


def _game_ready() -> bool:
    try:
        import UnityPy  # noqa: F401
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_cells_open_sea_and_a_coast_with_ground_at_the_edge():
    mod = "FF9CustomMap_test_nonexistent"
    assert T.reclaim(mod, cells=[(23, 10)], profile="cliff", dry_run=True)["area"]["area"] == 14
    s = T.reclaim(mod, cells=[(7, 0)], profile="flat", dry_run=True)          # stock area-56 ground at its edge
    assert s["area"]["source"] == "host" and s["area"]["area"] == 56 and s["area"]["camera_place"] == 2
