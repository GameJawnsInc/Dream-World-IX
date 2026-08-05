"""world.rimretile -- the cropped-shallow-rim terminator.

Hermetic: synthetic tiles only, so these run in a fresh worktree. Each law is exercised
from BOTH sides, because every failure this operator exists to prevent passed the geometry
gates it already had.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import rimretile as RR
from ff9mapkit.world import water as W


def _quad(i, j, uv=(0.5, 0.5), topo=53):
    """Two triangles covering 4u tile (i, j), as part_tris returns them."""
    from ff9mapkit.world.extract import encode_id
    idl = float(encode_id(topograph=topo))
    x0, z0 = i * RR.CELL, -j * RR.CELL
    c = {(0, 0): (x0, 0.0, z0), (1, 0): (x0 + 4, 0.0, z0),
         (1, 1): (x0 + 4, 0.0, z0 - 4), (0, 1): (x0, 0.0, z0 - 4)}
    out = []
    for tri in (((0, 0), (1, 0), (1, 1)), ((0, 0), (1, 1), (0, 1))):
        out.append([(i, j), [(c[k], (0.0, 1.0, 0.0), uv, (idl, 0.0, 0.0, 1.0))
                             for k in tri], topo])
    return out


def test_corner_and_cell_round_trip():
    for (i, j) in ((0, 0), (3, 7), (15, 15)):
        for [_c, verts, _t] in _quad(i, j):
            for (p, _n, _u, _t2) in verts:
                assert RR.cell_of(p) == (i, j) or RR.corner_of(p, i, j) in (
                    (0, 0), (1, 0), (1, 1), (0, 1))


def test_deepset_is_LAND_AWARE():
    """A 'sea4' shade with NO water triangle is a coast, not deep -- without this the
    census over-flags every real coastline."""
    island = [(0, 0)]
    shade = {(0, 0): [["sea4"] * RR.G for _ in range(RR.G)]}
    water = {(0, 0): [[False] * RR.G for _ in range(RR.G)]}
    water[(0, 0)][5][5] = True                       # our cell has water
    # neighbour E is sea4 but DRY -> land, not deep
    assert "E" not in RR.deepset(shade, water, island, 0, 0, 5, 5)
    water[(0, 0)][6][5] = True                       # now it is deep water
    assert "E" in RR.deepset(shade, water, island, 0, 0, 5, 5)


def test_offisland_is_the_generic_deep_RING():
    island = [(0, 0)]
    shade = {(0, 0): [["sea3"] * RR.G for _ in range(RR.G)]}
    water = {(0, 0): [[True] * RR.G for _ in range(RR.G)]}
    # cell (0, j) faces off-island to the W -> the ring, which is deep
    assert "W" in RR.deepset(shade, water, island, 0, 0, 0, 5)


def test_uncovered_REFUSES_a_deepset_the_donor_cannot_supply():
    """THE GOVERNING LAW: a missing tile must refuse, never be synthesized."""
    plan = {(0, 0): {(0, 5): ("sea5", frozenset("N"))}}
    assert RR.uncovered(plan, {}) == ["N"]                    # no vocabulary at all
    have = {tuple(o): {} for o in W.DEEPSET2TILE[frozenset("N")]}
    assert RR.uncovered(plan, have) == []


def test_repartition_gate_accepts_a_reshade_and_REJECTS_moved_geometry():
    """The gate that makes this safe where authoring uv was not."""
    before = {(0, 0): {"sea3": None, "sea5": None}}

    class _BM:                                        # minimal stand-in for part_tris
        def __init__(self, tris):
            self.verts = [v[0] for t in tris for v in t[1]]
            self.normals = [v[1] for t in tris for v in t[1]]
            self.uvs = [v[2] for t in tris for v in t[1]]
            self.tangents = [v[3] for t in tris for v in t[1]]
            self.flat_index = list(range(len(self.verts)))

    q = _quad(2, 2)
    same = {(0, 0): {"sea5": _BM(q)}}
    assert RR.repartition_ok({(0, 0): {"sea3": _BM(q)}}, same)   # part moved, geometry same
    moved = _quad(2, 2)
    moved[0][1][0] = ((99.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.5, 0.5), (0.0, 0.0, 0.0, 1.0))
    assert not RR.repartition_ok({(0, 0): {"sea3": _BM(q)}}, {(0, 0): {"sea5": _BM(moved)}})


def test_harvest_ignores_an_incomplete_tile(monkeypatch):
    """A 3-corner sliver never completes the 4-corner set, so it is not vocabulary."""
    from ff9mapkit.world import extract as X

    class _B:
        tris = [[0, 1, 2]]
        verts = [(0.0, 0.0, 0.0)] * 3
        uvs = [(0.1, 0.1)] * 3

    monkeypatch.setattr(X, "read_block", lambda *a, **k: _B())
    assert RR.harvest_variants([(0, 0)]) == {}


def test_harvest_DROPS_a_variant_whose_instances_disagree(monkeypatch):
    """An inconsistent variant is not a vocabulary -- drop it rather than average it.

    The first version of this test was NAMED for this law and exercised a different path
    (an incomplete tile), so a mutation removing the consistency filter passed it.
    """
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import water as W2

    class _B:
        """One complete 4-corner tile; `uvbase` shifts every uv so two donors disagree."""
        def __init__(self, uvbase):
            self.tris = [[0, 1, 2], [0, 2, 3]]
            self.verts = [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 0.0, -4.0), (0.0, 0.0, -4.0)]
            self.uvs = [(uvbase, uvbase)] * 4

    seq = iter([_B(0.10), _B(0.90)])
    monkeypatch.setattr(X, "read_block", lambda *a, **k: next(seq))
    monkeypatch.setattr(W2, "_fit_tile", lambda corners: (0.0, 0.5, 0.0, 0.5, "r0"))
    monkeypatch.setattr(W2, "_strip_of", lambda v0: 0)
    assert RR.harvest_variants([(0, 0), (1, 1)]) == {}, "disagreeing instances must drop"

    seq2 = iter([_B(0.10), _B(0.10)])
    monkeypatch.setattr(X, "read_block", lambda *a, **k: next(seq2))
    assert RR.harvest_variants([(0, 0), (1, 1)]), "agreeing instances must be harvested"


def test_harvest_tolerates_a_donor_with_no_sea5(monkeypatch):
    from ff9mapkit.world import extract as X

    def boom(*a, **k):
        raise ValueError("disc1 block[6][7] sea5 mesh not found (looked for container ...)")

    monkeypatch.setattr(X, "read_block", boom)
    assert RR.harvest_variants([(6, 7)]) == {}      # skipped, not raised


def test_plan_rim_flags_interior_crop_seams(monkeypatch):
    """THE CROP-SEAM WIDENING (2026-08-04): a cluster-SHIFTED carry lands its crop lines
    MID-CELL, where the frame-only audit never looked -- measured live on the composed
    dot pair (a hard-edged sea3 sheet ending mid-channel). A sea3 quad touching deep is
    a seam ANYWHERE (stock abuts sea3 to deep nowhere map-wide); a sea3 quad inside its
    own sheet is not."""
    shade_g = [["sea4"] * RR.G for _ in range(RR.G)]
    for i in (6, 7, 8):
        for j in (6, 7, 8):
            shade_g[i][j] = "sea3"
    water_g = [[True] * RR.G for _ in range(RR.G)]
    monkeypatch.setattr(RR, "_grids",
                        lambda cells: ({(5, 5): shade_g}, {(5, 5): water_g}))
    monkeypatch.setattr(RR, "_sea5_deepsets", lambda parts: {})
    plan = RR.plan_rim({(5, 5): {}})
    got = set(plan.get((5, 5), {}))
    assert (7, 7) not in got                     # the sheet interior is lawful
    edge = {(i, j) for i in (6, 7, 8) for j in (6, 7, 8)} - {(7, 7)}
    assert edge <= got, sorted(edge - got)       # every crop-edge tile is planned


def test_tile_uv_interpolates_a_cut_vert_and_keeps_corners_exact():
    """THE CUT-VERT LAW: the variant map is EVALUATED at the vert, never corner-snapped.
    Corner verts stay bit-identical to the harvested corners; a mid-tile vert of a
    coast-cut triangle gets the tile's real map at its position (the corner snap smeared
    it into a stretched face -- playtest 2026-08-04)."""
    uvmap = {(0, 0): (0.0, 0.5), (1, 0): (0.25, 0.5),
             (1, 1): (0.25, 0.75), (0, 1): (0.0, 0.75)}
    i, j = 3, 2                                # tile x 12..16, world z -8..-12
    assert RR._tile_uv(uvmap, (12.0, 0.0, -8.0), i, j) == uvmap[(0, 0)]
    assert RR._tile_uv(uvmap, (16.0, 0.0, -12.0), i, j) == uvmap[(1, 1)]
    u, v = RR._tile_uv(uvmap, (13.0, 0.0, -10.0), i, j)   # 1/4 across, 1/2 down
    assert abs(u - 0.0625) < 1e-9 and abs(v - 0.625) < 1e-9
    assert (u, v) not in uvmap.values()


def test_plan_rim_spares_the_shore_system(monkeypatch):
    """THE SHORE SCOPE: inside a live shore system sea4 lawfully runs UNDER the shallow
    bands (sea4-under-land), so tile-local deep arithmetic false-flags lawful ladder
    tiles -- the interior seam rules apply only away from shore. A sea3 patch tile with
    LAND in its 8-neighbourhood is spared; the open-water side of the same patch is
    still planned (the genuine crop-seam class)."""
    shade_g = [["sea4"] * RR.G for _ in range(RR.G)]
    for i in (6, 7, 8):
        for j in (6, 7, 8):
            shade_g[i][j] = "sea3"
    water_g = [[True] * RR.G for _ in range(RR.G)]
    water_g[5][6] = False                        # land west of the patch's NW corner
    monkeypatch.setattr(RR, "_grids",
                        lambda cells: ({(5, 5): shade_g}, {(5, 5): water_g}))
    monkeypatch.setattr(RR, "_sea5_deepsets", lambda parts: {})
    plan = RR.plan_rim({(5, 5): {}})
    got = set(plan.get((5, 5), {}))
    assert (6, 6) not in got and (6, 7) not in got   # shore-adjacent: spared
    assert (8, 6) in got and (8, 8) in got           # open-water crop edge: planned


def _pinch_grids(sh_n, sh_e, sh_s, sh_w):
    """One sea5 cell at (7, 7) with the four named neighbour shades; everything wet."""
    shade_g = [["sea5"] * RR.G for _ in range(RR.G)]
    shade_g[7][6], shade_g[8][7] = sh_n, sh_e
    shade_g[7][8], shade_g[6][7] = sh_s, sh_w
    return {(5, 5): shade_g}, {(5, 5): [[True] * RR.G for _ in range(RR.G)]}


def test_representable_PASSES_THROUGH_every_wang_key():
    """The fold must be inert on the 12 keys the alphabet already has -- an over-eager
    normalizer would silently re-tile lawful quads."""
    shade, water = _pinch_grids("sea5", "sea5", "sea5", "sea5")
    for ds in W.DEEPSET2TILE:
        assert RR.representable(ds, shade, water, [(5, 5)], 5, 5, 7, 7) == ds
    assert RR.representable(frozenset(), shade, water, [(5, 5)], 5, 5, 7, 7) == frozenset()
    four = frozenset("NESW")                     # not a pinch: plan targets sea4, still refused
    assert RR.representable(four, shade, water, [(5, 5)], 5, 5, 7, 7) == four


def test_representable_folds_an_OPPOSITE_PINCH_onto_the_containing_triple():
    """THE OPPOSITE-PINCH RULE: EW/NS are not keys of DEEPSET2TILE at all, so NO harvest
    can ever cover them; stock ships the shape and resolves it 5/5 with a 3-deep tile
    CONTAINING the pair (never a 1-deep tip, which would be an UNDER -- the defect)."""
    assert frozenset("EW") not in W.DEEPSET2TILE and frozenset("NS") not in W.DEEPSET2TILE
    shade, water = _pinch_grids("sea5", "sea4", "sea5", "sea4")
    got = RR.representable(frozenset("EW"), shade, water, [(5, 5)], 5, 5, 7, 7)
    assert got in W.DEEPSET2TILE and frozenset("EW") < got      # representable AND a superset
    assert got == frozenset("ESW")                              # stock's 3:2 majority side
    shade, water = _pinch_grids("sea4", "sea5", "sea4", "sea5")
    got = RR.representable(frozenset("NS"), shade, water, [(5, 5)], 5, 5, 7, 7)
    assert got == frozenset("NSW") and frozenset("NS") < got


def test_representable_never_points_a_new_deep_quarter_at_SEA3():
    """The preferred side is skipped when it is sea3 -- adding a deep-facing quarter
    toward shallow sea3 is the exact adjacency this operator exists to remove."""
    shade, water = _pinch_grids("sea5", "sea4", "sea3", "sea4")   # S is sea3, N is sea5
    assert RR.representable(frozenset("EW"), shade, water, [(5, 5)], 5, 5, 7, 7) \
        == frozenset("ENW")
    shade, water = _pinch_grids("sea4", "sea5", "sea4", "sea3")   # W is sea3, E is sea5
    assert RR.representable(frozenset("NS"), shade, water, [(5, 5)], 5, 5, 7, 7) \
        == frozenset("ENS")


def test_plan_rim_folds_the_pinch_so_uncovered_stops_refusing(monkeypatch):
    """End to end: an opposite-pinched frame quad used to make `uncovered` refuse the whole
    retile (the horseshoe carry, 2026-08-05); it now plans a tile the vocabulary has."""
    shade, water = _pinch_grids("sea5", "sea4", "sea5", "sea4")
    monkeypatch.setattr(RR, "_grids", lambda cells: (shade, water))
    monkeypatch.setattr(RR, "_sea5_deepsets", lambda parts: {})
    plan = RR.plan_rim({(5, 5): {}})
    assert plan[(5, 5)][(7, 7)][1] == frozenset("ESW")
    have = {tuple(o): {} for ds in W.DEEPSET2TILE for o in W.DEEPSET2TILE[ds]}
    assert RR.uncovered(plan, have) == []
    # and the raw geometry still reads EW, so seam_report scores it honestly as an OVER
    assert RR.deepset(shade, water, [(5, 5)], 5, 5, 7, 7) == frozenset("EW")
