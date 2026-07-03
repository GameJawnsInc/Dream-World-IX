"""world-reclaim: turn an OCEAN cell into walkable LAND (Path D -- new continent).

Hermetic: the synthesized flat-block geometry (fresh up-wound verts, walkable topograph, all 4 channels, ff9mesh
round-trip) + the reclaim orchestration (right deploy relpath/part, palette applied, dry-run writes nothing) with the
palette/deploy calls stubbed. One game-gated test proves a real palette textures the plane.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import mesh as M, extract as X, palette as PAL, terrain as T
from ff9mapkit.cli import _parse_cells


def _geom_normal_y(bm, tri):
    a, b, c = bm.verts[tri[0]], bm.verts[tri[1]], bm.verts[tri[2]]
    e1 = [b[i] - a[i] for i in range(3)]
    e2 = [c[i] - a[i] for i in range(3)]
    return e1[2] * e2[0] - e1[0] * e2[2]          # Cross(e1,e2).y -- the engine's WMBlock.cs:70 up-facing test


def test_flat_block_mesh_shape_and_winding():
    seg = 8
    bm = M.flat_block_mesh(disc=1, x=2, y=12, seg=seg, topograph=0)
    assert len(bm.tris) == 2 * seg * seg                      # 2 tris per quad
    assert bm.vcount == 6 * seg * seg                         # FRESH verts per triangle (flat/unindexed)
    assert bm.vcount == len(bm.flat_index)                    # unindexed: vcount == indexCount
    assert all(n == [0.0, 1.0, 0.0] for n in bm.normals)      # stored normals up (render shading)
    assert all(_geom_normal_y(bm, t) > 0 for t in bm.tris)    # EVERY tri geometrically up-facing (== walkable)
    xs = [v[0] for v in bm.verts]
    zs = [v[2] for v in bm.verts]
    ys = {v[1] for v in bm.verts}
    assert (min(xs), max(xs)) == (0.0, 64.0)                  # local block frame x[0,64]
    assert (min(zs), max(zs)) == (-64.0, 0.0)                 # z[-64,0]
    assert ys == {0.0}                                        # flat at height=0


def test_flat_block_mesh_topograph_walkable_and_roundtrips(tmp_path):
    bm = M.flat_block_mesh(disc=1, x=3, y=4, seg=4, topograph=0, height=2.5)
    idall = int(round(bm.tangents[0][0]))
    assert idall == X.encode_id(topograph=0)                  # tangent.x carries the walkable id
    d = X.decode_id(idall)
    assert d["topograph"] == 0 and d["event"] == 0            # plain walkable land, not an entrance
    assert idall not in (4078, 4088, 2040, 12782)             # not an engine-special-cased raycast id
    assert {v[1] for v in bm.verts} == {2.5}                  # height honoured
    # .ff9mesh write -> read round-trips every channel + the index buffer
    p = M.write_ff9mesh(bm, tmp_path / "flat.ff9mesh")
    r = M.read_ff9mesh(p)
    assert r["vcount"] == bm.vcount and len(r["indices"]) == len(bm.flat_index)
    assert r["normals"] and r["uvs"] and r["tangents"]


def test_island_block_mesh_profile():
    # a CORNER cell (water on 2 edges) ramps from underwater up to the plateau, mixing shore+grass, all walkable
    corner = M.island_block_mesh(disc=1, x=1, y=16, water_dirs=[(-1, 0), (0, -1)], seg=8, height=6.0, beach=18.0)
    ys = [v[1] for v in corner.verts]
    assert min(ys) == 0.0 and max(ys) == 6.0                 # ramps from the waterline (0) up to the plateau (6)
    assert all(_geom_normal_y(corner, t) > 0 for t in corner.tris)          # every ramp face still up-facing
    topos = {X.decode_id(int(round(corner.tangents[t[0]][0])))["topograph"] for t in corner.tris}
    assert 20 in topos and 0 in topos                        # tan-sand shore ring (20) + green-grass top (0)
    # an INTERIOR cell (no water edge) is a flat grass plateau
    interior = M.island_block_mesh(disc=1, x=2, y=17, water_dirs=[], seg=8, height=6.0)
    assert {v[1] for v in interior.verts} == {6.0}
    assert {X.decode_id(int(round(interior.tangents[t[0]][0])))["topograph"] for t in interior.tris} == {0}


def test_reclaim_dry_run_and_dispatch(monkeypatch):
    deployed = []
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)          # no install needed
    monkeypatch.setattr(X, "list_blocks", lambda **k: [(3, 12)])               # a real-coast neighbour of (2,12)
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: deployed.append((bm.x, bm.y, k.get("part"))))
    s = T.reclaim("MOD", cells=[(2, 12), (2, 13)], dry_run=True)               # island profile (default)
    assert s["op"] == "reclaim" and s["profile"] == "island" and s["disc"] == 1
    assert [c["cell"] for c in s["cells"]] == [[2, 12], [2, 13]]
    # (2,12): neighbours (3,12)=real land [no beach], (2,13)=reclaimed [no beach], (1,12)+(2,11)=water -> 2 edges
    assert s["cells"][0]["water_edges"] == 2
    assert deployed == []                                                     # dry-run writes nothing
    T.reclaim("MOD", cells=[(2, 12)], profile="flat", topograph=17)
    assert deployed == [(2, 12, "Terrain")]                                   # deploys the Terrain override


def test_reclaim_rejects_out_of_grid(monkeypatch):
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)
    with pytest.raises(ValueError):
        T.reclaim("MOD", cells=[(2, 20)], dry_run=True)      # y=20 is outside the 24x20 grid
    with pytest.raises(ValueError):
        T.reclaim("MOD", cells=[(24, 5)], dry_run=True)      # x=24 outside


def test_parse_cells():
    assert _parse_cells("2,12;2,13") == [(2, 12), (2, 13)]
    assert _parse_cells("3,4 5,6") == [(3, 4), (5, 6)]        # whitespace-separated too
    assert _parse_cells("2-4,5-6") == [(2, 5), (2, 6), (3, 5), (3, 6), (4, 5), (4, 6)]   # a rectangular landmass
    assert _parse_cells("1,1;1,1") == [(1, 1)]               # de-dups


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_reclaim_palette_textures_the_plane():
    bm = M.flat_block_mesh(disc=1, x=2, y=12, seg=8, topograph=0)
    bm2 = PAL.apply_palette_uvs(bm, topograph=0, disc=1, part="terrain")
    nonzero = sum(1 for u in bm2.uvs if abs(u[0]) > 1e-6 or abs(u[1]) > 1e-6)
    assert nonzero == bm2.vcount                              # every vert gets a real terrain-atlas UV (not white)
