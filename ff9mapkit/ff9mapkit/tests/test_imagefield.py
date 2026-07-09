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


# ---------------------------------------------------------------- anchored occluders (contact -> Z)

def test_occluder_z_is_actor_depth_at_contact():
    """The anchor law: overlay Z = the engine's actor OT depth (resz/4 + depthOffset,
    FieldMapActor.cs:122) at the un-projected contact point, +bias — so occlusion flips exactly at
    the contact line."""
    cam = _cam()
    contact = (230.0, 320.0)
    z = IF.occluder_z(cam, contact)
    (X, Z), = IF.unproject_floor(cam, [contact])
    assert z == round(C.depth((X, 0.0, Z), cam)) + IF.CONTACT_Z_BIAS


def test_occluder_z_monotonic_with_screen_depth():
    """Lower on the canvas = nearer the camera = smaller overlay Z (drawn further in front)."""
    cam = _cam()
    z_near = IF.occluder_z(cam, (192, 430))
    z_mid = IF.occluder_z(cam, (192, 320))
    z_far = IF.occluder_z(cam, (192, 200))
    assert z_near < z_mid < z_far


def test_occluder_z_rejects_above_horizon_and_too_far():
    cam = _cam()
    hy = C.horizon_canvas_y(cam)
    with pytest.raises(IF.ImageFieldError, match="contact point"):
        IF.occluder_z(cam, (192, hy - 10))
    # just below the horizon the floor runs to near-infinity -> z blows past the base layer band
    with pytest.raises(IF.ImageFieldError, match="base layer"):
        IF.occluder_z(cam, (192, hy + 0.01))


def test_parse_foreground_spec_forms():
    assert IF.parse_foreground_spec("pillar.png") == {"image": "pillar.png", "z": None, "contact": None}
    assert IF.parse_foreground_spec("pillar.png@230,320") == \
        {"image": "pillar.png", "z": None, "contact": (230.0, 320.0)}
    # an '@' in the path is only an anchor when the tail parses as two numbers
    assert IF.parse_foreground_spec("shots@home/pillar.png") == \
        {"image": "shots@home/pillar.png", "z": None, "contact": None}
    assert IF.parse_foreground_spec({"image": "p.png", "z": 42}) == \
        {"image": "p.png", "z": 42, "contact": None}
    assert IF.parse_foreground_spec({"image": "p.png", "contact": [230, 320]}) == \
        {"image": "p.png", "z": None, "contact": (230, 320)}


def test_build_with_anchored_foreground(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    Image.new("RGBA", (384, 448), (0, 0, 0, 0)).save(tmp_path / "fg.png")
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out",
                               foreground=[f"{tmp_path / 'fg.png'}@230,320"], name="OCCL")
    cam = _cam()
    want_z = IF.occluder_z(cam, (230.0, 320.0))
    assert man["foreground"] == [{"image": str(tmp_path / "fg.png"), "z": want_z, "contact": (230.0, 320.0)}]
    toml = (tmp_path / "out" / "OCCL.field.toml").read_text()
    assert f"z = {want_z}" in toml and "occluder anchored at floor contact (230,320)" in toml
    assert (tmp_path / "out" / "art" / "fg0.png").is_file()
    # the flip must be reachable: z sits strictly between the actor depth at the floor's front and back
    d_front = C.depth((0.0, 0.0, min(p[1] for p in man["world_floor"])), cam)
    d_back = C.depth((0.0, 0.0, max(p[1] for p in man["world_floor"])), cam)
    assert d_front < want_z < d_back


# ---------------------------------------------------------------- auto floor-seed (numpy tier)

def _paint_room(tmp_path, with_pillar=True):
    """The synth proof-room recipe: distinct wall band + a floor trapezoid with GRID LINES (the
    plank/grout hard case the closing step must bridge) + optionally a pillar interrupting it."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (384, 448), (38, 42, 58))
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, 384, 139], fill=(52, 56, 76))
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    dr.polygon(floor, fill=(158, 132, 96))
    for y in range(160, 440, 25):                                   # grout lines across the floor
        dr.line([(0, y), (384, y)], fill=(120, 96, 66), width=1)
    if with_pillar:
        dr.rectangle([213, 108, 247, 320], fill=(148, 150, 160))
    p = tmp_path / "room.png"
    img.save(p)
    return p, floor


def _poly_mask(poly, size=(384, 448)):
    from PIL import Image, ImageDraw
    m = Image.new("1", size, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
    return m


def test_auto_floor_finds_the_trapezoid(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    src, truth = _paint_room(tmp_path)
    got = IF.auto_floor(src)
    assert 3 <= len(got["floor"]) <= IF.AUTO_FLOOR_MAX_VERTS
    a = np.asarray(_poly_mask(got["floor"]), dtype=bool)
    b = np.asarray(_poly_mask(truth), dtype=bool)
    iou = (a & b).sum() / (a | b).sum()
    assert iou >= 0.80, f"IoU {iou:.2f} vs the painted floor"
    # and the seed must be buildable end-to-end (simple polygon, below horizon, Int16-safe)
    man = IF.build_image_field(src, got["floor"], tmp_path / "out", name="AUTOFLR")
    assert man["faces"] >= 2


def test_auto_floor_refuses_no_boundary(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (120, 110, 100)).save(tmp_path / "flat.png")   # one colour everywhere
    with pytest.raises(IF.ImageFieldError, match="no\\s+distinct floor boundary"):
        IF.auto_floor(tmp_path / "flat.png")


def test_auto_floor_refuses_noisy_seed(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    from PIL import Image
    rng = np.random.default_rng(9)
    # COARSE block noise: per-pixel static would blur toward uniform grey and dodge the seed gate
    blocks = rng.integers(0, 255, (56, 48, 3), dtype=np.uint8)
    Image.fromarray(blocks).resize((384, 448), Image.NEAREST).save(tmp_path / "noise.png")
    with pytest.raises(IF.ImageFieldError, match="uniform floor"):
        IF.auto_floor(tmp_path / "noise.png")


def test_auto_floor_without_numpy_errors_cleanly(tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    import sys
    from PIL import Image
    Image.new("RGB", (384, 448)).save(tmp_path / "x.png")
    monkeypatch.setitem(sys.modules, "numpy", None)                 # import numpy -> ImportError
    with pytest.raises(IF.ImageFieldError, match="needs numpy"):
        IF.auto_floor(tmp_path / "x.png")


# ---------------------------------------------------------------- the floor tracer (--trace)

def test_write_trace_html(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (800, 600), (40, 90, 120)).save(tmp_path / "photo.png")
    man = IF.write_trace_html(tmp_path / "photo.png", tmp_path / "trace.html", pitch=26)
    html = (tmp_path / "trace.html").read_text(encoding="utf-8")
    assert "data:image/jpeg;base64," in html                       # the exact cover-crop, embedded
    assert "ff9mapkit image-field" in html                          # the command template
    assert '"26":' in html and '"6":' in html and '"48":' in html   # per-pitch horizon table
    # the horizon it reports matches the camera math for the default pitch
    hy = C.horizon_canvas_y(guide.make_camera(26.0, 3000.0, fov_x_deg=42.0))
    assert abs(man["horizon"] - hy) < 0.11                          # table values are rounded to 0.1
    assert "floor=[]" in html.replace(" ", "")                      # un-seeded by default


def test_write_trace_html_preseeded(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (800, 600), (40, 90, 120)).save(tmp_path / "photo.png")
    IF.write_trace_html(tmp_path / "photo.png", tmp_path / "t.html",
                        floor0=[(130, 140), (254, 140), (364, 440), (20, 440)])
    html = (tmp_path / "t.html").read_text(encoding="utf-8")
    assert '{"x": 130.0, "y": 140.0}' in html                       # the seed polygon is pre-loaded
