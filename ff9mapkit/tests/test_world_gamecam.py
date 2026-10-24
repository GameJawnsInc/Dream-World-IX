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
