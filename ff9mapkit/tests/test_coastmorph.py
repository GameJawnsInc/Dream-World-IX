"""The coast-morph pillar (world/coastmorph.py) -- golden tests against the IN-GAME-PROVEN
build (2026-07-09, donor (7,17)'s NE cliff window, deployed cells (11,9) bump / (13,9)
headland vs the (9,9) verbatim reference; land approved round 1, water round 2).

These tests need the FF9 install (they decode the real donor bytes) and skip cleanly on a
public clone, like the other transplant proofs.
"""
import hashlib
import math

import pytest


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")

DONOR = (7, 17)
# the proven window's base-outline endpoints (donor world frame, snapped from the mesh)
START = (492.0, -1102.8203125)
END = (508.0, -1113.6796875)
#: sha256 over the sorted rounded emissions (terrain positions; sea positions+uvs) of the
#: proven headland build -- geometry is deterministic; grass UV quadrant PICKS are
#: deterministic too (sorted Delaunay iteration) but excluded so an anti-tiling hash-tweak
#: never masks a geometry regression.
GOLDEN_HASH = "9ad139e61b888b14"


def _window():
    from ff9mapkit.world import coastmorph as CM
    return CM.CliffWindow(DONOR, START, END)


def test_window_decodes_the_proven_columns():
    win = _window()
    assert len(win.base) == 5
    assert [round(p[0]) for p in win.base] == [492, 496, 500, 504, 508]
    # the lip-row laws, byte-exact on this specimen (crease 0.893 / base 0.923)
    assert all(abs(p[1]) < 0.01 for p in win.base)          # free-base at the waterline
    assert len(win.quads) == 4 and all(len(q) == 2 for q in win.quads)
    assert win.nhat[1] > 0                                   # seaward = north-east here


def test_bump_builds_the_proven_counts_and_refuses_the_fold():
    from ff9mapkit.world import coastmorph as CM
    disp, sea = CM.cliff_bump(DONOR, START, END, 2.5)
    assert disp.part == "terrain" and disp.expected == 26   # the deployed proven counts
    assert sea.part == "sea4" and sea.expected == 9
    # the ~2.5u conforming envelope is GEOMETRIC: 3.0 folds the tile whose shore vert sits
    # between two fixed water verts (the in-game-refused case, made a build-time refusal)
    with pytest.raises(ValueError, match="folds a tile"):
        CM.cliff_bump(DONOR, START, END, 3.0)


def test_headland_golden_build():
    from ff9mapkit.world import coastmorph as CM
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_headland(DONOR, START, END, 8.0)
    # the proven scope: 8 wall + 6 grass dropped / 19 sea dropped / zero surviving
    # moved-vert instances (the DROP-DON'T-DRAG law) / 16 wall + 18 grass + 17 sea emitted
    assert drop_t.expected == 14 and drop_s.expected == 19
    assert disp.expected == 0
    assert len(emit_t.tris) == 34 and len(emit_s.tris) == 17
    # every emitted tri is real geometry (the wall law: never test plan area)
    from ff9mapkit.world.transplant import _tri_area2_3d
    assert all(_tri_area2_3d(t3) > 1e-6 for t3 in emit_t.tris + emit_s.tris)
    # the golden emission hash (positions; sea incl. uvs) == the in-game-proven build
    def sig(tris, uv=True):
        return sorted(tuple(round(c, 6) for v in t3 for c in
                            (list(v[0]) + (list(v[2]) if uv else []))) for t3 in tris)
    h = hashlib.sha256(repr(sig(emit_t.tris, uv=False) + sig(emit_s.tris)).encode()).hexdigest()
    assert h[:16] == GOLDEN_HASH


def test_headland_refuses_an_illegal_gap_count():
    from ff9mapkit.world import coastmorph as CM
    # a 3-gap sub-window (492..504) breaks the deterministic-U-ramp mod-4 law
    with pytest.raises(ValueError, match="multiple of 4"):
        CM.cliff_headland(DONOR, START, (504.0, -1110.765625), 6.0)


def test_headland_grain_and_widths_stay_lawful():
    from ff9mapkit.world import coastmorph as CM
    _, _, _, emit_t, _ = CM.cliff_headland(DONOR, START, END, 8.0)
    longest = max(max(math.dist(t3[i][0], t3[(i + 1) % 3][0]) for i in range(3))
                  for t3 in emit_t.tris[16:])                # the grass fill
    assert longest <= CM.MAX_GRAIN
