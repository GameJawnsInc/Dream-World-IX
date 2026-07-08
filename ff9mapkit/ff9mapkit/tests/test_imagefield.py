"""Offline tests for the EXPERIMENTAL image->field MVP (imagefield.py).

The load-bearing correctness property (from the research + verify pass): the floor un-projection is
the true inverse of FF9's PERSPECTIVE field projection restricted to the y=0 plane — a closed-form
homography that must round-trip cam.to_canvas exactly, and MUST use cam.inv3(R_view), never a
transpose (R_view carries the k=14/15 vertical squash, so a transpose is ~hundreds of units wrong).
"""
import math

import pytest

from ff9mapkit import imagefield as IF
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide


def _cam(pitch=26.0, dist=3000.0, fov=42.0):
    return guide.make_camera(pitch, dist, fov_x_deg=fov)


def test_unproject_roundtrips_to_canvas():
    """A world floor point -> canvas -> unproject must recover it to <1e-6 world units, across the
    FF9 pitch band. This is the whole feature's correctness anchor."""
    for pitch in (10, 20, 26, 35, 45):
        cam = _cam(pitch)
        pts = [(-1200, 400), (900, 2500), (0, 1500), (600, 800)]
        px = [C.to_canvas((x, 0.0, z), cam) for (x, z) in pts]
        world = IF.unproject_floor(cam, px)
        for (X, Z), (gx, gz) in zip(pts, world):
            assert abs(gx - X) < 1e-6 and abs(gz - Z) < 1e-6, f"pitch {pitch}: ({X},{Z}) != ({gx},{gz})"


def test_unproject_uses_inv3_not_transpose():
    """Guard the k=14/15 trap: the true inverse round-trips; a transpose of R_view would be ~100s of
    units off. We assert the module's result is the accurate one."""
    cam = _cam()
    X, Z = 800.0, 1800.0
    cx, cy = C.to_canvas((X, 0.0, Z), cam)
    (gx, gz), = IF.unproject_floor(cam, [(cx, cy)])
    assert math.hypot(gx - X, gz - Z) < 1e-6
    # what a (wrong) transpose would have produced, to prove the distinction is real
    d = C.decompose(cam)
    Mt = C.transpose(d["R_view"])
    ray = C.mv(Mt, (cx - cam.range[0] / 2, cam.range[1] / 2 - cy, cam.proj))
    s = -d["C"][1] / ray[1]
    tx, tz = d["C"][0] + s * ray[0], d["C"][2] + s * ray[2]
    assert math.hypot(tx - X, tz - Z) > 50, "transpose should be grossly wrong (the k-squash trap)"


def test_unproject_above_horizon_raises():
    cam = _cam()
    hy = C.horizon_canvas_y(cam)
    with pytest.raises(IF.ImageFieldError, match="horizon"):
        IF.unproject_floor(cam, [(192, hy - 20)])   # a row above the horizon has no floor


def test_signed_area_and_ccw():
    ccw = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert IF._signed_area(ccw) > 0
    assert IF._as_ccw(list(reversed(ccw)))[0:2] == [(0, 0), (10, 0)]   # re-wound to CCW


def test_outset_grows_the_polygon():
    sq = [(-100, -100), (100, -100), (100, 100), (-100, 100)]
    grown = IF.outset_polygon(sq, 25.0)
    assert IF._signed_area(grown) > IF._signed_area(sq)               # area increased
    # each corner pushed out ~25u along both axes (a square miters to the diagonal)
    xs = [abs(x) for x, _ in grown]
    assert all(abs(x - 125) < 1e-6 for x in xs)


def test_triangulate_quad_and_concave():
    quad = [(0, 0), (10, 0), (10, 10), (0, 10)]
    verts, faces = IF.triangulate(quad)
    assert len(faces) == 2 and len(verts) == 4
    # an L-shaped concave hexagon -> 4 triangles, all non-degenerate
    L = [(0, 0), (20, 0), (20, 10), (10, 10), (10, 20), (0, 20)]
    v, f = IF.triangulate(L)
    assert len(f) == 4
    for a, b, c in f:
        assert abs(IF._cross(v[a], v[b], v[c])) > 1e-6                # no zero-area triangle


def test_walkmesh_obj_is_world_y0(tmp_path):
    verts = [(-500.0, 1000.0), (500.0, 1000.0), (0.0, -800.0)]
    IF.write_walkmesh_obj(verts, [(0, 1, 2)], tmp_path / "w.obj")
    txt = (tmp_path / "w.obj").read_text()
    assert "v -500.000 0 1000.000" in txt and "f 1 2 3" in txt        # y=0 plane, 1-indexed faces


def test_build_image_field_end_to_end(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="PICROOM")
    out = tmp_path / "out"
    assert (out / "PICROOM.field.toml").is_file()
    assert (out / "walkmesh.obj").is_file()
    assert (out / "art" / "base.png").is_file()
    assert Image.open(out / "art" / "base.png").size == (1536, 1792)   # 4x the logical canvas
    toml = (out / "PICROOM.field.toml").read_text()
    assert 'obj = "walkmesh.obj"' in toml and 'frame = "world"' in toml
    assert "[[layers]]" in toml and "z = 4000" in toml
    # spawn is inside the world floor bbox
    xs = [p[0] for p in man["world_floor"]]
    zs = [p[1] for p in man["world_floor"]]
    assert min(xs) <= man["spawn"][0] <= max(xs) and min(zs) <= man["spawn"][1] <= max(zs)


def test_build_rejects_int16_overflow(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (0, 0, 0)).save(tmp_path / "src.png")
    # world extents scale with camera distance; a far-pulled-back camera blows the floor past +/-32767
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    with pytest.raises(IF.ImageFieldError, match="Int16"):
        IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", distance=80000)
