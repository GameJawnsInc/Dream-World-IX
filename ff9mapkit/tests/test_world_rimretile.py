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
