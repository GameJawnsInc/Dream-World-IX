"""Yawed-camera support: render-centering, control-direction, and the build wiring.

Regression for the Session-14 yaw work:
  * make_camera must keep the scene origin at the canvas centre for ANY yaw (the bug was a
    pre-multiplied rot_y, which flung the floor off-screen);
  * yaw_deg recovers the yaw it was built with;
  * control_value_for_angle inverts the engine's (value+1)/256*360 mapping (verified in-game:
    yaw 45 -> value 31 -> W goes straight up the screen);
  * a yawed build bakes the matching TWIST, while a front-facing build stays the kit default (-1).
"""

from __future__ import annotations

import math

import pytest

from ff9mapkit.scene import cam as C, guide as G
from ff9mapkit.content import movement as M
from ff9mapkit import data as _data


@pytest.mark.parametrize("yaw", [0, 5, 15, 45, 90, 135, -30, -90])
def test_origin_stays_centered_at_any_yaw(yaw):
    cam = G.make_camera(40.0, 4500.0, fov_x_deg=42.2, yaw_deg=yaw)
    cx, cy = C.to_canvas((0.0, 0.0, 0.0), cam)
    assert cx == pytest.approx(cam.range[0] / 2.0, abs=0.05)
    assert cy == pytest.approx(cam.range[1] / 2.0, abs=0.05)


@pytest.mark.parametrize("yaw", [0, 15, 45, 90, -30, -89])
def test_yaw_deg_roundtrips(yaw):
    cam = G.make_camera(40.0, 4500.0, fov_x_deg=42.2, yaw_deg=yaw)
    assert C.yaw_deg(cam) == pytest.approx(yaw, abs=0.05)


@pytest.mark.parametrize("angle,value", [(0, -1), (45, 31), (90, 63), (180, 127), (-45, -33), (-90, -65)])
def test_control_value_for_angle(angle, value):
    assert M.control_value_for_angle(angle) == value
    # and the decoded angle matches the input (mod 360, circular)
    decoded = (value + 1) / 256.0 * 360.0
    diff = ((decoded - angle + 180) % 360) - 180
    assert abs(diff) <= 360.0 / 256.0


def test_set_control_direction_in_place_no_shift():
    eb = _data.blank_field_bytes("us")
    out = M.set_control_direction(eb, 31)
    assert len(out) == len(eb)                      # same-length patch, no bytecode shift
    # exactly one TWIST, now 67 00 1F 1F
    assert out.count(b"\x67\x00\x1f\x1f") == 1
    assert out.count(b"\x67\x00\xff\xff") == 0


def test_front_facing_is_default_minus_one():
    """A front-facing camera derives control value -1 (= the blank's existing default = 0 deg)."""
    cam = G.make_camera(40.0, 4500.0, fov_x_deg=42.2, yaw_deg=0)
    assert M.control_value_for_angle(C.yaw_deg(cam)) == -1
    blank = _data.blank_field_bytes("us")
    assert blank.count(b"\x67\x00\xff\xff") == 1     # kit default present, untouched for yaw 0
