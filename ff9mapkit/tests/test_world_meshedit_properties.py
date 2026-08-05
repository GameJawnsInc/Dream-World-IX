"""Hypothesis properties on meshedit's triangulators (audit rec 18) -- meshedit ONLY.

This layer is 100% offline (zero skipif), so property tests land in public CI and add no
install-gated surface. The properties are guard-rails on the silent-failure classes with a
real defect behind them -- the coast-mosaic RING-CONFORMITY LAW's concave-corner notch-quad
shipped ONE missing face past a sampled-holes gate -- not look-correctness (gates are not
oracles; 0-of-13). Deliberately NOT extended into transplant/coastmorph: test surface is
not free here (DEFECT FOLLOWS AUTHORSHIP), and those layers are exercised through their own
byte-grounded suites.

Rings are integer-lattice, star-shaped by construction (angular sort about the centroid --
simple by construction, no rejection loop), with duplicate angles assumed away.
"""
from __future__ import annotations

import math

import pytest

hyp = pytest.importorskip("hypothesis")
from hypothesis import assume, given, settings, strategies as st  # noqa: E402

from ff9mapkit.world import meshedit as ME  # noqa: E402


def _shoelace2(ring) -> float:
    return sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
               - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))


@st.composite
def lattice_rings(draw):
    pts = draw(st.lists(st.tuples(st.integers(0, 12), st.integers(0, 12)),
                        min_size=4, max_size=10, unique=True))
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    angs = sorted((math.atan2(p[1] - cz, p[0] - cx), p) for p in pts)
    assume(len({round(a, 12) for a, _ in angs}) == len(angs))    # no duplicate angles
    ring = [(float(p[0]), float(p[1])) for _, p in angs]
    assume(abs(_shoelace2(ring)) > 1e-9)                         # non-degenerate area
    return ring


@settings(max_examples=60, deadline=None)
@given(lattice_rings())
def test_every_ring_edge_appears_in_the_triangulation(ring):
    """THE RING-CONFORMITY property -- the one with a shipped defect behind it: a
    triangulation of a simple polygon must contain every boundary edge; the notch-quad
    diagonal that dropped one face would fail exactly here."""
    tris = ME.earclip(ring)
    edges = {frozenset((tri[a], tri[b])) for tri in tris
             for a, b in ((0, 1), (1, 2), (2, 0))}
    for i in range(len(ring)):
        e = frozenset((ring[i], ring[(i + 1) % len(ring)]))
        assert e in edges, f"boundary edge {sorted(e)} missing from the triangulation"


@settings(max_examples=60, deadline=None)
@given(lattice_rings())
def test_plan_area_is_conserved(ring):
    tris = ME.earclip(ring)
    tri_area = sum(abs(_shoelace2(t)) for t in tris) / 2.0
    assert abs(tri_area - abs(_shoelace2(ring)) / 2.0) < 1e-9


@settings(max_examples=60, deadline=None)
@given(lattice_rings())
def test_no_output_vertex_is_off_the_ring(ring):
    tris = ME.earclip(ring)
    assert {p for t in tris for p in t} <= set(ring)


@settings(max_examples=60, deadline=None)
@given(lattice_rings(), st.sampled_from([-1.0, 1.0]))
def test_flat_patch_winding_matches_the_requested_sign(ring, winding):
    """flat_patch reuses ring vertices EXACTLY (its off-ring raise must never fire on a
    valid ring) and orients every emitted triangle to the requested winding sign -- the
    SEA-SHEET LAW's failure mode (wrong winding renders and is void) as a property."""
    ring3 = [(x, 0.0, z) for (x, z) in ring]
    polys = ME.flat_patch(ring3, y=0.0, uv_quads=[(0.0, 0.0, 0.5, 0.5)], idall=232,
                          winding=winding)
    assert polys, "a non-degenerate ring must yield at least one triangle"
    for poly in polys:
        (ax, _, az), (bx, _, bz), (cx2, _, cz2) = (v[0] for v in poly)
        cross = (bx - ax) * (cz2 - az) - (cx2 - ax) * (bz - az)
        assert cross * winding >= 0, f"triangle wound against the requested sign {winding}"
