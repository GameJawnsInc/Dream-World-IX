"""PATH A — static-feed auto-routing: ``route = "auto"`` on patrol/march re-routes
jammed legs through the walkmesh pathfinder (content.pathfind.route_polyline) at
build time. The concave-notch class the sweep diagnoses is exactly what the router
fixes; these tests prove the loop offline on a real in-memory BgiWalkmesh.

Design pins under test: opt-in only (no route key => byte-identical, the walkmesh
is never even resolved); clear legs stay as authored; walls-only obstacles; the
2..8 waypoint ceiling is a hard, actionable error; determinism (same input =>
identical bytes)."""
from __future__ import annotations

import pytest

from ff9mapkit.content import behavior as B
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.content import pathfind
from ff9mapkit.scene import bgi


def u_mesh(notch_z: int):
    """A WELDED U-shaped floor: outer x[-800,800] z[-800,200] with the notch
    x(-400,400), z(notch_z, 200] removed. Shared vertex rows => the column/bar
    junctions are true interior edges (no phantom boundary seams)."""
    xs = (-800, -400, 400, 800)
    verts = [(x, 0, z) for z in (200, notch_z, -800) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4),          # upper-left column
            (2, 3, 7), (2, 7, 6),          # upper-right column
            (4, 5, 9), (4, 9, 8),          # lower-left
            (5, 6, 10), (5, 10, 9),        # the bar under the notch
            (6, 7, 11), (6, 11, 10)]       # lower-right
    return bgi.BgiWalkmesh.from_bytes(bgi.build(verts, tris).to_bytes())


DEEP = u_mesh(-400)          # deep notch: a cross-notch round trip needs > 8 points
SHALLOW = u_mesh(-50)        # shallow notch: a 2-point patrol fits under the ceiling


def _sweep_clean(wmesh, pts, closed):
    from ff9mapkit.scene import routes as R
    return all(not leg["spans"] for leg in R.sweep_polyline(pts, wmesh, [], closed=closed))


# ------------------------------------------------------------ route_polyline core
def test_route_polyline_inserts_detour_and_sweeps_clean():
    naive = [(-600, 0), (600, 0)]                  # crosses the notch: jams
    assert not _sweep_clean(DEEP, naive, False)
    pts, inserted = pathfind.route_polyline(DEEP, naive, closed=False)
    assert pts[0] == (-600, 0) and pts[-1] == (600, 0)   # authored endpoints survive
    assert inserted and inserted[0][0] == 0 and len(pts) > 2
    assert _sweep_clean(DEEP, pts, False)          # the routed line is walkable
    # determinism: same input, same route
    assert pathfind.route_polyline(DEEP, naive, closed=False) == (pts, inserted)


def test_route_polyline_clear_leg_untouched():
    authored = [(-600, -600), (600, -600)]         # straight through the bar: clear
    pts, inserted = pathfind.route_polyline(DEEP, authored, closed=False)
    assert pts == authored and inserted == []


def test_route_polyline_offmesh_waypoint_refused():
    with pytest.raises(pathfind.RouteLegError, match="itself OFF"):
        pathfind.route_polyline(DEEP, [(-600, 0), (0, 0)])     # (0,0) is in the notch


def test_route_polyline_disconnected_floors_refused():
    two = bgi.BgiWalkmesh.from_bytes(bgi.build(
        [(-800, 0, 200), (-400, 0, 200), (-400, 0, -200), (-800, 0, -200),
         (400, 0, 200), (800, 0, 200), (800, 0, -200), (400, 0, -200)],
        [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)]).to_bytes())
    with pytest.raises(pathfind.RouteLegError, match="NO route"):
        pathfind.route_polyline(two, [(-600, 0), (600, 0)])


# ------------------------------------------------------------ the [behavior] plan
def _raw(do: dict, marker_path=((-600, 0), (600, 0))):
    return {
        "field": {"id": 30414, "name": "BTROUTE"},
        "player": {"spawn": [-600, -700]},
        "npc": [{"name": "g", "pos": [-600, 0], "dialogue": "x"}],
        "marker": [{"name": "chord", "pos": [-600, 0],
                    "path": [list(p) for p in marker_path]}],
        "behavior": {"unit": [{"npc": "g", "branch": [{"do": do}]}]},
    }


def test_autoroute_plan_march_and_deterministic_build():
    raw = _raw({"march": "chord", "route": "auto"})
    assert BT.validate(raw) == []
    assert BT.wants_autoroute(raw)
    plan = BT.autoroute_plan(raw, DEEP)
    p = plan[(0, 0)]
    assert p["verb"] == "march" and p["inserted"] and len(p["points"]) <= BT.ROUTE_CEILING
    assert _sweep_clean(DEEP, p["points"], False)
    lines = BT.describe_autoroute(plan, raw)
    assert lines and "auto-routed" in lines[0] and "'g'" in lines[0]
    h1 = BT.build(raw, npc_slots={"g": 2}, routed=plan).compile().stable_hash()
    h2 = BT.build(raw, npc_slots={"g": 2},
                  routed=BT.autoroute_plan(raw, DEEP)).compile().stable_hash()
    assert h1 == h2                                # same input => identical bytes
    # the compiled March carries the ROUTED points, not the authored pair
    fb = BT.build(raw, npc_slots={"g": 2}, routed=plan)
    march = [a for a in fb._collect_actions(fb.units["g"]) if isinstance(a, B.March)]
    assert march[0].points == tuple(tuple(q) for q in p["points"])


def test_autoroute_patrol_routes_the_wrap_leg():
    raw = _raw({"patrol": "chord", "route": "auto"},
               marker_path=((-600, 100), (600, 100)))
    plan = BT.autoroute_plan(raw, SHALLOW)
    p = plan[(0, 0)]
    legs_routed = [leg for leg, _ in p["inserted"]]
    assert legs_routed == [0, 1]                   # patrol always cycles: wrap leg too
    assert len(p["points"]) <= BT.ROUTE_CEILING
    assert _sweep_clean(SHALLOW, p["points"], True)
    fb = BT.build(raw, npc_slots={"g": 2}, routed=plan)
    fb.compile()                                   # fits the unrolled if-chain


def test_autoroute_ceiling_is_an_actionable_error():
    raw = _raw({"patrol": "chord", "route": "auto"})    # deep notch: 10 points round-trip
    with pytest.raises(BT.BehaviorTomlError) as e:
        BT.autoroute_plan(raw, DEEP)
    msg = str(e.value)
    assert "30414" in msg and "'g'" in msg and "'chord'" in msg
    assert "at most 8" in msg and "(-600,0)->(600,0)" in msg


def test_route_key_negatives():
    # route on a verb with no static leg origin: tailored refusal
    bad = _raw({"walk_to": [-600, -600], "route": "auto"})
    assert any("only applies to patrol/march" in p for p in BT.validate(bad))
    bad = _raw({"flee": "player", "to": "chord", "route": "auto"})
    assert any("only applies to patrol/march" in p for p in BT.validate(bad))
    # the only value is "auto"
    bad = _raw({"march": "chord", "route": "always"})
    assert any('the only value is "auto"' in p for p in BT.validate(bad))
    # route="auto" with no plan handed to build(): loud, never a silent skip
    raw = _raw({"march": "chord", "route": "auto"})
    with pytest.raises(BT.BehaviorTomlError, match="no autoroute plan"):
        BT.build(raw, npc_slots={"g": 2})
    # no walkmesh resolvable: the plan itself refuses
    with pytest.raises(BT.BehaviorTomlError, match="walkmesh"):
        BT.autoroute_plan(raw, None)


def test_no_route_key_stays_byte_identical():
    raw = _raw({"march": "chord"})
    assert not BT.wants_autoroute(raw)
    assert BT.autoroute_plan(raw, DEEP) == {}      # nothing to plan
    h_plain = BT.build(raw, npc_slots={"g": 2}).compile().stable_hash()
    h_empty = BT.build(raw, npc_slots={"g": 2}, routed={}).compile().stable_hash()
    assert h_plain == h_empty


# ------------------------------------------------------------ the product path
def test_build_script_clear_route_auto_is_byte_identical(tmp_path):
    """route="auto" on a route whose legs are all CLEAR compiles byte-identically to
    the same field without the key -- the opt-in changes nothing until a leg jams."""
    from ff9mapkit import build as BLD

    def field(route_opt: str) -> bytes:
        toml = (
            '[field]\nid = 30414\nname = "BTR"\narea = 11\n'
            "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
            '\n[[npc]]\nname = "g"\npreset = "vivi"\npos = [0, -100]\ndialogue = "Hup."\n'
            "\n[behavior]\nwarmup = 30\n"
            '\n[[behavior.unit]]\nnpc = "g"\n'
            "\n[[behavior.unit.branch]]\n"
            f"do = {{ march = [[0, -100], [100, -100]]{route_opt} }}\n"
        )
        f = tmp_path / f"btr{len(route_opt)}.field.toml"
        f.write_text(toml, encoding="utf-8")
        p = BLD.FieldProject.load(f)
        assert BLD.validate(p) == []
        return BLD.build_script(p, "us", {501: 501})

    assert field(', route = "auto"') == field("")
