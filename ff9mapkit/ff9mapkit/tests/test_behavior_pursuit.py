"""THE PURSUIT SWEEP — the dynamic-feed half of the walkability check.

``route = "auto"`` REFUSES chase/wander (no build-time leg origin — the Path-B study,
`studies/behavior-trees/pathb/`), so a dynamic feed has no authored line to sweep. What
IS checkable offline is the FAMILY of legs its branch's own engagement gate admits:
every pair of occupiable positions inside the compiler's Chebyshev ``near`` box.

Design pins under test: the family is bounded by the branch's TIGHTEST near radius (the
rows are ANDed) and unbounded when no row names the target; pairs inside the ``standoff``
are excluded (the pursuer holds ground) and a blocked leg is only counted up to the
standoff ring; the raster/leg GRAIN never scales with the radius (a large family must not
silently rasterise the field into a false clean); a rate is never quoted off a handful of
pairs; and a convex field reports nothing.
"""
from __future__ import annotations

from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.scene import bgi
from ff9mapkit.scene import routes as R


def u_mesh(notch_z: int):
    """The autoroute suite's WELDED U floor: outer x[-800,800] z[-800,200] minus the
    notch x(-400,400) z(notch_z, 200]. A pursuit across the notch mouth jams."""
    xs = (-800, -400, 400, 800)
    verts = [(x, 0, z) for z in (200, notch_z, -800) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(verts, tris).to_bytes())


def flat_mesh(half: int = 800):
    """A CONVEX square floor — every straight line inside it is walkable."""
    verts = [(-half, 0, half), (half, 0, half), (half, 0, -half), (-half, 0, -half)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(verts, [(0, 1, 2), (0, 2, 3)]).to_bytes())


DEEP = u_mesh(-400)
FLAT = flat_mesh()


# ------------------------------------------------------------------ the sweep core
def test_convex_field_is_clean():
    res = R.sweep_pursuit(FLAT, 600, standoff=140)
    assert res["tested"] > 0                       # it really did test pairs
    assert res["blocked"] == 0
    assert R.describe_pursuit_problems("chase 'player'", res) == []


def test_concave_notch_is_caught_with_an_exemplar_pair():
    res = R.sweep_pursuit(DEEP, 900, standoff=0)
    assert res["blocked"] > 0
    probs = R.describe_pursuit_problems("chase 'player'", res)
    assert any("leaves the walkmesh" in p for p in probs)
    assert any("e.g. pursuer at" in p for p in probs)
    for h in res["worst"]:                         # every exemplar names a real hole:
        mx, mz = h["mid"]                          # its midpoint is INSIDE the notch
        assert -400 < mx < 400 and -400 < mz <= 200, (mx, mz)
        assert h["span"] > 0 and h["dist"] > 0


def test_standoff_excludes_close_pairs_and_truncates_the_leg():
    wide = R.sweep_pursuit(DEEP, 900, standoff=0)
    tight = R.sweep_pursuit(DEEP, 900, standoff=800)
    assert tight["tested"] < wide["tested"]        # close pairs dropped
    # a leg only counts blockage BEFORE the standoff ring, so a big standoff can only
    # ever reduce the measured span for the same family
    assert tight["blocked"] <= wide["blocked"]


def test_tighter_radius_is_safer():
    """The study's headline curve (0% below 600u on a real concave field, 82% at
    2400u+) must reproduce here: a tighter engagement gate is monotonically safer."""
    def rate(r):
        res = R.sweep_pursuit(DEEP, r, standoff=0)
        assert res["tested"] > 0
        return res["blocked"] / res["tested"]
    rates = [rate(r) for r in (200, 400, 900, 2000)]
    assert rates == sorted(rates)                  # never worse as the gate tightens
    assert rates[0] < 0.01 < rates[-1]             # near-clean up close, bad far out


def test_an_ungated_family_never_reports_a_false_clean():
    """THE RESOLUTION PIN, and the two bugs it caught. An ungated chase's radius is the
    whole field, and sizing the sampling off THAT number (rather than off the floor that
    actually exists) drove the endpoint grid to ~4000u on a 1600u mesh; selecting those
    endpoints by ``gi % stride == 0`` then matched no cell at all. Both failure modes
    reported 0 pairs tested as CLEAN -- the worst possible answer for a lint."""
    huge = R.sweep_pursuit(DEEP, 20000, standoff=0)
    assert huge["grain"] == R.WALL_CLEARANCE_W     # the leg grain never scales
    assert huge["sources"] > 0 and huge["tested"] > 0
    assert huge["blocked"] > 0                     # and it still finds the notch
    # a family wider than the field is the same family as one exactly that wide
    assert huge["tested"] == R.sweep_pursuit(DEEP, 2000, standoff=0)["tested"]


def test_small_sample_reports_counts_not_a_rate():
    """A rate off a handful of pairs is noise; state the finding instead."""
    tiny = {"tested": 20, "blocked": 14, "radius": 9000, "standoff": 0, "grain": 48.0,
            "spacing": 1900.0, "sources": 5,
            "worst": [{"a": (0, 0), "b": (10, 10), "dist": 14.1, "span": 9.0,
                       "mid": (5, 5)}]}
    probs = R.describe_pursuit_problems("chase 'player'", tiny)
    assert any("14 of only 20 sampled position pairs" in p for p in probs)
    assert not any("% of the position pairs" in p for p in probs)
    big = dict(tiny, tested=4000, blocked=200)
    probs = R.describe_pursuit_problems("chase 'player'", big)
    assert any("5.0% of the position pairs" in p for p in probs)
    # coverage is ALWAYS stated -- a capped sweep must never read as exhaustive
    for r in (tiny, big):
        assert any("legs tested at" in p for p in R.describe_pursuit_problems("x", r))


def test_boxes_restrict_the_family():
    """A source box on the far side of the notch from the target box keeps every pair
    blocked; boxes on the SAME side keep every pair clear."""
    left = (-800, -400, -200, 200)
    right = (400, 800, -200, 200)
    crossing = R.sweep_pursuit(DEEP, 2000, standoff=0, source_box=left, target_box=right)
    assert crossing["tested"] > 0 and crossing["blocked"] == crossing["tested"]
    same = R.sweep_pursuit(DEEP, 2000, standoff=0, source_box=left, target_box=left)
    assert same["tested"] > 0 and same["blocked"] == 0


def test_occupiable_cells_erode_by_the_collision_radius():
    occ, on = R.occupiable_cells(FLAT, R.WALL_CLEARANCE_W)
    assert occ and occ < on                        # the wall band is dropped
    for (gi, gj) in occ:                           # every kept cell clears the wall
        x, z = (gi + 0.5) * R.WALL_CLEARANCE_W, (gj + 0.5) * R.WALL_CLEARANCE_W
        assert min(800 - abs(x), 800 - abs(z)) >= R.WALL_CLEARANCE_W - 1e-6


def test_sweep_is_deterministic():
    a = R.sweep_pursuit(DEEP, 900, standoff=140)
    b = R.sweep_pursuit(DEEP, 900, standoff=140)
    assert a == b


# ------------------------------------------------------- the TOML reference extractor
def _toml(branch, npc_extra=None):
    npc = {"name": "guard", "pos": [0, -600], "preset": "GEO_NPC_F0_CSO"}
    npc.update(npc_extra or {})
    return {"npc": [npc, {"name": "thief", "pos": [600, 0], "preset": "GEO_NPC_F0_CSO"}],
            "player": {"spawn": [0, -700]},
            "behavior": {"unit": [{"npc": "guard", "branch": branch}]}}


def test_chase_radius_is_the_tightest_near_row():
    raw = _toml([{"when": [{"near": ["thief", 900]}, {"near": ["thief", 400]}],
                  "do": {"chase": "thief"}}])
    ref, = BT.pursuit_refs(raw)
    assert ref["verb"] == "chase" and ref["target"] == "thief"
    assert ref["radius"] == 400                    # ANDed rows -> the MINIMUM binds
    assert ref["standoff"] == 140                  # the compiler default


def test_chase_radius_from_any_near_and_the_standoff_override():
    raw = _toml([{"when": [{"any_near": [["thief", "player"], 550]}],
                  "do": {"chase": "thief", "standoff": 200}}])
    ref, = BT.pursuit_refs(raw)
    assert ref["radius"] == 550 and ref["standoff"] == 200


def test_near_row_for_a_different_target_does_not_bind():
    raw = _toml([{"when": [{"near": ["player", 300]}], "do": {"chase": "thief"}}])
    ref, = BT.pursuit_refs(raw)
    assert ref["radius"] is None                   # UNGATED w.r.t. the chase target


def test_ungated_chase_has_no_radius():
    raw = _toml([{"do": {"chase": "player"}}])
    ref, = BT.pursuit_refs(raw)
    assert ref["radius"] is None and ref["source_box"] is None


def test_near_point_becomes_a_source_box():
    raw = _toml([{"when": [{"near_point": [[100, 200], 300]}, {"near": ["thief", 500]}],
                  "do": {"chase": "thief"}}])
    ref, = BT.pursuit_refs(raw)
    assert ref["source_box"] == (-200, 400, -100, 500)
    assert ref["target_box"] is None               # the gate bounds ME, not my quarry


def test_wander_family_is_the_box_and_spans_twice_the_radius():
    raw = _toml([{"do": {"wander": [0, -600], "radius": 250}}])
    ref, = BT.pursuit_refs(raw)
    assert ref["verb"] == "wander" and ref["radius"] == 500 and ref["standoff"] == 0
    assert ref["source_box"] == ref["target_box"] == (-250, 250, -850, -350)


def test_static_only_field_yields_no_pursuit_refs():
    raw = _toml([{"do": {"patrol": [[0, -600], [200, -600]]}}])
    assert BT.pursuit_refs(raw) == []
