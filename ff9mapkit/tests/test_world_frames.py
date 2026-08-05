"""THE COORDINATE-FRAME CONSTANTS + frames.py (audit rec 12).

Step 1, the falsifier: the block size, the 4u lattice cell, and the world extent are
re-declared as bare literals across the world modules. This test asserts they all agree and
all derive from the ONE authoritative pair (``mesh.GRID_COLS``/``GRID_ROWS`` x the engine's
64u block). If it ever goes red, a live drift has been found -- fix the drifted literal, do
NOT relax the test. (The audit's migration half -- rewriting old call sites to import a
shared module -- was REFUSED: no behavioral divergence exists today, and touching
playtest-load-bearing arithmetic is the defect factory. The rule is DIRECTIONAL: new code
imports ``world.frames``; an old site converts only when already being edited.)
"""
from __future__ import annotations


def test_frame_constants_single_source():
    from ff9mapkit.workspace import worldscan
    from ff9mapkit.world import (coastnav, extract, interior, island, islandbeach, mesh,
                                 navimap, rimretile, terrain, texgates, water)
    # the 64u block -- every module's literal, one value
    assert (terrain.BLOCK == island.BLOCK == islandbeach.BLOCK == coastnav.BLOCK
            == water.BLOCK == interior.BLOCK == extract.BLOCK_SIZE
            == worldscan.BLOCK_UNITS == 64)
    # the 4u sub-tile lattice cell
    assert (islandbeach.CELL == rimretile.CELL == texgates.CELL == island.GRID
            == water.CELL == 4.0)
    # the wrapped world extent -- 24x20 blocks of 64u, nothing else
    from ff9mapkit.world import frames
    assert (navimap.WORLD_MAP_EXTENT == frames.WORLD_EXTENT == (coastnav.WORLD_W, 1280.0)
            == (mesh.GRID_COLS * 64.0, mesh.GRID_ROWS * 64.0))


# ---- frames.py (step 2: the additive module) ------------------------------------------------------------------------

def test_block_frame_round_trips_over_every_block():
    from ff9mapkit.world import frames as F
    for bx in range(F.GRID_COLS):
        for by in range(F.GRID_ROWS):
            assert F.block_to_world(bx, by) == (bx * 64, -by * 64)
            for lx, lz in ((0.0, 0.0), (32.0, -32.0), (63.9, -63.9)):
                wx, wz = F.block_local_to_world(lx, lz, bx, by)
                assert F.world_to_block(wx, wz) == (bx, by)
                rlx, rlz = F.world_to_block_local(wx, wz, bx, by)
                assert abs(rlx - lx) < 1e-9 and abs(rlz - lz) < 1e-9


def test_wrap_world_folds_the_four_seam_corners_onto_the_grid():
    from ff9mapkit.world import frames as F
    for wx, wz in ((1536.0, 0.0), (0.0, -1280.0), (1536.0, -1280.0), (-1.0, 1.0),
                   (1537.0, -1281.0)):
        fx, fz = F.wrap_world_xz(wx, wz)
        assert 0.0 <= fx < 1536.0 and -1280.0 < fz <= 0.0
        bx, by = F.world_to_block(fx, fz)
        assert 0 <= bx < F.GRID_COLS and 0 <= by < F.GRID_ROWS


def test_navimap_wrap_is_the_one_fold():
    """The move (audit rec 12): navimap's private _wrap_world IS frames.wrap_world_xz."""
    from ff9mapkit.world import frames as F, navimap as N
    assert N._wrap_world is F.wrap_world_xz


def test_the_two_lattice_conventions_differ_by_name_not_by_luck():
    """Same input, DIFFERENT j -- the sign convention lives in the function NAME. lattice_ij
    is rimretile's cell_of (j >= 0 from negated z); lattice_raw_xz is the interior/coastmorph
    raw-floor convention (j <= 0)."""
    from ff9mapkit.world import frames as F, rimretile as RR
    assert F.lattice_ij(9.0, -9.0) == (2, 2)
    assert F.lattice_raw_xz(9.0, -9.0) == (2, -3)
    assert F.lattice_ij(9.0, -9.0) == RR.cell_of((9.0, 0.0, -9.0))


# ---- the block_local census frame (step 3c: the vacuous-green refusal) ----------------------------------------------

def _one_tri(name, x=0, y=0):
    from ff9mapkit.world.extract import (BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN)
    idall = float(encode_id(topograph=0))
    pos = [[0.0, 3.5, 0.0], [8.0, 3.5, 0.0], [0.0, 3.5, -8.0]]
    return BlockMesh(name=name, disc=1, x=x, y=y, lod="0_1", vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * 3,
                                  CH_UV: [[0.0, 0.0]] * 3, CH_TAN: [[idall, 0.0, 0.0, 1.0]] * 3},
                     flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


def test_census_block_local_frame_refuses_a_mixed_block_stack():
    import pytest
    from ff9mapkit.world import placement as P
    a = _one_tri("Block[3][4] Terrain", x=3, y=4)
    b = _one_tri("Block[5][4] Sea4", x=5, y=4)
    P.census([("Terrain", a)], span=(1.0, 7.0, -7.0, -1.0), samples=2, frame="block_local")
    with pytest.raises(ValueError, match="span blocks"):
        P.census([("Terrain", a), ("Sea4", b)], span=(1.0, 7.0, -7.0, -1.0), samples=2,
                 frame="block_local")
    with pytest.raises(ValueError, match="outside the block frame"):
        P.census([("Terrain", a)], span=(2.0, 70.0, -62.0, -2.0), samples=2,
                 frame="block_local")
