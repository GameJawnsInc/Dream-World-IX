"""THE CELL-CLIPPED FILL (coastmorph._grass_fill_region) -- the lip-streak fix carried from world-island's
THE CELL-CLIPPED LIP to the coast-morph grass fills (cliff headland / bay / lobes, the beach slide's strip).

The defect: a mains UV is its 4u cell's map CLAMPED to the cell's window, and the fill mapped every tri through its
CENTROID cell, so an ear spanning two cells (the moved crease or the slid band chain against a lattice corner) wore
two corners clamped onto one UV point -- a rank-1 streak. The world-morphs scanner's own certified deploy lines carried
6 (one per build: bay (5,16) D=6 fully rank 1, headland (12,12) D=4 at 90.9, headland (13,17) D=3, bay (12,13) D=6,
slides (17,10) +2 and (13,3) +1); a depth sweep over every window that builds, 58. Stock's lip grass peaks at 5.8.

The unit tests need no install; the window tests decode the real bytes and skip on a public clone."""
from __future__ import annotations

import math
from collections import defaultdict

import pytest

from ff9mapkit.world import coastmorph as CM
from ff9mapkit.world import grassland as G
from ff9mapkit.world import island as IS

IDALL = (0.0, 0.0)

#: the (5,16) bay's rank-1 ear, verbatim (two crease verts + the stock lattice corner beside them)
EAR = [(372.4625, 4.156, -1069.0210), (369.5147, 4.344, -1065.3506), (372.0, 3.746, -1068.0)]


def _streaks(tris):
    return [r for r in (IS.uv_streak([v[0] for v in t3], [v[2] for v in t3]) for t3 in tris) if r is not None]


def test_the_ear_was_a_streak_through_its_centroid_cell():
    """Calibration: the detector DOES fire on the pre-fix mapping of the ear -- its centroid cell's map, the build's
    own quadrant (1, 1) clamping two corners onto one UV point."""
    cx = sum(p[0] for p in EAR) / 3.0
    cz = sum(p[2] for p in EAR) / 3.0
    cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
    uvs = [G.mains_uv(p[0], p[2], cell, (1, 1), 0) for p in EAR]
    assert IS.uv_streak(EAR, uvs) == math.inf


def test_the_ear_fills_cell_clipped():
    fill, loop_cuts = CM._grass_fill_region(EAR, {}, {}, IDALL)
    assert len(fill) > 1 and not _streaks(fill)
    for t3 in fill:                                       # each piece inside one cell, up to the cut snap
        xs = [v[0][0] for v in t3]
        zs = [v[0][2] for v in t3]
        i = math.floor(sum(xs) / 3.0 / 4.0)
        j = math.floor(sum(zs) / 3.0 / 4.0)
        assert all(4.0 * i - CM.FILL_CUT_SNAP <= x <= 4.0 * i + 4.0 + CM.FILL_CUT_SNAP for x in xs)
        assert all(4.0 * j - CM.FILL_CUT_SNAP <= z <= 4.0 * j + 4.0 + CM.FILL_CUT_SNAP for z in zs)
    # the crease edge carries its two lattice cuts; the edges into the lattice corner carry none
    (a, b, cuts), = loop_cuts.values()
    assert {CM._pk(a), CM._pk(b)} == {CM._pk(EAR[0]), CM._pk(EAR[1])} and len(cuts) == 2
    assert {c[0] for c in cuts} >= {372.0} and {c[2] for c in cuts} >= {-1068.0}


def test_edge_cuts_are_canonical_and_clear_of_the_ends():
    a, b = (370.3, 1.0, -1061.7), (377.9, 2.5, -1050.05)
    fwd, rev = CM._edge_cuts(a, b), CM._edge_cuts(b, a)
    assert fwd == rev[::-1] and fwd                       # the identical floats from either side
    for c in fwd:
        assert c[0] in (372.0, 376.0) or c[2] in (-1060.0, -1056.0, -1052.0)
        assert min(math.hypot(c[0] - p[0], c[2] - p[2]) for p in (a, b)) >= CM.FILL_CUT_SNAP
    # a crossing within the snap of an end is not cut
    assert CM._edge_cuts((371.9, 0.0, -1061.0), (369.0, 0.0, -1061.0)) == []
    # a block-border edge never cuts (its owner is the neighbour block's)
    assert CM._edge_cuts((384.0, 0.0, -1066.3), (384.0, 0.0, -1062.5)) == []
    assert CM._edge_cuts((384.0, 0.0, -1066.3), (384.0, 0.0, -1062.5), frame=False)


def test_t_split_is_a_lossless_subdivision():
    t3 = [((0.5, 1.0, 0.5), (0.0, 1.0, 0.0), (0.1, 0.2), IDALL),
          ((7.3, 1.4, 1.1), (0.0, 1.0, 0.0), (0.3, 0.25), IDALL),
          ((2.2, 0.8, 6.9), (0.0, 1.0, 0.0), (0.12, 0.4), IDALL)]
    cuts = CM._loop_cuts([v[0] for v in t3])
    tris, n = CM._t_split(t3, cuts)
    assert n == 3 and len(tris) > 3

    def area2(t):
        (ax, _, az), (bx, _, bz), (qx, _, qz) = (v[0] for v in t)
        return (bx - ax) * (qz - az) - (qx - ax) * (bz - az)
    assert sum(area2(t) for t in tris) == pytest.approx(area2(t3))
    assert all(area2(t) > 0 for t in tris)                # the winding is kept
    uvf = CM.TR._affine_uv(t3)
    for t in tris:                                        # every new vertex wears the tri's own map
        for (p, _n, uv, _i) in t:
            assert uv == pytest.approx(tuple(uvf(p[0], p[2])), abs=1e-9)


def test_a_block_border_edge_holds_its_line():
    """A fill-loop edge ON a block border crossing a lattice line is never cut (its weld is the neighbour block's):
    its nearer end HOLDS that line, so the loop's other edge from that end takes no cut there either."""
    e, f, c = (1408.0, 3.0, -820.875), (1408.0, 3.0, -816.0), (1411.2, 3.0, -817.1)
    held = CM._held_lines([e, f, c])
    assert held == {CM._pk(e): {(2, -820.0)}}
    assert CM._edge_cuts(c, e) != [] and CM._edge_cuts(c, e, held) == []
    fill, loop_cuts = CM._grass_fill_region([e, f, c], {}, {}, IDALL)
    assert loop_cuts == {} and len(fill) == 1            # the tri whole, e overhanging the line as before
    assert {CM._pk(v[0]) for v in fill[0]} == {CM._pk(p) for p in (e, f, c)}


def test_split_loop_owners_refuses_an_unowned_cut():
    with pytest.raises(ValueError, match="owner"):
        CM._split_loop_owners(CM._loop_cuts(EAR), [], [])


# ---------------------------------------------------------------- the real windows (needs the install)

def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


needs_game = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")

#: the scanner-certified deploy lines that streaked before the fix (verb, cell, start, end, depth)
STREAKED = [
    ("cliff_bay", (5, 16), (380.0, -1081.4140625), (356.0, -1055.09375), 6.0),
    ("cliff_headland", (12, 12), (789.0234375, -827.54296875), (768.0, -820.24609375), 4.0),
    ("cliff_headland", (13, 17), (867.71484375, -1108.0), (872.0, -1151.078125), 3.0),
    ("cliff_bay", (12, 13), (776.4375, -862.62890625), (793.1015625, -832.0), 6.0),
    ("beach_slide", (17, 10), (1140.8828125, -641.91015625), (1116.0, -660.0), 2.0),
    ("beach_slide", (13, 3), (868.58984375, -195.9453125), (852.02734375, -213.21484375), 1.0),
]


@needs_game
@pytest.mark.parametrize("verb,cell,start,end,depth", STREAKED)
def test_the_streaked_deploy_lines_read_zero(verb, cell, start, end, depth):
    tw = getattr(CM, verb)(cell, start, end, depth)
    emit = [t for t in tw if getattr(t, "part", None) == "terrain" and hasattr(t, "tris")]
    assert emit and not _streaks(emit[0].tris)


@needs_game
def test_a_window_on_the_block_border_mints_no_border_vertex():
    """The (22,12) bay's fill runs along the x=1408 block border (its window starts on the corner): no streak, and
    not one new vertex on the border -- the neighbour block's weld is untouched. (Cutting the border edge refused
    the window outright; fanning the tri round it scored 20.5; with the held line the fill's worst is 2.3, the
    uncut fill's was 10.9.)"""
    tw = CM.cliff_bay((22, 12), (1408.0, -800.0), (1408.0, -821.3203125), 4.0)
    emit = next(t for t in tw if getattr(t, "part", None) == "terrain" and hasattr(t, "tris"))
    assert not _streaks(emit.tris)
    from ff9mapkit.world import transplant as TR
    stock = {CM._pk(v[0]) for t3 in TR.world_tris(22, 12, "terrain") for v in t3}
    assert [v[0] for t3 in emit.tris for v in t3 if abs(v[0][0] - 1408.0) < 1e-6 and CM._pk(v[0]) not in stock] == []


def _after(cell, tw):
    """The cell's terrain + foam before and after the tweaks: ``(before, kept, emitted)`` (kept tris displaced)."""
    from ff9mapkit.world import transplant as TR
    before = [list(t3) for p in ("terrain", "beach1") for t3 in TR.world_tris(cell[0], cell[1], p)]
    drops, emits, moves = set(), [], {}
    for t in tw:
        if getattr(t, "part", None) == "terrain" and hasattr(t, "keys"):
            drops |= t.keys
        elif getattr(t, "part", None) == "terrain" and hasattr(t, "tris"):
            emits += [list(t3) for t3 in t.tris]
        elif hasattr(t, "moves") and getattr(t, "part", None) in (None, "terrain"):
            moves.update(t.moves)
    kept = []
    for t3 in before:
        if frozenset(CM._pk(v[0]) for v in t3) in drops:
            continue
        kept.append([(tuple(v[0][k] + moves[CM._pk(v[0])][k] for k in range(3)) if CM._pk(v[0]) in moves
                      else v[0], v[1], v[2], v[3]) for v in t3])
    return before, kept, emits


def _open_above_waterline(tris):
    n = defaultdict(int)
    for t3 in tris:
        for i in range(3):
            n[frozenset((CM._pk(t3[i][0]), CM._pk(t3[(i + 1) % 3][0])))] += 1
    return {e for e, c in n.items() if c == 1 and min(k[1] for k in e) > CM.BASE_Y_MAX}


@needs_game
@pytest.mark.parametrize("verb,cell,start,end,depth", [STREAKED[0], STREAKED[4]])
def test_the_split_owners_close_the_surface(verb, cell, start, end, depth):
    """No crack, T-vertex or near-miss twin: the owners across the cut fill boundary (wall, band, kept stock) split
    at the fill's own cut points."""
    from ff9mapkit.world.mesh import near_miss_pairs
    tw = getattr(CM, verb)(cell, start, end, depth)
    before, kept, emits = _after(cell, tw)
    x0, z1 = 64.0 * cell[0], -64.0 * cell[1]

    def interior(e):
        return not any(all(abs(k[ax] - g) < 0.02 for k in e)
                       for ax, g in ((0, x0), (0, x0 + 64.0), (2, z1), (2, z1 - 64.0)))
    assert {e for e in _open_above_waterline(kept + emits) - _open_above_waterline(before) if interior(e)} == set()
    xs = [v[0][0] for t3 in emits for v in t3]
    zs = [v[0][2] for t3 in emits for v in t3]
    near = [(True, t3) for t3 in emits] + [
        (False, t3) for t3 in kept
        if any(min(xs) - 6 <= v[0][0] <= max(xs) + 6 and min(zs) - 6 <= v[0][2] <= max(zs) + 6 for v in t3)]
    CM._tvertex_gate(near)
    new_v = {tuple(round(c, 6) for c in v[0]) for t3 in emits for v in t3}
    assert [p for p in near_miss_pairs([v[0] for t3 in kept + emits for v in t3])
            if p[0] in new_v or p[1] in new_v] == []
