"""Cutscene movement: named markers / entity refs for walk & teleport, and the build-time STALL check
(a field walk is synchronous + straight-line, so a target off the floor or a path across a wall hangs
the scene -- caught offline here). Pure (no game install needed); a quad walkmesh is built in-memory."""
from __future__ import annotations

import pytest

from ff9mapkit import build
from ff9mapkit.scene import bgi


def _quad_wmesh():
    # a flat floor covering x[-500,500] z[-800,200] (world coords, org 0 -> world == verts)
    corners = [(-500, 0, 200), (500, 0, 200), (500, 0, -800), (-500, 0, -800)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(corners, [(0, 1, 2), (0, 2, 3)]).to_bytes())


def _load(body, tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(body, encoding="utf-8")
    return build.FieldProject.load(p)


# --- the position registry + name resolution ----------------------------------------------
def test_registry_collects_player_npc_marker(tmp_path):
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[10,20]\n'
                 '[[npc]]\nname="Vivi"\npos=[100,-200]\n[[marker]]\nname="door"\npos=[0,-700]\n', tmp_path)
    reg = build._position_registry(proj)
    assert reg["player"] == (10, 20) and reg["spawn"] == (10, 20)
    assert reg["Vivi"] == (100, -200) and reg["door"] == (0, -700)


def test_resolve_point_passthrough_name_and_at():
    reg = {"door": (0, -700), "player": (10, 20), "Vivi": (100, -200)}
    assert build._resolve_point([5, 6], reg) == (5, 6)        # coord passthrough
    assert build._resolve_point("door", reg) == (0, -700)     # marker name
    assert build._resolve_point("@player", reg) == (10, 20)   # @ entity ref
    assert build._resolve_point("@Vivi", reg) == (100, -200)
    with pytest.raises(ValueError):
        build._resolve_point("nowhere", reg)


def test_resolve_move_steps_resolves_walk_and_teleport():
    class P:
        raw = {"player": {"spawn": [10, 20]}, "marker": [{"name": "door", "pos": [0, -700]}]}
    steps = [{"walk": "door"}, {"teleport": "@player"}, {"walk": [1, 2]}, {"say": "hi"}]
    out = build._resolve_move_steps(steps, P())
    assert out[0] == {"walk": [0, -700]}
    assert out[1] == {"teleport": [10, 20]}
    assert out[2] == {"walk": [1, 2]} and out[3] == {"say": "hi"}


# --- the stall geometry check -------------------------------------------------------------
def test_segment_leaves_floor_detects_exit_but_allows_walk_in():
    wm = _quad_wmesh()
    assert build._segment_leaves_floor(wm, (0, -300), (0, 100)) is False    # stays inside
    assert build._segment_leaves_floor(wm, (0, -300), (0, 900)) is True     # exits the floor (+z past 200)
    assert build._segment_leaves_floor(wm, (0, 900), (0, -300)) is False    # walk-IN from off-screen is ok


def test_walk_to_object_stops_short(tmp_path):
    # walking TO @player must stop just outside the player's collision box (walking onto it stalls)
    from ff9mapkit.scene import cam
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-520]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[800,-520]\n'
                 '[cutscene]\nactor="V"\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    out = build._resolve_move_steps(proj.raw["cutscene"]["steps"], proj, proj.raw["npc"][0])
    tx, tz = out[0]["walk"]
    assert 0 < tx < 800                                          # stopped between the actor and the player
    d = ((tx - 0) ** 2 + (tz + 520) ** 2) ** 0.5
    assert abs(d - (2 * cam.OBJECT_COLLISION_W + build._APPROACH_MARGIN)) < 2   # just outside the box
    # a plain marker (not an object) is NOT offset -- it's an exact point the author chose
    proj2 = _load('[field]\nid=4003\nname="X"\narea=11\n[[npc]]\nname="V"\npos=[800,-520]\n'
                  '[[marker]]\nname="x"\npos=[0,-520]\n[cutscene]\nactor="V"\nsteps=[ { walk = "x" } ]\n', tmp_path)
    out2 = build._resolve_move_steps(proj2.raw["cutscene"]["steps"], proj2, proj2.raw["npc"][0])
    assert out2[0]["walk"] == [0, -520]


def test_validate_warns_walk_into_object_box(tmp_path):
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-300]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[0,-700]\n[[marker]]\nname="onplayer"\npos=[0,-300]\n')
    bad = _load(body + '[cutscene]\nactor="V"\nsteps=[ { walk = "onplayer" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(bad, wm, w)
    assert any("collision box" in m for m in w)
    good = _load(body + '[cutscene]\nactor="V"\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    w2 = []
    build._validate_cutscene_movement(good, wm, w2)
    assert not any("collision box" in m for m in w2)            # @player auto-approaches -> no stall


def test_validate_warns_path_through_object(tmp_path):
    # endpoints clear, but the straight path grazes a standing character's box -> stalls mid-walk
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-150]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[-400,0]\n[[marker]]\nname="far"\npos=[400,0]\n'
            '[cutscene]\nactor="V"\nsteps=[ { walk = "far" } ]\n')
    proj = _load(body, tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert any("passes through" in m for m in w)


def test_walk_up_to_object_does_not_falseflag_its_own_approach(tmp_path):
    # a walk TO @player (auto-stopped at ~232) must NOT itself be flagged as passing through the box
    wm = _quad_wmesh()
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-700]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n'
                 '[cutscene]\nactor="V"\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert not any("collision box" in m or "passes through" in m for m in w)


# --- multi-waypoint path -----------------------------------------------------------------
def test_resolve_path_resolves_each_waypoint(tmp_path):
    import math
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-700]\n'
                 '[[npc]]\nname="V"\npos=[-900,-700]\n'
                 '[[marker]]\nname="a"\npos=[-400,-200]\n[[marker]]\nname="b"\npos=[400,-200]\n'
                 '[cutscene]\nactor="V"\nsteps=[ { path = ["a", "b", "@player"] } ]\n', tmp_path)
    out = build._resolve_move_steps(proj.raw["cutscene"]["steps"], proj, proj.raw["npc"][0])
    p = out[0]["path"]
    assert p[0] == [-400, -200] and p[1] == [400, -200]        # markers are exact
    assert math.dist(p[2], [0, -700]) > 192                    # last @player waypoint stops short of the box


def test_path_compiles_to_consecutive_walks():
    from ff9mapkit.content import cutscene as cs
    two_walks = cs.compile_steps([{"walk": [0, 0]}, {"walk": [100, 0]}], [])
    one_path = cs.compile_steps([{"path": [[0, 0], [100, 0]]}], [])
    assert one_path == two_walks                               # a 2-point path == two walks


def test_validate_flags_unknown_path_waypoint(tmp_path):
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[camera]\nborrow="c.bgx"\n'
                 '[walkmesh]\nquad=[[0,0],[10,0],[10,10],[0,10]]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n'
                 '[cutscene]\nactor="V"\nsteps=[ { path = ["ghost"] } ]\n', tmp_path)
    assert any("ghost" in m for m in build.validate(proj))


def test_validate_path_legs_checked_for_stall(tmp_path):
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-150]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[-400,0]\n'
            '[[marker]]\nname="mid"\npos=[-400,-300]\n[[marker]]\nname="far"\npos=[400,0]\n'
            '[cutscene]\nactor="V"\nsteps=[ { path = ["mid","far"] } ]\n')   # 2nd leg grazes the player
    proj = _load(body, tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert any("passes through" in m for m in w)


def test_validate_cutscene_movement_warns_offmesh_and_clean(tmp_path):
    wm = _quad_wmesh()
    base = ('[field]\nid=4003\nname="X"\narea=11\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[0,-300]\n'
            '[[marker]]\nname="far"\npos=[0,5000]\n[[marker]]\nname="near"\npos=[0,0]\n')
    bad = _load(base + '[cutscene]\nactor="V"\nsteps=[ { walk = "far" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(bad, wm, w)
    assert any("off the walkmesh" in m for m in w)
    good = _load(base + '[cutscene]\nactor="V"\nsteps=[ { walk = "near" } ]\n', tmp_path)
    w2 = []
    build._validate_cutscene_movement(good, wm, w2)
    assert w2 == []


# --- validate(): markers + named targets resolve -----------------------------------------
def test_validate_flags_unknown_move_target(tmp_path):
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[camera]\nborrow="c.bgx"\n'
                 '[walkmesh]\nquad=[[0,0],[10,0],[10,10],[0,10]]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n'
                 '[cutscene]\nactor="V"\nsteps=[ { walk = "ghost" } ]\n', tmp_path)
    assert any("ghost" in m for m in build.validate(proj))


def test_validate_accepts_marker_target_and_flags_bad_marker(tmp_path):
    ok = _load('[field]\nid=4003\nname="X"\narea=11\n[camera]\nborrow="c.bgx"\n'
               '[walkmesh]\nquad=[[0,0],[10,0],[10,10],[0,10]]\n'
               '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n[[marker]]\nname="spot"\npos=[5,5]\n'
               '[cutscene]\nactor="V"\nsteps=[ { walk = "spot" } ]\n', tmp_path)
    assert not any("spot" in m and "isn't" in m for m in build.validate(ok))
    bad = _load('[field]\nid=4003\nname="X"\narea=11\n[[marker]]\npos=[1,2]\n', tmp_path)
    assert any("[[marker]]" in m for m in build.validate(bad))
