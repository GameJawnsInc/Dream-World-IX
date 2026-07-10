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


#: the bay's proven-build hash (D=6 on the same window; deployed at (12,9) 2026-07-10)
GOLDEN_BAY_HASH = "232a4c1c4dd2b634"


def test_bay_golden_build():
    from ff9mapkit.world import coastmorph as CM
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_bay(DONOR, START, END, 6.0)
    # 8 wall + 15 grass dropped (the crease-footprint extension) / 11 sea / zero survivors
    assert drop_t.expected == 23 and drop_s.expected == 11
    assert disp.expected == 0
    assert len(emit_t.tris) == 29 and len(emit_s.tris) == 15
    def sig(tris, uv=True):
        return sorted(tuple(round(c, 6) for v in t3 for c in
                            (list(v[0]) + (list(v[2]) if uv else []))) for t3 in tris)
    h = hashlib.sha256(repr(sig(emit_t.tris, uv=False) + sig(emit_s.tris)).encode()).hexdigest()
    assert h[:16] == GOLDEN_BAY_HASH


def test_bay_refuses_a_component_reach():
    from ff9mapkit.world import coastmorph as CM
    # at depth 8 the bay's inland outline reaches past the window's grass component --
    # the containment gate refuses (the component laws, made a build-time refusal)
    with pytest.raises(ValueError, match="escapes the drop sets"):
        CM.cliff_bay(DONOR, START, END, 8.0)


#: the composed morph's window (480..508, spanning the REFINED-crease fan gap at 480-484)
#: and its proven-build hash (deployed at (10,9) 2026-07-10)
LOBES_START = (480.0, -1110.99)
LOBES_END = (508.0, -1113.6796875)
GOLDEN_LOBES_HASH = "1c5dab560c183654"


def test_lobes_golden_build():
    """A bay between two headlands as ONE composed reshape -- exercises the refined-fan gap
    decode, the free equal-arc resample (the pinned scheme degenerates on multi-lobe
    profiles), the phase-table wall UVs, and the grass ring-extension ladder."""
    import hashlib as _h
    from ff9mapkit.world import coastmorph as CM
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_lobes(
        DONOR, LOBES_START, LOBES_END, (3.5, -5.0, 6.5))
    assert drop_t.expected == 39 and drop_s.expected == 23
    assert disp.expected == 0
    assert len(emit_t.tris) == 47 and len(emit_s.tris) == 23
    def sig(tris, uv=True):
        return sorted(tuple(round(c, 6) for v in t3 for c in
                            (list(v[0]) + (list(v[2]) if uv else []))) for t3 in tris)
    h = _h.sha256(repr(sig(emit_t.tris, uv=False) + sig(emit_s.tris)).encode()).hexdigest()
    assert h[:16] == GOLDEN_LOBES_HASH


def test_lobes_reach_gate_refuses_the_shallow_ladder():
    from ff9mapkit.world import coastmorph as CM
    # a window starting one column further west pushes its first headland lobe's footprint
    # into the sea5 band -- the REACH gate refuses (non-sea4 within the morph's reach)
    with pytest.raises(ValueError, match="reaches sea"):
        CM.cliff_lobes(DONOR, (476.0, -1108.9), LOBES_END, (3.5, -5.0, 6.5))


#: the (7,17) S-beach waterline run (deployed with the D=2.5 seaward bow at (11,8) 2026-07-10)
BEACH_START = (476.0, -1124.0)
BEACH_END = (504.0, -1132.0)


def test_beach_bump_builds_and_gates():
    """The beach frontier's rung 1: the LADDER-TAPER bow. The foam drags (edge-anchored);
    every seaward water band moves as a cos^2-tapered field through its own tile map
    (SeaBump -- water never drags, on any band), so the ladder keeps its real band-width
    statistics (a waterline-only bow pinched the wash 4.0 -> 0.8u = the in-game seam).
    The RIBBON GATE still refuses a landward bow that pinches the swash."""
    from ff9mapkit.world import coastmorph as CM
    (disp,) = CM.beach_bump(DONOR, BEACH_START, BEACH_END, 2.5)
    # taper + pure DRAG (one part=None displacement over the depth-scaled ~24.5u reach) --
    # water tolerates SMALL strain (<=16%, the strain gate), not re-evaluation at field scale
    assert disp.part is None and disp.expected == 190
    with pytest.raises(ValueError, match="RIBBON GATE"):
        CM.beach_bump(DONOR, BEACH_START, BEACH_END, -2.0)


def test_beach_bump_refuses_a_non_waterline_run():
    from ff9mapkit.world import coastmorph as CM
    # sand-seam endpoints (the landward boundary) are not a waterline run
    with pytest.raises(ValueError, match="waterline"):
        CM.beach_bump(DONOR, (480.0, -1120.0), (496.0, -1125.0), 2.0)


def test_structural_refuses_a_grassless_top():
    from ff9mapkit.world import coastmorph as CM
    # the (9,5) continent-island-A donor has ZERO grass (highland/mural top families) --
    # the baked-terrain law: no fill language, so structural morphs refuse cleanly and
    # only the conforming bow applies. Window = a clean run on block (10,6).
    with pytest.raises(ValueError, match="no grass mains"):
        CM.cliff_headland((10, 6), (695.6, -407.9), (680.0, -436.0), 6.0)


def test_headland_refuses_an_illegal_gap_count():
    from ff9mapkit.world import coastmorph as CM
    # a 3-gap sub-window (492..504) cannot satisfy the deterministic U-ramp: its clean
    # gaps cover only 3 of the 4 texture phases (the free resample lifts the old strict
    # mod-4 window rule, but a pattern for every phase must exist in-window)
    with pytest.raises(ValueError, match="texture phases"):
        CM.cliff_headland(DONOR, START, (504.0, -1110.765625), 6.0)


def test_headland_grain_and_widths_stay_lawful():
    from ff9mapkit.world import coastmorph as CM
    _, _, _, emit_t, _ = CM.cliff_headland(DONOR, START, END, 8.0)
    longest = max(max(math.dist(t3[i][0], t3[(i + 1) % 3][0]) for i in range(3))
                  for t3 in emit_t.tris[16:])                # the grass fill
    assert longest <= CM.MAX_GRAIN
