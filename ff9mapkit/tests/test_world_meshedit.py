"""world.meshedit -- the coast-edit primitives that built the Path D V-shore corner.

Hermetic: synthetic geometry only, no game install and no extracted templates, so these
actually RUN in a fresh worktree rather than skipping (the worktree skip trap is how a
black screen once reached a playtest).

Every law in the module gets a test that FAILS when the law is removed -- a green suite
that cannot fail is the recurring defect class here, so each law is exercised from BOTH
sides: the lawful case passes, and the falsified alternative is shown to be caught.
"""
from __future__ import annotations

import math

import pytest

from ff9mapkit.world import meshedit as ME


# a gentle synthetic shore running roughly south, land to the east
SHORE = [(0.0, 0.0), (1.0, -4.0), (1.6, -8.2), (1.2, -12.4), (2.4, -16.0)]


def _sweep(**kw):
    opts = dict(top_y=3.2, u_start=0.80, foot_offset=0.94, seg_max=2.0)
    opts.update(kw)
    return ME.sweep_wall(SHORE, **opts)


# ------------------------------------------------------------------ helpers
def test_seaward_is_right_of_travel_and_unit():
    s = ME.seaward((0.0, 0.0), (0.0, -1.0))       # heading south
    assert math.isclose(math.hypot(*s), 1.0, rel_tol=1e-12)
    assert s[0] < 0                                # sea to the west
    with pytest.raises(ValueError):
        ME.seaward((1.0, 1.0), (1.0, 1.0))


def test_densify_bounds_every_segment_and_keeps_the_line():
    out = ME.densify([(0.0, 0.0), (0.0, -10.0)], 2.0)
    assert len(out) == 6
    assert all(abs(p[0]) < 1e-12 for p in out)     # collinear: shape untouched
    for a, b in zip(out, out[1:]):
        assert math.dist(a, b) <= 2.0 + 1e-9
    assert out[0] == (0.0, 0.0) and out[-1] == (0.0, -10.0)


def test_miter_offset_keeps_the_offset_distance_on_both_legs():
    chain = [(0.0, 0.0), (0.0, -4.0), (3.0, -7.0)]
    off = ME.miter_offset(chain, 1.0)
    # the mitred interior point must sit 1.0 from BOTH adjacent segment lines
    for a, b in ((chain[0], chain[1]), (chain[1], chain[2])):
        s = ME.seaward(a, b)
        d = (off[1][0] - a[0]) * s[0] + (off[1][1] - a[1]) * s[1]
        assert math.isclose(d, 1.0, abs_tol=1e-9)


def test_miter_offset_refuses_a_180_degree_reversal():
    with pytest.raises(ValueError, match="reversal"):
        ME.miter_offset([(0.0, 0.0), (0.0, -4.0), (0.0, 0.0)], 1.0)


# ------------------------------------------ THE FLOW CONSTRAINT / JOINT-KINK
def test_seat_transform_is_rigid_and_lands_on_the_target_chord():
    seat = ME.seat_transform((0.0, 0.0), (0.0, -10.0), (5.0, -5.0), (12.0, -12.0))
    assert math.dist(seat((0.0, 0.0)), (5.0, -5.0)) < 1e-9
    assert math.dist(seat((0.0, -10.0)), (12.0, -12.0)) < 1e-9
    # uniform scale: a donor-space distance scales by exactly `scale`
    d_donor = math.dist((0.0, -2.0), (1.0, -6.0))
    d_seated = math.dist(seat((0.0, -2.0)), seat((1.0, -6.0)))
    assert math.isclose(d_seated, d_donor * seat.scale, rel_tol=1e-12)


def test_flow_constraint_accepts_the_lawful_window_and_rejects_below_135():
    assert ME.flow_ok([160.0, 180.0, 201.0])
    assert not ME.flow_ok([160.0, 130.9])          # the falsified 125 relaxation
    assert ME.FLOW_MIN_HEADING == 135.0


def test_flow_constraint_catches_the_window_the_hug_gate_rejected():
    # the (20,15) donor: seats with a 130.9 entry -- caught at the joint in game terms
    seg = [(0.0, 0.0), (2.0, -1.7), (1.6, -4.2), (-0.6, -7.6)]
    h = ME.seated_headings(seg, (0.0, 0.0), (2.0, -9.0))
    assert not ME.flow_ok(h)


def test_joint_kinks_measure_both_welds():
    kin, kout = ME.joint_kinks([158.3, 162.5, 156.3], 159.6, 158.7)
    assert kin < ME.KINK_MAX and kout < ME.KINK_MAX
    kin2, _ = ME.joint_kinks([231.0], 159.6, 159.6)
    assert kin2 > 60.0                             # the disconnected-slab class


# -------------------------------------------------------- THE TUCK VOCABULARY
def test_sweep_wall_is_walk_visible_with_the_foot_seaward():
    w = _sweep()
    assert w.tris
    for p3, _uv in w.tris:
        assert ME._up_ny(*p3) > 0.1                # no membrane needed
    ys = {round(p[1], 6) for p3, _ in w.tris for p in p3}
    assert ys == {3.2, 0.0}                        # crest at the lawn, foot at water


def test_sweep_wall_seals_the_sightline_by_construction():
    """Foot SEAWARD of the crest is what removes the apron and the curtain.

    A ray arriving from seaward is above the face at the foot line (opaque sea below)
    and the face rises to meet the lawn, so it must hit wall or lawn.
    """
    w = _sweep()
    for p3, _uv in w.tris:
        crest = [p for p in p3 if p[1] > 1.6]
        foot = [p for p in p3 if p[1] <= 1e-9]
        if not crest or not foot:
            continue
        a, b = crest[0], foot[0]
        i = min(range(len(SHORE) - 1),
                key=lambda k: math.dist(((SHORE[k][0] + SHORE[k + 1][0]) / 2,
                                         (SHORE[k][1] + SHORE[k + 1][1]) / 2),
                                        (a[0], a[2])))
        s = ME.seaward(SHORE[i], SHORE[i + 1])
        assert (b[0] - a[0]) * s[0] + (b[2] - a[2]) * s[1] > 0.5


def test_sweep_wall_rejects_an_overhang_profile():
    """THE OVERHANG-CONTEXT LAW at the call site: a foot INLAND is refused."""
    with pytest.raises(ValueError, match="walk-visible"):
        _sweep(foot_offset=-0.94)


def test_sweep_wall_holds_the_bench_texel_density_everywhere():
    w = _sweep(u_end=0.71)
    for p3, uv3 in w.tris:
        assert ME.texel_density(p3, uv3) < 2.0 * ME.URATE


def test_sweep_wall_keeps_uv_inside_the_band_across_a_wrap():
    lo, hi = ME.ROCK_BAND
    w = _sweep(u_start=0.93, u_end=0.75)           # forces a band wrap
    assert w.wrap_splits >= 1
    for _p3, uv3 in w.tris:
        for u, v in uv3:
            assert lo - 1e-9 <= u <= hi + 1e-9
            assert v in (ME.V_TOP, ME.V_BOT)


def test_sweep_wall_density_gate_catches_a_mishandled_wrap():
    """The picket-fence streak: a whole band compressed into one face."""
    p3 = [(0.0, 3.2, 0.0), (3.9, 3.2, 0.0), (0.0, 0.0, 0.94)]
    uv3 = [(0.9252, ME.V_TOP), (0.7277, ME.V_TOP), (0.9252, ME.V_BOT)]
    assert ME.texel_density(p3, uv3) > 2.0 * ME.URATE


def test_sweep_wall_publishes_rungs_that_cover_the_whole_run():
    """DENSIFY FIRST: the lawn must be able to share exactly these vertices."""
    w = _sweep(u_start=0.93, u_end=0.75)
    assert len(w.rungs) >= len(ME.densify(SHORE, 2.0))
    assert math.dist(w.rungs[0], SHORE[0]) < 1e-9
    assert math.dist(w.rungs[-1], SHORE[-1]) < 1e-9
    for a, b in zip(w.rungs, w.rungs[1:]):
        assert math.dist(a, b) <= 2.0 + 1e-6


def test_sharing_the_rungs_is_what_removes_the_boundary_tjunctions():
    """The failure this law prevents, shown from both sides."""
    w = _sweep(u_start=0.93, u_end=0.75)
    inland = [(p[0] + 6.0, p[1]) for p in SHORE]
    # (a) lawn built on the COARSE chain: the wall's extra rungs are T-junctions
    coarse = ME.earclip(list(SHORE) + list(reversed(inland)))
    coarse_tris = [tuple((p[0], p[1]) for p in t) for t in coarse]
    assert ME.find_tjunctions(coarse_tris, ext_verts=w.rungs)
    # (b) lawn built on the SHARED rungs: none
    shared = ME.earclip(list(w.rungs) + list(reversed(inland)))
    shared_tris = [tuple((p[0], p[1]) for p in t) for t in shared]
    assert not [h for h in ME.find_tjunctions(shared_tris, ext_verts=w.rungs)
                if h[3] < 1e-6]


def test_sweep_wall_anchors_its_feet_to_the_kept_welds():
    w = _sweep(foot_anchor_a=(-0.5, 0.0, 0.1), foot_anchor_b=(1.0, 0.0, -16.5))
    feet = [p for p3, _ in w.tris for p in p3 if p[1] <= 1e-9]
    assert any(math.dist(p, (-0.5, 0.0, 0.1)) < 1e-9 for p in feet)
    assert any(math.dist(p, (1.0, 0.0, -16.5)) < 1e-9 for p in feet)


# --------------------------------------------------------------- the gap cover
def test_earclip_covers_a_simple_ring_exactly_once():
    ring = [(0.0, 0.0), (4.0, 0.0), (4.0, -4.0), (0.0, -4.0)]
    tris = ME.earclip(ring)
    assert len(tris) == 2
    area = sum(abs(ME._cross(*t)) / 2.0 for t in tris)
    assert math.isclose(area, 16.0, rel_tol=1e-9)


def test_cover_gap_refines_until_the_paint_is_clean():
    """A patch with no clean donor is too big, not doomed."""
    ring = [(0.0, 0.0), (8.0, 0.0), (8.0, -8.0), (0.0, -8.0)]

    def uv_at(p, sh):
        return (p[0] * 0.01 + sh, p[1] * 0.01)

    def is_clean(uv3):                              # big footprints hit "poison"
        span = max(u for u, _ in uv3) - min(u for u, _ in uv3)
        return span < 0.03

    out = ME.cover_gap(ring, uv_at=uv_at, shifts=[0.0], is_clean=is_clean,
                       min_edge=0.05)
    assert len(out) > 2
    for tri, sh in out:
        assert is_clean([uv_at(p, sh) for p in tri])


def test_cover_gap_scores_tone_against_the_neighbourhood_not_the_donor():
    """THE WRONG REFERENCE: the meadow-triangle class."""
    ring = [(0.0, 0.0), (2.0, 0.0), (2.0, -2.0), (0.0, -2.0)]
    palette = {0: (200.0, 200.0, 120.0), 1: (95.0, 110.0, 55.0)}

    def uv_at(p, sh):
        return (p[0] * 0.001 + sh, p[1] * 0.001)

    out = ME.cover_gap(
        ring, uv_at=uv_at, shifts=[0, 1], is_clean=lambda uv3: True,
        tone=lambda uv3: palette[0] if uv3[0][0] < 0.5 else palette[1],
        ref_tone=lambda cen: (93.0, 108.0, 54.0))
    assert out and all(sh == 1 for _t, sh in out)   # the tonal match, not the first


def test_cover_gap_never_splits_a_shared_ring_edge():
    ring = [(0.0, 0.0), (8.0, 0.0), (8.0, -8.0), (0.0, -8.0)]
    shared = {((0.0, 0.0), (8.0, 0.0))}

    def on_ring(a, b):
        return (tuple(a), tuple(b)) in shared or (tuple(b), tuple(a)) in shared

    out = ME.cover_gap(ring, uv_at=lambda p, sh: (p[0] * 0.01, p[1] * 0.01),
                       shifts=[0], is_clean=lambda uv3: False, on_ring=on_ring,
                       min_edge=0.05)
    for tri, _sh in out:                            # the shared edge survives whole
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if on_ring(a, b):
                assert math.isclose(math.dist(a, b), 8.0, rel_tol=1e-9)


# ----------------------------------------------------------------- T-junctions
def test_find_tjunctions_sees_what_a_weld_audit_cannot():
    a = ((0.0, 0.0), (4.0, 0.0), (0.0, -4.0))
    b = ((4.0, 0.0), (2.0, 0.0), (4.0, -4.0))       # (2,0) sits inside a's edge
    hits = ME.find_tjunctions([a, b])
    assert any(h[0] == (2.0, 0.0) for h in hits)
    # ... and no near-MISS duplicate pair exists for an audit to catch
    verts = [p for t in (a, b) for p in t]
    for i in range(len(verts)):
        for j in range(i + 1, len(verts)):
            d = math.dist(verts[i], verts[j])
            assert d == 0 or d > 0.05


def test_repair_tjunctions_closes_them_and_carries_the_payload():
    a = ((0.0, 0.0), (4.0, 0.0), (0.0, -4.0))
    b = ((4.0, 0.0), (2.0, 0.0), (4.0, -4.0))
    out, rounds = ME.repair_tjunctions([(a, "A"), (b, "B")])
    assert rounds >= 0
    assert not ME.find_tjunctions([t for t, _ in out], eps=1e-4)
    assert {pl for _t, pl in out} == {"A", "B"}     # splits inherit their parent


def test_repair_tjunctions_uses_neighbour_vertices_we_cannot_re_cut():
    tri = ((0.0, 0.0), (4.0, 0.0), (0.0, -4.0))
    out, _ = ME.repair_tjunctions([(tri, None)], ext_verts=[(2.0, 0.0)])
    assert len(out) == 2
    assert any((2.0, 0.0) in t for t, _ in out)


def test_repair_refuses_a_loose_tolerance_because_that_opens_a_hole():
    """A repair that is not exact is a hole -- measured: 26 px of background."""
    tri = ((0.0, 0.0), (4.0, 0.0), (0.0, -4.0))
    with pytest.raises(ValueError, match="too loose"):
        ME.repair_tjunctions([(tri, None)], ext_verts=[(2.0, 0.0025)],
                             exact_eps=2.5e-3)


def test_a_near_but_not_exact_split_would_leave_a_measurable_gap():
    """Why the tolerance above is refused, demonstrated geometrically."""
    off = 2.5e-3
    a, b, w = (0.0, 0.0), (4.0, 0.0), (2.0, off)
    child_area = abs(ME._cross(a, w, (0.0, -4.0))) / 2 + abs(ME._cross(w, b, (0.0, -4.0))) / 2
    parent_area = abs(ME._cross(a, b, (0.0, -4.0))) / 2
    assert abs(child_area - parent_area) > 1e-4     # the sliver gap, not a repair


# --------------------------------------------------------------------- excise
# Registration: studies/coast-shape-language/EXCISE-PREDICTION.md

def _quad(x0, z0, x1, z1, y=0.0):
    """Two tris covering an axis-aligned rect, wound consistently."""
    def v(x, z):
        return ((x, y, z), (0.0, 1.0, 0.0), (0.0, 0.0), (228.0, 0.0, 0.0, 1.0))
    return [[v(x0, z0), v(x1, z0), v(x1, z1)], [v(x0, z0), v(x1, z1), v(x0, z1)]]


def test_vertex_components_separates_masses_that_share_no_vertex():
    a = _quad(0, 0, 4, 4)
    b = _quad(100, 0, 104, 4)
    comps = ME.vertex_components(a + b)
    assert len(comps) == 2
    assert sorted(len(c) for c in comps) == [2, 2]


def test_vertex_components_keeps_masses_that_touch_together():
    """Sharing ONE vertex is enough to be one mass -- the drop set must not split it."""
    a = _quad(0, 0, 4, 4)
    b = _quad(4, 4, 8, 8)                       # shares exactly the corner (4,0,4)
    assert len(ME.vertex_components(a + b)) == 1


def test_boundary_cycles_finds_a_hole_as_its_own_ring():
    """A sheet with a hole has TWO cycles: outer frame and the hole."""
    tris = []
    for x in range(0, 12, 4):
        for z in range(0, 12, 4):
            if (x, z) == (4, 4):                # punch the middle cell
                continue
            tris += _quad(x, z, x + 4, z + 4)
    rings = ME.boundary_cycles(tris)
    assert len(rings) == 2, [len(r) for r in rings]
    inner = rings[1]
    xs = [p[0] for p in inner]
    zs = [p[2] for p in inner]
    assert (min(xs), max(xs), min(zs), max(zs)) == (4.0, 8.0, 4.0, 8.0)


def test_boundary_cycles_does_not_merge_two_holes_at_a_junction_vertex():
    """THE JUNCTION FAULT, from both sides.

    Connected components of the boundary GRAPH merge two disjoint cycles that share a
    single vertex. That error made a real donor rect report "no island hole" when 132 of
    its 218 boundary verts traced island coast. Cycles must be consumed as EDGES.
    """
    tris = []
    for x in range(0, 16, 4):
        for z in range(0, 16, 4):
            if (x, z) in ((4, 4), (8, 8)):      # two holes meeting at corner (8,8)
                continue
            tris += _quad(x, z, x + 4, z + 4)
    rings = ME.boundary_cycles(tris)
    assert len(rings) == 3, [len(r) for r in rings]      # frame + TWO holes, not one
    # and a graph-component tracer would have reported 2 -- shown here explicitly
    import collections
    cnt = collections.Counter()
    for t in tris:
        k = [tuple(round(c, 4) for c in v[0]) for v in t]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            cnt[tuple(sorted((k[i], k[j])))] += 1
    adj = collections.defaultdict(set)
    for (p, q), c in cnt.items():
        if c == 1:
            adj[p].add(q)
            adj[q].add(p)
    seen, groups = set(), 0
    for s in adj:
        if s in seen:
            continue
        groups += 1
        stack = [s]
        seen.add(s)
        while stack:
            for w in adj[stack.pop()]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
    assert groups == 2                                   # the fault, reproduced


def test_flat_patch_reuses_ring_vertices_exactly():
    """A REPAIR THAT IS NOT EXACT IS A HOLE -- the patch must add no boundary vertex."""
    ring = [(4.0, 0.0, 4.0), (8.0, 0.0, 4.0), (8.0, 0.0, 8.0), (4.0, 0.0, 8.0)]
    tris = ME.flat_patch(ring, y=0.0, uv_quads=[(0.0, 0.0, 0.5039, 0.5079)], idall=228)
    src = {(round(p[0], 9), round(p[2], 9)) for p in ring}
    for t in tris:
        for v in t:
            assert (round(v[0][0], 9), round(v[0][2], 9)) in src


def test_flat_patch_is_planar_and_carries_the_idall():
    ring = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (8.0, 0.0, 8.0), (0.0, 0.0, 8.0)]
    tris = ME.flat_patch(ring, y=0.0, uv_quads=[(0.0, 0.0, 0.5039, 0.5079),
                                                (0.5039, 0.0, 0.9921, 0.5079)],
                         idall=228)
    assert tris
    for t in tris:
        for v in t:
            assert v[0][1] == 0.0
            assert int(v[3][0]) == 228


def test_flat_patch_uv_stays_inside_its_quadrant():
    """Free tile choice is not free tile ABUSE: a quad's uv must stay in that quad."""
    q = (0.5039, 0.5079, 0.9921, 1.0)
    ring = [(0.0, 0.0, 0.0), (12.0, 0.0, 0.0), (12.0, 0.0, 12.0), (0.0, 0.0, 12.0)]
    for t in ME.flat_patch(ring, y=0.0, uv_quads=[q], idall=228):
        for v in t:
            assert q[0] - 1e-9 <= v[2][0] <= q[2] + 1e-9
            assert q[1] - 1e-9 <= v[2][1] <= q[3] + 1e-9


def test_flat_patch_refuses_an_empty_quadrant_list():
    with pytest.raises(ValueError, match="uv quadrant"):
        ME.flat_patch([(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 0.0, 4.0)],
                      y=0.0, uv_quads=[], idall=228)


def test_boundary_cycles_emits_exact_floats_not_its_rounding_keys():
    """NEVER HAND-ROUND GEOMETRY -- round to KEY, emit the exact float.

    Real donor verts are off-lattice floats like 394.003906. A ring that carried the
    4-decimal key 394.0039 instead landed 4e-6 away: identical to the eye, and 16
    near-miss pairs to the hairline-crack gate, which is the exact defect class the
    beach-end saga traced to hand-rounded coordinates.
    """
    x = 394.003906                                   # a real off-lattice donor x
    tris = _quad(x, 0.0, x + 4.0, 4.0)
    ring = ME.boundary_cycles(tris)[0]
    assert any(abs(p[0] - x) < 1e-12 for p in ring), ring
    for p in ring:                                   # nothing may be the rounded key
        assert not (0 < abs(p[0] - x) < 1e-3)


def _plan_cross(t):
    a, b, c = [(v[0][0], v[0][2]) for v in t]
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


def test_flat_patch_matches_the_requested_winding():
    """A patch wound the wrong way renders but is BACK-FACING to the ground raycast.

    Measured: all 1025 stock sea4 tris in a donor rect wind negative; an otherwise-exact
    fill wound positive scored 73 introduced census misses -- it looked like ocean and
    registered as void.
    """
    ring = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (8.0, 0.0, 8.0), (0.0, 0.0, 8.0)]
    q = [(0.0, 0.0, 0.5039, 0.5079)]
    neg = ME.flat_patch(ring, y=0.0, uv_quads=q, idall=228, winding=-1.0)
    pos = ME.flat_patch(ring, y=0.0, uv_quads=q, idall=228, winding=1.0)
    assert neg and pos
    assert all(_plan_cross(t) < 0 for t in neg)
    assert all(_plan_cross(t) > 0 for t in pos)


def test_flat_patch_winding_is_independent_of_ring_orientation():
    """Reversing the input ring must not flip the output -- else the caller must guess."""
    fwd = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (8.0, 0.0, 8.0), (0.0, 0.0, 8.0)]
    q = [(0.0, 0.0, 0.5039, 0.5079)]
    for ring in (fwd, list(reversed(fwd))):
        for t in ME.flat_patch(ring, y=0.0, uv_quads=q, idall=228, winding=-1.0):
            assert _plan_cross(t) < 0
