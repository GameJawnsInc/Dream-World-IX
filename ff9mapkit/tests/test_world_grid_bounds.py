"""THE GRID-BOUNDS GATE (2026-07-21, the dunes off-grid incident).

The engine's overworld is a FIXED 24x20 block grid (WMWorld.BuildBlockArray = ``new
WMBlock[24, 20]``; the debug-menu teleport refuses anything off it with "outside the 24x20
grid (x 0..1535, z 0..-1279)"). A landmass/override written off that grid is a dead file the
engine never streams -- and the OPEN-OCEAN TARGET census is VACUOUSLY clean off the map edge
(no mesh assets because there is no map), so nothing caught the dunes mint spilling onto rows
20-22 until the user's own teleport bounced. These tests pin the gate at every chokepoint:
the predicate, ``build_landmass`` (world-island), and the lowest-level write functions.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import island as I
from ff9mapkit.world import mesh as M


# --------------------------------------------------------------------------- the constants
def test_authoritative_constants_match_engine():
    # WMWorld.cs:1675  new WMBlock[24, 20]  /  Ff9mkDebugMenu.cs:1595  bx>=24 || bz>=20
    assert (M.GRID_COLS, M.GRID_ROWS) == (24, 20)
    assert M.GRID_WORLD_X_MAX == 1535        # 24 * 64 - 1
    assert M.GRID_WORLD_Z_MIN == -1279       # -(20 * 64 - 1)


def test_grid_constants_single_source():
    # terrain.py / water.py / transplant.py all re-export the ONE literal from mesh.py
    from ff9mapkit.world import terrain, transplant, water
    assert (terrain.GRID_X, terrain.GRID_Y) == (M.GRID_COLS, M.GRID_ROWS)
    assert (water.GRID_X, water.GRID_Y) == (M.GRID_COLS, M.GRID_ROWS)
    assert (transplant.GRID_X, transplant.GRID_Y) == (M.GRID_COLS, M.GRID_ROWS)


# --------------------------------------------------------------------------- the predicate
@pytest.mark.parametrize("x,y", [(0, 0), (23, 19), (23, 0), (0, 19), (12, 10)])
def test_block_in_grid_accepts_corners_and_last_row_col(x, y):
    assert M.block_in_grid(x, y) is True
    M.require_block_in_grid(x, y)            # must not raise


@pytest.mark.parametrize("x,y", [(24, 0), (0, 20), (24, 20), (-1, 5), (5, -1), (9, 21)])
def test_block_in_grid_rejects_off_grid(x, y):
    assert M.block_in_grid(x, y) is False
    with pytest.raises(ValueError, match=r"OFF the 24x20"):
        M.require_block_in_grid(x, y)


# --------------------------------------------------------------------------- build_landmass (world-island)
def test_build_landmass_refuses_the_dunes_off_grid_repro():
    # the exact incident: dunes mint centre (608,-1376) r56 -> blocks (8-10, 20-22), all off-grid
    with pytest.raises(ValueError) as ei:
        I.build_landmass(center=(608.0, -1376.0), base_radius=56.0, seed=2,
                         ground="desert", stamps=None, disc=1)
    msg = str(ei.value)
    assert "OFF the 24x20" in msg and "spills" in msg
    assert "(9, 21)" in msg                  # names the offending block(s)


def test_build_landmass_row19_col23_in_grid_still_builds():
    # a small island wholly inside the grid passes the gate and builds real blocks
    built = I.build_landmass(center=(1248.0, -1184.0), base_radius=24.0, seed=2,
                             ground="desert", stamps=None, disc=1)
    assert built["blocks"]
    assert all(M.block_in_grid(bx, by) for (bx, by) in built["blocks"])


# --------------------------------------------------------------------------- lowest-level write funcs
def test_deploy_override_refuses_off_grid_before_touching_fs():
    bm = M.hidden_block_mesh(name="Block[9][21] Terrain", x=9, y=21)
    # gate fires before find_game_path, so a bogus game path is never resolved
    with pytest.raises(ValueError, match=r"OFF the 24x20"):
        M.deploy_override(bm, mod_folder="X", game="C:/definitely/not/a/game")


def test_deploy_override_writes_last_valid_block(tmp_path):
    bm = M.hidden_block_mesh(name="Block[23][19] Terrain", x=23, y=19)
    p = M.deploy_override(bm, mod_folder="M", game=str(tmp_path))
    assert p.is_file()


def test_deploy_donor_sidecar_refuses_off_grid(tmp_path):
    with pytest.raises(ValueError, match=r"OFF the 24x20"):
        M.deploy_donor_sidecar(0, 0, mod_folder="M", disc=1, x=5, y=20, game=str(tmp_path))
