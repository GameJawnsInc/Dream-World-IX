"""The game's world-map fog as the editor's game camera draws it (overworld editor rung C18): the measured ramp, the
weather table's colour, the two years (Mist, and the years without), and the panel's Mist switch."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from ff9mapkit.world import fog as FG
from ff9mapkit.world import gamecam as G

HEADER = ("# This file contains world map weather colors.\n# light0.vx;...\n# Int16;...\n")
DAYLIGHT = ("100;100;100;724;724;724;1648;1548;1348;256;768;1696;26;26;26;45;49;64;12000;12000;205;217;247;11000;11000;"
            "201;211;241;12000;0;205;217;247;3596;3596;3596;4096;0;0;0.48;0.70;0.85;1;1;1;1;1;1;# Daylight 0\n")
EVENING = ("1168;868;468;1112;812;512;1736;1580;1280;2100;2000;800;8;8;8;38;12;12;9312;9280;230;120;40;10000;12000;"
           "230;148;56;10288;0;230;148;56;3896;3196;2896;4096;0;0;0.73;0.58;0.39;1;0;0;0;0;0.68;# Evening 0\n")


def _install(tmp_path, csv=HEADER + DAYLIGHT + EVENING, ini=None):
    p = tmp_path / FG.WEATHER_CSV
    p.parent.mkdir(parents=True)
    p.write_text(csv, encoding="utf-8")
    if ini is not None:
        (tmp_path / "Memoria.ini").write_text(ini, encoding="utf-8")
    return tmp_path


def test_the_ramp_is_linear_in_depth_and_longer_over_high_ground():
    f = FG.Fog()
    assert f.factor(FG.START, 0.0) == 0.0 and f.factor(FG.END, 0.0) == 1.0
    assert f.factor((FG.START + FG.END) / 2, 0.0) == pytest.approx(0.5)
    assert f.factor(FG.END, 20.0) < 0.6 < f.factor(FG.END, 0.0)        # the highlands stand out of the mist
    assert f.factor(FG.END + FG.PER_U * 20.0, 20.0) == pytest.approx(1.0)
    out = f.apply(np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]), np.array([0.0, np.inf]), np.array([0.0, 0.0]))
    assert out[0].tolist() == [0.0, 0.0, 0.0] and out[1].tolist() == list(map(float, FG.FOG_RGB))   # the sky: all fog


def test_the_colour_is_the_weather_table_s_fog_dw(tmp_path):
    game = _install(tmp_path)
    assert FG.weather_rgb(game) == (201, 211, 241)                      # Daylight 0's fogDW, not its fogUP
    assert FG.weather_rgb(game, 1) == (230, 148, 56)
    assert FG.weather_rgb(game, 9) is None and FG.weather_rgb(tmp_path / "nowhere") is None
    assert FG.from_game(game).rgb == (201, 211, 241)
    assert FG.from_game(tmp_path / "nowhere").rgb == FG.FOG_RGB          # no table: the colour measured


def test_the_two_years(tmp_path):
    game = _install(tmp_path, ini="[Worldmap]\nFogStartDistance = 400\nFogEndDistance = 490\nMistStartDistance = 25\n"
                                  "MistEndDistance = 250\nMistDensity = 15\nMistStartDistance_base = 40\n")
    mist, clear = FG.from_game(game), FG.from_game(game, mist=False)
    assert (mist.start, mist.end, mist.per_u, mist.unmeasured) == (FG.START, FG.END, FG.PER_U, ())
    assert (clear.start, clear.end, clear.per_u, clear.mist) == (400.0, 490.0, 0.0, False)
    assert "FogStartDistance" in clear.note() and "measured" in mist.note() and "differ" not in mist.note()
    other = FG.from_game(_install(tmp_path / "b", ini="[Worldmap]\nMistEndDistance = 80\n"))
    assert "MistEndDistance 80" in other.note() and "MistStartDistance" not in other.note()   # the unset ones: Memoria's
    assert G.Settings.from_ini("[Worldmap]\nFogStartDistance = 400\n").fog_start == 400.0


def test_a_key_the_ini_leaves_out_is_memoria_s_own_default(tmp_path):
    """Memoria's WorldmapSection binds each key with a default (BindInt32), and a missing key runs at it. The kit used
    the ini comment's "vanilla" numbers instead (86 / 142, 27 / 80 / 7 / 55): with no keys, the no-mist view fogged the
    land solid by 142u where the engine keeps it clear to 250u, and the Mist tooltip called the engine's own defaults
    -- the very ones measured -- unmeasured (review of C18)."""
    s = G.Settings()
    assert (s.fog_start, s.fog_end) == (250.0, 350.0)
    assert {k: getattr(s, k) for k in FG.MEASURED_MIST} == FG.MEASURED_MIST
    assert (s.field_of_view, s.camera_distance, s.camera_height, s.camera_aim_height) == (44.0, 100.0, 100.0, 100.0)
    bare = _install(tmp_path, ini="[Worldmap]\n")
    assert FG.from_game(bare).unmeasured == () and "differ" not in FG.from_game(bare).note()
    clear = FG.from_game(bare, mist=False)
    assert (clear.start, clear.end) == (250.0, 350.0)
    assert FG.from_game(tmp_path / "nowhere", mist=False).end == 350.0      # no ini at all: the same


def test_the_software_twin_fogs_by_each_pixel_s_ray():
    """fog_still (the GPU's twin): a pixel's height comes from its ray, so a far pixel low in the frame (ground) and
    one high in it (a peak at the same depth) fog differently, and a sky pixel is the fog's colour."""
    view = dict(kind="persp", eye=(0.0, 10.0, 0.0), at=(0.0, 10.0, -10.0), fov=60.0)
    img = np.zeros((40, 40, 3), dtype=np.uint8)
    dep = np.full((40, 40), 60.0)
    dep[0, 0] = np.inf
    out = FG.fog_still(img, dep, view, FG.Fog())
    assert out[0, 0].tolist() == list(FG.FOG_RGB)
    assert out[5, 20].max() < out[35, 20].max()                          # higher up the frame: less fog


def test_the_mist_switch_sets_the_game_camera_s_fog(monkeypatch, tmp_path):
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    game = _install(tmp_path, ini="[Worldmap]\nFogStartDistance = 400\nFogEndDistance = 490\n")
    panel = WorldView3DPanel(pick_palette("dark"))
    panel.site = SimpleNamespace(game=game)
    panel.view = SimpleNamespace(fog=None, update=lambda: None)
    panel._set_fog()
    assert panel.view.fog.mist and panel.view.fog.rgb == (201, 211, 241)
    assert "Mist years" in panel.mist_box.toolTip() and "measured" in panel.mist_box.toolTip()
    panel.mist_box.setChecked(False)                                     # the years without mist
    assert not panel.view.fog.mist and panel.view.fog.start == 400.0
    assert "FogStartDistance" in panel.mist_box.toolTip()
