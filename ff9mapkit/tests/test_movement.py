"""Cutscene movement: named markers / entity refs for walk & teleport, and the build-time STALL check
(a field walk is synchronous + straight-line, so a target off the floor or a path across a wall hangs
the scene -- caught offline here). Pure (no game install needed); a quad walkmesh is built in-memory."""
from __future__ import annotations

import pytest

from ff9mapkit import build
from ff9mapkit.scene import bgi
from ff9mapkit.content import pathfind


def _quad_wmesh():
    # a flat floor covering x[-500,500] z[-800,200] (world coords, org 0 -> world == verts)
    corners = [(-500, 0, 200), (500, 0, 200), (500, 0, -800), (-500, 0, -800)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(corners, [(0, 1, 2), (0, 2, 3)]).to_bytes())


def _big_wmesh():
    # a roomy floor (the _spk demo room) -- space to route around an obstacle
    c = [(-1220, 0, 257), (1220, 0, 257), (1220, 0, -1931), (-1220, 0, -1931)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(c, [(0, 1, 2), (0, 2, 3)]).to_bytes())


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
                 '[cutscene]\nactors=["V"]\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    out = build._resolve_move_steps(proj.raw["cutscene"]["steps"], proj, proj.raw["npc"][0])
    tx, tz = out[0]["walk"]
    assert 0 < tx < 800                                          # stopped between the actor and the player
    d = ((tx - 0) ** 2 + (tz + 520) ** 2) ** 0.5
    assert abs(d - (2 * cam.OBJECT_COLLISION_W + build._APPROACH_MARGIN)) < 2   # just outside the box
    # a plain marker (not an object) is NOT offset -- it's an exact point the author chose
    proj2 = _load('[field]\nid=4003\nname="X"\narea=11\n[[npc]]\nname="V"\npos=[800,-520]\n'
                  '[[marker]]\nname="x"\npos=[0,-520]\n[cutscene]\nactors=["V"]\nsteps=[ { walk = "x" } ]\n', tmp_path)
    out2 = build._resolve_move_steps(proj2.raw["cutscene"]["steps"], proj2, proj2.raw["npc"][0])
    assert out2[0]["walk"] == [0, -520]


def test_validate_warns_walk_into_object_box(tmp_path):
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-300]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[0,-700]\n[[marker]]\nname="onplayer"\npos=[0,-300]\n')
    bad = _load(body + '[cutscene]\nactors=["V"]\nsteps=[ { walk = "onplayer" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(bad, wm, w)
    assert any("collision box" in m for m in w)
    good = _load(body + '[cutscene]\nactors=["V"]\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    w2 = []
    build._validate_cutscene_movement(good, wm, w2)
    assert not any("collision box" in m for m in w2)            # @player auto-approaches -> no stall


def test_walk_blocked_by_character_is_autorouted(tmp_path):
    # a WALK whose straight path grazes a character is now AUTO-ROUTED around it (not warned) -- the
    # increment-3 behavior (an explicit `path` is still checked per-leg; see the path test below).
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-150]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[-400,0]\n[[marker]]\nname="far"\npos=[400,0]\n'
            '[cutscene]\nactors=["V"]\nsteps=[ { walk = "far" } ]\n')
    proj = _load(body, tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert w == []                                             # routed around the player -> no warning


def test_validate_warns_when_no_route(tmp_path):
    # a thin corridor fully plugged by a character -> no route exists -> the walk stays -> still warns
    c = [(-500, 0, 40), (500, 0, 40), (500, 0, -40), (-500, 0, -40)]
    wm = bgi.BgiWalkmesh.from_bytes(bgi.build(c, [(0, 1, 2), (0, 2, 3)]).to_bytes())
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,0]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[-400,0]\n[[marker]]\nname="far"\npos=[400,0]\n'
            '[cutscene]\nactors=["V"]\nsteps=[ { walk = "far" } ]\n')
    proj = _load(body, tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert any("passes through" in m or "off the walkmesh" in m for m in w)


def test_walk_up_to_object_does_not_falseflag_its_own_approach(tmp_path):
    # a walk TO @player (auto-stopped at ~232) must NOT itself be flagged as passing through the box
    wm = _quad_wmesh()
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-700]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n'
                 '[cutscene]\nactors=["V"]\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert not any("collision box" in m or "passes through" in m for m in w)


# --- multi-waypoint path -----------------------------------------------------------------
def test_resolve_path_resolves_each_waypoint(tmp_path):
    import math
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-700]\n'
                 '[[npc]]\nname="V"\npos=[-900,-700]\n'
                 '[[marker]]\nname="a"\npos=[-400,-200]\n[[marker]]\nname="b"\npos=[400,-200]\n'
                 '[cutscene]\nactors=["V"]\nsteps=[ { path = ["a", "b", "@player"] } ]\n', tmp_path)
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
                 '[cutscene]\nactors=["V"]\nsteps=[ { path = ["ghost"] } ]\n', tmp_path)
    assert any("ghost" in m for m in build.validate(proj))


def test_validate_path_legs_checked_for_stall(tmp_path):
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-150]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[-400,0]\n'
            '[[marker]]\nname="mid"\npos=[-400,-300]\n[[marker]]\nname="far"\npos=[400,0]\n'
            '[cutscene]\nactors=["V"]\nsteps=[ { path = ["mid","far"] } ]\n')   # 2nd leg grazes the player
    proj = _load(body, tmp_path)
    w = []
    build._validate_cutscene_movement(proj, wm, w)
    assert any("passes through" in m for m in w)


# --- auto-pathing -------------------------------------------------------------------------
def test_pathfind_routes_around_obstacle():
    # The radii are read from the constants `route()` ITSELF defaults to, not re-pinned as literals:
    # this test used to hardcode 48, which stopped being the wall radius when the in-game measurement
    # (2026-07-30, calibration field 30510) corrected `cam.COLLISION_RADIUS_W` 48 -> 80. A stale
    # literal here checks a radius nothing uses.
    from ff9mapkit.scene import cam, routes
    R, OBS_R = cam.COLLISION_RADIUS_W, 2 * cam.OBJECT_COLLISION_W
    wm = _big_wmesh()
    straight_clear = pathfind._clear(wm, (-900, -700), (900, -700), [(0, -700)], R, OBS_R)
    assert not straight_clear                                   # a straight line hits the player
    r = pathfind.route(wm, (-900, -700), (900, -700), obstacles=[(0, -700)])
    assert r and len(r) > 1                                     # a multi-leg detour
    pts = [(-900, -700)] + r
    assert all(pathfind._clear(wm, pts[i], pts[i + 1], [(0, -700)], R, OBS_R) for i in range(len(pts) - 1))
    # ...and the same invariant measured EXACTLY, independent of `_clear`'s own sampling -- the
    # regression this file caught was a leg passing 188.6u from the obstacle centre that `_clear`'s
    # 80u-stepped sample walked straight over. An oracle that shares the code under test cannot see that.
    assert all(routes.seg_dist_xz(0, -700, pts[i], pts[i + 1]) >= OBS_R
               for i in range(len(pts) - 1))
    assert r[-1] == (900, -700)                                 # ends at the exact goal


def test_autoroute_converts_blocked_walk_to_path(tmp_path):
    wm = _big_wmesh()
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-700]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[-900,-700]\n'
                 '[[marker]]\nname="goal"\npos=[900,-700]\n'
                 '[cutscene]\nactors=["V"]\nsteps=[ { walk = "goal" } ]\n', tmp_path)
    actor = proj.raw["npc"][0]
    steps = build._resolve_move_steps(proj.raw["cutscene"]["steps"], proj, actor)
    routed = build._autoroute_steps(steps, proj, wm, actor)
    assert "path" in routed[0] and "walk" not in routed[0]      # a blocked walk became a route
    assert len(routed[0]["path"]) > 1
    w = []
    build._validate_cutscene_movement(proj, wm, w)              # the routed result validates clean
    assert w == []


def test_autoroute_leaves_clear_walk_untouched(tmp_path):
    wm = _big_wmesh()
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[-900,-700]\n'
                 '[[marker]]\nname="g"\npos=[-900,-200]\n'      # a clear straight line, no obstacles
                 '[cutscene]\nactors=["V"]\nsteps=[ { walk = "g" } ]\n', tmp_path)
    actor = proj.raw["npc"][0]
    steps = build._resolve_move_steps(proj.raw["cutscene"]["steps"], proj, actor)
    assert build._autoroute_steps(steps, proj, wm, actor) == [{"walk": [-900, -200]}]   # unchanged


def test_validate_cutscene_movement_warns_offmesh_and_clean(tmp_path):
    wm = _quad_wmesh()
    base = ('[field]\nid=4003\nname="X"\narea=11\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[0,-300]\n'
            '[[marker]]\nname="far"\npos=[0,5000]\n[[marker]]\nname="near"\npos=[0,0]\n')
    bad = _load(base + '[cutscene]\nactors=["V"]\nsteps=[ { walk = "far" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(bad, wm, w)
    assert any("off the walkmesh" in m for m in w)
    good = _load(base + '[cutscene]\nactors=["V"]\nsteps=[ { walk = "near" } ]\n', tmp_path)
    w2 = []
    build._validate_cutscene_movement(good, wm, w2)
    assert w2 == []


# --- validate(): markers + named targets resolve -----------------------------------------
def test_validate_flags_unknown_move_target(tmp_path):
    proj = _load('[field]\nid=4003\nname="X"\narea=11\n[camera]\nborrow="c.bgx"\n'
                 '[walkmesh]\nquad=[[0,0],[10,0],[10,10],[0,10]]\n'
                 '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n'
                 '[cutscene]\nactors=["V"]\nsteps=[ { walk = "ghost" } ]\n', tmp_path)
    assert any("ghost" in m for m in build.validate(proj))


def test_validate_accepts_marker_target_and_flags_bad_marker(tmp_path):
    ok = _load('[field]\nid=4003\nname="X"\narea=11\n[camera]\nborrow="c.bgx"\n'
               '[walkmesh]\nquad=[[0,0],[10,0],[10,10],[0,10]]\n'
               '[[npc]]\nname="V"\npreset="vivi"\npos=[0,0]\n[[marker]]\nname="spot"\npos=[5,5]\n'
               '[cutscene]\nactors=["V"]\nsteps=[ { walk = "spot" } ]\n', tmp_path)
    assert not any("spot" in m and "isn't" in m for m in build.validate(ok))
    bad = _load('[field]\nid=4003\nname="X"\narea=11\n[[marker]]\npos=[1,2]\n', tmp_path)
    assert any("[[marker]]" in m for m in build.validate(bad))


# --- rotating-cast beat filtering (the stolen-ember composition finding) -------------------
def test_window_excluded_npc_is_not_an_obstacle(tmp_path):
    # Two NPCs share one spot with ADJACENT scenario windows (the rotating-cast idiom): a scene gated
    # at one window must NOT see the other window's NPC as an obstacle -- they never coexist. Ungated
    # scenes and window-overlapping NPCs still warn (fail-safe).
    wm = _quad_wmesh()
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-700]\n'
            '[[npc]]\nname="early"\npreset="vivi"\npos=[0,0]\nscenario_min=100\nscenario_max=300\n'
            '[[npc]]\nname="late"\npreset="vivi"\npos=[-60,40]\nscenario_min=300\n')
    # the early NPC's scene (beat 100): walking @player from (0,0) grazes 'late' at (-60,40)?
    # place 'late' ON the walk line so an unfiltered check would flag it.
    body = body.replace('pos=[-60,40]', 'pos=[0,-350]')
    gated = _load(body + '[[cutscene]]\nactors=["early"]\nrequires_scenario=100\n'
                         'steps=[ { walk = "@player" } ]\n', tmp_path)
    w = []
    build._validate_cutscene_movement(gated, wm, w)
    assert not any("'late'" in m for m in w)               # window-excluded -> not an obstacle
    # the SAME scene ungated: 'late' may coexist -> the walk is routed or warned (not silently ignored)
    ungated = _load(body + '[[cutscene]]\nactors=["early"]\nsteps=[ { walk = "@player" } ]\n', tmp_path)
    w2 = []
    build._validate_cutscene_movement(ungated, wm, w2)
    ok2 = build._obstacle_points(ungated, "early")          # unfiltered: 'late' IS an obstacle point
    assert (0, -350) in ok2
    # and the beat filter itself:
    assert build._npc_coexists_at_beat({"scenario_min": 300}, 100) is False
    assert build._npc_coexists_at_beat({"scenario_min": 100, "scenario_max": 300}, 100) is True
    assert build._npc_coexists_at_beat({"scenario_min": 100, "scenario_max": 300}, 300) is False
    assert build._npc_coexists_at_beat({}, 100) is True     # no window -> always present
    assert build._npc_coexists_at_beat({"scenario_min": 300}, None) is True   # ungated scene -> obstacle


def test_lint_logic_external_settable_suppresses_cross_member_gate(tmp_path):
    # A campaign member's gate is routinely opened by a SIBLING field's write: with the campaign-wide
    # producer set threaded in (build_campaign -> project.external_settable), the member-scoped
    # dangling-gate warning must not false-positive; without it, it still fires (standalone builds).
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-300]\n'
            '[[gateway]]\nto=4004\nentrance=0\nzone=[[0,0],[100,0],[100,100],[0,100]]\n'
            'requires_flag=8624\n')
    proj = _load(body, tmp_path)
    assert any("requires flag 8624" in m for m in build.lint_logic(proj))
    proj.external_settable = frozenset({8624})
    assert not any("requires flag 8624" in m for m in build.lint_logic(proj))


def test_cast_scene_injects_control_watchdog(tmp_path):
    # The control WATCHDOG (in-game diagnosed 2026-07-12): a field with an owns-control cast scene gets ONE
    # shared concurrent entry that re-locks a late engine control grant while the scene-running MAP flag is
    # up; the conductor raises/lowers that flag around its body. A slow (Moguri'd/scrolling) field entry can
    # outlive the conductor's spin cap -- without the watchdog the late grant hands the player control
    # mid-scene, and walking into an actor's synchronous walk path stalls the scene forever.
    from ff9mapkit.content import conductor as _conductor, region as _region
    from ff9mapkit.eb import EbScript
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-300]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[0,-700]\n'
            '[cutscene]\nactors=["V"]\nsteps=[ { say = "hi" } ]\n')
    proj = _load(body, tmp_path)
    data = build.build_script(proj, "us", {}, cutscene_txids=[500])
    eb = EbScript.from_bytes(data)
    flag = _conductor.WATCHDOG_MAP_FLAG
    poll = bytes([0x05, _region.MAP_BOOL, flag & 0xFF, (flag >> 8) & 0xFF])  # SET({Map.Bit[110] ...
    bodies = [(e.index, data[e.funcs[0].abs_start:e.funcs[0].abs_end])
              for e in eb.entries if not e.empty and e.funcs]
    wd = [i for i, b in bodies if poll[:2] in b and b.count(0x2D)]           # the Map.Bit poll + DisableMove
    assert wd, "no watchdog entry found"
    # the conductor raises + lowers the scene-running flag around its body
    raise_bytes = _region.set_var(_region.MAP_BOOL, flag, 1)
    lower_bytes = _region.set_var(_region.MAP_BOOL, flag, 0)
    assert any(raise_bytes in b and lower_bytes in b for _i, b in bodies), "conductor doesn't drive the flag"
    # a field with NO cast scene ships no watchdog (byte-identity guarded by the golden too)
    plain = _load('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-300]\n', tmp_path)
    data2 = build.build_script(plain, "us", {})
    assert poll[:3] not in data2


def test_walk_to_live_object_compiles_as_engine_follow(tmp_path):
    # A walk to a LIVE object (@player / an NPC name) compiles as WalkTowardObject (0x24 MOVA): the engine
    # walks to the target's LIVE position and ends ON CONTACT with it -- so the followed target can never
    # block the walk (in-game 2026-07-12: a static build-time target let a one-frame input window brick the
    # scene). A walk to plain coords / a marker stays a static Walk.
    from ff9mapkit.eb import EbScript
    body = ('[field]\nid=4003\nname="X"\narea=11\n[player]\nspawn=[0,-300]\n'
            '[[npc]]\nname="V"\npreset="vivi"\npos=[0,-700]\n'
            '[[marker]]\nname="spot"\npos=[100,-500]\n'
            '[cutscene]\nactors=["V"]\nsteps=[ { walk = "@player" }, { say = "hi" }, { walk = "spot" } ]\n')
    proj = _load(body, tmp_path)
    data = build.build_script(proj, "us", {}, cutscene_txids=[500])
    eb = EbScript.from_bytes(data)
    npc_entry = next(e for e in eb.entries if not e.empty and e.func_by_tag(20) is not None)
    tags = {}
    for f in npc_entry.funcs:
        if f.tag >= 20:
            tags[f.tag] = [(i.op, [i.imm(k) for k in range(len(i.args))]) for i in eb.instrs(f)]
    assert (0x24, [250]) in tags[20]                      # walk-up = WalkTowardObject(player) -- follow
    assert not any(op == 0x23 for op, _a in tags[20])     # no static Walk in the follow tag
    assert any(op == 0x23 for op, _a in tags[21])         # the marker walk stays a static Walk
