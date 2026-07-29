"""THE FLOOR LAW — the multi-floor half of the walkability instruments.

A walker lives on ONE floor and can only change floors across a SEAM edge. Every
spatial instrument used to test point-in-mesh in flattened 2D, so a wander target /
route point / NPC post on a raised terrace passed every offline gate while the
ground-floor walker marched into the terrace base and wedged — three HANGOUT playtest
rounds of "glitchy waypoints" that every sweep called clean (field 559's fork, 4
floors). Design pins under test:

* :meth:`BgiWalkmesh.floors_at` reports EVERY floor containing a point (XZ overlap
  included); ``point_on_walkmesh`` stays first-match / floor-blind.
* a polyline leg is clean only if it stays on its floor or crosses AT a seam — an
  unseamed crossing is a ``jumps`` record, phrased with "NO SEAM" (the lint's error
  marker); floors that merely OVERLAP in XZ (a balcony) are not a crossing.
* :func:`sweep_wander` models the engine's roll honestly: it lands ANYWHERE in the
  box (mesh or not), so off-mesh and unseamed-floor box area jams the walker; a box
  whose floor changes all happen at seams stays QUIET.
* :func:`sweep_pursuit` counts an unseamed floor break as blocked, exactly like
  leaving the mesh.
* the auto-router refuses (loudly) a leg it would have routed straight across a
  terrace base — its A* is floor-blind, so the safety re-sweep must catch it.
"""
from __future__ import annotations

import pytest

from ff9mapkit.content import pathfind
from ff9mapkit.scene import bgi
from ff9mapkit.scene import routes as R


def terrace_mesh(seamed: bool):
    """Ground floor 0 (x 0..1000, y 0) ABUTTING a raised terrace floor 1
    (x 1000..2000, y 400), disjoint vertex sets — the multi-floor .bgi convention.
    ``seamed`` links the shared x=1000 edge the way a real ramp/stair field does."""
    verts = [(0, 0, 0), (1000, 0, 0), (1000, 0, 1000), (0, 0, 1000),
             (1000, 400, 0), (2000, 400, 0), (2000, 400, 1000), (1000, 400, 1000)]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)]
    m = bgi.BgiWalkmesh.from_bytes(
        bgi.build(verts, faces, floor_ids=[0, 0, 1, 1]).to_bytes())
    if seamed:
        seam = (0, tuple(sorted(((1000, 0, 0), (1000, 0, 1000)))),
                1, tuple(sorted(((1000, 400, 0), (1000, 400, 1000)))))
        linked, missing, _ = m.apply_seams([seam])
        assert (linked, missing) == (1, 0)
    return m


def balcony_mesh():
    """A 200u balcony (floor 1, y 400) hovering OVER the ground floor — the floors
    OVERLAP in XZ but never touch: 25% of real fields do this (the Path-B census)."""
    verts = [(0, 0, 0), (1000, 0, 0), (1000, 0, 1000), (0, 0, 1000),
             (400, 400, 400), (600, 400, 400), (600, 400, 600), (400, 400, 600)]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)]
    return bgi.BgiWalkmesh.from_bytes(
        bgi.build(verts, faces, floor_ids=[0, 0, 1, 1]).to_bytes())


# ------------------------------------------------------------------ the point test
def test_floors_at_reports_every_floor():
    m = terrace_mesh(False)
    assert m.floors_at(500, 500) == [0]
    assert m.floors_at(1500, 500) == [1]
    assert m.floors_at(2500, 500) == []
    assert m.point_on_walkmesh(1500, 500) == 1
    b = balcony_mesh()
    assert b.floors_at(500, 500) == [0, 1]         # XZ overlap: BOTH reported
    assert b.point_on_walkmesh(500, 500) == 0      # first match — floor-blind by design


def test_seam_edges_xz():
    assert terrace_mesh(False).seam_edges_xz() == {}
    seams = terrace_mesh(True).seam_edges_xz()
    assert list(seams) == [(0, 1)]
    (a, b), = seams[(0, 1)]
    assert a[0] == b[0] == 1000                    # the shared edge, in XZ


# ------------------------------------------------------------------ polyline legs
def test_polyline_flags_an_unseamed_floor_crossing():
    m = terrace_mesh(False)
    legs = R.sweep_polyline([(500, 500), (1500, 500)], m)
    assert not legs[0]["spans"]                    # flattened 2D: it LOOKS on-mesh
    (j,) = legs[0]["jumps"]
    assert j["from"] == [0] and j["to"] == [1]
    assert abs(j["x"] - 1000) < 80                 # at the terrace base
    (warn,) = R.describe_leg_problems("beat", legs)
    assert "NO SEAM" in warn and "floor 0 -> floor 1" in warn


def test_a_seam_makes_the_same_crossing_legal():
    m = terrace_mesh(True)
    legs = R.sweep_polyline([(500, 500), (1500, 500)], m)
    assert not legs[0]["spans"] and not legs[0]["jumps"]
    assert R.describe_leg_problems("beat", legs) == []


def test_balcony_overlap_is_not_a_crossing():
    legs = R.sweep_polyline([(200, 500), (800, 500)], balcony_mesh())
    assert not legs[0]["jumps"]                    # the walker stays UNDER the balcony


def test_duck_typed_meshes_still_sweep():
    class FakeMesh:
        def world_verts(self):
            return []

        tris = ()

        def point_on_walkmesh(self, x, z):
            return 0 if 0 <= x <= 1000 else None

    legs = R.sweep_polyline([(0, 0), (900, 0)], FakeMesh(), bedges=[])
    assert not legs[0]["spans"] and not legs[0]["jumps"]


# ------------------------------------------------------------------ the wander roll
def test_wander_flags_a_box_overhanging_a_terrace():
    res = R.sweep_wander(terrace_mesh(False), 700, 500, 400)
    assert res["alien_cells"] > 0 and res["alien_floors"] == [1]
    assert res["jammed"] > 0
    probs = R.describe_wander_problems("'peddler'", res)
    assert any("never checks the mesh" in p for p in probs)
    assert any("sit on floor 1" in p for p in probs)
    assert any("NO SEAM" in p for p in probs)      # an exemplar names the base wall
    # deterministic: the lint must not flicker between runs
    assert res == R.sweep_wander(terrace_mesh(False), 700, 500, 400)


def test_wander_stays_quiet_when_the_crossing_is_a_seam():
    res = R.sweep_wander(terrace_mesh(True), 700, 500, 400)
    assert res["alien_cells"] > 0                  # the box still spans the terrace...
    assert res["jammed"] == 0                      # ...but every roll is reachable
    assert R.describe_wander_problems("'peddler'", res) == []


def test_wander_flags_a_box_overhanging_the_mesh_edge():
    res = R.sweep_wander(terrace_mesh(True), 500, 200, 400)   # box dips past z=0
    assert res["off_cells"] > 0 and res["jammed"] > 0
    probs = R.describe_wander_problems("'mage'", res)
    assert any("OFF the walkmesh" in p for p in probs)
    assert any("walks OFF-MESH" in p for p in probs)


def test_wander_centre_off_mesh_is_its_own_finding():
    res = R.sweep_wander(terrace_mesh(True), -500, 500, 200)
    assert res["centre_floors"] == [] and res["tested"] == 0
    (warn,) = R.describe_wander_problems("'lost'", res)
    assert "CENTRE" in warn and "OFF the walkmesh" in warn


# ------------------------------------------------------------------ pursuit families
def test_pursuit_counts_an_unseamed_floor_break_as_blocked():
    blocked = R.sweep_pursuit(terrace_mesh(False), 2000, standoff=0)
    assert 0 < blocked["blocked"] < blocked["tested"]   # cross-floor pairs jam only
    clear = R.sweep_pursuit(terrace_mesh(True), 2000, standoff=0)
    assert clear["tested"] > 0 and clear["blocked"] == 0


# ------------------------------------------------------------------ the auto-router
def test_route_polyline_refuses_an_unrouteable_floor_break():
    """Loud, never silent: pre-fix the router accepted this leg as clean (the sweep
    saw no off-mesh span in 2D) and compiled a walker that wedges every lap. Now the
    jump makes it route -- and the honest answer is that no route EXISTS (unseamed
    floors are disconnected for a 48u walker), or, if the floor-blind A* does thread
    something, the floor-aware re-sweep refuses it naming the seam fix."""
    with pytest.raises(pathfind.RouteLegError) as e:
        pathfind.route_polyline(terrace_mesh(False), [(500, 500), (1500, 500)])
    assert "disconnected floors" in str(e.value) or "seam" in str(e.value)
    pts, inserted = pathfind.route_polyline(terrace_mesh(True), [(500, 500), (1500, 500)])
    assert pts == [(500, 500), (1500, 500)] and inserted == []
