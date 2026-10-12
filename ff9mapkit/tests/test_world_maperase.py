"""THE MAP ERASE (world-minimap): land a mod folder removed comes off the painted chart.

Hermetic: a synthetic chart (a stained, grainy parchment inside a frame line) paints its islands OFF the geometry,
the way the real chart sits up to ~15px from it, and the erase must find them by the art. The real-chart proof is
the study crops (six sunk islands, both charts) plus a relaunch.
"""
from __future__ import annotations

import numpy as np
import pytest

from ff9mapkit.world import maperase as ME

W, H = 220, 180
PARCH = np.array([166.0, 119.0, 58.0])
LANDC = np.array([110.0, 88.0, 30.0])
HALOC = np.array([150.0, 131.0, 72.0])


def _disc(cx, cy, r):
    yy, xx = np.mgrid[0:H, 0:W]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def _chart(seed=7):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    stain = 6.0 * np.sin(xx / 37.0)[..., None] * np.array([1.0, 0.8, 0.5])
    A = PARCH + stain + rng.normal(0, 4.0, (H, W, 3))
    A[:6], A[-6:], A[:, :6], A[:, -6:] = (60.0, 20.0, 10.0), (60.0, 20.0, 10.0), (60.0, 20.0, 10.0), (60.0, 20.0, 10.0)
    inside = np.zeros((H, W), bool)
    inside[10:-10, 10:-10] = True
    return A, inside


def _paint(A, mask, colour, rng):
    A[mask] = colour + rng.normal(0, 3.0, (int(mask.sum()), 3))


def _scene(*, halo: bool, painted: bool = True, off=(5, -4)):
    """An island at (120, 95) r 16 (painted at +off), a kept islet at (45, 50) r 9 painted at the same offset; with
    ``halo``, a shallow band round the island that the chart paints as halo."""
    A, inside = _chart()
    rng = np.random.default_rng(3)
    stock = np.zeros((H, W), np.uint8)
    if halo:
        stock[_disc(120, 95, 30)] = ME.SHALLOW
    stock[_disc(120, 95, 16)] = ME.LAND
    stock[_disc(45, 50, 9)] = ME.LAND
    dx, dy = off
    if halo:
        _paint(A, _disc(120 + dx, 95 + dy, 30), HALOC, rng)
    if painted:
        _paint(A, _disc(120 + dx, 95 + dy, 16), LANDC, rng)
    _paint(A, _disc(45 + dx, 50 + dy, 9), LANDC, rng)
    return A, inside, stock


def _dist(A, colour):
    return np.sqrt(((A - colour) ** 2).sum(-1))


def test_an_island_in_deep_water_comes_off_where_the_chart_drew_it():
    A, inside, stock = _scene(halo=False)
    before = A.copy()
    effective = stock.copy()
    effective[_disc(120, 95, 16)] = ME.DEEP                     # sunk: open sea where it stood
    reps = ME.erase_removed(A, stock, effective, inside=inside)
    assert len(reps) == 1 and reps[0]["shift"] == (5, -4)       # found by the ART, ~6px off the geometry
    assert reps[0]["iou"] > 0.8 > reps[0]["iou_unshifted"]
    drawn = _disc(125, 91, 16)
    assert (_dist(A[drawn], LANDC) < 30).sum() == 0               # no land colour left
    assert _dist(A[drawn], PARCH).mean() < 14                    # it reads as the parchment round it
    changed = (A != before).any(-1)
    assert not changed[~inside].any()                            # the frame is never touched
    assert not changed[_disc(50, 46, 12)].any()                  # the kept islet is byte-for-byte the same
    assert not changed[~_disc(125, 91, 22)].any()                # nothing but the island (and its 1px fringe)


def test_an_island_in_a_halo_becomes_halo_not_a_parchment_hole():
    A, inside, stock = _scene(halo=True)
    effective = stock.copy()
    effective[_disc(120, 95, 16)] = ME.SHALLOW                  # re-banded: shallow water where it stood
    reps = ME.erase_removed(A, stock, effective, inside=inside)
    assert reps and reps[0]["erased_px"] > 0 and reps[0]["to_halo_px"] > 0.8 * reps[0]["erased_px"]
    drawn = _disc(125, 91, 14)
    assert (_dist(A[drawn], LANDC) < 30).sum() == 0
    assert _dist(A[drawn], HALOC).mean() < _dist(A[drawn], PARCH).mean()   # continues the halo round it


def test_a_halo_whose_water_turned_deep_goes_too():
    A, inside, stock = _scene(halo=True)
    effective = stock.copy()
    effective[_disc(120, 95, 30)] = ME.DEEP                     # the island AND its shallows: all open sea
    reps = ME.erase_removed(A, stock, effective, inside=inside)
    assert reps[0]["halo_to_sea_px"] > 0
    ring = _disc(125, 91, 27) & ~_disc(125, 91, 19)
    assert _dist(A[ring], PARCH).mean() < _dist(A[ring], HALOC).mean()


def test_a_known_drift_reaches_an_island_painted_past_the_search():
    """The all-world chart drifts linearly off its frame (up to ~24px at its edges): past ALIGN_REACH an island is
    out of the search (skipped, untouched) until the measured drift centres the search on it."""
    off = (3, -26)
    for drift, found in ((None, False), (lambda x, y: (2.0, -24.0), True)):
        A, inside, stock = _scene(halo=False, off=off)
        before = A.copy()
        effective = stock.copy()
        effective[_disc(120, 95, 16)] = ME.DEEP
        rep = ME.erase_removed(A, stock, effective, inside=inside, drift=drift)[0]
        if found:
            assert rep["shift"] == off and rep["expected"] == (2, -24) and rep["erased_px"] > 0
            assert (_dist(A[_disc(123, 69, 16)], LANDC) < 30).sum() == 0
        else:
            assert "skipped" in rep and np.array_equal(A, before)


def test_land_the_chart_does_not_draw_is_skipped_untouched():
    A, inside, stock = _scene(halo=False, painted=False)
    before = A.copy()
    effective = stock.copy()
    effective[_disc(120, 95, 16)] = ME.DEEP
    reps = ME.erase_removed(A, stock, effective, inside=inside)
    assert reps and reps[0]["erased_px"] == 0 and "skipped" in reps[0]
    assert np.array_equal(A, before)


def test_a_coast_tweak_is_not_lost_land_and_nothing_removed_is_a_no_op():
    A, inside, stock = _scene(halo=False)
    before = A.copy()
    assert ME.erase_removed(A, stock, stock.copy(), inside=inside) == []
    effective = stock.copy()
    effective[95, 104:108] = ME.DEEP                             # 4px off a coast: under MIN_REMOVED_PX
    assert ME.erase_removed(A, stock, effective, inside=inside) == []
    assert np.array_equal(A, before)


def test_class_rasters_read_the_folders_parts_over_stock(monkeypatch):
    """Stock land + its shallow band on a real cell; the folder blanks the Terrain with a hidden stub (world-sink's
    emptied part) and keeps the water: the land is removed, the water is not, and a Donor.txt cell is no edit."""
    from ff9mapkit.world import discmirror as DM, transplant as T

    def tri(x0, z0, x1, z1, y=1.0):
        return [((x0, y, z0), None, None, (0,)), ((x1, y, z0), None, None, (0,)), ((x0, y, z1), None, None, (0,))]
    stock_tris = {"terrain": [tri(330, -330, 350, -350)], "sea3": [tri(320, -320, 370, -370, 0.0)]}
    monkeypatch.setattr(DM, "_real_parts", lambda disc, lod="0_1", game=None: {(5, 5): {"terrain", "sea3"}})
    monkeypatch.setattr(T, "world_tris", lambda bx, by, p, **k: stock_tris.get(p, []) if (bx, by) == (5, 5) else [])
    hidden = [[((0.0, -80.0, 0.0), None, None, (1,)), ((0.1, -80.0, 0.0), None, None, (1,)),
               ((0.0, -80.0, 0.1), None, None, (1,))]]
    monkeypatch.setattr(T, "world_tris_stacked",
                        lambda mod, bx, by, p, **k: (hidden, "x") if p == "terrain" else (stock_tris.get(p, []), None))
    monkeypatch.setattr(ME, "deployed_cells", lambda mod, **k: ({(5, 5): {"terrain"}, (9, 9): {"terrain"}}, {(9, 9)}))
    stock, eff, edited = ME.class_rasters("lab", disc=1, to_px=lambda wx, wz: (wx - 300, -wz - 300), size=(100, 100))
    assert edited == [(5, 5)]                                    # (9, 9) re-points at a donor: not an edit
    assert stock[40, 35] == ME.LAND and stock[22, 60] == ME.SHALLOW
    assert eff[40, 35] == ME.SHALLOW and eff[22, 60] == ME.SHALLOW   # the stub is not land: the water shows
    assert stock[90, 90] == ME.DEEP


@pytest.mark.parametrize("frame_name", ["WORLD_MAP_ART_FRAME", "MIST_MAP_ART_FRAME"])
def test_the_chart_frames_are_pinned(frame_name):
    from ff9mapkit.world import navimap as NM
    fx, fy, fw, fh = getattr(NM, frame_name)
    if frame_name == "WORLD_MAP_ART_FRAME":
        assert (round(fx * 1273), round(fy * 1080), round(fw * 1273), round(fh * 1080)) == (51, 42, 1168, 1002)
    else:                                       # a close-up: the world overhangs the 1273x1080 image
        assert fx < 0 and fy < 0 and fw > 1 and fh > 1
