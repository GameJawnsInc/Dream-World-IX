"""THE SEA4-UNDER-LAND LAW -- a deep-sea plane must never span beneath land.

Why this is a law and not a nicety: :func:`ff9mapkit.world.placement.place` rejects any triangle
whose hit is ABOVE the ray origin, and a sea-level actor casts from only ``y + 2.34375``. Land at
the usual y=3.2 is therefore INVISIBLE to a boat's ground query, which falls straight through to
whatever lies underneath. Leave the full-cell Sea4 plane whole and the query reads deep sea
(topograph 57) -- the Rung-5a island was sailed clean through. Cut it and the ray MISSES, and a
water-area miss IS the engine's invisible vehicle wall.

Pure unit tests on synthetic meshes: no game install, no extracted templates, so these run
identically in a fresh worktree (see the worktree skip trap in the project brief).
"""
import pytest

from ff9mapkit.world import island as I
from ff9mapkit.world import placement as P
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN


def _mesh(name, tris_xyz, *, idall=0):
    """A BlockMesh from a list of 3-tuples of (x, y, z), all up-facing."""
    pos, nrm, uv, tan, flat, tidx = [], [], [], [], [], []
    for t3 in tris_xyz:
        base = len(pos)
        for (x, y, z) in t3:
            pos.append([x, y, z])
            nrm.append([0.0, 1.0, 0.0])
            uv.append([0.0, 0.0])
            tan.append([float(idall), 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)
        tidx.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=1, x=0, y=0, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tidx, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _grid_plane(n=8, step=8.0, y=0.0):
    """An n x n quad grid over the block-local cell (x 0..64, z -64..0), up-facing, at ``y``."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -(j + 1) * step, -j * step
            tris.append([(x0, y, z0), (x0, y, z1), (x1, y, z1)])
            tris.append([(x0, y, z0), (x1, y, z1), (x1, y, z0)])
    return _mesh("Sea4", tris, idall=P.IDALL_SKIP and 0 or 0)


def _land_square(x0, x1, z0, z1, y=3.2):
    """A flat land patch at ``y``, well above the sea-level ray ceiling of 2.34375."""
    return _mesh("Terrain", [[(x0, y, z0), (x0, y, z1), (x1, y, z1)],
                             [(x0, y, z0), (x1, y, z1), (x1, y, z0)]])


LAND = (16.0, 48.0, -48.0, -16.0)


def test_land_is_above_the_sea_level_ray_ceiling():
    """The premise. If this ever stops holding, the law's rationale changes."""
    assert 3.2 > P.WALK_RAY_START, "land at y=3.2 must sit above a sea-level actor's ray origin"


def test_uncut_plane_is_boat_permeable():
    """The bug, reproduced: with the plane whole, a sea-level ray over land reads the SEA."""
    land, sea = _land_square(*LAND), _grid_plane()
    meshlist = [("Terrain", land), ("Sea4", sea)]
    _, sky_name, _, _ = P.place(meshlist, 32.0, -32.0, 0.0, sky=True)
    _, boat_name, _, _ = P.place(meshlist, 32.0, -32.0, 0.0, sky=False)
    assert sky_name == "Terrain", "a player arriving from above lands on the island"
    assert boat_name == "Sea4", "and with the plane uncut a boat at sea level reads open ocean"


def test_cut_plane_removes_every_tri_wholly_under_land():
    land, sea = _land_square(*LAND), _grid_plane()
    cut = I._cut_plane(sea, 0, 0, frozenset(), land)
    assert len(cut.tris) < len(sea.tris), "the cut must actually remove something"
    for tri in cut.tris:
        corners = [(cut.chan_arrays[CH_POS][j][0], cut.chan_arrays[CH_POS][j][2]) for j in tri]
        assert not all(I._xz_inside(I._xz_tri_cover(land), x, z) for x, z in corners), \
            "no surviving Sea4 tri may lie wholly beneath the land footprint"


def test_cut_plane_makes_the_interior_a_vehicle_wall():
    """The fix: over land the sea-level ray now MISSES, which IS the invisible vehicle wall."""
    land, sea = _land_square(*LAND), _grid_plane()
    meshlist = [("Terrain", land), ("Sea4", I._cut_plane(sea, 0, 0, frozenset(), land))]
    _, boat_name, _, topo = P.place(meshlist, 32.0, -32.0, 0.0, sky=False)
    assert boat_name == "MISS", "a boat over the island interior must find no walkmesh"
    assert topo is None


def test_cut_is_conservative_and_leaves_no_hole_outside_the_land():
    """A CENTROID cut tears a query hole just outside the shoreline -- the placement census caught
    it the first time this was written that way. Every sample clear of the land must still ground."""
    land, sea = _land_square(*LAND), _grid_plane()
    meshlist = [("Terrain", land), ("Sea4", I._cut_plane(sea, 0, 0, frozenset(), land))]
    cover = I._xz_tri_cover(land)
    for i in range(33):
        for j in range(33):
            x, z = 0.5 + 63.0 * i / 32.0, -0.5 - 63.0 * j / 32.0
            if I._xz_inside(cover, x, z):
                continue
            _, name, _, _ = P.place(meshlist, x, z, 0.0, sky=True)
            assert name != "MISS", f"open water at ({x:.1f}, {z:.1f}) lost its Sea4 -- render/query hole"


def test_open_ocean_block_is_untouched():
    """No land in the block -> the plane must survive whole."""
    sea = _grid_plane()
    assert len(I._cut_plane(sea, 0, 0, frozenset(), None).tris) == len(sea.tris)
    empty = _mesh("Terrain", [])
    assert len(I._cut_plane(sea, 0, 0, frozenset(), empty).tris) == len(sea.tris)


def test_beach_lattice_cut_still_applies_alongside_the_land_cut():
    """The pre-existing beach ``sea4_cut`` (4-unit lattice cells, world frame) must keep working
    when a land footprint is passed too -- the beach block takes BOTH."""
    sea = _grid_plane()
    far = _land_square(0.0, 1.0, -1.0, -0.0)              # a sliver, so the land cut is ~inert
    cells = {(0, -1), (1, -1), (0, -2), (1, -2)}          # bx=by=0 -> lattice == local/4
    with_cells = I._cut_plane(sea, 0, 0, cells, far)
    without = I._cut_plane(sea, 0, 0, frozenset(), far)
    assert len(with_cells.tris) < len(without.tris), "the lattice cut must still bite"


@pytest.mark.parametrize("y", [0.0, 1.0, 2.0])
def test_land_below_the_ceiling_needs_no_cut(y):
    """Land that meets the water low enough is hit by the sea-level ray directly -- the reason a
    gentle shore was never permeable and the cliff was."""
    land, sea = _land_square(*LAND, y=y), _grid_plane()
    _, name, _, _ = P.place([("Terrain", land), ("Sea4", sea)], 32.0, -32.0, 0.0, sky=False)
    assert name == "Terrain"
