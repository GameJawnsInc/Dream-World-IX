"""Tier-3 import foundation: parse a real field's binary .bgs camera (BGSCENE_DEF / BGCAM_DEF).

The 52-byte BGCAM struct was validated byte-exact against the engine's own .bgx export in the
offline p0data spike (2026-06-04, GRGR field). These tests round-trip WITHOUT shipping any game
data, and anchor to the real, verified GRGR camera values."""
from pathlib import Path
import struct

from ff9mapkit.scene import bgs, cam as C

FIX = Path(__file__).parent / "fixtures"


def _grgr():
    return C.parse_bgx_cameras(str(FIX / "grgr.bgx"))[0]


def test_camera_block_roundtrip():
    c = _grgr()
    block = bgs.camera_to_block(c)
    assert len(block) == bgs.CAMERA_SIZE == 52
    back = bgs.camera_from_block(block)
    assert back.proj == c.proj
    assert back.r == c.r
    assert back.t == c.t
    assert back.centerOffset == c.centerOffset
    assert back.range == c.range
    assert back.viewport == c.viewport
    assert back.depthOffset == c.depthOffset


def test_parse_cameras_from_bgs_blob():
    c = _grgr()
    header = struct.pack(
        "<6H4I12h",
        0, 0, 0, 0, 0, 1,              # sceneLength..cameraCount = 1
        0, 0, 0, bgs.HEADER_SIZE,      # cameraOffset = right after the header
        *([0] * 12),                   # scene bounds (unused for cameras)
    )
    data = header + bgs.camera_to_block(c)
    cams = bgs.parse_cameras(data)
    assert len(cams) == 1
    assert cams[0].proj == c.proj and cams[0].r == c.r and cams[0].t == c.t


def test_grgr_real_values():
    # exact GRGR camera, matched byte-for-byte vs p0data in the spike
    c = _grgr()
    assert c.proj == 497
    assert c.t == [0, -248, 5018]
    d = C.decompose(c)
    assert abs(d["fov_x_deg"] - 42.2) < 0.3
    assert abs(C.pitch_deg(c) - 49.6) < 0.3
