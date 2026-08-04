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


# --------------------------------------------------- THE FAN LAW (border crack)
# Registration: studies/coast-shape-language/EXCISE-V2-PREDICTION.md (ATTEMPT 3).

#: The weld audit's near-miss tolerance -- two vertices closer than this are a crack
#: candidate. The fan defect put four pairs inside it.
WELD_TOL = 0.05

#: A ring with the STRUCTURE the excise fills carry: a run of collinear lattice
#: vertices, a long inlet leading away from it, and -- far round the ring -- an apex
#: sitting barely off the run's own line. Coordinates are invented; only the shape
#: class is borrowed. First-ear clipping eats the inlet, is then left with the run
#: adjacent to that apex, and fans it into slivers.
FAN_RING = [(24.0, -12.0), (24.0, -8.0), (24.0, -4.0), (24.0, 0.0),
            (20.0, 0.0), (16.0, 0.0), (12.0, 0.0),
            (12.0, 4.0), (8.0, 4.0), (4.0, 4.0), (4.0, 0.5), (0.0, 2.8),
            (-4.0, 2.4), (-8.0, 2.4), (-12.0, 6.1), (-14.9, 8.0), (-16.0, 9.1),
            (-20.0, 9.8), (-21.0, 8.0), (-22.0, 4.5), (-21.0, 0.0),
            (-16.8, -0.41), (-17.0, -4.41), (-20.0, -7.37), (-24.0, -6.5),
            (-24.0, -12.0)]


def _line_crossings(tris2, x):
    """Every distinct z where a plan triangulation's edges meet the vertical line ``x``.

    These are exactly the vertices the transplant's block-border re-partition mints when
    that line is a block border, so their spacing IS the weld audit's subject.
    """
    zs = set()
    for t in tris2:
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            if abs(a[0] - x) < 1e-12:
                zs.add(round(a[1], 9))
            elif (a[0] - x) * (b[0] - x) < 0:
                s = (x - a[0]) / (b[0] - a[0])
                zs.add(round(a[1] + s * (b[1] - a[1]), 9))
    return sorted(zs)


def _closest_crossing(tris2, lines):
    """The smallest gap between two crossings on any of ``lines`` (inf if never two)."""
    worst = math.inf
    for x in lines:
        zs = _line_crossings(tris2, x)
        for lo, hi in zip(zs, zs[1:]):
            worst = min(worst, hi - lo)
    return worst


#: block borders are 64u apart and every shift is 0-mod-4, so a re-partition plane always
#: lands on the 4u lattice -- score the whole family rather than guessing which one.
FAN_LINES = [float(x) for x in range(-24, 25, 4)]


def test_earclip_first_ear_fans_a_collinear_run_into_slivers():
    """THE WITNESS. Without this the fix looks like a no-op refactor.

    A collinear vertex can never be an ear (its cross product is zero), so a run survives
    until its neighbourhood is eaten and is then triangulated against whatever distant
    vertex is adjacent by then. The patch itself is still exact -- same ring vertices,
    same coverage -- and the defect only appears DOWNSTREAM, when the block-border
    re-partition mints a vertex per fan diagonal and two land inside the weld tolerance.
    """
    tris = ME.earclip(FAN_RING)                       # default: first valid ear
    assert _closest_crossing(tris, FAN_LINES) < WELD_TOL


def test_earclip_quality_keeps_every_diagonal_local():
    """THE FAN LAW: scoring ears by their smallest angle keeps the diagonals short."""
    tris = ME.earclip(FAN_RING, quality=True)
    assert _closest_crossing(tris, FAN_LINES) >= WELD_TOL


def test_earclip_quality_changes_diagonals_not_coverage():
    """Same polygon, same vertices, same area -- only the diagonals move."""
    base = ME.earclip(FAN_RING)
    good = ME.earclip(FAN_RING, quality=True)
    assert len(good) == len(base) == len(FAN_RING) - 2
    assert {tuple(p) for t in good for p in t} == {tuple(p) for p in FAN_RING}
    area = sum(abs(ME._cross(*t)) / 2.0 for t in base)
    assert math.isclose(sum(abs(ME._cross(*t)) / 2.0 for t in good), area, rel_tol=1e-9)
    assert good != base                               # it really did pick other ears


def test_flat_patch_opts_into_the_quality_earclip():
    """THE CALL SITE. The helper being capable is not the same as the fill spending it --
    a `quality=True` dropped here passes every earclip test and ships the crack back."""
    ring = [(p[0], 0.0, p[1]) for p in FAN_RING]
    tris = ME.flat_patch(ring, y=0.0, uv_quads=[(0.0, 0.0, 0.5039, 0.5079)], idall=228)
    plan = [tuple((v[0][0], v[0][2]) for v in t) for t in tris]
    assert _closest_crossing(plan, FAN_LINES) >= WELD_TOL


# ------------------------------------------------------- region-capable morphs
# Registration: studies/coast-shape-language/REGION-MORPH-PREDICTION.md

def test_region_frame_of_a_single_cell_is_that_cell():
    from ff9mapkit.world.coastmorph import CliffWindow
    assert CliffWindow.region_frame((7, 17)) == (448.0, 512.0, -1152.0, -1088.0)
    assert CliffWindow.region_frame((7, 17), (1, 1)) == CliffWindow.region_frame((7, 17))


def test_region_frame_spans_the_whole_rect_not_the_anchor_cell():
    """THE FRAME IS THE REGION'S. If this returned the anchor cell, every interior
    border would be treated as an outer frame and its base edges dropped -- the coast
    would be cut at each block line and no window could cross one."""
    from ff9mapkit.world.coastmorph import CliffWindow
    x0, x1, z0, z1 = CliffWindow.region_frame((7, 17), (4, 2))
    assert (x0, x1) == (448.0, 704.0)              # 4 cells wide, not 1
    assert (z0, z1) == (-1216.0, -1088.0)          # 2 cells tall
    # the interior borders must lie strictly INSIDE the frame, so they are not excluded
    for interior in (512.0, 576.0, 640.0):
        assert x0 < interior < x1


def test_region_frame_refuses_a_degenerate_size():
    from ff9mapkit.world.coastmorph import CliffWindow
    with pytest.raises(ValueError, match="at least 1x1"):
        CliffWindow.region_frame((7, 17), (0, 2))


def test_cliff_window_reads_every_cell_of_the_rect(monkeypatch):
    """The region READ, pinned through a seam so it runs without a game install.

    A mutation that put the read back to `range(dbx, dbx+1)` passed the whole hermetic
    suite -- the law was only exercised by live game data, which a fresh worktree does
    not have. Injecting the reader is the fix: never read the real file to test a rule.
    """
    from ff9mapkit.world import coastmorph as CM

    asked = []

    def fake_world_tris(bx, by, part, **kw):
        asked.append((bx, by, part))
        return []

    monkeypatch.setattr(CM.TR, "world_tris", fake_world_tris)
    with pytest.raises(ValueError, match="no topo-58 cliff band"):
        CM.CliffWindow((7, 17), (0.0, 0.0), (1.0, 1.0), size=(4, 2))

    cells = {(bx, by) for bx, by, _ in asked}
    assert cells == {(bx, by) for by in (17, 18) for bx in (7, 8, 9, 10)}, cells
    assert {p for _, _, p in asked} == {"terrain", "sea4"}


def test_cliff_window_single_cell_reads_only_that_cell(monkeypatch):
    from ff9mapkit.world import coastmorph as CM

    asked = []
    monkeypatch.setattr(CM.TR, "world_tris",
                        lambda bx, by, part, **kw: asked.append((bx, by)) or [])
    with pytest.raises(ValueError, match="no topo-58 cliff band"):
        CM.CliffWindow((7, 17), (0.0, 0.0), (1.0, 1.0))
    assert set(asked) == {(7, 17)}


# ---------------------------------------------- the ground source-family detection

def _mains_tri(u, v, topo=0):
    def vert():
        return ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (u, v), (float(topo), 0.0, 0.0, 1.0))
    return [vert(), vert(), vert()]


def test_mains_family_reads_the_dominant_family():
    """A donor with NO sand band used to default to grass whatever its mains said."""
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world.transplant import GroundRetile
    u0, v0, u1, v1 = G.ground_main_region("desert")
    mid = ((u0 + u1) / 2, (v0 + v1) / 2)
    tris = [_mains_tri(*mid) for _ in range(40)]
    assert GroundRetile._mains_family(tris, (9, 5)) == "desert"


def test_mains_family_refuses_an_ambiguous_donor():
    """G-4: a mixed landmass must REFUSE, not be guessed at."""
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world.transplant import GroundRetile
    tris = []
    for fam in ("desert", "snow"):
        u0, v0, u1, v1 = G.ground_main_region(fam)
        tris += [_mains_tri((u0 + u1) / 2, (v0 + v1) / 2) for _ in range(30)]
    with pytest.raises(ValueError, match="no dominant ground family"):
        GroundRetile._mains_family(tris, (0, 0))


def test_mains_family_falls_back_to_grass_when_there_are_no_mains():
    from ff9mapkit.world.transplant import GroundRetile
    assert GroundRetile._mains_family([], (0, 0)) == "grass"


def test_for_donor_uses_mains_detection_when_there_is_no_sand_band(monkeypatch):
    """The bug was in for_donor's FALLBACK, so testing _mains_family alone is not enough.

    A mutation restoring `else "grass"` passed every test until this one existed --
    the helper was covered, its call site was not.
    """
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world import transplant as TR

    u0, v0, u1, v1 = G.ground_main_region("desert")
    mid_u, mid_v = (u0 + u1) / 2, (v0 + v1) / 2

    def fake_world_tris(bx, by, part, **kw):
        if part != "terrain" or (bx, by) != (9, 5):
            return []
        v = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (mid_u, mid_v), (17.0, 0.0, 0.0, 1.0))
        return [[v, v, v] for _ in range(40)]

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    monkeypatch.setattr(CM, "_sand_band_family", lambda *a, **k: None)

    # a desert source hits the "grass->X only" gap, and the message names the family it
    # detected -- which is the observable proof that mains detection ran.
    with pytest.raises(ValueError, match="is desert"):
        TR.GroundRetile.for_donor((9, 5), "snow", strips="none")


# ------------------------------------------- excise: a waterline ON THE RECT FRAME

def _tri(pts, y=0.0, idall=228.0):
    return [((p[0], p[1] if len(p) > 2 else y, p[-1]), (0.0, 1.0, 0.0),
             (0.5, 0.5), (idall, 0.0, 0.0, 1.0)) for p in pts]


def test_excise_accepts_a_waterline_lying_on_the_rect_frame(monkeypatch):
    """v1 refused these as weld failures, blaming a shallow ladder it could not re-zip.

    Measured on the two rects it blocked -- Daguerreo (5,15)+3x2 and the sinuous island
    (3,11)+2x4 -- 39/39 and 41/41 of the weld-missing vertices lie EXACTLY on the rect
    frame, none is an interior hole, and none is welded to a kept assembly. A frame
    vertex has no sea4 partner INSIDE the rect and should not need one: beyond the frame
    is the neighbouring cell's ocean.
    """
    from ff9mapkit.world import transplant as TR

    # a kept island (interior, larger) and a foreign crumb touching the x=64 frame
    kept = [_tri([(10.0, -10.0), (20.0, -10.0), (15.0, -20.0)]),
            _tri([(10.0, -10.0), (15.0, -20.0), (8.0, -18.0)])]
    crumb = [_tri([(64.0, -10.0), (64.0, -20.0), (56.0, -15.0)])]
    # sea4 owns the crumb's INTERIOR waterline vertex (56,-15) -- as the real sheet does,
    # since that is where the excised mass welds to deep water -- but has NO vertex on the
    # x=64 frame, which is exactly the case v1 mistook for a ladder it could not re-zip.
    sea4 = [_tri([(0.0, 0.0), (40.0, 0.0), (56.0, -15.0)]),
            _tri([(0.0, 0.0), (56.0, -15.0), (0.0, -64.0)]),
            _tri([(0.0, -64.0), (56.0, -15.0), (40.0, -64.0)])]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    _tweaks, rep = TR.excise_plan((0, 0), (1, 1))

    assert rep["foreign"], "the frame-touching crumb should be excised"
    assert rep.get("frame_waterline", 0) > 0, "frame waterline verts should be counted"
    assert rep["weld_exact"] is True, rep.get("weld_missing")
    assert not rep.get("refused"), rep.get("refused")


def test_excise_still_refuses_a_genuine_interior_sheet_hole(monkeypatch):
    """The safety direction: relaxing the frame case must not let INTERIOR holes pass.

    Same fixture as above, except sea4 does NOT own the crumb's interior waterline vertex
    (56,-15). That is a real hole in the deep sheet -- the fill could not weld there --
    and it must still refuse. Without this, `_on_frame` returning True unconditionally
    passes every test while shipping unweldable fills.
    """
    from ff9mapkit.world import transplant as TR

    kept = [_tri([(10.0, -10.0), (20.0, -10.0), (15.0, -20.0)]),
            _tri([(10.0, -10.0), (15.0, -20.0), (8.0, -18.0)])]
    crumb = [_tri([(64.0, -10.0), (64.0, -20.0), (56.0, -15.0)])]
    sea4 = [_tri([(0.0, 0.0), (40.0, 0.0), (0.0, -64.0)]),
            _tri([(40.0, 0.0), (40.0, -64.0), (0.0, -64.0)])]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    _tweaks, rep = TR.excise_plan((0, 0), (1, 1))

    assert rep["weld_exact"] is False
    assert (56.0, 0.0, -15.0) in [tuple(v) for v in rep["weld_missing"]]
    assert "refused" in rep


# ---------------------------------------------------------------- THE LATTICE LAW

QUADS4 = ((0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5),
          (0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0))
#: an irregular ~20x16u ring seated off-lattice, ring verts off the 4u grid
LRING = [(1.3, 0.0, -1.7), (21.1, 0.0, -2.2), (22.4, 0.0, -14.9), (10.0, 0.0, -17.8),
         (0.6, 0.0, -13.1)]


def test_lattice_patch_no_triangle_spans_a_tile():
    """THE LATTICE LAW: stock sea4 is a strict 4u lattice (tri area max 10.5u2, edge max
    7u); the crescent's whole-footprint ear-clip minted 615u2 / 71.5u-edge triangles that
    the wave-animated sheet rendered as a faceted iceberg. Every emitted triangle must
    live inside ONE 4u cell."""
    out = ME.lattice_patch(LRING, y=0.0, uv_quads=QUADS4, idall=228)
    assert out
    for t in out:
        xs = [v[0][0] for v in t]
        zs = [v[0][2] for v in t]
        assert max(xs) - min(xs) <= 4.0 + 1e-6 and max(zs) - min(zs) <= 4.0 + 1e-6
        cellx = {math.floor((x - 1e-9) / 4.0) for x in xs if x - min(xs) > 1e-9}
        assert math.dist((min(xs), min(zs)), (max(xs), max(zs))) <= 5.66


def test_lattice_patch_full_tile_uv_spans_the_whole_quadrant():
    """The modulo-wrap defect: (x/4)%1 maps a lattice-aligned far edge back to 0, so a
    full tile's corners all collapse onto the quadrant corner -- one texel smeared over
    the tile (measured: 121 of 142 fill tiles read as one quadrant, adjacent-variation
    0.098 vs stock's 0.880). A full tile's uvs must span its full quadrant rect."""
    ring = [(0.0, 0.0, 0.0), (16.0, 0.0, 0.0), (16.0, 0.0, -16.0), (0.0, 0.0, -16.0)]
    out = ME.lattice_patch(ring, y=0.0, uv_quads=QUADS4, idall=228)
    by_cell = {}
    for t in out:
        c = (math.floor(sum(v[0][0] for v in t) / 3.0 / 4.0),
             math.floor(-sum(v[0][2] for v in t) / 3.0 / 4.0))
        by_cell.setdefault(c, []).append(t)
    assert len(by_cell) == 16
    for c, tris in by_cell.items():
        us = [v[2][0] for t in tris for v in t]
        vs = [v[2][1] for t in tris for v in t]
        assert abs((max(us) - min(us)) - 0.5) < 1e-6, "u must span the quadrant"
        assert abs((max(vs) - min(vs)) - 0.5) < 1e-6, "v must span the quadrant"
        qs = {(min(us), min(vs))}
        assert len(qs) == 1                            # per-tile coherence


def test_lattice_patch_quadrants_spread_not_collapse():
    """The 1-vert fake-key defect: _tile_quad_index divides by a real centroid's 3, so a
    single-vertex key collapsed neighbouring cells onto one hash (quadrants 119/10/1/5).
    Over a 16x16-cell sheet every quadrant must appear substantially."""
    ring = [(0.0, 0.0, 0.0), (64.0, 0.0, 0.0), (64.0, 0.0, -64.0), (0.0, 0.0, -64.0)]
    out = ME.lattice_patch(ring, y=0.0, uv_quads=QUADS4, idall=228)
    from collections import Counter
    c = Counter()
    quad_of = {}
    for t in out:
        us = [v[2][0] for v in t]
        vs = [v[2][1] for v in t]
        q = (min(us) >= 0.5, min(vs) >= 0.5)
        c[q] += 1
        cell = (math.floor(sum(v[0][0] for v in t) / 3.0 / 4.0),
                math.floor(-sum(v[0][2] for v in t) / 3.0 / 4.0))
        quad_of[cell] = q
    assert len(c) == 4
    assert max(c.values()) / min(c.values()) <= 2.5    # the uv gate's own skew ceiling
    # ADJACENT variation, the statistic that actually caught the collapse: a key that
    # merges neighbouring cells makes runs of identical quadrants (measured 0.098 against
    # stock's 0.880; a 3-cell collapse still passes presence + skew at ~0.33)
    pairs = diff = 0
    for (gx, gz), q in quad_of.items():
        for nb in ((gx + 1, gz), (gx, gz + 1)):
            if nb in quad_of:
                pairs += 1
                diff += (quad_of[nb] != q)
    assert pairs and diff / pairs >= 0.5, f"adjacent-variation {diff}/{pairs} -- a lattice/collapsed key"


def test_lattice_patch_reuses_ring_verts_byte_exact_and_snaps_to_floats():
    """Two float laws in one fixture. Ring verts appear byte-exact (the weld contract),
    and a minted lattice crossing within snap_tol of an EXISTING sheet vertex lands on
    that vertex's EXACT float -- snapping onto a 4dp-rounded key mints the very
    0.00002u near-miss the snap exists to remove (measured on the crescent)."""
    ring = [(1.23456789, 0.0, -0.5), (9.87654321, 0.0, -0.5),
            (9.87654321, 0.0, -9.5), (1.23456789, 0.0, -9.5)]
    sheet_vert = (4.0001234567, -0.4998765)            # ~0.0002 off the x=4 crossing
    out = ME.lattice_patch(ring, y=0.0, uv_quads=QUADS4, idall=228,
                           snap_verts=[sheet_vert])
    got = {(v[0][0], v[0][2]) for t in out for v in t}
    for rx, _y, rz in ring:
        assert (rx, rz) in got, "ring vert not byte-exact in the fill"
    assert sheet_vert in got, "the crossing must snap onto the sheet vert's exact float"
    assert not any(abs(x - 4.0) < 1e-9 and abs(z - -0.5) < 1e-6 for (x, z) in got), \
        "the un-snapped crossing must not survive alongside the snapped one"


def test_lattice_patch_survives_a_spur_polygon():
    """The stuck-clip regression: a ring whose boundary runs along a cell plane and back
    mints an (A, X, A) spur that jams the ear-clipper ('stuck with 5 vertices' on the
    crescent's (940,-164) cell). The patch must fill it, not raise."""
    ring = [(0.5, 0.0, -0.5), (7.5, 0.0, -0.5), (8.0, 0.0, -4.0), (7.5, 0.0, -7.5),
            (4.0, 0.0, -4.0),                          # touches the interior lattice cross
            (0.5, 0.0, -7.5)]
    out = ME.lattice_patch(ring, y=0.0, uv_quads=QUADS4, idall=228)
    assert out
    area = sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                   - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) / 2
               for t in out)
    assert area > 20.0                                 # the footprint is actually covered


def test_excise_refuses_when_a_ring_cannot_be_filled(monkeypatch):
    """FAIL CLOSED ON A SKIPPED RING: a ring that raises out of the fill used to be
    recorded in skipped_rings and the tweaks handed back anyway -- a DROP with no fill,
    a silent void the size of the footprint (surfaced when the first lattice cut jammed:
    weld_exact=True, fill=0, no refusal)."""
    from ff9mapkit.world import transplant as TR

    kept = [_tri([(10.0, -40.0), (20.0, -40.0), (15.0, -50.0)]),
            _tri([(10.0, -40.0), (15.0, -50.0), (8.0, -48.0)]),
            _tri([(20.0, -40.0), (25.0, -46.0), (15.0, -50.0)])]
    crumb = [_tri([(64.0, -8.0), (64.0, -24.0), (52.0, -20.0)])]
    sea4 = [_tri([(0.0, 0.0), (40.0, 0.0), (52.0, -20.0)]),
            _tri([(0.0, 0.0), (52.0, -20.0), (0.0, -64.0)])]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)

    def jam(*a, **k):
        raise ValueError("ear-clip stuck with 5 vertices")
    monkeypatch.setattr(TR.ME if hasattr(TR, "ME") else __import__(
        "ff9mapkit.world.meshedit", fromlist=["x"]), "lattice_patch", jam)

    tweaks, rep = TR.excise_plan((0, 0), (1, 1))
    assert rep.get("refused"), "a dropped-but-unfilled footprint must refuse"
    assert tweaks == []


def test_excise_closes_a_structure_notch_over_the_object_base(monkeypatch):
    """EXCISE v3 -- THE STRUCTURE NOTCH. The world sheet is CUT under baked structures
    (measured: block (14,2)'s harbor base is exactly the 5 'interior' waterline verts the
    gate refused on the crescent, byte-exact). THE OBJECT ANCHOR means no carry ships the
    structure, so a dropped mass's structure footprint must be CLOSED OVER by the fill.

    Here the crumb's ring vert (52,-12) has no sea4 partner and is off-frame -- v2 refuses
    it -- but it is the y=0 base of the block's own object mesh, so v3 deletes the detour
    and fills straight across.
    """
    from ff9mapkit.world import transplant as TR

    kept = [_tri([(10.0, -40.0), (20.0, -40.0), (15.0, -50.0)]),
            _tri([(10.0, -40.0), (15.0, -50.0), (8.0, -48.0)]),
            _tri([(20.0, -40.0), (25.0, -46.0), (15.0, -50.0)])]
    # ring order A(64,-8) B(64,-24) C(52,-20) D(52,-12): two frame verts, one sea4-shared,
    # one structure-base
    crumb = [_tri([(64.0, -8.0), (64.0, -24.0), (52.0, -20.0)]),
             _tri([(64.0, -8.0), (52.0, -20.0), (52.0, -12.0)])]
    sea4 = [_tri([(0.0, 0.0), (40.0, 0.0), (52.0, -20.0)]),
            _tri([(0.0, 0.0), (52.0, -20.0), (0.0, -64.0)])]
    # the structure: one tri whose ONLY y=0 vert is the notch vert; the rest are up the wall
    obj = [_tri([(52.0, 0.0, -12.0), (48.0, 3.0, -10.0), (48.0, 3.0, -14.0)])]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4, "object": obj}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    _tweaks, rep = TR.excise_plan((0, 0), (1, 1))

    assert not rep.get("refused"), rep.get("refused")
    assert rep["weld_exact"] is True, rep.get("weld_missing")
    assert rep.get("structure_base") == 1
    assert rep["fill_tris"] >= 1, "the fill must close over the notch, not vanish"
    # THE LATTICE LAW at the excise call site: the fill must be stock-SHAPED water --
    # no triangle spanning a 4u tile (whole-footprint ear-clip minted 71.5u edges on the
    # crescent and rendered as a faceted iceberg)
    fill = [t for tw in _tweaks if isinstance(tw, TR.EmitTris) for t in tw.emit()]
    for t in fill:
        for i in range(3):
            assert math.dist(t[i][0], t[(i + 1) % 3][0]) <= 5.66


def test_excise_notch_deletion_never_touches_a_run_without_waterline_verts(monkeypatch):
    """The vacuous direction of v3's discriminant: ``all(v in obj_base for wl)`` over an
    EMPTY waterline list is true, so without the ``if not wl`` guard, the mere presence of
    a structure anywhere in the rect would delete every off-frame crop-profile corner --
    ordinary coast geometry with nothing structural about it. The corner must survive and
    appear (flattened) in the fill boundary.
    """
    from ff9mapkit.world import transplant as TR

    kept = [_tri([(10.0, -40.0), (20.0, -40.0), (15.0, -50.0)]),
            _tri([(10.0, -40.0), (15.0, -50.0), (8.0, -48.0)]),
            _tri([(20.0, -40.0), (25.0, -46.0), (15.0, -50.0)])]
    # ring A(64,-8) B(64,-24) C(52,-20) P(56,y=2,-14): frame, frame, sea4-shared, and a
    # RAISED off-frame profile corner (a crop-slice step, not a structure base)
    crumb = [_tri([(64.0, -8.0), (64.0, -24.0), (52.0, -20.0)]),
             _tri([(64.0, -8.0), (52.0, -20.0), (56.0, 2.0, -14.0)])]
    sea4 = [_tri([(0.0, 0.0), (40.0, 0.0), (52.0, -20.0)]),
            _tri([(0.0, 0.0), (52.0, -20.0), (0.0, -64.0)])]
    obj = [_tri([(30.0, 0.0, -30.0), (28.0, 3.0, -28.0), (28.0, 3.0, -32.0)])]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4, "object": obj}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    tweaks, rep = TR.excise_plan((0, 0), (1, 1))

    assert not rep.get("refused"), rep.get("refused")
    assert not rep.get("structure_base")
    fill = [t for tw in tweaks if isinstance(tw, TR.EmitTris) for t in tw.emit()]
    corners = {(round(v[0][0], 3), round(v[0][2], 3)) for t in fill for v in t}
    assert (56.0, -14.0) in corners, "the profile corner was deleted from the fill boundary"


def test_excise_still_refuses_when_the_interior_vert_is_not_the_structures_base(monkeypatch):
    """The fail-closed direction of v3: an object mesh being PRESENT in the rect must not
    excuse an interior vert the structure does not own. Same fixture, but the object's
    base vert is elsewhere -- the v1 refusal must survive. Without this, a discriminant
    forced always-true passes every test while shipping unweldable fills.
    """
    from ff9mapkit.world import transplant as TR

    kept = [_tri([(10.0, -40.0), (20.0, -40.0), (15.0, -50.0)]),
            _tri([(10.0, -40.0), (15.0, -50.0), (8.0, -48.0)]),
            _tri([(20.0, -40.0), (25.0, -46.0), (15.0, -50.0)])]
    crumb = [_tri([(64.0, -8.0), (64.0, -24.0), (52.0, -20.0)]),
             _tri([(64.0, -8.0), (52.0, -20.0), (52.0, -12.0)])]
    sea4 = [_tri([(0.0, 0.0), (40.0, 0.0), (52.0, -20.0)]),
            _tri([(0.0, 0.0), (52.0, -20.0), (0.0, -64.0)])]
    obj = [_tri([(30.0, 0.0, -30.0), (28.0, 3.0, -28.0), (28.0, 3.0, -32.0)])]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4, "object": obj}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    _tweaks, rep = TR.excise_plan((0, 0), (1, 1))

    assert rep["weld_exact"] is False
    assert (52.0, 0.0, -12.0) in [tuple(v) for v in rep["weld_missing"]]
    assert "refused" in rep
    assert not rep.get("structure_base")


def test_excise_fill_does_not_fan_across_a_block_border(monkeypatch):
    """THE FAN LAW at the EXCISE call site -- two helpers deep from where it is spent.

    ``flat_patch`` opting into quality ear-clipping is worth nothing unless the excise
    fill is the thing being clipped. The fill's ring here is the FAN_RING shape, seated
    so it crosses the rect frame: with first-ear clipping its diagonals cross a 4u lattice
    line 0.008u apart, which is exactly how the sinuous (3,11)+2x4 and Daguerreo
    (5,15)+3x2 rects failed the weld audit with pairs=1 and pairs=4.
    """
    from ff9mapkit.world import transplant as TR

    seated = [(p[0] + 24.0, p[1] - 30.0) for p in FAN_RING]        # touches the x=0 frame
    crumb = [_tri([(a[0], a[1]), (b[0], b[1]), (c[0], c[1])])
             for (a, b, c) in ME.earclip(seated)]                  # boundary == the ring
    kept = [_tri([(20.0, -55.0), (24.0, -55.0), (22.0, -60.0)])]
    # sea4 owns every waterline vertex of the excised mass, as the real sheet does
    sea4 = [_tri([(p[0], p[1]), (60.0, -2.0), (62.0, -6.0)]) for p in seated]

    def fake_world_tris(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return {"terrain": kept + crumb, "sea4": sea4}.get(part, [])

    monkeypatch.setattr(TR, "world_tris", fake_world_tris)
    # keep_largest=False: this fixture is deliberately lopsided (a big crumb dropped, a
    # tiny mass kept) because it exercises the FILL's triangulation, not carry sanity.
    # THE CARRIED-SUBJECT GUARD correctly refuses it, so the override is what keeps this
    # test about the thing it is testing.
    tweaks, rep = TR.excise_plan((0, 0), (1, 1), keep_largest=False)

    assert not rep.get("refused"), rep.get("refused")
    fill = [t for tw in tweaks if isinstance(tw, TR.EmitTris) for t in tw.emit()]
    assert fill, "the excised crumb must be re-zipped with a sea4 fill"
    plan = [tuple((v[0][0], v[0][2]) for v in t) for t in fill]
    lines = [float(x) for x in range(0, 49, 4)]
    assert _closest_crossing(plan, lines) >= WELD_TOL


# ------------------------------------------------- THE LAYOUT-SUPPORT WARNING

def _grass_donor(monkeypatch):
    """A beachless donor whose mains are unambiguously grass."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world import transplant as TR
    u0, v0, u1, v1 = G.ground_main_region("grass")
    mu, mv = (u0 + u1) / 2, (v0 + v1) / 2

    def fake(bx, by, part, **kw):
        if part != "terrain" or (bx, by) != (1, 1):
            return []
        v = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (mu, mv), (0.0, 0.0, 0.0, 1.0))
        return [[v, v, v] for _ in range(40)]

    monkeypatch.setattr(TR, "world_tris", fake)
    monkeypatch.setattr(CM, "_sand_band_family", lambda *a, **k: None)
    return TR


def test_layout_support_table_matches_the_census_headline():
    """grass<->desert is the only strong pair -- the number the whole feature rests on."""
    from ff9mapkit.world.transplant import LAYOUT_SUPPORT, LAYOUT_SUPPORT_WARN
    assert LAYOUT_SUPPORT["grass"]["desert"] > LAYOUT_SUPPORT_WARN
    assert LAYOUT_SUPPORT["desert"]["grass"] > LAYOUT_SUPPORT_WARN
    # every other pair from grass or desert is off the measured path
    for src in ("grass", "desert"):
        other = {d: s for d, s in LAYOUT_SUPPORT[src].items()
                 if d not in ("grass", "desert")}
        assert max(other.values()) < LAYOUT_SUPPORT_WARN, other


def test_ground_retile_warns_on_an_off_path_pair(monkeypatch):
    TR = _grass_donor(monkeypatch)
    with pytest.warns(UserWarning, match="OFF THE MEASURED PATH"):
        TR.GroundRetile.for_donor((1, 1), "snow", strips="none")


def test_ground_retile_is_SILENT_on_the_proven_pair(monkeypatch):
    """The warning must discriminate -- one that always fires carries no information."""
    import warnings as _w
    TR = _grass_donor(monkeypatch)
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        TR.GroundRetile.for_donor((1, 1), "desert", strips="none")
    assert not [c for c in caught if "MEASURED PATH" in str(c.message)]


def test_mains_family_accepts_a_UNANIMOUS_small_donor():
    """A real 1x1 carryable island read {'grass': 11} and was refused for being small.

    The floor guards against a few stray tris outvoting a present competitor; with no
    competitor there is nothing to be ambiguous between.
    """
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world.transplant import GroundRetile
    u0, v0, u1, v1 = G.ground_main_region("grass")
    tris = [_mains_tri((u0 + u1) / 2, (v0 + v1) / 2) for _ in range(11)]
    assert GroundRetile._mains_family(tris, (12, 10)) == "grass"


def test_mains_family_still_refuses_a_small_CONTESTED_donor():
    """The relaxation must not swallow the ambiguity case it was carved out of."""
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world.transplant import GroundRetile
    tris = []
    for fam, k in (("grass", 6), ("desert", 5)):
        u0, v0, u1, v1 = G.ground_main_region(fam)
        tris += [_mains_tri((u0 + u1) / 2, (v0 + v1) / 2) for _ in range(k)]
    with pytest.raises(ValueError, match="no dominant ground family"):
        GroundRetile._mains_family(tris, (0, 0))


# ------------------------------------- the three fail-closed gaps (measured, then closed)

def _beach_tri(topo):
    """A tri carrying `topo` -- via encode_id, because the topograph is BIT-ENCODED in
    the IDALL, not the raw tangent.x. Writing the bare number silently decodes to
    something else (55 -> 10), which is a test that measures nothing."""
    from ff9mapkit.world.extract import encode_id
    idall = float(encode_id(topograph=topo))
    v = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.5, 0.5), (idall, 0.0, 0.0, 1.0))
    return [v, v, v]


def test_beach1_water_passes_verbatim_and_is_COUNTED():
    """Water in beach1 is correctly verbatim -- but it must be visible, not silent."""
    from ff9mapkit.world.transplant import GroundRetile
    gt = GroundRetile(dst="desert", src="grass")
    out = gt.apply("beach1", _beach_tri(55))          # 55 is water
    assert out is not None and gt.n["beach1_water"] == 1
    assert not gt.unclassified


def test_beach1_UNMEASURED_class_now_refuses():
    """The guard must be observed to FIRE. Before this, any non-foam beach1 tri passed
    verbatim with no counter -- water and an unmeasured class were indistinguishable."""
    from ff9mapkit.world.transplant import GroundRetile
    gt = GroundRetile(dst="desert", src="grass")
    gt.apply("beach1", _beach_tri(41))                # neither foam (30/34) nor water
    assert gt.unclassified and gt.unclassified[0]["topo"] == 41
    assert gt.gate()["ok"] is False


def test_snow_sand_band_refuses_BY_NAME():
    """topo 33 used to make a block read as beachless; the failure named nothing."""
    from ff9mapkit.world import coastmorph as CM
    with pytest.raises(ValueError, match="SNOW shore-sand band"):
        CM._sand_band_family([_beach_tri(CM._SAND_SNOW_TOPO)], what="donor (7,3)")


def test_a_block_with_no_sand_at_all_is_still_beachless():
    """The snow refusal must not swallow the ordinary no-sand case."""
    from ff9mapkit.world import coastmorph as CM
    assert CM._sand_band_family([_beach_tri(0)], what="donor") is None


def test_recover_budget_counts_only_what_can_actually_recover(monkeypatch):
    """The budget used to count EVERY refusal in a recover cell, including foreign
    classes the recover path never takes -- making expected["recovered"] unreachable,
    so the gate could only ever fail. Donor (4,12) budgeted 8 against 5 reachable tris.
    """
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import grassland as G
    from ff9mapkit.world import transplant as TR
    from ff9mapkit.world.extract import encode_id

    u0, v0, u1, v1 = G.ground_main_region("grass")
    inside = ((u0 + u1) / 2, (v0 + v1) / 2)     # classifies as mains -> names src=grass
    outside = (0.999, 0.999)                    # in-family topo, no class -> recoverable

    def tri(topo, uv, x=2.0, z=-2.0):
        v = ((x, 0.0, z), (0.0, 1.0, 0.0), uv, (float(encode_id(topograph=topo)),
                                                0.0, 0.0, 1.0))
        return [v, v, v]

    def fake(bx, by, part, **kw):
        if part != "terrain" or (bx, by) != (1, 1):
            return []
        return ([tri(0, inside) for _ in range(40)]      # grass mains, sets src
                + [tri(0, outside)]                       # in-family refusal: RECOVERABLE
                + [tri(49, outside)] * 3)                 # mountain rock: never recoverable

    monkeypatch.setattr(TR, "world_tris", fake)
    monkeypatch.setattr(CM, "_sand_band_family", lambda *a, **k: None)
    gt = TR.GroundRetile.for_donor((1, 1), "desert", strips="none")
    assert gt.src == "grass"
    # 4 refusals share the cell; only the ONE in-family tri can recover.
    assert gt.recover_budget == 1, gt.recover_budget
    assert gt.expected["recovered"] == 1


# --------------------------------------------------- THE CARRIED-SUBJECT GUARD

def _excise_world(land_tris_kept, land_tris_dropped):
    """A donor rect with two land assemblies: one clear of the frame, one crossing it."""
    from ff9mapkit.world.extract import encode_id
    B, idl = 64.0, float(encode_id(topograph=0))

    def quad(x0, z0, w, h, n):
        """n disjoint tris inside [x0,x0+w] x [z0,z0-h] (each its own vertex set)."""
        out = []
        for k in range(n):
            ox = x0 + (k % 8) * (w / 9.0)
            oz = z0 - (k // 8) * (h / 9.0)
            p = [(ox, 3.2, oz), (ox + 0.4, 3.2, oz), (ox, 3.2, oz - 0.4)]
            out.append([(q, (0.0, 1.0, 0.0), (0.5, 0.5), (idl, 0.0, 0.0, 1.0)) for q in p])
        return out

    kept = quad(20.0, -20.0, 20.0, 20.0, land_tris_kept)          # well inside
    # hard against x=0 so EVERY tri is within land_margin of the frame. Spread wider
    # and the disjoint tris become their own assemblies, most of them clear of the
    # frame -- which is how the first cut of this helper reported kept_land=17 for a
    # case meant to keep 2.
    crossing = quad(0.0, -5.0, 1.0, 30.0, land_tris_dropped)
    return kept, crossing


def test_carried_subject_guard_refuses_a_carry_that_drops_its_own_subject(monkeypatch):
    """Six of ten 'gates CLEAN' rects carried a crumb or nothing; the gates cannot tell."""
    from ff9mapkit.world import transplant as TR
    kept, crossing = _excise_world(2, 40)

    def fake(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return kept + crossing if part == "terrain" else []

    monkeypatch.setattr(TR, "world_tris", fake)
    _tw, rep = TR.excise_plan((0, 0), (1, 1))
    assert "excises its own subject" in (rep.get("refused") or "")
    assert rep["kept_land"] == 2 and rep["dropped_land"] == 40


def test_carried_subject_guard_allows_a_carry_that_keeps_more_than_it_drops(monkeypatch):
    """The guard must DISCRIMINATE -- the shipped isthmus keeps 578 and drops 109."""
    from ff9mapkit.world import transplant as TR
    kept, crossing = _excise_world(40, 6)

    def fake(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return kept + crossing if part == "terrain" else []

    monkeypatch.setattr(TR, "world_tris", fake)
    _tw, rep = TR.excise_plan((0, 0), (1, 1))
    assert "excises its own subject" not in (rep.get("refused") or "")


def test_carried_subject_guard_can_be_overridden_deliberately(monkeypatch):
    from ff9mapkit.world import transplant as TR
    kept, crossing = _excise_world(2, 40)

    def fake(bx, by, part, **kw):
        if (bx, by) != (0, 0):
            return []
        return kept + crossing if part == "terrain" else []

    monkeypatch.setattr(TR, "world_tris", fake)
    _tw, rep = TR.excise_plan((0, 0), (1, 1), keep_largest=False)
    assert "excises its own subject" not in (rep.get("refused") or "")


# ------------------------------------------------------- THE RING DROP (re-shade)

def _flat_tri(x, z, *, wind=-1.0, nrm=(-0.121, 0.979, 0.167)):
    """A flat y=0 water tri wound to `wind` (stock sea winds negative)."""
    a, b, c = (x, 0.0, z), (x + 2.0, 0.0, z), (x, 0.0, z - 2.0)
    if wind > 0:
        b, c = c, b
    return [(p, nrm, (0.3, 0.3), (99.0, 0.0, 0.0, 1.0)) for p in (a, b, c)]


def test_retag_flat_conserves_geometry_exactly():
    """A re-shade must be unable to move a weld: positions and normals verbatim."""
    src = [_flat_tri(4.0 * i, -8.0) for i in range(6)]
    out = ME.retag_flat(src, uv_quads=((0.0, 0.0, 0.5, 0.5),), idall=228)
    assert len(out) == len(src)
    for a, b in zip(src, out):
        assert [v[0] for v in a] == [v[0] for v in b]      # positions
        assert [v[1] for v in a] == [v[1] for v in b]      # normals
        assert all(v[3][0] == 228.0 for v in b)            # retagged IDALL


def test_retag_flat_uv_is_anchored_on_the_triangle_s_own_tile():
    """`x/4 % 1` wraps to 0 at every tile edge, so a tile-SPANNING tri collapses to a
    zero-width uv and stretches one texel across the face. These are stock water tris
    with median plan area 8u2 against a 16u2 tile, so they span most of one -- the uv
    must be anchored on the tile and reach 1.0 at its far edge.
    """
    q = (0.0, 0.0, 0.5039, 0.5079)
    # a tri spanning a whole tile: x 8->12 sits exactly on tile 2
    tri = [((8.0, 0.0, -8.0), (0.0, 1.0, 0.0), (0.0, 0.0), (99.0, 0.0, 0.0, 1.0)),
           ((12.0, 0.0, -8.0), (0.0, 1.0, 0.0), (0.0, 0.0), (99.0, 0.0, 0.0, 1.0)),
           ((8.0, 0.0, -12.0), (0.0, 1.0, 0.0), (0.0, 0.0), (99.0, 0.0, 0.0, 1.0))]
    out = ME.retag_flat([tri], uv_quads=(q,), idall=228, winding=None)
    us = sorted(v[2][0] for v in out[0])
    vs = sorted(v[2][1] for v in out[0])
    # the span must cover the full quadrant, not collapse to its origin
    assert us[-1] - us[0] == pytest.approx(q[2] - q[0]), us
    assert vs[-1] - vs[0] == pytest.approx(q[3] - q[1]), vs


def test_retag_flat_gives_both_tris_of_a_tile_the_SAME_quadrant():
    """THE PER-TILE QUADRANT LAW -- the defect that shipped a checkerboard.

    Stock: 134 of 135 tiles have every triangle on one quadrant. Choosing per TRIANGLE
    puts a different atlas sub-tile either side of every tile diagonal.
    """
    def tri_at(x, z, flip):
        pts = ([(x, 0.0, z), (x + 4.0, 0.0, z), (x, 0.0, z - 4.0)] if not flip else
               [(x + 4.0, 0.0, z), (x + 4.0, 0.0, z - 4.0), (x, 0.0, z - 4.0)])
        return [(p, (0.0, 1.0, 0.0), (0.0, 0.0), (99.0, 0.0, 0.0, 1.0)) for p in pts]

    for k in range(6):                       # several tiles, both halves of each
        a = ME._tile_quad_index(tri_at(4.0 * k, -8.0, False), 4)
        b = ME._tile_quad_index(tri_at(4.0 * k, -8.0, True), 4)
        assert a == b, f"tile {k}: halves disagree ({a} vs {b})"


def test_tile_quad_index_is_not_a_LATTICE():
    """A low-bit hash makes tile parity PREDICT the quadrant: regular where stock is
    irregular, which is the checkerboard's cousin."""
    from collections import Counter
    best = 0.0
    idx = {}
    for gx in range(40):
        for gz in range(40):
            tri = [((gx * 4.0 + 2, 0.0, -(gz * 4.0 + 2)),)]
            idx[(gx, gz)] = ME._tile_quad_index(tri, 4)
    for m in (2, 3, 4):
        byp = {}
        for (gx, gz), q in idx.items():
            byp.setdefault((gx % m, gz % m), Counter())[q] += 1
        hit = sum(c.most_common(1)[0][1] for c in byp.values()) / len(idx)
        best = max(best, hit - len(byp) / len(idx))
    assert best < 0.45, f"a small lattice predicts the quadrant {best:.0%} of the time"


def test_retag_flat_refuses_to_flip_a_face():
    """A back-facing sea tri RENDERS yet reads as void -- a re-shade must never cause it."""
    with pytest.raises(ValueError, match="must not.*flip|winds"):
        ME.retag_flat([_flat_tri(0.0, 0.0, wind=+1.0)],
                      uv_quads=((0.0, 0.0, 0.5, 0.5),), idall=228, winding=-1.0)


def test_deepen_shallow_plan_conserves_the_tri_count(monkeypatch):
    """Every dropped shallow tri must reappear as deep water -- no hole, no extra."""
    from ff9mapkit.world import transplant as TR
    ring = [_flat_tri(4.0 * i, -12.0) for i in range(7)]

    def fake(bx, by, part, **kw):
        return ring if part == "sea3" else []

    monkeypatch.setattr(TR, "world_tris", fake)
    _tw, rep = TR.deepen_shallow_plan((0, 0), (1, 1))
    assert rep["dropped"] == {"sea3": 7} and rep["converted"] == 7
    assert rep["conserved"] is True


def test_deepen_shallow_plan_refuses_a_ring_less_donor(monkeypatch):
    """The comma and the corner isle are already deep-water -- saying so beats a no-op."""
    from ff9mapkit.world import transplant as TR
    monkeypatch.setattr(TR, "world_tris", lambda *a, **k: [])
    _tw, rep = TR.deepen_shallow_plan((0, 0), (1, 1))
    assert "no shallow ring" in rep["refused"]
