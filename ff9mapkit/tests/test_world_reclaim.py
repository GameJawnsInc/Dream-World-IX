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


def _tri_slope_deg(bm, tri):
    import math
    a, b, c = bm.verts[tri[0]], bm.verts[tri[1]], bm.verts[tri[2]]
    ux, uy, uz = (b[i] - a[i] for i in range(3))
    wx, wy, wz = (c[i] - a[i] for i in range(3))
    nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
    L = math.sqrt(nx * nx + ny * ny + nz * nz)
    return math.degrees(math.acos(min(1.0, abs(ny) / L))) if L > 1e-9 else 0.0


def test_cliff_block_mesh_is_a_steep_faithful_wall():
    # the FAITHFUL (7,17) cliff: a rolling top dropping to Y=0 via a STEEP ~73deg rock WALL, NOT a gentle apron.
    bm = M.cliff_block_mesh(disc=1, x=4, y=17, cliff_dirs=[(-1, 0), (1, 0), (0, 1), (0, -1)], seg=10,
                            land_height=4.0, rim_run=1.2, roll_amp=0.6)
    ys = [v[1] for v in bm.verts]
    assert min(ys) == 0.0 and max(ys) >= 4.0                  # border at the waterline (0) -> land top (~4 + roll)
    assert all(_geom_normal_y(bm, t) > 0 for t in bm.tris)    # EVERY tri up-facing -> survives the walkmesh filter
    # the wall tris (topo 58) are STEEP: essentially all >45deg, median well above the island apron's ~24deg
    wall = [t for t in bm.tris
            if X.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] == 58
            and (max(bm.verts[k][1] for k in t) - min(bm.verts[k][1] for k in t)) > 0.3]
    slopes = sorted(_tri_slope_deg(bm, t) for t in wall)
    assert slopes and min(slopes) > 45.0                      # 100% of face tris are a wall, not a ramp (matches real)
    assert 65.0 < slopes[len(slopes) // 2] < 80.0             # median ~73deg (real measured 72deg)
    topos = {X.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] for t in bm.tris}
    assert topos == {0, 58}                                   # walkable plains top (0) + blocked rock wall (58)
    # WATERTIGHT: coincident XZ corners share Y (height is a pure fn of XZ) -> no tears
    seen = {}
    for v in bm.verts:
        k = (round(v[0], 3), round(v[2], 3))
        assert abs(seen.setdefault(k, v[1]) - v[1]) < 1e-4
    # a cell with NO cliff edges is a flat-topped interior (no wall)
    interior = M.cliff_block_mesh(disc=1, x=2, y=17, cliff_dirs=[], seg=8, land_height=4.0, roll_amp=0.0)
    assert {X.decode_id(int(round(interior.tangents[t[0]][0])))["topograph"] for t in interior.tris} == {0}


def test_cliff_rock_uvs_constant_density_no_corner_stretch():
    # the real cliff-face UV rule (survey of 7808 real wall tris): constant texel density via ALONG-SHORE ARC-LENGTH,
    # NOT atan2 angle (which stretched at corners). Assert: U tiles the rock strip, density is uniform incl. at corners.
    import math
    bm = M.cliff_block_mesh(disc=1, x=4, y=17, cliff_dirs=[(-1, 0), (1, 0), (0, 1), (0, -1)], seg=10)
    for u in bm.chan_arrays[X.CH_UV]:
        u[0] = u[1] = 0.0                                    # clear (palette would set these) so we read only the rock UVs
    bm = T._apply_cliff_rock_uvs(bm)
    V, UV = bm.verts, bm.uvs
    dens_all, dens_corner = [], []
    for t in range(len(bm.flat_index) // 3):
        idx = bm.flat_index[3 * t:3 * t + 3]
        if X.decode_id(int(round(bm.tangents[idx[0]][0])))["topograph"] != 58:
            continue
        ys = [V[i][1] for i in idx]
        if max(ys) - min(ys) <= 0.3:
            continue
        us = [UV[i][0] for i in idx]; vs = [UV[i][1] for i in idx]
        assert all(0.699 - 1e-6 <= u <= 0.947 + 1e-6 for u in us)      # U stays inside the rock strip
        edges = max(math.dist(V[idx[a]], V[idx[b]]) for a in range(3) for b in range(a + 1, 3))
        d = math.hypot(max(us) - min(us), max(vs) - min(vs)) / edges
        dens_all.append(d)
        cxx = sum(V[i][0] for i in idx) / 3; czz = sum(V[i][2] for i in idx) / 3
        if min(cxx, 64 - cxx) < 8 and min(-czz, 64 + czz) < 8:         # a corner tri
            dens_corner.append(d)
    assert dens_all and dens_corner
    med_all = sorted(dens_all)[len(dens_all) // 2]
    med_corner = sorted(dens_corner)[len(dens_corner) // 2]
    assert 0.008 < med_all < 0.016                            # ~real 0.0115-0.013 texels/u
    assert abs(med_corner - med_all) / med_all < 0.35         # corners are NOT stretched (density ~ the flats)


def test_blob_cliff_is_a_smooth_organic_island():
    # the faithful move off the 64u SQUARE: a smooth star-convex outline (FF9 coasts are gentle ~25u curves,
    # NOT rectangles). Assert: organic outline (not axis-aligned), watertight, all walkable, rock UV along the curve.
    import math
    bm, outline = M.blob_cliff_block_mesh(x=4, y=17)
    # outline is organic: radii vary (a real curve), and it is NOT the cell rectangle (no long axis-aligned runs)
    rad = [math.hypot(px - 32.0, pz + 32.0) for (px, pz) in outline]
    assert 15.0 < min(rad) and max(rad) < 31.0                 # inside the 64u cell with a water margin, non-degenerate
    assert (max(rad) - min(rad)) > 1.5                         # the radius varies -> a curve, not a circle/square
    axis_aligned = sum(1 for i in range(len(outline))
                       if abs(outline[i][0] - outline[i - 1][0]) < 0.05 or abs(outline[i][1] - outline[i - 1][1]) < 0.05)
    assert axis_aligned < len(outline) * 0.15                  # almost no axis-aligned edges (not a rectangle)
    # mesh integrity: every tri up-facing (walkable, incl. the submerged floor)
    assert all(_geom_normal_y(bm, t) > 0 for t in bm.tris)
    # flat_index is what write_ff9mesh() actually serializes -- it must mirror the (possibly winding-flipped) tris,
    # not the pre-flip emission order, or the shipped index buffer would still be down-facing
    assert all(_geom_normal_y(bm, bm.flat_index[3 * k:3 * k + 3]) > 0 for k in range(len(bm.tris)))
    # the ISLAND (topo 0 grass + 58 wall) is watertight (coincident XZ share Y); the submerged floor is a separate layer
    island_vis = {i for t in bm.tris if X.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] in (0, 58) for i in t}
    seen = {}
    for i in island_vis:
        v = bm.verts[i]
        k = (round(v[0], 3), round(v[2], 3))
        assert abs(seen.setdefault(k, v[1]) - v[1]) < 1e-4
    topos = {X.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] for t in bm.tris}
    assert topos == {0, 58, 57}                                # grass top + rock wall + submerged sea-floor (full cell)
    ys = [v[1] for v in bm.verts]
    assert min(ys) < 0.0 and 3.0 < max(ys) < 4.2              # submerged floor (<0) up to the island top (~land_height)
    assert 0.0 in {round(v[1], 2) for t in bm.tris if X.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] == 58
                   for v in [bm.verts[i] for i in t]}          # the rock wall reaches the waterline (Y=0)
    # rock UV runs along the SMOOTH outline arc-length -> stays in the strip, uniform density (no corner warp)
    for u in bm.chan_arrays[X.CH_UV]:
        u[0] = u[1] = 0.0
    bm = T._apply_cliff_rock_uvs(bm, outline=outline)
    wall_us = [bm.uvs[i][0] for t in bm.tris if X.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] == 58 for i in t]
    assert wall_us and all(0.699 - 1e-6 <= u <= 0.947 + 1e-6 for u in wall_us)
    # a distinct seed per cell -> a distinct shape (reproducible, not identical islands)
    _, outline2 = M.blob_cliff_block_mesh(x=9, y=3)
    assert outline2 != outline


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
    with pytest.raises(ValueError, match=r"^cell \(2,20\) out of the"):
        T.reclaim("MOD", cells=[(2, 20)], dry_run=True)      # y=20 is outside the 24x20 grid
    with pytest.raises(ValueError, match=r"^cell \(24,5\) out of the"):
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
