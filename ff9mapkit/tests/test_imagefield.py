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
    # the owner directive (field-entry arc): every generator emits the computed settle, in the CLI
    # form -- the exact extract._ENTRY_SETTLE_LINE, first key under [camera]
    from ff9mapkit import extract
    assert "[camera]\n" + extract._ENTRY_SETTLE_LINE in toml
    # spawn is inside the world floor bbox
    xs = [p[0] for p in man["world_floor"]]
    zs = [p[1] for p in man["world_floor"]]
    assert min(xs) <= man["spawn"][0] <= max(xs) and min(zs) <= man["spawn"][1] <= max(zs)


def _src(tmp_path):
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    return tmp_path / "src.png"


def _px(world, pitch=26.0):
    """World floor points -> the canvas pixels the tab would have clicked (default rig)."""
    cam = guide.make_camera(pitch, IF.DEFAULT_DISTANCE, fov_x_deg=IF.DEFAULT_FOV,
                            range_wh=(IF.CANVAS_W, IF.CANVAS_H))
    return [C.to_canvas((x, 0.0, z), cam) for (x, z) in world]


def _inside(p, poly):
    """Even-odd point-in-polygon (test-side, independent of the module's)."""
    x, z = p
    hit = False
    for i in range(len(poly)):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % len(poly)]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            hit = not hit
    return hit


def _obj_verts(path):
    return [(float(p[1]), float(p[3])) for p in
            (ln.split() for ln in path.read_text().splitlines() if ln.startswith("v "))]


def test_a_crossed_floor_outline_is_refused_before_anything_is_written(tmp_path):
    """Finding T5: a bowtie (an outline whose sides cross) triangulated over its whole hull, so the
    walkmesh covered floor the author never traced. Refused, naming the sides, with nothing written."""
    pytest.importorskip("PIL")
    bowtie = [(100, 300), (280, 440), (280, 300), (100, 440)]
    with pytest.raises(IF.ImageFieldError, match=r"from vertex 0 to 1 crosses the side from vertex 2 to 3"):
        IF.build_image_field(_src(tmp_path), bowtie, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_the_outline_check_is_one_rule_for_the_tab_and_the_build():
    assert IF.outline_problem([(100, 300), (280, 300), (280, 440), (100, 440)]) is None
    assert "crosses" in IF.outline_problem([(100, 300), (280, 440), (280, 300), (100, 440)])
    # a corner resting exactly on a side that is not its own is not a simple outline either
    assert "crosses" in IF.outline_problem([(0, 0), (100, 0), (100, 100), (50, 0), (0, 100)])
    # an outline that walks back along itself encloses nothing on that stretch
    assert "doubles back" in IF.outline_problem([(0, 0), (100, 0), (50, 0), (50, 100)])
    assert "no floor" in IF.outline_problem([(0, 0), (100, 0), (200, 0)])
    # a clicked-twice corner is not a crossing (the build drops the duplicate)
    assert IF.outline_problem([(0, 0), (100, 0), (100, 0), (100, 100), (0, 100)]) is None


def test_a_notch_too_narrow_for_the_walk_margin_is_refused_naming_its_vertex(tmp_path):
    """Finding T4: grown by the 48u walk margin, the walls of a 60u slit cross, and the ear-clipper
    emitted overlapping triangles. Refused before any write, naming where."""
    pytest.importorskip("PIL")
    u = [(-600, 800), (600, 800), (600, 2000), (30, 2000), (30, 1000), (-30, 1000),
         (-30, 2000), (-600, 2000)]
    assert IF.outline_problem(u) is None               # the outline itself is legal
    with pytest.raises(IF.ImageFieldError, match=r"too narrow near vertex [3-6]\b"):
        IF.build_image_field(_src(tmp_path), _px(u), tmp_path / "out")
    assert not (tmp_path / "out").exists()
    wide = [(-600, 800), (600, 800), (600, 2000), (200, 2000), (200, 1000), (-200, 1000),
            (-200, 2000), (-600, 2000)]
    IF.build_image_field(_src(tmp_path), _px(wide), tmp_path / "ok")   # a 400u notch builds
    # a sharp V cut into the floor: its inner corner's miter is long but correct (only a CONVEX
    # corner is bevelled; a bevel there would cross the walls and refuse a buildable floor)
    v = [(-800, 800), (800, 800), (800, 2400), (300, 2400), (0, 1200), (-300, 2400), (-800, 2400)]
    IF.build_image_field(_src(tmp_path), _px(v), tmp_path / "v")


def test_a_sharp_tip_is_bevelled_not_thrown_across_the_room(tmp_path):
    """Finding T4: the miter had no limit -- a 5 degree tip moved 1100 world units. Every walkmesh
    vertex now stays within the miter limit of the traced floor."""
    pytest.importorskip("PIL")
    half = math.radians(2.5)
    tip = [(-100, 900), (100, 900), (0, 900 + 100 / math.tan(half))]
    IF.build_image_field(_src(tmp_path), _px(tip), tmp_path / "out")
    reach = IF.MITER_LIMIT * IF.COLLISION_OUTSET + 1e-3
    for v in _obj_verts(tmp_path / "out" / "walkmesh.obj"):
        assert min(math.hypot(v[0] - p[0], v[1] - p[1]) for p in tip) <= reach, v


def test_a_doubled_click_is_dropped_and_every_corner_is_still_grown(tmp_path):
    """Finding T4: a consecutive duplicate vertex (the CLI --floor, the toml inversion) left that
    corner un-grown -- a zero-length edge has no normal."""
    pytest.importorskip("PIL")
    floor = [(130, 140), (254, 140), (254, 140), (364, 440), (20, 440)]
    IF.build_image_field(_src(tmp_path), floor, tmp_path / "out")
    verts = _obj_verts(tmp_path / "out" / "walkmesh.obj")
    assert len(verts) == 4
    world = IF.unproject_floor(guide.make_camera(26.0, IF.DEFAULT_DISTANCE,
                                                 fov_x_deg=IF.DEFAULT_FOV), floor)
    assert all(min(math.hypot(v[0] - p[0], v[1] - p[1]) for p in world) > 40 for v in verts)


def test_overlapping_walkmesh_triangles_are_refused(tmp_path, monkeypatch):
    """The last guard of T4: whatever the cause, triangles whose areas sum past the grown floor's
    own area overlap -- the build refuses rather than ship floor twice."""
    pytest.importorskip("PIL")
    real = IF.triangulate

    def doubled(poly):
        pts, faces = real(poly)
        return pts, faces + faces[:1]
    monkeypatch.setattr(IF, "triangulate", doubled)
    with pytest.raises(IF.ImageFieldError, match="overlap"):
        IF.build_image_field(_src(tmp_path), [(130, 140), (254, 140), (364, 440), (20, 440)],
                             tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_the_spawn_lies_on_an_l_or_u_shaped_floor(tmp_path):
    """Finding T3: the spawn was the vertex mean, which lies off an L or a U -- the player started
    off the floor. A convex floor keeps the mean exactly (no generated value moves)."""
    pytest.importorskip("PIL")
    L = [(-900, 800), (900, 800), (900, 1100), (-600, 1100), (-600, 2600), (-900, 2600)]
    U = [(-900, 800), (900, 800), (900, 2400), (600, 2400), (600, 1100), (-600, 1100),
         (-600, 2400), (-900, 2400)]
    for name, poly in (("L", L), ("U", U)):
        mean = (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
        assert not _inside(mean, poly), f"{name}: the fixture must put the mean off the floor"
        man = IF.build_image_field(_src(tmp_path), _px(poly), tmp_path / name)
        assert _inside(man["spawn"], man["world_floor"]), (name, man["spawn"])
    quad = [(130, 140), (254, 140), (364, 440), (20, 440)]
    man = IF.build_image_field(_src(tmp_path), quad, tmp_path / "quad")
    w = man["world_floor"]
    assert man["spawn"] == (sum(p[0] for p in w) / 4, sum(p[1] for p in w) / 4)


def test_build_rejects_int16_overflow(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (0, 0, 0)).save(tmp_path / "src.png")
    # world extents scale with camera distance; a far-pulled-back camera blows the floor past +/-32767
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    with pytest.raises(IF.ImageFieldError, match="Int16"):
        IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", distance=80000)


@pytest.mark.parametrize("name", ['A"B', "Q?X", "sub/dir", "has space", "", "../up"])
def test_a_bad_field_name_is_refused_before_anything_is_written(tmp_path, name):
    """Finding T7: the name is the toml's FILE name and its [field] name. It was never checked:
    walkmesh.obj and art/ were written, then the toml write raised an OSError the CLI did not
    catch (a traceback, and on a regenerate a new floor under the old toml)."""
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    with pytest.raises(IF.ImageFieldError, match="letters, digits"):
        IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name=name)
    assert not (tmp_path / "out").exists()


def test_a_zone_beyond_the_int16_world_is_refused_before_anything_is_written(tmp_path):
    """Finding T9: the floor was bound-checked but gateway/event corners were not. A door drawn in
    the top rows of the photo at the default pitch un-projects past |z| 32767; Generate wrote it
    and the build failed later with a struct.error far from the cause."""
    pytest.importorskip("PIL")
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    floor = [(130, 200), (254, 200), (364, 440), (20, 440)]
    for kw in ({"gateways": ["4005@60,2;140,2;140,30;60,30"]},
               {"events": ["hi@60,2;140,2;140,30;60,30"]}):
        with pytest.raises(IF.ImageFieldError, match="Int16"):
            IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", **kw)
        assert not (tmp_path / "out").exists()
    IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out",   # in bound: built
                         gateways=["4005@60,300;140,300;140,330;60,330"])


def test_the_cli_band_checks_the_id_and_its_deploy_hint_names_it(tmp_path, capsys):
    """Finding T18: the success print hard-coded '--id 30058' whatever --id was, so a copied hint
    deployed into somebody else's scratch slot; and --id was never band-checked (9000-9012, real
    ids and ids past 32767 all generated). The path in the hint is quoted (T22: spaces)."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import cli
    (tmp_path / "my photos").mkdir()
    src = tmp_path / "my photos" / "src.png"
    Image.new("RGB", (384, 448), (90, 80, 70)).save(src)
    base = ["image-field", str(src), "--floor", "130,140 254,140 364,440 20,440", "--name", "ROOM"]
    for bad in ("9005", "100", "40000"):
        out = tmp_path / f"bad{bad}"
        assert cli.main(base + ["--out", str(out), "--id", bad]) == 2
        assert not out.exists()
        assert bad in capsys.readouterr().err
    out = tmp_path / "my photos" / "room-field"
    assert cli.main(base + ["--out", str(out), "--id", "30777"]) == 0
    said = capsys.readouterr().out
    assert "30058" not in said and "--id 30777" in said and "Warp 30777" in said
    assert f'"{out / "ROOM.field.toml"}"' in said


def _sideways_phone_photo(path):
    """An 800x400 JPEG stored landscape with EXIF Orientation=6 (a portrait phone shot): every
    photo viewer shows it 400x800. Left half red, right half blue, so a rotation is visible."""
    from PIL import Image
    im = Image.new("RGB", (800, 400), (200, 30, 30))
    im.paste((30, 30, 200), (400, 0, 800, 400))
    exif = Image.Exif()
    exif[0x0112] = 6
    im.save(path, exif=exif, quality=95)
    return path


def _grey16(path):
    """A 16-bit greyscale PNG (mode I;16): a horizontal gradient whose 8-bit mean is ~95."""
    import numpy as np
    from PIL import Image
    row = np.linspace(0, 48000, 384, dtype=np.uint16)
    Image.fromarray(np.tile(row, (448, 1))).save(path)
    assert Image.open(path).mode.startswith("I")       # the premise: really a 16-bit image
    return path


def test_the_photo_is_read_upright_and_16_bit_is_not_white(tmp_path):
    """Findings T19 + E11: every ingest did Image.open(p).convert('RGB'), which ignores EXIF
    orientation (a phone photo traced and shipped sideways) and clamps 16-bit samples to 255
    (a white rectangle, canvas and shipped art alike). open_rgb is the one reader."""
    pytest.importorskip("PIL")
    pytest.importorskip("numpy")
    import numpy as np
    from PIL import Image
    im = IF.open_rgb(_sideways_phone_photo(tmp_path / "phone.jpg"))
    assert im.mode == "RGB" and im.size == (400, 800)  # upright, as every viewer shows it
    g = IF.open_rgb(_grey16(tmp_path / "grey16.png"))
    assert g.mode == "RGB" and 80 < float(np.asarray(g).mean()) < 110


def test_every_photo_ingest_spends_the_one_reader():
    """The call-site law: the build, the auto floor-seed and the HTML tracer each read the source
    photo; a site that goes back to Image.open(...).convert('RGB') reopens T19/E11 silently."""
    import inspect
    for fn in (IF.build_image_field, IF.auto_floor, IF.write_trace_html):
        src = inspect.getsource(fn)
        assert "open_rgb(image_path)" in src, fn.__name__
        assert "Image.open(image_path)" not in src, fn.__name__


def test_the_build_ships_the_photo_the_way_the_tab_shows_it(tmp_path):
    pytest.importorskip("PIL")
    pytest.importorskip("numpy")
    import numpy as np
    from PIL import Image, ImageOps
    floor = [(130, 200), (254, 200), (364, 440), (20, 440)]
    phone = _sideways_phone_photo(tmp_path / "phone.jpg")
    upright = tmp_path / "upright.png"
    ImageOps.exif_transpose(Image.open(phone)).save(upright)
    IF.build_image_field(phone, floor, tmp_path / "a")
    IF.build_image_field(upright, floor, tmp_path / "b")
    a = np.asarray(Image.open(tmp_path / "a" / "art" / "base.png"), dtype=np.int16)
    b = np.asarray(Image.open(tmp_path / "b" / "art" / "base.png"), dtype=np.int16)
    assert np.abs(a - b).max() <= 2                    # the same pixels (JPEG decode aside)
    IF.build_image_field(_grey16(tmp_path / "g.png"), floor, tmp_path / "g")
    base = np.asarray(Image.open(tmp_path / "g" / "art" / "base.png"))
    assert float(base.mean()) < 200                    # not the white rectangle


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


def test_auto_floor_cuts_at_a_doorway_constriction(tmp_path):
    """The real-photo hallway failure: SAME-material floor continuing through a doorway must not
    drag the polygon into the far room -- the sustained width collapse (doorway ~0.38x the local
    hallway width here) terminates the walk at the constriction."""
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (384, 448), (60, 62, 80))
    dr = ImageDraw.Draw(img)
    F = (150, 125, 92)
    dr.polygon([(150, 170), (234, 170), (330, 447), (54, 447)], fill=F)     # this room's floor
    dr.polygon([(172, 120), (212, 120), (212, 170), (172, 170)], fill=F)    # a 40px doorway gap
    dr.polygon([(90, 122), (294, 122), (294, 160), (90, 160)], fill=F)      # the far room (wide again)
    p = tmp_path / "hall.png"
    img.save(p)
    got = IF.auto_floor(p)
    top = min(y for _, y in got["floor"])
    assert top >= 160, f"polygon reached y={top}: it followed the floor through the doorway"


def test_auto_floor_depth_cap(tmp_path):
    """Floor colour running to the canvas top (a corridor to the horizon) is clamped at the world-
    depth cap (1x camera distance -> canvas y ~116 at the default camera), not at the image top."""
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (384, 448), (60, 62, 80))
    ImageDraw.Draw(img).polygon([(100, 40), (284, 40), (340, 447), (44, 447)], fill=(150, 125, 92))
    p = tmp_path / "deep.png"
    img.save(p)
    got = IF.auto_floor(p)
    top = min(y for _, y in got["floor"])
    hy_cap = C.to_canvas((0.0, 0.0, 3000.0), guide.make_camera(26.0, 3000.0, fov_x_deg=42.0))[1]
    assert top >= hy_cap - 1, f"polygon top y={top} passed the depth cap ({hy_cap:.0f})"


def test_auto_floor_without_numpy_errors_cleanly(tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    import sys
    from PIL import Image
    Image.new("RGB", (384, 448)).save(tmp_path / "x.png")
    monkeypatch.setitem(sys.modules, "numpy", None)                 # import numpy -> ImportError
    with pytest.raises(IF.ImageFieldError, match="needs numpy"):
        IF.auto_floor(tmp_path / "x.png")


# ---------------------------------------------------------------- click-authoring Rung 0 conversions

def test_click_to_world_grid_roundtrip():
    """Rung 0's offline gate (studies/click-authoring/PLAN.md): a grid of canvas points through
    click_to_world -> world_to_click must land back to < 1e-9 canvas px, across the synthesized
    envelope (pitch 10-45, yaw +/-25, two FOVs)."""
    for pitch in (10, 26, 45):
        for yaw in (-25, 0, 25):
            for fov in (36.0, 48.0):
                cam = guide.make_camera(pitch, 3000.0, fov_x_deg=fov, yaw_deg=yaw)
                hy = C.horizon_canvas_y(cam)
                for cx in range(12, 384, 62):
                    for cy in range(0, 448, 32):
                        if cy <= hy + 2:            # at/above the horizon there is no floor
                            continue
                        X, Z = IF.click_to_world(cam, (cx, cy))
                        bx, by = IF.world_to_click(cam, (X, Z))
                        err = math.hypot(bx - cx, by - cy)
                        assert err < 1e-9, \
                            f"pitch {pitch} yaw {yaw} fov {fov}: ({cx},{cy}) round-trips {err:g} px off"


def test_click_roundtrip_with_real_style_center_offset():
    """REAL imported cameras carry a nonzero GTE centerOffset (the map158 donor's [26, 400]);
    the un-projection must fold it out exactly as to_canvas folds it in. Before the fix this
    round-tripped |offset| px wrong (measured 400.8 px on the donor — the click-authoring
    census's first catch)."""
    cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0, center_offset=(26, 400),
                            range_wh=(512, 400))
    hy = C.horizon_canvas_y(cam)
    for cx in (30, 250, 480):
        for cy in (int(hy + 10), 200, 390):
            if cy <= hy + 3:
                continue
            X, Z = IF.click_to_world(cam, (cx, cy))
            bx, by = IF.world_to_click(cam, (X, Z))
            assert math.hypot(bx - cx, by - cy) < 1e-9


def test_click_to_world_refuses_above_horizon():
    """The horizon guard: refuse, never clamp — a silent clamp would place content at absurd depth."""
    cam = _cam()
    hy = C.horizon_canvas_y(cam)
    with pytest.raises(IF.ImageFieldError, match="horizon"):
        IF.click_to_world(cam, (192, hy - 5))


def test_click_roundtrip_tripwire_is_live(monkeypatch):
    """The self-check must actually fire: an inverse that drifts from the forward projection (the
    transpose class, a degenerate camera) raises loudly instead of returning a plausible point."""
    cam = _cam()
    real = IF.unproject_floor
    monkeypatch.setattr(IF, "unproject_floor",
                        lambda c, pts: [(x + 120.0, z) for (x, z) in real(c, pts)])
    with pytest.raises(IF.ImageFieldError, match="re-projects"):
        IF.click_to_world(cam, (200, 300))


def test_world_to_click_refuses_behind_camera():
    """A point at/behind the camera plane would silently mirror onto the canvas (the projection
    divides by abs(z)); the forward hop refuses it instead."""
    cam = _cam()
    cz = C.decompose(cam)["C"][2]
    with pytest.raises(IF.ImageFieldError, match="behind the camera"):
        IF.world_to_click(cam, (0.0, cz - 5000.0))


# ---------------------------------------------------------------- Rung 3: the walkmesh raycast

def _bary(a, b, c, u, v):
    w = 1.0 - u - v
    return tuple(a[i] * w + b[i] * u + c[i] * v for i in range(3))


def test_click_ray_agrees_with_the_plane_inverse():
    """One owner: intersecting click_ray with y=0 must equal unproject_floor exactly — on a
    REAL-style camera (nonzero centerOffset), the class the fold bug lived in."""
    cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0, center_offset=(26, 400),
                            range_wh=(512, 400))
    for pt in ((60.0, 320.0), (250.0, 380.0), (480.0, 305.0)):   # horizon here is y~296
        (X, Z), = IF.unproject_floor(cam, [pt])
        C0, ray = IF.click_ray(cam, pt)
        s = -C0[1] / ray[1]
        assert math.hypot((C0[0] + s * ray[0]) - X, (C0[2] + s * ray[2]) - Z) < 1e-9


def test_click_to_surface_recovers_sloped_points():
    """The plane model's blind spot IS this function's home turf: interior points of a RAMP
    triangle recover exactly through project -> raycast."""
    cam = _cam()
    ramp = ((-500.0, 0.0, 800.0), (500.0, 0.0, 800.0), (0.0, 400.0, 1600.0))
    for (u, v) in ((0.2, 0.3), (0.5, 0.2), (0.1, 0.7), (0.33, 0.33)):
        p = _bary(*ramp, u, v)
        got = IF.click_to_surface(cam, [ramp], C.to_canvas(p, cam))
        assert math.dist(got["pos"], p) < 1e-6
        assert got["tri"] == 0 and len(got["hits"]) == 1


def test_click_to_surface_stacked_floors_nearest_first():
    """A bridge over a floor: both hits reported nearest-first, the VISIBLE (upper) one wins —
    you click what you see; the rest is the caller's disambiguation list."""
    cam = _cam()
    lower = ((-2000.0, 0.0, 400.0), (2000.0, 0.0, 400.0), (0.0, 0.0, 6000.0))
    upper = ((-400.0, 500.0, 1200.0), (400.0, 500.0, 1200.0), (0.0, 500.0, 2000.0))
    p_up = _bary(*upper, 0.3, 0.3)
    got = IF.click_to_surface(cam, [lower, upper], C.to_canvas(p_up, cam))
    assert len(got["hits"]) == 2
    assert got["tri"] == 1 and math.dist(got["pos"], p_up) < 1e-6
    assert got["hits"][0][0] < got["hits"][1][0]   # sorted by ray distance
    assert got["hits"][1][1] == 0                  # the buried floor is the second hit


def test_click_to_surface_no_mesh_refuses():
    cam = _cam()
    off = ((5000.0, 0.0, 800.0), (6000.0, 0.0, 800.0), (5500.0, 0.0, 1600.0))
    with pytest.raises(IF.ImageFieldError, match="no walkmesh under the click"):
        IF.click_to_surface(cam, [off], (192.0, 300.0))


def test_click_to_surface_ignores_behind_camera():
    """A triangle behind the camera never answers for a pixel (s > 0 only)."""
    cam = _cam()
    cz = C.decompose(cam)["C"][2]
    behind = ((-500.0, 0.0, cz - 4000.0), (500.0, 0.0, cz - 4000.0), (0.0, 0.0, cz - 6000.0))
    with pytest.raises(IF.ImageFieldError, match="no walkmesh"):
        IF.click_to_surface(cam, [behind], (192.0, 300.0))


def test_world_point_to_click_roundtrips_mesh_points():
    cam = _cam()
    p = (120.0, 350.0, 1400.0)
    cx, cy = IF.world_point_to_click(cam, p)
    got = IF.click_to_surface(
        cam, [((0.0, 350.0, 1000.0), (300.0, 350.0, 1200.0), (100.0, 350.0, 1800.0))], (cx, cy))
    assert math.dist(got["pos"], p) < 1e-6


def test_mesh_world_tris_maps_floors():
    """The adapter: world frame = vert + orgPos + floor.org (the import-frame law), one floor
    index per triangle — duck-typed, mirroring BgiWalkmesh's own world_verts contract."""
    class _V:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z

    class _T:
        def __init__(self, *vtx):
            self.vtx = list(vtx)

    class _F:
        def __init__(self, tris):
            self.tri_ndx_list = tris

    class _Mesh:
        floors = [_F([0]), _F([1])]
        tris = [_T(0, 1, 2), _T(3, 4, 5)]

        def world_verts(self):
            return [(0, 0, 0), (10, 0, 0), (0, 0, 10),
                    (0, 5, 0), (10, 5, 0), (0, 5, 10)]

    tris, floors = IF.mesh_world_tris(_Mesh())
    assert floors == [0, 1]
    assert tris[1][0] == (0, -5, 0)                # RENDER frame: y negated (WalkMesh.cs:54)


def test_mesh_world_tris_render_flip_is_load_bearing():
    """The engine negates walkmesh Y before the GTE, so a DEEP floor (build-frame y=+2000) is
    seen by the camera at y=-2000 — compose_background's proven footprint flip. Pin it end to
    end: the pixel of the RENDER-frame point recovers through the adapter's triangles, and the
    un-flipped projection lands somewhere else entirely (the class of misplacement this
    prevents)."""
    cam = _cam()

    class _V:
        pass

    class _T:
        def __init__(self, *vtx):
            self.vtx = list(vtx)

    class _F:
        def __init__(self, tris):
            self.tri_ndx_list = tris

    class _Mesh:
        floors = [_F([0])]
        tris = [_T(0, 1, 2)]

        def world_verts(self):
            return [(-800.0, 2000.0, 1400.0), (800.0, 2000.0, 1400.0), (0.0, 2000.0, 2600.0)]

    tris, _ = IF.mesh_world_tris(_Mesh())
    p_render = _bary(*tris[0], 0.3, 0.3)           # a visible point of the deep floor
    got = IF.click_to_surface(cam, tris, C.to_canvas(p_render, cam))
    assert math.dist(got["pos"], p_render) < 1e-6
    # the un-flipped pixel for the same spot is far away on canvas — the flip is not cosmetic
    p_build = (p_render[0], -p_render[1], p_render[2])
    cx_r, cy_r = C.to_canvas(p_render, cam)
    cx_b, cy_b = C.to_canvas(p_build, cam)
    assert math.hypot(cx_r - cx_b, cy_r - cy_b) > 50


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


# ---------------------------------------------------------------------------- regenerate merge
# A re-run used to be one unconditional write_text: every hand-authored table in the project was
# silently destroyed (imagefield's copy of the floorplan bulldozer, closed there as rung 7c').
# The merge bands are floorplan.merge_room's grammar; these fences mirror its test shapes.

def _merge_project(tmp_path, gateways=("4005@60,300;140,300;140,330;60,330",)):
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                               gateways=list(gateways),
                               events=["It creaks.@200,340;300,340;300,380;200,380"])
    return tmp_path / "out" / "MERGE.field.toml", floor, man


def _hand_author(toml_path):
    """What a Place-tab session (or a hand editor) adds to a generated project."""
    text = toml_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    # under [field], where the Editor's Field form writes it and build.py reads it (finding T2:
    # the fixture once put it top-level, a place nothing writes, so the wipe went unseen)
    lines.insert(lines.index("[field]") + 1, "text_block = 30058")
    text = "\n".join(lines) + "\n" + (
        '\n[[npc]]\nname = "mist_porter"\npreset = "vivi"\npos = [0, 1500]\n'
        '\n[[gateway]]\nname = "west_gate"\nto = 301\nzone = [[-500, 900], [-400, 900], '
        '[-400, 1000], [-500, 1000]]\n'
        '\n[[layers]]\nimage = "art/painted_arch.png"\nz = 700\n'
        '\n[music]\nsong = 39\n')
    toml_path.write_text(text, encoding="utf-8", newline="\n")


def test_regenerate_preserves_hand_authored_content(tmp_path):
    """The whole point: npc/music/text_block/hand door/painted layer survive a re-run verbatim;
    the generator's own tables regenerate; kept names every preserved thing."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path)
    _hand_author(toml)
    man2 = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                                gateways=["4005@60,300;140,300;140,330;60,330"],
                                events=["It creaks.@200,340;300,340;300,380;200,380"])
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert data["field"]["text_block"] == 30058
    assert data["npc"][0]["name"] == "mist_porter" and data["npc"][0]["pos"] == [0, 1500]
    assert data["music"]["song"] == 39
    names = [g["name"] for g in data["gateway"]]
    assert names == ["traced_door0", "west_gate"]     # generated first, hand rows appended
    assert [la["image"] for la in data["layers"]] == ["art/base.png", "art/painted_arch.png"]
    assert data["event"][0]["name"] == "traced_zone0"
    kept = "\n".join(man2["kept"])
    assert "west_gate" in kept and "[[npc]]" in kept and "[music]" in kept
    assert "painted_arch" in kept and "[field].text_block" in kept


def test_the_editors_field_form_keys_ride_through_a_regenerate(tmp_path):
    """[field] merges PER KEY (finding T2): the generator owns id/name/area, while the Editor's
    Field form writes location, title, text_block and borrow_bg into the same table -- and a
    wholesale band erased them, reporting only 'retaken: field'. Driven through FieldDoc, the
    Editor's own model, so the keys sit exactly where the form saves them."""
    pytest.importorskip("PIL")
    import tomllib
    from ff9mapkit.editor.model import FieldDoc
    toml, floor, _man = _merge_project(tmp_path)
    doc = FieldDoc.load(toml)
    doc.field.update({"location": "Mog's Hut", "title": "my notes", "text_block": 30058,
                      "hide_area_title": True})
    doc.save()
    man2 = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                                gateways=["4005@60,300;140,300;140,330;60,330"],
                                events=["It creaks.@200,340;300,340;300,380;200,380"])
    field = tomllib.loads(toml.read_text(encoding="utf-8"))["field"]
    assert field["location"] == "Mog's Hut" and field["title"] == "my notes"
    assert field["text_block"] == 30058 and field["hide_area_title"] is True
    assert (field["id"], field["name"], field["area"]) == (4003, "MERGE", 11)
    kept = man2["kept"]
    for k in ("location", "title", "text_block", "hide_area_title"):
        assert f"[field].{k}" in kept
    assert not [r for r in man2["retaken"] if r.startswith("field")]   # untouched: no retake


def test_a_hand_changed_generator_field_key_is_retaken_by_name(tmp_path):
    """id/name/area stay the generator's: a hand-changed one is overwritten by the session and
    named key by key in retaken, beside the hand keys that rode through."""
    pytest.importorskip("PIL")
    import tomllib
    from ff9mapkit.editor.model import FieldDoc
    toml, floor, _man = _merge_project(tmp_path)
    doc = FieldDoc.load(toml)
    doc.field.update({"area": 12, "location": "Dali"})
    doc.save()
    man2 = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                                gateways=["4005@60,300;140,300;140,330;60,330"],
                                events=["It creaks.@200,340;300,340;300,380;200,380"])
    field = tomllib.loads(toml.read_text(encoding="utf-8"))["field"]
    assert field["area"] == 11 and field["location"] == "Dali"
    assert [r for r in man2["retaken"] if r.startswith("field")] == ["field.area"]


def test_a_kept_borrow_bg_keeps_the_area_it_names_its_donor_with():
    """Review of T2: borrow_bg resolves TOGETHER with area (FBG_N<area>_<borrow>). Keeping the
    borrow while re-taking area = 11 wrote a pair that names a different (or no) donor."""
    import tomllib
    gen = ('# x\n[field]\nid = 4003\nname = "M"\narea = 11\n\n[camera]\npitch = 30\n\n'
           '[player]\nspawn = [0, 0]\n')
    text, kept, retaken, _removed = IF.merge_project_toml(
        gen, {"field": {"id": 4003, "name": "M", "area": 52, "borrow_bg": "B12"}})
    field = tomllib.loads(text)["field"]
    assert (field["area"], field["borrow_bg"]) == (52, "B12")
    assert "field.area" not in retaken and "[field].area" in kept
    # without a borrow, area stays the generator's (the rule above)
    text, _k, retaken, _r = IF.merge_project_toml(
        gen, {"field": {"id": 4003, "name": "M", "area": 52, "location": "Dali"}})
    assert tomllib.loads(text)["field"]["area"] == 11 and "field.area" in retaken


def test_a_moved_generated_field_block_fails_loudly_not_silently():
    """If the generator's [field] lines ever change shape, the per-key merge must refuse --
    the quiet alternative is a regenerate that drops the Editor's keys again (T2)."""
    gen = '# x\n[field]\nid = 4003\narea = 11\nname = "M"\n\n[player]\nspawn = [0, 0]\n'
    with pytest.raises(IF.ImageFieldError, match=r"\[field\] block"):
        IF.merge_project_toml(gen, {"field": {"id": 4003, "name": "M", "area": 11,
                                              "location": "Dali"}})


# ---------------------------------------------------------------------------- the CLI's report (E10)
def test_a_complete_build_is_not_reported_failed_on_a_cp1252_pipe(tmp_path):
    """Finding E10: the CLI prints its report AFTER every file is written, and an arrow in an event
    message raised UnicodeEncodeError on a cp1252 stdout -- exit 1 for a complete project, so the
    Workspace said 'failed'. A REAL subprocess under a forced cp1252 stdout (the Workspace's pipe on
    a Western Windows locale; forced so the fence holds on a UTF-8 host too)."""
    pytest.importorskip("PIL")
    import os
    import subprocess
    import sys
    from pathlib import Path

    import ff9mapkit
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    pkg_root = Path(ff9mapkit.__file__).resolve().parent.parent
    r = subprocess.run(
        [sys.executable, "-m", "ff9mapkit", "image-field", str(tmp_path / "src.png"),
         "--floor", "130,140 254,140 364,440 20,440", "--out", str(tmp_path / "out"),
         "--name", "ARROW", "--event-zone", "Go → north@200,340;300,340;300,380;200,380"],
        cwd=pkg_root, env=env, capture_output=True, timeout=120)
    assert (tmp_path / "out" / "ARROW.field.toml").is_file()      # the project IS complete...
    out = r.stdout.decode("cp1252", "replace") + r.stderr.decode("cp1252", "replace")
    assert r.returncode == 0, out
    assert "synthesized ARROW" in out and "Deploy + walk it" in out   # ...and the report finished


def test_regenerate_deletes_its_own_stale_doors_and_keeps_yours(tmp_path):
    """Ownership by prefix, not by name-merge, because a name merge cannot express DELETION:
    a door dropped from the session must go, while the hand door stays."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(
        tmp_path, gateways=("4005@60,300;140,300;140,330;60,330",
                            "4007@250,300;330,300;330,330;250,330"))
    _hand_author(toml)
    IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                         gateways=["4005@60,300;140,300;140,330;60,330"])   # one door dropped
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert [g["name"] for g in data["gateway"]] == ["traced_door0", "west_gate"]
    assert all(g["to"] != 4007 for g in data["gateway"])


def test_a_place_drawn_door0_on_a_current_project_is_preserved(tmp_path):
    """Once a project carries traced_ rows, door0-style names are HAND rows (the Place tab
    mints them) -- the legacy claim must not eat them."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path)
    text = toml.read_text(encoding="utf-8") + (
        '\n[[gateway]]\nname = "door0"\nto = 301\nzone = [[-500, 900], [-400, 900], '
        '[-400, 1000], [-500, 1000]]\n')
    toml.write_text(text, encoding="utf-8", newline="\n")
    IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                         gateways=["4005@60,300;140,300;140,330;60,330"])
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert [g["name"] for g in data["gateway"]] == ["traced_door0", "door0"]
    assert IF.is_generated_region("gateway", "traced_door0")
    assert not IF.is_generated_region("gateway", "door0")


def test_legacy_door_rows_are_claimed_once_not_duplicated(tmp_path):
    """A pre-prefix project's own door0 row is replaced by its traced_ twin when the run
    re-emits the same quad -- not doubled. Its zone0, which this run does NOT re-emit, is
    KEPT: nothing distinguishes it from a zone the Place tab drew, and an unprovable row is
    never deleted (it used to be, and that same rule ate real Place rows -- finding T1)."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path)
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    # rewrite as the LEGACY shape: the generator's rows under their old names, plus a hand npc
    for i, g in enumerate(data["gateway"]):
        g["name"] = f"door{i}"
    for i, e in enumerate(data["event"]):
        e["name"] = f"zone{i}"
    assert not IF.is_generated_region("gateway", "door0")        # a name alone proves nothing
    from ff9mapkit.editor import model as _model
    toml.write_text(_model.dumps(dict(data, npc=[{"name": "keeper", "preset": "vivi",
                                                  "pos": [0, 1500]}])),
                    encoding="utf-8", newline="\n")
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                               gateways=["4005@60,300;140,300;140,330;60,330"])
    data2 = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert [g["name"] for g in data2["gateway"]] == ["traced_door0"]   # replaced, not doubled
    assert [e["name"] for e in data2.get("event", [])] == ["zone0"]    # unprovable -> kept
    assert "[[event]] zone0" in man["kept"] and man["removed"] == []
    assert data2["npc"][0]["name"] == "keeper"


def test_regenerate_refuses_an_unparseable_project_before_writing_anything(tmp_path):
    """The refusal fires BEFORE walkmesh/art are overwritten -- a refusal must never leave a
    half-rewritten project (the floorplan emit's byte-compare fence, restated here)."""
    pytest.importorskip("PIL")
    import hashlib
    toml, floor, _man = _merge_project(tmp_path)
    toml.write_text(toml.read_text(encoding="utf-8") + "\n[broken\n", encoding="utf-8")

    def _tree(root):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}

    before = _tree(tmp_path / "out")
    # CHANGED inputs, or the fence is vacuous: with the same photo and floor a violation
    # would rewrite byte-identical artifacts and the compare could never go red (the
    # adversarial review's catch on this test's own first cut)
    from PIL import Image
    Image.new("RGB", (384, 448), (10, 200, 10)).save(tmp_path / "src.png")
    floor2 = [(100, 160), (300, 160), (340, 430), (40, 430)]
    with pytest.raises(IF.ImageFieldError, match="--force"):
        IF.build_image_field(tmp_path / "src.png", floor2, tmp_path / "out", name="MERGE")
    assert _tree(tmp_path / "out") == before          # byte-identical across the refusal
    man = IF.build_image_field(tmp_path / "src.png", floor2, tmp_path / "out", name="MERGE",
                               force=True)            # the escape hatch discards
    assert man["kept"] == [] and (tmp_path / "out" / "MERGE.field.toml").is_file()
    assert _tree(tmp_path / "out") != before          # anti-vacuity: the inputs DO move bytes


def test_player_spawn_is_generator_owned_and_the_retake_is_said_out_loud(tmp_path):
    """[player].spawn regenerates (the session's centroid wins) -- but a hand-moved spawn is
    REPORTED via retaken, never silently reverted."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path)
    text = toml.read_text(encoding="utf-8").replace("spawn = [", "spawn = [9, ")
    toml.write_text(text, encoding="utf-8", newline="\n")
    moved = tomllib.loads(toml.read_text(encoding="utf-8"))["player"]["spawn"]
    man2 = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                                gateways=["4005@60,300;140,300;140,330;60,330"],
                                events=["It creaks.@200,340;300,340;300,380;200,380"])
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert data["player"]["spawn"] != moved            # the centroid is re-derived
    assert "player.spawn" in man2["retaken"]


def test_place_authored_arrivals_ride_through_a_regenerate(tmp_path):
    """[player] merges PER KEY: the Place tab writes [[player.arrival]] rows into the same
    table the generator owns the spawn of, and the wholesale band was deleting them (the
    review's catch — the floorplan owns [player] wholesale only because ITS composer
    generates arrivals; this one never does)."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path)
    toml.write_text(toml.read_text(encoding="utf-8") + (
        '\n[[player.arrival]]\nentrance = 0\npos = [0, 900]\n'
        '\n[[player.arrival]]\nentrance = 2\npos = [300, 1400]\nface = "north"\n'),
        encoding="utf-8", newline="\n")
    man2 = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                                gateways=["4005@60,300;140,300;140,330;60,330"],
                                events=["It creaks.@200,340;300,340;300,380;200,380"])
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    rows = data["player"]["arrival"]
    assert [r["entrance"] for r in rows] == [0, 2] and rows[1]["face"] == "north"
    assert isinstance(data["player"]["spawn"], list)   # the generator's key survives beside them
    assert any("arrival" in k for k in man2["kept"])
    assert "player.spawn" not in man2["retaken"]       # an untouched spawn is not a retake


def test_a_no_regions_regenerate_never_claims_place_rows(tmp_path):
    """THE RECURRING-DELETION HOLE (the review's high finding): a project traced with NO
    regions emits no traced_ row, so the file reads as legacy forever — and the legacy claim
    ate a Place-drawn door0 on EVERY regenerate. The claim is now gated on the session
    actually emitting regions; a no-regions regenerate preserves door0/zone0 indefinitely."""
    pytest.importorskip("PIL")
    import tomllib
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE")
    toml = tmp_path / "out" / "MERGE.field.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + (
        '\n[[gateway]]\nname = "door0"\nto = 301\nzone = [[-500, 900], [-400, 900], '
        '[-400, 1000], [-500, 1000]]\n'), encoding="utf-8", newline="\n")
    for _ in range(2):                                 # every regenerate, not just the first
        man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE")
        data = tomllib.loads(toml.read_text(encoding="utf-8"))
        assert [g["name"] for g in data["gateway"]] == ["door0"]
        assert man["removed"] == []


_PLACE_ROWS = (
    '\n[[gateway]]\nname = "door0"\nto = 301\nzone = [[-500, 900], [-400, 900], '
    '[-400, 1000], [-500, 1000]]\n'
    '\n[[event]]\nname = "zone0"\nmessage = "..."\nzone = [[100, 900], [200, 900], '
    '[200, 1000], [100, 1000]]\n')


@pytest.mark.parametrize("regions", [
    {"events": ["It creaks.@200,340;300,340;300,380;200,380"]},
    {"gateways": ["4005@60,300;140,300;140,330;60,330"]},
    {"gateways": ["4005@60,300;140,300;140,330;60,330"],
     "events": ["It creaks.@200,340;300,340;300,380;200,380"]},
], ids=["first-event", "first-gateway", "both"])
def test_the_first_region_a_session_adds_never_deletes_a_place_row(tmp_path, regions):
    """THE TRANSITION the no-regions gate left open (review finding T1): trace a floor and
    generate with NO regions, draw a door and a zone in the Place tab (it mints door0/zone0),
    then add the session's FIRST region and regenerate. The file had no traced_ row, so it read
    as a pre-prefix project and the hand rows were claimed and deleted. A row the generator
    cannot PROVE it emitted is never deleted — whatever the session does next."""
    pytest.importorskip("PIL")
    import tomllib
    from PIL import Image
    Image.new("RGB", (384, 448), (90, 80, 70)).save(tmp_path / "src.png")
    floor = [(130, 140), (254, 140), (364, 440), (20, 440)]
    IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE")
    toml = tmp_path / "out" / "MERGE.field.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + _PLACE_ROWS, encoding="utf-8", newline="\n")
    for _ in range(2):                                 # the first regenerate with regions, and the next
        man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                                   **regions)
        data = tomllib.loads(toml.read_text(encoding="utf-8"))
        assert "door0" in [g["name"] for g in data["gateway"]]
        assert "zone0" in [e["name"] for e in data["event"]]
        assert next(g for g in data["gateway"] if g["name"] == "door0")["to"] == 301
        assert man["removed"] == []
        assert "[[gateway]] door0" in man["kept"] and "[[event]] zone0" in man["kept"]


def test_a_pre_prefix_row_is_renamed_only_when_the_run_re_emits_its_exact_quad(tmp_path):
    """The one thing that still proves a door0 is the OLD generator's: this run emits the very
    same quad again (a b18/b19 project reopened from its sidecar regenerates px-exact). Then the
    row is replaced by its traced_ twin — said out loud in retaken, never doubled. A pre-prefix
    row whose quad the run does NOT re-emit stays: indistinguishable from a Place row, so kept."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path)       # one gateway + one event, traced_ names
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    data["gateway"][0]["name"] = "door0"               # the pre-prefix shape of the SAME rows
    data["event"][0]["name"] = "zone0"
    from ff9mapkit.editor import model as _model
    toml.write_text(_model.dumps(data), encoding="utf-8", newline="\n")
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                               gateways=["4005@60,300;140,300;140,330;60,330"],
                               events=["It creaks.@200,340;300,340;300,380;200,380"])
    data2 = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert [g["name"] for g in data2["gateway"]] == ["traced_door0"]      # renamed, not doubled
    assert [e["name"] for e in data2["event"]] == ["traced_zone0"]
    assert man["removed"] == []                        # nothing was lost, so nothing is "removed"
    retaken = "\n".join(man["retaken"])
    assert "door0" in retaken and "traced_door0" in retaken
    assert "zone0" in retaken and "traced_zone0" in retaken
    retaken.encode("cp1252")                           # the CLI prints these under a cp1252 pipe


_GW = "4005@60,300;140,300;140,330;60,330"
_EV = "It creaks.@200,340;300,340;300,380;200,380"


def _rewrite(toml, edit):
    """Load the project's toml, let ``edit(data)`` change it, write it back the Editor's way."""
    import tomllib
    from ff9mapkit.editor import model as _model
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    edit(data)
    toml.write_text(_model.dumps(data), encoding="utf-8", newline="\n")


def _regen(tmp_path, floor, **kw):
    import tomllib
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE", **kw)
    return man, tomllib.loads((tmp_path / "out" / "MERGE.field.toml").read_text(encoding="utf-8"))


def test_the_twin_rename_is_fenced_on_every_side(tmp_path):
    """The rename may only ever take a PRE-PREFIX-NAMED row of the SAME KIND on a file with NO
    traced_ row. Each guard, loosened, deletes a row somebody drew -- so each has a row here."""
    pytest.importorskip("PIL")
    toml, floor, _man = _merge_project(tmp_path)       # traced_door0 + traced_zone0

    # (1) a CURRENT project (it has traced_ rows): a Place door0 on the traced door's exact quad
    _rewrite(toml, lambda d: d["gateway"].append(dict(d["gateway"][0], name="door0", to=301)))
    man, data = _regen(tmp_path, floor, gateways=[_GW], events=[_EV])
    assert [(g["name"], g["to"]) for g in data["gateway"]] == [("traced_door0", 4005), ("door0", 301)]
    assert man["removed"] == []

    # (2)-(4) a PRE-PREFIX file: only door<N>/zone<N> of the right kind are candidates
    def legacy(d):
        quad = d["gateway"][0]["zone"]
        d["gateway"] = [dict(d["gateway"][0], name="west_gate", to=11),
                        dict(d["gateway"][0], name="door_west", to=12)]
        d["event"] = [{"name": "zone0", "message": "mine", "zone": quad}]   # an EVENT on the door's quad
    _rewrite(toml, legacy)
    man, data = _regen(tmp_path, floor, gateways=[_GW])
    assert sorted(g["name"] for g in data["gateway"]) == ["door_west", "traced_door0", "west_gate"]
    assert [e["name"] for e in data["event"]] == ["zone0"] and man["removed"] == []


def test_a_pre_prefix_row_stored_with_a_doubled_last_vertex_is_still_its_twin(tmp_path):
    """The IsInQuad-safe stored form repeats the last corner; it is the same quad."""
    pytest.importorskip("PIL")
    toml, floor, _man = _merge_project(tmp_path)

    def legacy(d):
        g = d["gateway"][0]
        d["gateway"] = [dict(g, name="door0", zone=g["zone"] + [g["zone"][-1]])]
        d.pop("event")
    _rewrite(toml, legacy)
    _man2, data = _regen(tmp_path, floor, gateways=[_GW])
    assert [g["name"] for g in data["gateway"]] == ["traced_door0"]


def test_a_pre_prefix_door_is_still_recognized_after_the_pitch_is_changed(tmp_path):
    """The old row's quad was written through the camera the FILE records. Through the new
    camera alone the same pixels land elsewhere: the twin was missed and the old door stayed as
    a second, live gateway at its old spot (the adversarial pass's regression on the T1 fix)."""
    pytest.importorskip("PIL")
    toml, floor, _man = _merge_project(tmp_path)

    def legacy(d):
        d["gateway"][0]["name"] = "door0"
        d["event"][0]["name"] = "zone0"
    _rewrite(toml, legacy)
    man, data = _regen(tmp_path, floor, gateways=[_GW], events=[_EV], pitch=30.0)
    assert [g["name"] for g in data["gateway"]] == ["traced_door0"]      # one door, not two
    assert [e["name"] for e in data["event"]] == ["traced_zone0"]
    assert data["camera"]["pitch"] == 30 and man["removed"] == []


def test_what_a_regenerate_takes_from_a_traced_row_is_said_out_loud(tmp_path):
    """A traced row is regenerated WHOLE. A retarget made in Place and a reward added in the
    Editor used to vanish silently; both are now named. (They are deliberately NOT carried over:
    see the next test.)"""
    pytest.importorskip("PIL")
    toml, floor, _man = _merge_project(tmp_path)

    def author(d):
        d["event"][0].update(give_item=[236, 1], message="MY OWN WORDS")
        d["gateway"][0].update(to=2222, requires_flag="met_cid")
    _rewrite(toml, author)
    man, data = _regen(tmp_path, floor, gateways=[_GW], events=[_EV])
    assert data["event"][0] == {k: v for k, v in data["event"][0].items() if k in ("name", "message", "zone")}
    assert data["event"][0]["message"] == "It creaks." and data["gateway"][0]["to"] == 4005
    retaken = "\n".join(man["retaken"])
    assert "traced_door0.to (was 2222" in retaken and "traced_zone0.message" in retaken
    assert "traced_zone0.give_item (a hand-added key, dropped" in retaken
    assert "traced_door0.requires_flag (a hand-added key, dropped" in retaken
    retaken.encode("cp1252")
    man2, _data2 = _regen(tmp_path, floor, gateways=[_GW], events=[_EV])
    assert not [r for r in man2["retaken"] if "traced_" in r]             # said once, not forever


def test_a_hand_key_is_never_grafted_onto_the_door_that_inherits_the_name(tmp_path):
    """traced_ names are POSITIONAL. Delete session door A and door B becomes traced_door0: A's
    reward and flag gate must not land on B's quad (the second adversarial pass's catch on a
    follow-up that carried such keys over by name)."""
    pytest.importorskip("PIL")
    door_b = "4007@250,300;330,300;330,330;250,330"
    toml, floor, _man = _merge_project(tmp_path, gateways=(_GW, door_b))
    _rewrite(toml, lambda d: d["gateway"][0].update(reward={"item": "Elixir"}, requires_flag=9000))
    man, data = _regen(tmp_path, floor, gateways=[door_b])                 # door A deleted in the session
    assert len(data["gateway"]) == 1
    row = data["gateway"][0]
    assert (row["name"], row["to"]) == ("traced_door0", 4007)
    assert "reward" not in row and "requires_flag" not in row
    assert any("traced_door0.reward" in r and "dropped" in r for r in man["retaken"])


def test_only_one_pre_prefix_row_can_take_a_traced_name(tmp_path):
    """A pitch change gives a region TWO quads a pre-prefix row could sit on: the one under the
    file's old camera and the one under the new. Two rows, one on each, must not both be claimed
    as the same door -- one is renamed, the other is somebody's and stays exactly as it was."""
    pytest.importorskip("PIL")
    import tomllib
    toml, floor, _man = _merge_project(tmp_path, gateways=(_GW,))
    old_quad = tomllib.loads(toml.read_text(encoding="utf-8"))["gateway"][0]["zone"]
    _man30, data30 = _regen(tmp_path, floor, gateways=[_GW], pitch=30.0)   # learn the new-camera quad
    new_quad = data30["gateway"][0]["zone"]
    assert new_quad != old_quad

    def legacy(d):                                     # back to the pitch-26 file, pre-prefix shape
        d["camera"]["pitch"] = 26
        d["gateway"] = [{"name": "door0", "to": 4005, "zone": old_quad},
                        {"name": "door1", "to": 4999, "zone": new_quad, "note": "mine"}]
        d.pop("event", None)
    _rewrite(toml, legacy)
    man, data = _regen(tmp_path, floor, gateways=[_GW], pitch=30.0)
    rows = {g["name"]: g for g in data["gateway"]}
    assert sorted(rows) == ["door1", "traced_door0"]
    assert rows["door1"] == {"name": "door1", "to": 4999, "zone": new_quad, "note": "mine"}
    assert man["removed"] == []


def test_claimed_and_stale_rows_are_named_in_removed(tmp_path):
    """Deletion is REPORTED, never silent (floorplan.merge_room's own contract): a stale
    traced_ door and a traced_ zone dropped from the session both land in removed,
    and the manifest carries the list the CLI prints."""
    pytest.importorskip("PIL")
    toml, floor, _man = _merge_project(
        tmp_path, gateways=("4005@60,300;140,300;140,330;60,330",
                            "4007@250,300;330,300;330,330;250,330"))
    man = IF.build_image_field(tmp_path / "src.png", floor, tmp_path / "out", name="MERGE",
                               gateways=["4005@60,300;140,300;140,330;60,330"])
    assert "[[gateway]] traced_door1" in man["removed"]
    assert "[[event]] traced_zone0" in man["removed"]  # the session dropped its event too


# --------------------------------------------------------------- batch 3, the final review
def test_an_existing_project_keeps_its_name_through_a_regenerate(tmp_path):
    """The name rule (T7) guards the mint of a new <name>.field.toml. A project built before the
    rule may be named attic-room; refusing its own name made it impossible to regenerate. A NEW
    file under such a name is still refused before anything is written."""
    from pathlib import Path

    from PIL import Image
    photo = tmp_path / "room.png"
    Image.new("RGB", (800, 600), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    out = tmp_path / "proj"
    made = Path(IF.build_image_field(photo, floor, out, name="ATTIC", field_id=30779)["toml"])
    old = made.with_name("attic-room.field.toml")
    old.write_text(made.read_text(encoding="utf-8").replace('name = "ATTIC"', 'name = "attic-room"'),
                   encoding="utf-8")
    made.unlink()
    moved = [(120.0, 210.0)] + floor[1:]
    man = IF.build_image_field(photo, moved, out, name="attic-room", field_id=30779)
    assert Path(man["toml"]) == old and old.is_file()
    with pytest.raises(IF.ImageFieldError, match="letters, digits and underscores"):
        IF.build_image_field(photo, floor, tmp_path / "fresh", name="attic-room", field_id=30779)
    assert not (tmp_path / "fresh").exists()


def test_exif_turned_reads_the_orientation_tag(tmp_path):
    from PIL import Image
    plain = tmp_path / "plain.png"
    Image.new("RGB", (8, 6)).save(plain)
    exif = Image.Exif()
    exif[0x0112] = 6
    turned = tmp_path / "turned.jpg"
    Image.new("RGB", (8, 6)).save(turned, exif=exif)
    exif[0x0112] = 1
    upright = tmp_path / "upright.jpg"
    Image.new("RGB", (8, 6)).save(upright, exif=exif)
    assert IF.exif_turned(turned) is True
    assert IF.exif_turned(plain) is False and IF.exif_turned(upright) is False
    assert IF.exif_turned(tmp_path / "gone.jpg") is False


@pytest.mark.parametrize("name", ["x/../PHONE", "x\\..\\PHONE", "./PHONE"])
def test_a_name_carrying_a_path_is_never_past_the_name_rule(tmp_path, name):
    """The exemption 'this name already names a file' was asked of the PATH: 'x/../PHONE'
    resolves to the existing PHONE.field.toml, skipped the rule, and was written into the
    project as its name (the backslash form died in the TOML parser instead -- the crash the rule
    exists to stop). Only a bare name can be an existing project's name."""
    from PIL import Image
    photo = tmp_path / "room.png"
    Image.new("RGB", (800, 600), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    out = tmp_path / "proj"
    IF.build_image_field(photo, floor, out, name="PHONE", field_id=30779)
    before = {q.name: q.read_bytes() for q in out.rglob("*") if q.is_file()}
    with pytest.raises(IF.ImageFieldError, match="letters, digits and underscores"):
        IF.build_image_field(photo, floor, out, name=name, field_id=30779)
    assert {q.name: q.read_bytes() for q in out.rglob("*") if q.is_file()} == before
