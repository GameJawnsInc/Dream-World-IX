"""world-water: the marching-band graded open-ocean synthesizer.

Fully hermetic -- :func:`water` SYNTHESIZES its meshes (it never reads real p0data; the donor is only NAMED in a
sidecar), so the only IO is deploy_override / deploy_donor_sidecar, which we stub. Coverage:
  * the deploy orchestration (6 parts + a Donor.txt per cell, right names/donor, dry-run writes nothing, grid validation)
  * the byte-derived language + the MARCHING-BAND invariants that offline stats CAN check: sea3 never touches sea4,
    the seam matches ACROSS cells/blocks (the whole point of world-space edge sampling), UVs stay in-texture, the
    4-rotation orientation model, and the default gradient actually grades.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import extract as X, mesh as M, water as W


# ---- deploy orchestration -------------------------------------------------------------------------------------------

def _capture(monkeypatch):
    overrides, sidecars = [], []
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, **k: overrides.append((bm.x, bm.y, bm.vcount, k.get("part"))))
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: sidecars.append((dx, dy, k["x"], k["y"])))
    return overrides, sidecars


def test_water_deploys_six_parts_and_sidecar(monkeypatch):
    overrides, sidecars = _capture(monkeypatch)
    s = W.water("MOD", cells=[(3, 17)], donor=(15, 4))
    assert s["op"] == "water" and s["donor"] == [15, 4]
    parts = [o[3] for o in overrides]
    assert parts == ["Terrain", "Sea3", "Sea5", "Sea4", "Sea1", "Sea2"]      # fixed, complete part set
    assert all(o[0] == 3 and o[1] == 17 for o in overrides)                  # all on the target cell
    assert sidecars == [(15, 4, 3, 17)]                                      # one Donor.txt naming the donor
    # the blanked coast shades are the 3-vert hidden mesh; the water bands are real geometry
    by_part = {o[3]: o[2] for o in overrides}
    assert by_part["Sea1"] == 3 and by_part["Sea2"] == 3
    assert by_part["Sea3"] > 3 and by_part["Sea4"] > 3


def test_water_multi_cell_deploys_each(monkeypatch):
    overrides, sidecars = _capture(monkeypatch)
    W.water("MOD", cells=[(3, 17), (4, 17)])
    cells = {(o[0], o[1]) for o in overrides}
    assert cells == {(3, 17), (4, 17)}
    assert len(overrides) == 12 and len(sidecars) == 2                       # 6 parts x 2 cells, a sidecar each


def test_water_dry_run_writes_nothing(monkeypatch):
    overrides, sidecars = _capture(monkeypatch)
    s = W.water("MOD", cells=[(3, 17)], dry_run=True)
    assert s["dry_run"] is True and s["cells"] and overrides == [] and sidecars == []


def test_water_validates_grid_and_args(monkeypatch):
    _capture(monkeypatch)
    with pytest.raises(ValueError):
        W.water("MOD", cells=[(3, 20)], dry_run=True)          # cell off the 24x20 grid
    with pytest.raises(ValueError):
        W.water("MOD", cells=[(3, 17)], donor=(24, 4), dry_run=True)   # donor off-grid
    with pytest.raises(ValueError):
        W.water("MOD", cells=[], dry_run=True)                 # no cells
    with pytest.raises(ValueError):
        W.water("MOD", cells=[(3, 17)], deep_dir="X", dry_run=True)    # bad direction


# ---- open-ocean default vs the graded ramp --------------------------------------------------------------------------

def test_open_ocean_is_the_default_and_mostly_deep():
    s = W.water("MOD", cells=[(3, 17)], dry_run=True)          # no --deep -> faithful open ocean
    assert s["mode"] == "open" and s["deep_dir"] is None
    sh = s["cells"][0]["shades"]
    assert sh["sea4"] > 200 and sh["sea3"] * 5 < sh["sea4"]    # dominantly deep (real open ocean ~94% Sea4)
    assert sh["sea3"] > 0                                       # but a light scatter of shallows, not pure deep


def test_open_ocean_shallows_zero_is_uniform_deep():
    s = W.water("MOD", cells=[(3, 17)], shallows=0.0, dry_run=True)
    assert s["cells"][0]["shades"] == {"sea3": 0, "sea5": 0, "sea4": 256}


def test_deep_dir_opts_into_the_graded_ramp():
    s = W.water("MOD", cells=[(3, 17)], deep_dir="S", dry_run=True)
    assert s["mode"] == "S"
    sh = s["cells"][0]["shades"]
    assert sh["sea3"] > 50 and sh["sea4"] > 50                  # a real gradient: both halves substantial


def test_open_ocean_field_places_the_shallow_fraction():
    d = W.open_ocean_depth_field([(3, 17)], shallows=0.10)
    below = sum(1 for i in range(W.G) for j in range(W.G)
                if d(3 * W.BLOCK + (i + 0.5) * W.CELL, -17 * W.BLOCK - (j + 0.5) * W.CELL) < 1.0)
    assert 20 <= below <= 32                                    # ~10% of 256 cell centres dip shallow (by construction)


# ---- the ocean walkmesh: at the surface, boat-traversable ------------------------------------------------------------

def _capture_meshes(monkeypatch):
    meshes = {}
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: meshes.__setitem__(k.get("part"), bm))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: None)
    return meshes


def test_terrain_walkmesh_sits_at_the_surface_with_a_sea_topograph(monkeypatch):
    meshes = _capture_meshes(monkeypatch)
    W.water("MOD", cells=[(3, 17)])
    ter = meshes["Terrain"]
    # the walkmesh is at the water surface (just below Y=0), NOT the old -3 submerged floor that buried the model
    assert all(abs(v[1] - W.WATER_Y) < 1e-6 for v in ter.verts)
    assert -1.0 < W.WATER_Y <= 0.0
    # and carries the deep-sea topograph (57): a boat (mode 7) traverses it, on-foot/chocobo is blocked -- real ocean
    topos = {X.decode_id(int(round(t[0])))["topograph"] for t in ter.tangents}
    assert topos == {57} and W.WATER_TOPOGRAPH == 57


def test_reproduce_shares_the_ocean_walkmesh(monkeypatch):
    # the A/B reference deploys the SAME surface water walkmesh (it reproduces ocean, not land)
    _stub_reproduce_source(monkeypatch)                        # feeds read_shade_grid / read_sea5_tiles
    meshes = _capture_meshes(monkeypatch)
    W.reproduce("MOD", cells=[(3, 17)])
    ter = meshes["Terrain"]
    assert all(abs(v[1] - W.WATER_Y) < 1e-6 for v in ter.verts)
    assert {X.decode_id(int(round(t[0])))["topograph"] for t in ter.tangents} == {57}


# ---- verbatim A/B reference deploy -----------------------------------------------------------------------------------

def _fake_sea_block(x, y, part, vcount):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    n = vcount
    chan = {CH_POS: [[1.0, 2.0, 3.0]] * n, CH_NRM: [[0.0, 1.0, 0.0]] * n,
            CH_UV: [[0.5, 0.5]] * n, CH_TAN: [[1.0, 0.0, 0.0, 1.0]] * n}
    return BlockMesh(name=f"Block[{x}][{y}] {part}", disc=1, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}, chan_arrays=chan,
                     flat_index=list(range(n)), tris=[[i, i + 1, i + 2] for i in range(0, n, 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _stub_open_ocean(monkeypatch):
    """A source block with real sea3/sea4/sea5 and NO terrain/sea1/sea2 (like the byte-proven block 8,4)."""
    counts = {"sea3": 9, "sea4": 30, "sea5": 6}
    def fake(x, y, **k):
        part = k.get("part")
        if part in counts:
            return _fake_sea_block(x, y, part, counts[part])
        raise ValueError(f"block ({x},{y}) has no {part}")
    monkeypatch.setattr(X, "read_block", fake)
    return counts


def test_deploy_verbatim_carries_real_sea_and_matches_water_shape(monkeypatch):
    counts = _stub_open_ocean(monkeypatch)
    overrides, sidecars = _capture(monkeypatch)
    s = W.deploy_verbatim("MOD", cells=[(3, 17)], source=(8, 4), donor=(15, 4))
    assert s["op"] == "water-verbatim" and s["source"] == [8, 4]
    # SAME deploy shape as water(): 6 parts in the same order + a donor sidecar
    assert [o[3] for o in overrides] == ["Terrain", "Sea3", "Sea5", "Sea4", "Sea1", "Sea2"]
    by_part = {o[3]: o[2] for o in overrides}
    assert by_part["Sea3"] == counts["sea3"] and by_part["Sea4"] == counts["sea4"] and by_part["Sea5"] == counts["sea5"]
    assert by_part["Sea1"] == 3 and by_part["Sea2"] == 3            # blanked (source has none)
    assert all(o[0] == 3 and o[1] == 17 for o in overrides)         # every mesh relocated to the target cell
    assert sidecars == [(15, 4, 3, 17)]
    assert s["cells"][0]["carried"] == ["Sea3", "Sea4", "Sea5"]


def test_deploy_verbatim_does_not_mutate_the_source(monkeypatch):
    _stub_open_ocean(monkeypatch)
    _capture(monkeypatch)
    src = X.read_block(8, 4, part="sea4")
    W.deploy_verbatim("MOD", cells=[(3, 17), (4, 17)], source=(8, 4))
    assert src.x == 8 and src.y == 4                                # the relocation is a copy, not in-place


def test_deploy_verbatim_dry_run_and_validation(monkeypatch):
    _stub_open_ocean(monkeypatch)
    overrides, sidecars = _capture(monkeypatch)
    s = W.deploy_verbatim("MOD", cells=[(3, 17)], dry_run=True)
    assert s["dry_run"] is True and s["cells"] and overrides == [] and sidecars == []
    with pytest.raises(ValueError):
        W.deploy_verbatim("MOD", cells=[(3, 20)], dry_run=True)     # cell off-grid
    with pytest.raises(ValueError):
        W.deploy_verbatim("MOD", cells=[(3, 17)], donor=(24, 4), dry_run=True)   # donor off-grid


def test_deploy_verbatim_rejects_a_non_ocean_source(monkeypatch):
    monkeypatch.setattr(X, "read_block", lambda x, y, **k: (_ for _ in ()).throw(ValueError("land block")))
    _capture(monkeypatch)
    with pytest.raises(ValueError, match="Sea3/Sea4/Sea5"):
        W.deploy_verbatim("MOD", cells=[(3, 17)], source=(12, 10), dry_run=True)


# ---- reproduce a real block's arrangement (the fidelity A/B) ---------------------------------------------------------

def _fake_part_block(x, y, part, cells):
    """A block whose Sea ``part`` sub-mesh covers exactly ``cells`` (each a 4u quad, so read_shade_grid bins it there)."""
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, tris = [], []
    for (i, j) in cells:
        x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
        base = len(pos)
        for (px, pz) in [(x0, z0), (x1, z0), (x1, z1), (x0, z0), (x1, z1), (x0, z1)]:
            pos.append([px, 0.0, pz])
        tris += [[base, base + 1, base + 2], [base + 3, base + 4, base + 5]]
    n = len(pos)
    chan = {CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: [[0.5, 0.5]] * n, CH_TAN: [[1.0, 0.0, 0.0, 1.0]] * n}
    return BlockMesh(name=f"Block[{x}][{y}] {part}", disc=1, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}, chan_arrays=chan,
                     flat_index=list(range(n)), tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _stub_reproduce_source(monkeypatch):
    """A source block with a clean N-shallow gradient: rows j<5 sea3, row j==5 sea5, rows j>5 sea4."""
    sea3 = [(i, j) for i in range(16) for j in range(5)]
    sea5 = [(i, 5) for i in range(16)]
    sea4 = [(i, j) for i in range(16) for j in range(6, 16)]
    by_part = {"sea3": sea3, "sea5": sea5, "sea4": sea4}
    def fake(x, y, **k):
        part = k.get("part")
        if part in by_part:
            return _fake_part_block(x, y, part, by_part[part])
        raise ValueError(part)
    monkeypatch.setattr(X, "read_block", fake)
    return {"sea3": 80, "sea5": 16, "sea4": 160}


def test_read_shade_grid_bins_tris(monkeypatch):
    _stub_reproduce_source(monkeypatch)
    grid = W.read_shade_grid(8, 4)
    assert grid[0][0] == "sea3" and grid[0][5] == "sea5" and grid[0][15] == "sea4"
    assert W.shade_counts(grid) == {"sea3": 80, "sea5": 16, "sea4": 160}


def test_arrangement_from_block_reselects_every_sea5(monkeypatch):
    _stub_reproduce_source(monkeypatch)
    grid, sea5tile = W.arrangement_from_block(8, 4)
    sea5cells = [(i, j) for i in range(W.G) for j in range(W.G) if grid[i][j] == "sea5"]
    assert len(sea5tile) == len(sea5cells)                         # every sea5 cell re-tiled
    # a sea5 cell with sea4 to the SOUTH gets the tip pointing south = strip0 / r90 (DEEPSET2TILE[{"S"}])
    assert sea5tile[(0, 5)] == (0, "r90")
    assert W.adjacency_violations(grid) == 0                       # a marching-band-consistent layout


def test_reproduce_matches_source_layout_and_deploys(monkeypatch):
    counts = _stub_reproduce_source(monkeypatch)
    overrides, sidecars = _capture(monkeypatch)
    s = W.reproduce("MOD", cells=[(3, 17)], source=(8, 4), donor=(15, 4))
    assert s["op"] == "water-reproduce" and s["source"] == [8, 4]
    # the reproduced cell has the SOURCE's shade distribution (that's the whole point -- same layout, synth tiles)
    assert s["cells"][0]["shades"] == counts and s["cells"][0]["adjacency_violations"] == 0
    assert [o[3] for o in overrides] == ["Terrain", "Sea3", "Sea5", "Sea4", "Sea1", "Sea2"]
    assert all(o[0] == 3 and o[1] == 17 for o in overrides) and sidecars == [(15, 4, 3, 17)]


def test_reproduce_dry_run_and_validation(monkeypatch):
    _stub_reproduce_source(monkeypatch)
    overrides, sidecars = _capture(monkeypatch)
    s = W.reproduce("MOD", cells=[(3, 17)], dry_run=True)
    assert s["dry_run"] is True and s["cells"] and overrides == [] and sidecars == []
    with pytest.raises(ValueError):
        W.reproduce("MOD", cells=[(3, 20)], dry_run=True)          # cell off-grid
    with pytest.raises(ValueError):
        W.reproduce("MOD", cells=[(3, 17)], donor=(24, 4), dry_run=True)   # donor off-grid


# ---- exact real-tile reproduction (read the block's actual Sea5 tiles, not a shade guess) ----------------------------

def _sea5_corners_uv(u0, u1, v0, v1, oname):
    m = W.OMAPS[oname]
    return {(fx, fz): (u0 + m(fx, fz)[0] * (u1 - u0), v0 + m(fx, fz)[1] * (v1 - v0)) for fx in (0, 1) for fz in (0, 1)}


def _sea5_corners(strip, oname):
    return _sea5_corners_uv(W.UFULL[0], W.UFULL[1], W.VSTRIP[strip][0], W.VSTRIP[strip][1], oname)


def _fake_sea5_block(x, y, celluvs):
    """A Sea5 sub-mesh whose cell ``(i,j)`` carries the exact corner UVs ``celluvs[(i,j)] = {(fx,fz): (u,v)}``."""
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, uv, tris = [], [], []
    for (i, j), corners in celluvs.items():
        pts = {(0, 0): (i * 4.0, -j * 4.0), (1, 0): ((i + 1) * 4.0, -j * 4.0),
               (1, 1): ((i + 1) * 4.0, -(j + 1) * 4.0), (0, 1): (i * 4.0, -(j + 1) * 4.0)}
        base = len(pos)
        for c in [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]:
            px, pz = pts[c]
            pos.append([px, 0.0, pz])
            uv.append(list(corners[c]))
        tris += [[base, base + 1, base + 2], [base + 3, base + 4, base + 5]]
    n = len(pos)
    chan = {CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: uv, CH_TAN: [[1.0, 0.0, 0.0, 1.0]] * n}
    return BlockMesh(name=f"Block[{x}][{y}] sea5", disc=1, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}, chan_arrays=chan,
                     flat_index=list(range(n)), tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def test_fit_tile_roundtrips_every_strip_and_rotation():
    for strip in range(4):
        for oname in W.ROTS:
            u0, u1, v0, v1, name = W._fit_tile(_sea5_corners(strip, oname))
            assert W._strip_of(v0) == strip and name == oname


def test_fit_tile_rejects_a_transpose():
    u0, u1 = W.UFULL
    v0, v1 = W.VSTRIP[1]
    # u tracks fz, v tracks fx -> a transpose, which no pure rotation reproduces
    d = {(fx, fz): (u0 + fz * (u1 - u0), v0 + fx * (v1 - v0)) for fx in (0, 1) for fz in (0, 1)}
    assert W._fit_tile(d) is None


def test_read_sea5_tiles_recovers_orientation_and_exact_rect(monkeypatch):
    specs = {(3, 3): (2, "r0"), (4, 4): (1, "r90"), (7, 2): (0, "r270"), (9, 9): (3, "r180")}
    celluvs = {c: _sea5_corners(strip, oname) for c, (strip, oname) in specs.items()}

    def fake(x, y, **k):
        if k.get("part") == "sea5":
            return _fake_sea5_block(x, y, celluvs)
        raise ValueError("only sea5")
    monkeypatch.setattr(X, "read_block", fake)
    got = W.read_sea5_tiles(8, 4)
    assert {c: v[:2] for c, v in got.items()} == specs             # (strip, rotation) recovered
    for c, (strip, _) in specs.items():                            # and the exact rect is carried
        assert got[c][2:] == pytest.approx((W.UFULL[0], W.UFULL[1], W.VSTRIP[strip][0], W.VSTRIP[strip][1]))


def test_reproduce_carries_exact_deviating_v_band(monkeypatch):
    # real block (8,4) strip3 tiles sample v-band (0.74016, 1.0), which DEVIATES from canonical VSTRIP[3]=(0.75591,1.0);
    # the fix carries the real rect so the reproduction matches the block (not the nearest canonical strip)
    dev_v0, dev_v1 = 0.74016, 1.0
    celluvs = {(5, 5): _sea5_corners_uv(W.UFULL[0], W.UFULL[1], dev_v0, dev_v1, "r0")}

    def fake(x, y, **k):
        if k.get("part") == "sea5":
            return _fake_sea5_block(x, y, celluvs)
        raise ValueError("only sea5")     # sea3/sea4 absent -> (5,5) sea5, the rest default to sea4
    monkeypatch.setattr(X, "read_block", fake)
    grid, sea5tile = W.arrangement_from_block(8, 4)
    assert grid[5][5] == "sea5"
    t = sea5tile[(5, 5)]
    assert t[0] == 3 and t[1] == "r0"                              # classified strip 3 / r0
    assert t[4] == pytest.approx(dev_v0)                           # carries the REAL v0
    assert abs(t[4] - W.VSTRIP[3][0]) > 0.01                       # and it is NOT the canonical band (the fix)


def test_arrangement_prefers_real_tiles_over_the_shade_heuristic(monkeypatch):
    sea3 = [(i, j) for i in range(16) for j in range(5)]
    sea5 = [(i, 5) for i in range(16)]
    sea4 = [(i, j) for i in range(16) for j in range(6, 16)]
    real = _sea5_corners(2, "r180")                                # deliberately != the heuristic's (0,"r90")

    def fake(x, y, **k):
        p = k.get("part")
        if p == "sea3":
            return _fake_part_block(x, y, "sea3", sea3)
        if p == "sea4":
            return _fake_part_block(x, y, "sea4", sea4)
        if p == "sea5":
            return _fake_sea5_block(x, y, {c: real for c in sea5})
        raise ValueError(p)
    monkeypatch.setattr(X, "read_block", fake)
    _, with_real = W.arrangement_from_block(8, 4, real_tiles=True)
    _, heuristic = W.arrangement_from_block(8, 4, real_tiles=False)
    assert with_real[(0, 5)][:2] == (2, "r180")                    # the real UV wins (strip, rotation)
    assert heuristic[(0, 5)] == (0, "r90")                         # the shade guess (a sea5 cell facing sea4 to the south)


# ---- the marching-band language + invariants ------------------------------------------------------------------------

def test_sea3_never_touches_sea4_within_a_cell():
    depth = W.default_depth_field([(3, 17)], deep_dir="S")
    _, grid, _ = W.build_cell(3, 17, depth=depth)
    assert W.adjacency_violations(grid) == 0                    # a Sea5 band ALWAYS bridges shallow<->deep


def test_seam_sample_points_shared_across_blocks():
    """The world-coord generalization, tested where it can actually FAIL: adjacent cells must resolve their shared edge
    to the IDENTICAL world point, so the depth classification agrees and the seams line up across BLOCK boundaries. A
    block-local `_edge_mids` (dropping the bx*64 / -by*64 offset) breaks this -- and THIS assertion catches it, where a
    plain 0-{sea3,sea4}-count does not (a graded field rarely abuts sea3 on sea4 even when sampling is broken)."""
    G = W.G
    for j in range(G):
        assert W._edge_mids(3, 17, G - 1, j)["E"] == W._edge_mids(4, 17, 0, j)["W"]    # horizontal block seam
    for i in range(G):
        assert W._edge_mids(3, 17, i, G - 1)["S"] == W._edge_mids(3, 18, i, 0)["N"]    # vertical block seam
    # anchor the absolute world frame too (a self-consistent sign flip would pass identity alone)
    assert W._edge_mids(3, 17, G - 1, 0)["E"] == (256.0, -1090.0)
    assert W._edge_mids(3, 17, 0, G - 1)["S"] == (194.0, -1152.0)


def test_transition_band_bridges_a_block_seam():
    """Behavioral, non-vacuous: over a real S-gradient the region spans sea3..sea4 (a genuine gradient) yet the Sea5
    band always bridges shallow<->deep ACROSS the vertical block seam (0 direct sea3|sea4 adjacencies)."""
    depth = W.default_depth_field([(3, 17), (3, 18)], deep_dir="S")
    top = W.build_cell(3, 17, depth=depth)[1]
    bot = W.build_cell(3, 18, depth=depth)[1]
    G = W.G
    seam = sum(1 for i in range(G) if {top[i][G - 1], bot[i][0]} == {"sea3", "sea4"})
    union = {top[i][j] for i in range(G) for j in range(G)} | {bot[i][j] for i in range(G) for j in range(G)}
    assert seam == 0
    assert "sea3" in union and "sea4" in union       # non-vacuous: the region really spans shallow..deep


def test_default_gradient_actually_grades():
    # a single cell yields BOTH shallow and deep (a real gradient, not one flat shade)
    depth = W.default_depth_field([(3, 17)], deep_dir="S")
    counts = W.shade_counts(W.build_cell(3, 17, depth=depth)[1])
    assert counts["sea3"] > 0 and counts["sea4"] > 0 and counts["sea5"] > 0
    # deeper toward S: a southern cell is more deep-heavy than a northern one over the same field
    cells = [(3, 17), (3, 19)]
    d2 = W.default_depth_field(cells, deep_dir="S")
    north = W.shade_counts(W.build_cell(3, 17, depth=d2)[1])
    south = W.shade_counts(W.build_cell(3, 19, depth=d2)[1])
    assert south["sea4"] > north["sea4"] and north["sea3"] > south["sea3"]


def test_custom_depth_callable_is_used():
    # an all-deep field -> every cell Sea4; an all-shallow field -> every cell Sea3
    _, deep_grid, _ = W.build_cell(3, 17, depth=lambda x, z: 999.0, threshold=1.0)
    _, shallow_grid, _ = W.build_cell(3, 17, depth=lambda x, z: -999.0, threshold=1.0)
    assert W.shade_counts(deep_grid) == {"sea3": 0, "sea5": 0, "sea4": 256}
    assert W.shade_counts(shallow_grid) == {"sea3": 256, "sea5": 0, "sea4": 0}


def test_deepset2tile_covers_every_partial_edge_set():
    # every 1/2/3-deep-edge subset that is NOT a 2-opposite channel must map to a Wang tile
    import itertools
    for n in (1, 2, 3):
        for combo in itertools.combinations("NESW", n):
            de = frozenset(combo)
            opposite = de in (frozenset("NS"), frozenset("EW"))
            if not opposite:
                assert de in W.DEEPSET2TILE, de


def test_uvs_stay_within_texture():
    depth = W.default_depth_field([(3, 17)], deep_dir="S")
    bands, _, _ = W.build_cell(3, 17, depth=depth)
    uvs = [c for band in bands.values() for tri in band for (_, uv) in tri for c in uv]
    assert uvs and 0.0 <= min(uvs) and max(uvs) <= 1.0


def test_omaps_are_the_four_rotations():
    assert set(W.OMAPS) == {"r0", "r90", "r180", "r270"}
    r0, r90, r180, r270 = (W.OMAPS[k] for k in ("r0", "r90", "r180", "r270"))
    assert r0(0, 0) == (0, 0) and r0(1, 0) == (1, 0) and r0(0, 1) == (0, 1)   # identity
    assert r180(0, 0) == (1, 1) and r180(1, 1) == (0, 0)                      # flips both axes
    assert r90(1, 0) == (0, 0) and r270(0, 0) == (1, 0)                       # 90 / 270


def test_build_cell_determinism_and_seed():
    depth = W.default_depth_field([(3, 17)], deep_dir="S")
    a_bands, a_grid, a_s5 = W.build_cell(3, 17, depth=depth, seed=7)
    b_bands, b_grid, b_s5 = W.build_cell(3, 17, depth=depth, seed=7)
    assert a_bands == b_bands and a_grid == b_grid and a_s5 == b_s5   # same seed -> fully identical
    # the shade PLACEMENT is set by the depth field (seed only reshuffles anti-tiling + sea5 variants), so a different
    # seed leaves the grid identical and the invariant intact
    _, c_grid, _ = W.build_cell(3, 17, depth=depth, seed=8)
    assert c_grid == a_grid and W.adjacency_violations(c_grid) == 0


# ---- the mesh construction primitives -------------------------------------------------------------------------------

def test_tri_soup_block_mesh_shape_and_uv():
    tris = [[((0.0, 0.0, 0.0), (0.1, 0.2)), ((4.0, 0.0, 0.0), (0.3, 0.4)), ((4.0, 0.0, -4.0), (0.5, 0.6))]]
    bm = M.tri_soup_block_mesh(tris, name="Block[3][17] Sea4", x=3, y=17, normal=W.NORMAL)
    assert bm.vcount == 3 and bm.tris == [[0, 1, 2]]
    assert bm.uvs[0] == [0.1, 0.2] and bm.verts[1] == [4.0, 0.0, 0.0]
    assert all(tuple(n) == W.NORMAL for n in bm.normals)       # byte-proven water normal stamped on every vert
    assert all(t == [1.0, 0.0, 0.0, 1.0] for t in bm.tangents)  # trivial tangent (render layer, no IDALL)


def test_hidden_block_mesh_is_a_buried_degenerate_tri():
    bm = M.hidden_block_mesh(name="Block[3][17] Sea1", x=3, y=17)
    assert bm.vcount == 3 and bm.tris == [[0, 1, 2]]
    assert all(v[1] <= -80.0 for v in bm.verts)                # far below the world -> renders nothing


def test_water_meshes_serialize_roundtrip(tmp_path):
    depth = W.default_depth_field([(3, 17)], deep_dir="S")
    bands, _, _ = W.build_cell(3, 17, depth=depth)
    bm = M.tri_soup_block_mesh(bands[2], name="Block[3][17] Sea4", x=3, y=17, normal=W.NORMAL)
    p = M.write_ff9mesh(bm, tmp_path / "sea4.ff9mesh")
    d = M.read_ff9mesh(p)
    assert d["vcount"] == bm.vcount and len(d["indices"]) == bm.vcount
    assert all(abs(a - b) < 1e-6 for a, b in zip(d["normals"][0], W.NORMAL))   # normal survives (float32)
