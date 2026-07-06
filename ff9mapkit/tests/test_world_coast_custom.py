"""Hermetic tests for the custom-coastline ribbon-warp (ff9mapkit.world.coast_custom).

Never touches the game or p0data: extract.read_block is stubbed with a synthetic straight-beach donor,
and mesh.deploy_override / deploy_donor_sidecar are captured. Mirrors tests/test_world_water.py.
"""
import math

import pytest

from ff9mapkit.world import coast_custom as CC
from ff9mapkit.world import mesh as M
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, encode_id, decode_id


# --------------------------------------------------------------------------------------------------
# synthetic donor: a straight beach, shore at Z=-32 running along +X; land north (Z in [-32,0]).
# --------------------------------------------------------------------------------------------------
def _mk_block(name, tris):
    """tris = list of (corners, topo); corners = 3x ((x,y,z),(u,v))."""
    pos, nrm, uv, tan, flat, tri_idx = [], [], [], [], [], []
    vi = 0
    for (corners, topo) in tris:
        idall = float(encode_id(topograph=topo))
        base = vi
        for ((px, py, pz), (u, v)) in corners:
            pos.append([px, py, pz]); nrm.append([0.0, 1.0, 0.0])
            uv.append([u, v]); tan.append([idall, 0.0, 0.0, 1.0]); flat.append(vi); vi += 1
        tri_idx.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=1, x=0, y=0, lod="0_1", vcount=vi, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tri_idx, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _fake_terrain():
    """Land filling X[0,64], Z[-32,0]: grass (topo 0) with a sand row (topo 31) at the shore."""
    tris = []
    step = 8.0
    for i in range(8):
        for j in range(4):                                  # j: 0..3 -> Z 0..-32
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -j * step, -(j + 1) * step
            topo = 31 if j == 3 else 0                       # sand nearest the shore
            u = i / 8.0
            for (a, b, c) in (((x0, 0.0, z0), (x1, 0.0, z1), (x0, 0.0, z1)),
                              ((x0, 0.0, z0), (x1, 0.0, z0), (x1, 0.0, z1))):
                tris.append(([(a, (u, 0.2)), (b, (u, 0.4)), (c, (u, 0.6))], topo))
    return _mk_block("Block[17][15] Terrain", tris)


def _fake_beach1():
    """A thin waterline strip at Z=-32 running along +X (PCA axis -> +X)."""
    tris = []
    for i in range(10):
        x0, x1 = 8 + i * 4.0, 8 + (i + 1) * 4.0
        z0, z1 = -31.0, -33.0
        tris.append(([((x0, 0.0, z0), (0.1, 0.1)), ((x1, 0.0, z1), (0.2, 0.2)),
                      ((x0, 0.0, z1), (0.3, 0.3))], 30))
    return _mk_block("Block[17][15] beach1", tris)


def _fake_sea4():
    """A tiny full-plane deep Sea4 stand-in (topo 57, Y=0) -- the DEEP_SEA_SOURCE (12,0) byte-copy target."""
    return _mk_block("Block[12][0] sea4",
                     [([((0.0, 0.0, 0.0), (0.0, 0.0)), ((64.0, 0.0, 0.0), (1.0, 0.0)),
                        ((64.0, 0.0, -64.0), (1.0, 1.0))], 57)])


@pytest.fixture
def donor_patch(monkeypatch):
    def fake_read_block(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        if not (0 <= x < CC.GRID_X and 0 <= y < CC.GRID_Y):
            raise ValueError(f"disc{disc} block[{x}][{y}] {part} mesh not found")   # match the real path
        if part == "sea4":
            return _fake_sea4()
        if part == "terrain":
            return _fake_terrain()
        if part == "beach1":
            return _fake_beach1()
        raise ValueError(f"no {part}")
    monkeypatch.setattr("ff9mapkit.world.extract.read_block", fake_read_block)


@pytest.fixture
def capture(monkeypatch):
    overrides, sidecars = [], []
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, **k: overrides.append((bm.x, bm.y, bm.vcount, k.get("part"))))
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: sidecars.append((dx, dy, k["x"], k["y"])))
    return overrides, sidecars


# --------------------------------------------------------------------------------------------------
# Outline
# --------------------------------------------------------------------------------------------------
def test_outline_arclength():
    ol = CC.Outline([(0, 0), (30, 0), (30, -40)])
    assert ol.length == pytest.approx(70.0)


def test_outline_project_interior_perpendicular():
    ol = CC.Outline([(0, 0), (100, 0)], land_side="left")
    sigma, d, dist = ol.project(50, 10)
    assert sigma == pytest.approx(50.0)
    assert dist == pytest.approx(10.0)


def test_outline_project_beyond_endpoint_is_far():
    # a point well past the end must have |d| == its true distance, not the perpendicular-to-line value
    ol = CC.Outline([(0, 0), (100, 0)], land_side="left")
    sigma, d, dist = ol.project(150, 0)                      # 50u past the end, on the line
    assert dist == pytest.approx(50.0)
    assert abs(d) == pytest.approx(50.0)


def test_outline_land_side_sign_flip():
    ol_l = CC.Outline([(0, 0), (100, 0)], land_side="left")
    ol_r = CC.Outline([(0, 0), (100, 0)], land_side="right")
    _, d_l, _ = ol_l.project(50, 10)
    _, d_r, _ = ol_r.project(50, 10)
    assert d_l == pytest.approx(-d_r)                        # opposite land sides -> opposite d


def test_outline_min_turn_radius():
    assert math.isinf(CC.Outline([(0, 0), (100, 0)]).min_turn_radius())      # straight -> inf
    r = CC.Outline([(0, 0), (50, 0), (50, -50)]).min_turn_radius()           # a right angle
    assert r < 50.0


def test_outline_rejects_degenerate():
    with pytest.raises(ValueError):
        CC.Outline([(5, 5)])
    with pytest.raises(ValueError):
        CC.Outline([(5, 5), (5, 5)])


# --------------------------------------------------------------------------------------------------
# DonorField
# --------------------------------------------------------------------------------------------------
def test_donorfield_frame_and_sample(donor_patch):
    f = CC.DonorField((17, 15))
    # PCA of the straight beach1 -> along-shore ~ +X
    assert abs(f.shat[0]) == pytest.approx(1.0, abs=0.05)
    assert abs(f.shat[1]) == pytest.approx(0.0, abs=0.05)
    # seaward u signed so land (north, Z in [-32,0]) is d<0: sample a land point vs a water point
    # world == local for the fake donor (block 0,0). Land at (30,-16); water at (30,-60).
    s_land = f._s(30, -16); d_land = f._d(30, -16)
    assert f.sample(s_land, d_land) is not None
    s_wat = f._s(30, -60); d_wat = f._d(30, -60)
    assert f.sample(s_wat, d_wat) is None


def test_donorfield_requires_beach(monkeypatch):
    def only_terrain(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        if part == "terrain":
            return _fake_terrain()
        raise ValueError("no beach1")
    monkeypatch.setattr("ff9mapkit.world.extract.read_block", only_terrain)
    with pytest.raises(ValueError, match="beach1"):
        CC.DonorField((8, 4))


# --------------------------------------------------------------------------------------------------
# build_cell
# --------------------------------------------------------------------------------------------------
def _straight_shore_field_and_outline():
    f = CC.DonorField((17, 15))
    # a straight world shoreline along +X at Z=-1120 (cell row by=17 spans Z -1088..-1152)
    ol = CC.Outline([(60, -1120), (260, -1120)], land_side="left")
    return f, ol


def test_build_cell_has_land_and_water(donor_patch):
    f, ol = _straight_shore_field_and_outline()
    bm, stats = CC.build_cell(f, ol, 2, 17, seg=16)
    assert bm is not None
    assert stats["land_tris"] > 0 and stats["water_tris"] > 0
    assert bm.vcount == 3 * (stats["land_tris"] + stats["water_tris"])


def test_build_cell_all_tris_up_wound(donor_patch):
    """Geometric normal.y > 0 for every tri (what makes the walkmesh up-facing / non-culled)."""
    f, ol = _straight_shore_field_and_outline()
    bm, _ = CC.build_cell(f, ol, 2, 17, seg=12)
    for t in range(len(bm.flat_index) // 3):
        a, b, c = (bm.verts[bm.flat_index[3 * t + k]] for k in range(3))
        e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        ny = e1[2] * e2[0] - e1[0] * e2[2]                  # cross(e1,e2).y  (purely XZ)
        assert ny > 0, f"tri {t} is back-wound (ny={ny})"


def test_build_cell_water_tris_carry_sea_topograph(donor_patch):
    f, ol = _straight_shore_field_and_outline()
    bm, _ = CC.build_cell(f, ol, 2, 17, seg=16)
    topos = {decode_id(int(round(bm.tangents[bm.flat_index[3 * t]][0])))["topograph"]
             for t in range(len(bm.flat_index) // 3)}
    assert CC.WATER_TOPOGRAPH in topos                       # some tris are boat-water
    assert topos & {0, 31}                                   # some tris are donor land


def test_build_cell_roundtrips_ff9mesh(donor_patch, tmp_path):
    f, ol = _straight_shore_field_and_outline()
    bm, _ = CC.build_cell(f, ol, 2, 17, seg=10)
    p = tmp_path / "t.ff9mesh"
    M.write_ff9mesh(bm, p)
    got = M.read_ff9mesh(p)
    assert got["vcount"] == bm.vcount
    assert len(got["indices"]) == len(bm.flat_index)


def test_build_cell_local_frame_in_bounds(donor_patch):
    f, ol = _straight_shore_field_and_outline()
    bm, _ = CC.build_cell(f, ol, 2, 17, seg=16)
    for v in bm.verts:
        assert -0.01 <= v[0] <= 64.01                       # block-local X in [0,64]
        assert -64.01 <= v[2] <= 0.01                       # block-local Z in [-64,0]


def test_build_cell_all_water_returns_none(donor_patch):
    f = CC.DonorField((17, 15))
    ol = CC.Outline([(60, -1120), (260, -1120)], land_side="left")
    # a cell far seaward (south of the shore) has no land
    bm, stats = CC.build_cell(f, ol, 2, 19, seg=8)
    assert bm is None
    assert stats["land_tris"] == 0


def test_seam_watertight_across_adjacent_cells(donor_patch):
    """Two adjacent cells must agree exactly on their shared block edge (world XZ + Y)."""
    f = CC.DonorField((17, 15))
    ol = CC.Outline([(60, -1120), (400, -1120)], land_side="left")
    seg = 16
    a, _ = CC.build_cell(f, ol, 2, 17, seg=seg)
    b, _ = CC.build_cell(f, ol, 3, 17, seg=seg)
    # cell (2,17) east edge is local x=64 -> world x=192; cell (3,17) west edge is local x=0 -> world x=192.
    # both cells share by=17 (same block origin Z), so equal local Z == equal world Z.
    edge_a = {(round(v[2], 4), round(v[1], 4)) for v in a.verts if abs(v[0] - 64.0) < 1e-4}   # (Z, Y) at x==64
    edge_b = {(round(v[2], 4), round(v[1], 4)) for v in b.verts if abs(v[0] - 0.0) < 1e-4}     # (Z, Y) at x==0
    assert edge_a and edge_b
    assert edge_a == edge_b                                  # identical world Z + Y on the shared seam


# --------------------------------------------------------------------------------------------------
# coast_custom orchestration
# --------------------------------------------------------------------------------------------------
def test_coast_custom_deploys_terrain_sea_and_sidecar(donor_patch, capture):
    overrides, sidecars = capture
    summary = CC.coast_custom("FF9CustomMap",
                              outline=[(60, -1120), (400, -1120)],
                              beach_donor=(17, 15), sea_donor=(15, 4),
                              cells=[(2, 17), (3, 17), (4, 17)], land_side="left", seg=12)
    assert summary["op"] == "coast-custom"
    ncells = len(summary["cells"])
    # per cell: Terrain + Sea4 (deep plane) + the 4 blanked bands (Sea1/2/3/5) = 6 overrides
    parts = [p for (_, _, _, p) in overrides]
    assert parts.count("Terrain") == ncells
    assert parts.count("Sea4") == ncells                        # the full deep plane, not buried land
    for name in ("Sea1", "Sea2", "Sea3", "Sea5"):
        assert parts.count(name) == ncells                      # near-shore bands blanked
    assert len(overrides) == 6 * ncells
    # one Donor.txt per cell naming the sea donor (which carries the Terrain+Sea material binding)
    assert len(sidecars) == ncells
    assert all((dx, dy) == (15, 4) for (dx, dy, _, _) in sidecars)


def test_coast_custom_dry_run_writes_nothing(donor_patch, capture):
    overrides, sidecars = capture
    summary = CC.coast_custom("FF9CustomMap",
                              outline=[(60, -1120), (400, -1120)],
                              cells=[(2, 17), (3, 17)], seg=10, dry_run=True)
    assert overrides == [] and sidecars == []
    assert summary["dry_run"] is True
    assert summary["cells"]                                  # geometry still computed


def test_coast_custom_skips_all_water_cells(donor_patch, capture):
    summary = CC.coast_custom("FF9CustomMap",
                              outline=[(60, -1120), (400, -1120)],
                              cells=[(2, 17), (2, 19)], seg=10, dry_run=True)
    assert [2, 17] in [c["cell"] for c in summary["cells"]]
    assert [2, 19] in summary["skipped"]                    # seaward cell has no land


def test_coast_custom_validates_grid(donor_patch):
    with pytest.raises(ValueError):
        CC.coast_custom("FF9CustomMap", outline=[(0, -1120), (64, -1120)], cells=[(99, 0)], dry_run=True)
    # an off-grid donor must fail with the clean bounds message BEFORE any p0data read
    with pytest.raises(ValueError, match="out of the"):
        CC.coast_custom("FF9CustomMap", outline=[(0, -1120), (64, -1120)],
                        beach_donor=(99, 0), cells=[(2, 17)], dry_run=True)


def test_coast_custom_seg_must_be_positive(donor_patch):
    with pytest.raises(ValueError, match="seg"):
        CC.coast_custom("FF9CustomMap", outline=[(60, -1120), (400, -1120)],
                        cells=[(3, 17)], seg=0, dry_run=True)


def test_coast_custom_offgrid_outline_raises(donor_patch):
    # a positive-Z (wrong sign) / off-grid outline with auto-derive must error, not silently no-op
    with pytest.raises(ValueError, match="off the"):
        CC.coast_custom("FF9CustomMap", outline=[(3000, 500), (3200, 500)], dry_run=True)


def test_coast_custom_fold_warning(donor_patch):
    # a hairpin far tighter than the donor's ~32u cross-shore reach must flag a fold
    summary = CC.coast_custom("FF9CustomMap",
                              outline=[(200, -1120), (210, -1120), (200, -1122)],
                              cells=[(3, 17)], seg=8, dry_run=True)
    assert summary["fold_warning"] is True


def test_coast_custom_preview_png(donor_patch, tmp_path):
    png = tmp_path / "preview.png"
    CC.coast_custom("FF9CustomMap", outline=[(60, -1120), (400, -1120)],
                    cells=[(2, 17), (3, 17), (4, 17)], seg=12, dry_run=True, preview=str(png))
    assert png.exists() and png.stat().st_size > 0


def test_coast_custom_auto_derives_cells(donor_patch, capture):
    summary = CC.coast_custom("FF9CustomMap",
                              outline=[(140, -1120), (400, -1120)],
                              seg=10, dry_run=True)                 # no cells= -> derive
    assert len(summary["cells"]) > 0
    for c in summary["cells"]:
        assert c["land_tris"] > 0


# --------------------------------------------------------------------------------------------------
# regression tests for the reviewed fixes
# --------------------------------------------------------------------------------------------------
def _ramped_terrain():
    """Land whose height ramps ALONG the shore (+X) -- a hard-modulo tile wrap would jump Y at each seam."""
    tris = []
    step = 8.0
    yy = lambda x: (x / 64.0) * 10.0
    for i in range(8):
        for j in range(4):
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -j * step, -(j + 1) * step
            topo = 31 if j == 3 else 0
            u = i / 8.0
            for (a, b, c) in (((x0, yy(x0), z0), (x1, yy(x1), z1), (x0, yy(x0), z1)),
                              ((x0, yy(x0), z0), (x1, yy(x1), z0), (x1, yy(x1), z1))):
                tris.append(([(a, (u, 0.2)), (b, (u, 0.4)), (c, (u, 0.6))], topo))
    return _mk_block("Block[17][15] Terrain", tris)


def test_sample_ping_pong_continuous_across_period(monkeypatch):
    """Reflective tiling: sampled land Y is CONTINUOUS across period boundaries (a hard modulo would jump ~6u)."""
    def frb(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        if part == "terrain":
            return _ramped_terrain()
        if part == "beach1":
            return _fake_beach1()
        raise ValueError(part)
    monkeypatch.setattr("ff9mapkit.world.extract.read_block", frb)
    f = CC.DonorField((17, 15))
    ys, N, span = [], 300, 2.5 * f.period
    for k in range(N + 1):
        hit = f.sample(f.s_lo + span * k / N, -4.0)              # d=-4 -> firmly inland
        if hit is not None:
            ys.append(hit["y"])
    assert len(ys) > 50
    assert max(abs(ys[k] - ys[k - 1]) for k in range(1, len(ys))) < 1.5   # no wrap-seam Y jump


def test_build_cell_land_side_right_flips_geometric_side(donor_patch):
    """land_side='right' paints land on the OPPOSITE world-Z side vs 'left' -- end-to-end, not just Outline."""
    f = CC.DonorField((17, 15))
    shore = [(60, -1120), (400, -1120)]                          # straight +X shore at world Z=-1120

    def land_centroid_z(ol, bx=2, by=17):
        bm, stats = CC.build_cell(f, ol, bx, by, seg=16)
        oz = -by * CC.BLOCK
        zs = []
        for t in range(len(bm.flat_index) // 3):
            c = bm.flat_index[3 * t:3 * t + 3]
            if CC._tri_topo(bm, c[0]) == CC.WATER_TOPOGRAPH:
                continue
            zs.append(sum(oz + bm.verts[i][2] for i in c) / 3.0)
        return sum(zs) / len(zs)

    zl = land_centroid_z(CC.Outline(shore, land_side="left"))
    zr = land_centroid_z(CC.Outline(shore, land_side="right"))
    assert zl > -1120.0 > zr                                    # left land sits north, right land sits south


def test_build_cell_water_tris_flat_and_below_surface(donor_patch):
    """Fully-submerged water tris sit at water_y; NO water tri pokes above the Y=0 sea render."""
    f, ol = _straight_shore_field_and_outline()
    bm, _ = CC.build_cell(f, ol, 2, 17, seg=16)
    submerged = 0
    for t in range(len(bm.flat_index) // 3):
        idx = [bm.flat_index[3 * t + k] for k in range(3)]
        if decode_id(int(round(bm.tangents[idx[0]][0])))["topograph"] != CC.WATER_TOPOGRAPH:
            continue
        vs = [bm.verts[i] for i in idx]
        for v in vs:
            assert v[1] <= 1e-6, f"water tri {t} vert Y={v[1]} above the sea surface"
        if all(abs(v[1] - CC.WATER_Y) < 1e-6 for v in vs):
            submerged += 1
    assert submerged > 0


def test_build_cell_height_threads_to_water_y(donor_patch):
    """A non-default height (=water_y) reaches the submerged water verts."""
    f, ol = _straight_shore_field_and_outline()
    hy = -3.5
    bm, _ = CC.build_cell(f, ol, 2, 17, seg=16, water_y=hy)
    hit = False
    for t in range(len(bm.flat_index) // 3):
        idx = [bm.flat_index[3 * t + k] for k in range(3)]
        if decode_id(int(round(bm.tangents[idx[0]][0])))["topograph"] != CC.WATER_TOPOGRAPH:
            continue
        if all(bm.verts[i][1] == hy for i in idx):
            hit = True
    assert hit, "non-default water_y did not propagate to submerged water verts"


def test_parse_outline_tolerates_spaces_in_pairs():
    from ff9mapkit.cli import _parse_outline
    assert _parse_outline("140, -1150; 260, -1108") == [(140.0, -1150.0), (260.0, -1108.0)]
