"""The census's per-triangle precompute (PERF.md 5, P1): ``placement.census`` sky-casts 576 samples and asked each
candidate triangle, at every sample, what depends on the triangle alone -- its IDALL and skip, its walkable normal,
its barycentric denominator. 40% of a forest Check (24 censuses). Each is now computed once per census, with the
same expressions on the same operands, so the verdicts are the same floats.

Hermetic: every mesh is synthesized (``test_world_placement_order``'s builders).
"""
from __future__ import annotations

import math

from ff9mapkit.world import placement as P

from .test_world_placement_order import GRASS, _bm, _grid


def _stack():
    """A grass grid, a lid over part of it (a stacked sheet), and tris the filters drop: an IDALL_SKIP, a VETO, a
    steep wall, a degenerate sliver and a down-facing one -- each placed where samples land."""
    lid = [(((8.0, 9.0, -8.0), (40.0, 9.0, -8.0), (8.0, 9.0, -40.0)), GRASS)]
    odd = [(((20.0, 12.0, -20.0), (30.0, 12.0, -20.0), (20.0, 12.0, -30.0)), 4078),          # IDALL_SKIP
           (((44.0, 11.0, -44.0), (60.0, 11.0, -44.0), (44.0, 11.0, -60.0)), P.VETO),        # flight-only
           (((2.0, 0.0, -50.0), (2.0, 30.0, -50.0), (20.0, 0.0, -50.0)), GRASS),             # a wall
           (((5.0, 14.0, -5.0), (6.0, 14.0, -5.0), (7.0, 14.0, -5.0)), GRASS),               # degenerate in plan
           (((50.0, 13.0, -10.0), (50.0, 13.0, -30.0), (60.0, 13.0, -10.0)), GRASS)]         # faces down
    return [("Object", _bm(lid + odd, name="Block[0][0] Object")), ("Terrain", _grid(GRASS, 3.2))]


class _CountingMath:
    """placement's ``math``, counting ``sqrt`` (each candidate triangle's normal length): the name swapped, never the
    process-wide module."""

    def __init__(self):
        self.sqrt_calls = 0

    def sqrt(self, v):
        self.sqrt_calls += 1
        return math.sqrt(v)

    def __getattr__(self, name):
        return getattr(math, name)


def test_a_census_judges_each_triangle_s_own_tests_once(monkeypatch):
    stack = _stack()
    tris = sum(len(bm.tris) for _, bm in stack)
    m = _CountingMath()
    monkeypatch.setattr(P, "math", m)
    P.census(stack, samples=24)
    assert 0 < m.sqrt_calls <= tris                  # once per triangle, not once per candidate per sample


def test_the_precomputed_census_is_the_census(monkeypatch):
    """Every sample's ground, sheets, stacks and inversions are those of the per-sample code (the precompute off)."""
    stack = _stack()
    fast = P.census(stack, samples=24)
    assert fast["stacked"] and fast["counts"]        # the fixture exercises the stacked-sheet census
    prep = P._prepare(stack)
    for x, z in ((24.0, -24.0), (25.0, -25.0), (52.0, -52.0), (10.0, -50.0), (55.0, -15.0), (5.5, -5.0), (1.0, -1.0)):
        for strict in (True, False):
            assert P.all_sheets(stack, x, z, strict=strict, prep=prep) == P.all_sheets(stack, x, z, strict=strict)
        assert P.place(stack, x, z, prep=prep) == P.place(stack, x, z)
    monkeypatch.setattr(P, "_prepare", lambda meshlist: None)
    assert P.census(stack, samples=24) == fast


def test_a_mesh_without_tangents_is_asked_only_where_a_sample_lands(monkeypatch):
    """The precompute judged every triangle of every mesh up front, so a mesh with no tangent channel (no IDALL)
    raised even where no sample touches it -- a census the per-sample code ran raised (review of the perf commits).
    Such a mesh keeps the per-sample code: it raises only where a sample lands on it, as before."""
    from ff9mapkit.world.extract import CH_TAN
    stack = _stack()
    bare = _bm([(((200.0, 5.0, -200.0), (210.0, 5.0, -200.0), (200.0, 5.0, -210.0)), GRASS)], name="Block[0][0] Object")
    del bare.chan_arrays[CH_TAN]                                      # off the sampled span, and no IDALL
    del bare.channels[CH_TAN]
    stack = [("Object", bare), stack[1]]
    monkeypatch.setattr(P, "_prepare", lambda meshlist, real=P._prepare: real(meshlist))
    fast = P.census(stack, samples=12)
    monkeypatch.setattr(P, "_prepare", lambda meshlist: None)
    assert P.census(stack, samples=12) == fast
