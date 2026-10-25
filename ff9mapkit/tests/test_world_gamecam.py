"""The game's own world camera, decoded (overworld editor C7): Memoria.ini's [Worldmap], the posstat conversion and its
blends, the settled pose, the eye's lift over the terrain, and THE HANDEDNESS the renderer now shares with the game
(measured against nine in-game stills, studies/overworld-editor/C7.md: render.py had drawn the game's mirror image)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from ff9mapkit.world import gamecam as G
from ff9mapkit.world import render as R


def test_settings_read_the_user_s_worldmap_section():
    ini = ("[Graphics]\nFieldOfView = 99\n[Worldmap]\n\t; FieldOfView (default 44, max 160)\n"
           "FieldOfView = 58\nCameraDistance = 120 ; wider\nCameraHeight=90\n[Next]\nCameraAimHeight = 5\n")
    s = G.Settings.from_ini(ini)
    assert (s.field_of_view, s.camera_distance, s.camera_height, s.camera_aim_height) == (58.0, 120.0, 90.0, 100.0)
    assert G.Settings.from_ini("") == G.Settings()


def test_the_posstats_convert_as_the_constructor_does():
    assert G.posstat(1) == (350.0, 6000 / 256, 3200 / 256, 3000 / 256, 1200 / 256)   # heights flip sign: PSX y ran down
    assert len(G.POSSTAT_RAW) == 10 and len(G.AREA2PLACE) == 64
    assert [G.AREA2PLACE[a] for a in (14, 27, 39, 40, 45, 46, 51, 63)] == [0, 2, 2, 1, 1, 0, 2, 2]


def test_the_altitude_and_tilt_blends():
    assert G.height_param(-10.0) == 0 and G.height_param(40.0) == 4096
    assert G.height_param(3.2) == int((int(3.2 * 256) + 1000) * 4096 / 4500)
    assert G.tilt_param(0) == 0 and G.tilt_param(4096) == 4096 and 0 < G.tilt_param(2048) < 4096
    low = G.blend(-10.0, area=14)                                # all the way "down": posstat 0 on foot, place 0
    assert low == pytest.approx(G.posstat(0))
    assert G.blend(-10.0, area=42) == pytest.approx(G.posstat(3))  # stock grass at the Landing Site: place 1
    assert G.blend(-10.0, area=14, upper_counter=4096) == pytest.approx(G.posstat(7))   # tilted up: the fly pose


def test_the_settled_pose():
    s = G.Settings(field_of_view=58.0)
    v = G.pose((100.0, 3.2, -200.0), 0.0, settings=s, area=14)
    pers, dist, height, correct, aim = G.blend(3.2, area=14)
    assert v["eye"] == pytest.approx((100.0, 3.2 + height + G.TWEAK_EYE_Y, -200.0 + dist))   # yaw 0: eye at +z
    assert v["at"] == pytest.approx((100.0, 3.2 + aim + G.TWEAK_AIM_Y, -200.0))
    assert v["fov"] == pytest.approx(pers / 8.0 * 58.0 / 44.0)
    v90 = G.pose((100.0, 3.2, -200.0), 90.0, settings=s, area=14)
    assert v90["eye"][0] == pytest.approx(100.0 + dist) and v90["eye"][2] == pytest.approx(-200.0)
    wide = G.pose((100.0, 3.2, -200.0), 0.0, settings=G.Settings(camera_distance=150.0), area=14)
    assert wide["eye"][2] == pytest.approx(-200.0 + dist * 1.5)


def test_the_eye_lifts_over_high_ground():
    v = G.pose((0.0, 3.2, 0.0), 0.0, area=14, ground=lambda x, z: 20.0 if z > 5.0 else 3.2)
    correct = G.blend(3.2, area=14)[3]
    assert v["eye"][1] == pytest.approx(correct + 20.0 + G.TWEAK_EYE_Y) and v["game"]["lifted"] > 0
    # on its own lawn too: cameraCorrect (11.7u) outranks cameraHeight (~8.9u) on foot, so the eye rests at the ground
    # plus cameraCorrect (the river stills measured the same 2.81u lift); only ground well below the party does not
    flat = G.pose((0.0, 3.2, 0.0), 0.0, area=14, ground=lambda x, z: 3.2)
    assert flat["eye"][1] == pytest.approx(correct + 3.2 + G.TWEAK_EYE_Y)
    low = G.pose((0.0, 3.2, 0.0), 0.0, area=14, ground=lambda x, z: -10.0)
    assert low["game"]["lifted"] == 0.0
    capped = G.pose((0.0, 3.2, 0.0), 0.0, area=14, ground=lambda x, z: 90.0)
    assert capped["eye"][1] == pytest.approx(correct + G.TERRAIN_CAP + G.TWEAK_EYE_Y)


def test_the_renderer_draws_in_the_game_s_handedness():
    """Unity's LookAt frame is left-handed: looking along +z, +x is screen-right. render.py drew fwd x Y, the mirror;
    nine in-game stills chose this frame 9 of 9 (C7.md). A point to the camera's right must land right of centre."""
    view = {"kind": "persp", "eye": (0.0, 10.0, 0.0), "at": (0.0, 10.0, 10.0), "fov": 60.0}
    sx, sy, _d = R.project(view, np.array([[5.0, 10.0, 10.0], [0.0, 15.0, 10.0]]), (100, 100))
    assert sx[0] > 50.0 and sy[1] < 50.0                        # +x right, +y up
    v = G.pose((0.0, 3.2, 0.0), 0.0, area=14)                    # the game camera at yaw 0 looks toward -z
    sx, _sy, _d = R.project(v, np.array([[-5.0, 3.2, -10.0]]), (100, 100))
    assert sx[0] > 50.0                                           # so -x is on its right, as in the game
    assert math.isclose(G.s_pct(58), 0.58)


# ---------------------------------------------------------------- C8: the vehicles
def test_the_transport_table_is_read_through_the_stack(tmp_path):
    game = tmp_path / "game"
    stock = game / "StreamingAssets" / "Data" / "World"
    stock.mkdir(parents=True)
    head = "# type;...\n"
    (stock / "TransportControls.csv").write_text(head + "".join(
        f"{t};0;0;0;0;0;0;0;0;0;0;0;0;0;0;{c};0;0;0;# row\n" for t, c in G.TRANSPORT.values()), encoding="utf-8")
    assert G.transport_table(game) == G.TRANSPORT                      # no FolderNames: the base game's
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "MINE"\n', encoding="utf-8")
    mine = game / "MINE" / "StreamingAssets" / "Data" / "World"
    mine.mkdir(parents=True)
    rows = {**G.TRANSPORT, 10: (0, 0)}
    (mine / "TransportControls.csv").write_text(head + "".join(
        f"{t};0;0;0;0;0;0;0;0;0;0;0;0;0;0;{c};0;0;0;\n" for t, c in rows.values()), encoding="utf-8")
    assert G.transport_table(game)[10] == (0, 0)                       # the mod folder's row wins, as in Memoria
    assert G.transport_table(None) == G.TRANSPORT


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_a_transport_table_with_a_byte_order_mark_reads_as_the_game_reads_it(tmp_path, encoding):
    """Memoria reads TransportControls.csv through the same StreamReader as the weather table, which strips a
    byte-order mark; the kit kept it, read the first comment line as row 0, and fell back to the stock rows, so the
    game camera posed a mod's vehicle with the stock camera (review of the C18 fixes, fourth round)."""
    game = tmp_path / "game"
    (game / "StreamingAssets" / "Data" / "World").mkdir(parents=True)
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "MINE"\n', encoding="utf-8")
    mine = game / "MINE" / "StreamingAssets" / "Data" / "World"
    mine.mkdir(parents=True)
    rows = {**G.TRANSPORT, 1: (0, 4)}                                    # the yellow chocobo, another camera row
    (mine / "TransportControls.csv").write_bytes(("# type;...\n" + "".join(
        f"{t};0;0;0;0;0;0;0;0;0;0;0;0;0;0;{c};0;0;0;\n" for t, c in rows.values())).encode(encoding))
    assert G.transport_table(game)[1] == (0, 4)


def test_each_vehicle_s_camera():
    s = G.Settings(field_of_view=58.0)
    p = (500.0, 3.2, -500.0)
    foot, choco = G.pose(p, 0.0, settings=s, mode=0), G.pose(p, 0.0, settings=s, mode=1)
    assert choco["game"]["type_cam"] == 1 and choco["eye"] != foot["eye"]        # its own element row
    forest = G.pose(p, 0.0, settings=s, mode=1, topograph=37)
    assert forest["fov"] == 58.0 and choco["fov"] != 58.0                       # over forest: FieldOfView itself
    boat = G.pose((500.0, -0.703, -500.0), 0.0, settings=s, mode=7, how="loaded")   # as C8 met it: loaded aboard
    pers = boat["game"]["pers"]
    assert boat["fov"] == pytest.approx(pers / 9.5 * 58.0 / 44.0)              # the Blue Narciss divides by 9.5
    assert boat["eye"][1] - boat["game"]["height"] == pytest.approx(-0.703 + 320 / 256.0)
    assert boat["at"][1] == pytest.approx(-0.703 + boat["game"]["aim"] + 701 / 256.0)
    air = G.pose((500.0, 3.0, -500.0), 0.0, settings=s, mode=8, how="loaded")
    assert air["game"]["type"] == 1 and air["fov"] == 58.0                     # flight: FieldOfView itself
    assert air["eye"][1] >= G.FLYER_EYE_FLOOR + 1419 / 256.0 - 1e-9             # the flyer's eye floor
    high = G.pose((500.0, 40.0, -500.0), 0.0, settings=s, mode=8, how="loaded")
    assert high["eye"][1] == pytest.approx(40.0 + high["game"]["height"] + 1419 / 256.0)
    gold = G.pose(p, 0.0, settings=s, mode=6)
    gold_up = G.pose(p, 0.0, settings=s, mode=6, how="pepper")
    assert gold_up["eye"][1] - gold["eye"][1] == pytest.approx((1419 - 558) / 256.0)   # the Dead Pepper's nudge
    assert gold_up["at"][1] - gold["at"][1] == pytest.approx((996 - 312) / 256.0)
    assert gold["game"]["fix"] == G.WALK_Y and gold_up["game"]["fix"] == G.RISEN_Y


#: C21's in-game verdicts (c21_lab.py; evidence/c21): (mode, how, dispatcher) -> the nudge target the stills chose
C21_MEASURED = {(6, "boarded", 9007): G.WALK_Y, (6, "pepper", 9007): G.RISEN_Y, (8, "boarded", 9007): G.WALK_Y,
                (6, "boarded", 9008): G.RISEN_Y, (6, "pepper", 9008): G.RISEN_Y, (9, "boarded", 9008): G.RISEN_Y,
                (7, "boarded", 9003): G.WALK_Y, (1, "boarded", 9007): G.WALK_Y,
                (8, "loaded", 9007): G.RISEN_Y, (7, "loaded", 9003): G.BOAT_Y}       # the last two: C8's


@pytest.mark.parametrize("key", sorted(C21_MEASURED))
def test_the_nudge_target_is_what_the_game_drew(key):
    mode, how, world = key
    assert G.fix_target(mode, how=how, world=world) == C21_MEASURED[key]


def test_the_nudge_target_by_disc_and_its_refusals():
    assert G.dispatcher_for(7) == 9003 and G.dispatcher_for(8) == 9007 and G.dispatcher_for(6, disc=4) == 9008
    assert G.fix_target(6) == G.WALK_Y and G.fix_target(6, disc=4) == G.RISEN_Y     # one take-off, two worlds
    assert G.fix_target(7, disc=4) == G.BOAT_Y                                        # 9008 boards no boat by tag 21
    with pytest.raises(ValueError):
        G.fix_target(8, how="pepper")
    with pytest.raises(ValueError):
        G.fix_target(6, how="airborne")
    p = (500.0, 20.0, -500.0)
    assert G.pose(p, 0.0, mode=6, fix=(0, 0))["game"]["fix"] == (0, 0)                # given outright


def _census(dispatchers) -> dict:
    """THE TABLE FROM THE BYTES: each free-roam dispatcher's RunScriptSync calls with tag 19 / 21, classified by
    their own request block (from the label before the call to the call): [190] = 6 there is the take-off,
    RunWorldCode(5, 1) the Dead Pepper's rise, [190] = 7 / 8 / 9 an on-foot boarding of that mode."""
    import re
    from ff9mapkit.eb.ebsrc import write_source
    out = {}
    for name, data in dispatchers.items():
        m = re.search(r"world(\d\d)$", name)
        world = 9000 + int(m.group(1))
        lines = write_source(data, title=name).splitlines()
        for i, ln in enumerate(lines):
            c = re.match(r"RunScriptSync\(\d+, \d+, (19|21)\)", ln)
            if not c:
                continue
            j = i
            while j > 0 and not re.match(r"L\d+:$", lines[j]):
                j -= 1
            blk = "\n".join(lines[j:i])
            sets = [int(v) for v in re.findall(r"Global\.Byte\[190\] const\((\d+)\) B_LET", blk)]
            tag = int(c.group(1))
            if 6 in sets:
                out.setdefault(world, {})["takeoff"] = tag
            elif "RunWorldCode(5, 1)" in blk:
                out.setdefault(world, {})["pepper"] = tag
            elif sets and sets[-1] in (7, 8, 9):
                out.setdefault(world, {}).setdefault("board", {})[sets[-1]] = tag
    return out


def test_the_tag_table_is_the_install_s_own():
    """DISPATCHER_TAGS re-derived from the install's world scripts (skipped without one): a table that only a
    docstring defends would drift from the bytes it reads."""
    from ff9mapkit.world.entrance import load_world_dispatchers
    try:
        dispatchers = load_world_dispatchers()
    except Exception as e:                                            # noqa: BLE001 -- no install here
        pytest.skip(f"no FF9 install: {e}")
    assert _census(dispatchers) == G.DISPATCHER_TAGS
