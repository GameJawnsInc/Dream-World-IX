"""THE PREFAB FRAME (studies/overworld-editor/PREFABS.md, rung P0): opt-in, the same land wherever it is stamped.

A landmass prefab is a frozen composition (one plain ``world-island`` mint + carried relief) placed by whole 64u
blocks. It can only carry its in-game walk to a new site if the new site gets the SAME bytes, shifted. Three draws
read absolute position and break that; ``prefab_frame=True`` makes each one relative:

  * the meadow-decal origin shuffle (``grassland.place_stamps(ordered=True)``) -- it shuffled a set in hash order;
  * the rolling relief (``island.build_landmass``) -- read at absolute x,z, seeded from the centre;
  * the mountain apron's undecodable-cell tile (``interior.carve_mountain``) -- hashed from the absolute cell.

Off (the default) is today's bytes: every recipe on disk replays through it. That half is pinned here by what the
default path hands its draws (absolute coordinates, the unordered shuffle); the byte pin itself (14 mint configs,
81 deployed files) was taken by hand before the change and is recorded in PREFABS.md.

Each claim is calibrated both ways: the comparator that says SAME for a framed shift says DIFF for the unframed
one and for a 32u shift (not a whole block -- the cell clip moves, different land either way).
"""
from __future__ import annotations

import collections
import re
import warnings

import numpy as np
import pytest

from ff9mapkit.world import grassland as G, island as I

BASE = (96.0, -928.0)                      # blocks (0-2, 13-15): stock open ocean
WHOLE = ((0.0, -128.0), (64.0, -64.0), (192.0, 0.0))


def _f32(v) -> float:
    return float(np.float32(v))            # what the .ff9mesh stores (the engine reads float32)


def _land(built, cx, cz) -> collections.Counter:
    """Every triangle (position relative to the frame block, uv, tangent) at float32, vertex order ignored."""
    out = collections.Counter()
    k_x, k_z = 64.0 * (cx // 64.0), 64.0 * (cz // 64.0)
    for (bx, by), bm in built["blocks"].items():
        fx, fz = 64.0 * bx - k_x, -64.0 * by - k_z
        for t in bm.tris:
            out[tuple(sorted((_f32(bm.verts[i][0]) + fx, _f32(bm.verts[i][1]), _f32(bm.verts[i][2]) + fz,
                              *map(_f32, bm.uvs[i]), *map(_f32, bm.tangents[i])) for i in t))] += 1
    return out


def _moved_same(kw, shift, *, frame) -> bool:
    a = _land(I.build_landmass(center=BASE, prefab_frame=frame, **kw), *BASE)
    c = (BASE[0] + shift[0], BASE[1] + shift[1])
    return _land(I.build_landmass(center=c, prefab_frame=frame, **kw), *c) == a


RELIEF = dict(base_radius=30.0, seed=7.0, relief_amp=1.3)


# ---------------------------------------------------------------- hermetic: the mint
@pytest.mark.parametrize("shift", WHOLE)
def test_a_framed_relief_island_is_the_same_land_moved_by_whole_blocks(shift):
    assert _moved_same(RELIEF, shift, frame=True)


def test_the_unframed_relief_island_is_not_and_a_part_block_shift_is_never():
    """The calibration: the comparator above says DIFF where the land differs."""
    assert not _moved_same(RELIEF, (0.0, -128.0), frame=False)      # the leak the frame closes
    assert not _moved_same(RELIEF, (32.0, 0.0), frame=True)         # not a whole block: re-clipped cells


def test_the_default_mint_hands_its_draws_absolute_coordinates(monkeypatch):
    """OFF IS TODAY'S BYTES: the default reads the relief at world x,z with the centre's seed and shuffles the
    decals unordered; the frame reads them relative to the centre's block, seeded from ``seed``."""
    seen = {}
    real_relief = G.relief

    def relief(x, z, *, seed, amp):
        seen.setdefault("relief", []).append((x, z, seed))
        return real_relief(x, z, seed=seed, amp=amp)

    def place(cells, stamps, **kw):
        seen["ordered"] = kw.get("ordered", False)
        return [], {}
    monkeypatch.setattr(G, "relief", relief)
    monkeypatch.setattr(G, "place_stamps", place)
    cx, cz = BASE
    for frame in (False, True):
        seen.clear()
        built = I.build_landmass(center=BASE, stamps=["a stamp"], prefab_frame=frame, **RELIEF)
        xs = [x for x, _z, _s in seen["relief"]]
        seeds = {s for _x, _z, s in seen["relief"]}
        if frame:
            assert seen["ordered"] is True and built["prefab_frame"] == (64.0 * (cx // 64), 64.0 * (cz // 64))
            assert min(xs) >= -64.0 and max(xs) <= 128.0                 # within the frame's few blocks
            assert seeds == {(int(round(7.0 * 1000)) ^ I.PREFAB_RELIEF_SALT) & 0xFFFFFFFF}
        else:
            assert seen["ordered"] is False and built["prefab_frame"] is None
            assert min(xs) > cx - 40 and max(xs) < cx + 40                 # absolute world x round the centre
            assert seeds == {int(cx * 7 + cz * 13) & 0xFFFFFFFF}            # the centre-derived default


def test_the_frame_refuses_what_it_cannot_keep():
    with pytest.raises(ValueError, match="explicit seed"):
        I.build_landmass(center=BASE, prefab_frame=True)
    with pytest.raises(ValueError, match="blob mint only"):
        I.build_landmass(center=BASE, seed=5.0, prefab_frame=True, beach={"bearing": (0.0, 90.0)})


def test_the_ordered_decal_shuffle_moves_with_its_cells():
    """``place_stamps(ordered=True)`` over cells moved one block (16 cells) places the same stamp, moved."""
    stamp = {"w": 2, "h": 2, "core": 4, "trunc": 0, "cells": {"0,0": [{"poly": [(0, 0), (4, 0), (4, 4)]}]}}
    cells = [(i, j) for i in range(-40, -20) for j in range(200, 230)]
    moved = [(i + 16, j - 32) for i, j in cells]
    got = []
    for cs in (cells, moved):
        pl, _ = G.place_stamps(cs, [stamp, dict(stamp)], box_ok=lambda box: True, n_patches=2, ordered=True)
        got.append(pl)
    assert [(o[0] + 16, o[1] - 32) + o[2:5] for o in got[0]] == [o[:5] for o in got[1]]


def test_a_recipe_row_keeps_the_frame_and_drops_it_at_its_default():
    """A saved recipe must not lose the flag (a stamped prefab replayed unframed is different land)."""
    from ff9mapkit.world import recipe as R
    isl = R.row_for(["world-island", "--mod-folder", "M", "--center", "96,-928", "--seed", "5", "--prefab-frame"])
    mtn = R.row_for(["world-mountain", "--mod-folder", "M", "--center", "88,-924", "--prefab-frame"])
    assert isl["prefab_frame"] is True and mtn["prefab_frame"] is True
    plain = R.row_for(["world-island", "--mod-folder", "M", "--center", "96,-928", "--seed", "5"])
    assert "prefab_frame" not in plain
    assert R.canon(dict(plain, prefab_frame=False)) == R.canon(plain)
    assert R.canon(isl) != R.canon(plain)


# ---------------------------------------------------------------- install-gated: decals and the carry
def _install():
    from ff9mapkit import config
    try:
        game = config.find_game_path(None)
        if (game / "StreamingAssets").is_dir():
            return game
        why = "no StreamingAssets under the resolved FF9 install"
    except Exception as e:                                   # noqa: BLE001 -- any resolution failure is a skip
        why = f"the FF9 install did not resolve ({type(e).__name__}: {e})"
    warnings.warn("THE PREFAB FRAME WENT UNVERIFIED on real bytes in this run: " + why + ". This is the WORKTREE "
                  "SKIP TRAP -- re-run where the install resolves.", UserWarning)
    pytest.skip(why)


def test_a_framed_meadow_island_is_the_same_land_moved_and_the_unframed_one_is_not():
    _install()
    kw = dict(base_radius=44.0, seed=5.0, stamps="auto")
    assert _moved_same(kw, (0.0, -128.0), frame=True)
    assert not _moved_same(kw, (0.0, -128.0), frame=False)      # the set-ordered shuffle the frame replaces


_BLOCK = re.compile(r"Block\[(\d+)\]\[(\d+)\] (\w+)\.ff9mesh$")


def _terrain_by_block(root, dby):
    out = {}
    for p in root.rglob("*.ff9mesh"):
        m = _BLOCK.search(p.name)
        if m and "Disc1" in p.parts:
            out[(int(m[1]), int(m[2]) - dby, m[3])] = p.read_bytes()
    return out


def test_a_framed_desert_peak_isle_writes_the_same_bytes_at_both_sites(tmp_path):
    """The whole prefab through ``world-fuse``'s own rows (the mint, then the rigid-rock carry turned 90): framed,
    every world file at the second site is the first site's, byte for byte; unframed, the carry's apron is not
    (measured: 59 tris of one block wear other fallback tiles)."""
    from ff9mapkit.world import fuse as FU
    game = _install()

    def build(name, z, frame):
        folder = tmp_path / name
        folder.mkdir()
        isl = {"center": [96.0, z], "radius": 60.0, "seed": 5.0, "ground": "desert"}
        mtn = {"center": [88.0, z + 4.0], "rot": 90.0, "donor": "19,3", "ground": "desert"}
        if frame:
            isl["prefab_frame"] = mtn["prefab_frame"] = True
        out = FU.compose_layout(str(folder), {"island": [isl], "mountain": [mtn]}, game=game, skip_mirror=True)
        assert out["clean"], out["gates"]
        return folder

    on_a, on_b = _terrain_by_block(build("on_a", -928.0, True), 0), _terrain_by_block(build("on_b", -1056.0, True), 2)
    assert on_a and on_a == on_b
    off_a = _terrain_by_block(build("off_a", -928.0, False), 0)
    off_b = _terrain_by_block(build("off_b", -1056.0, False), 2)
    assert set(off_a) == set(off_b)
    assert [k for k in off_a if off_a[k] != off_b[k]] == [(1, 14, "Terrain")]
