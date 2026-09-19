"""Offline tests for the software model-preview renderer (no install/UnityPy needed).

The renderer's load-bearing conventions, each pinned here on tiny synthetic Model structs:
painter order (larger mean z = farther = drawn first), the Unity->PIL V flip when sampling a
texture, the REPEAT-wrap tile normalization (UVs a whole tile off must render identically --
GEO_SUB_W0_001 mesh1 authors u in [1..2] / v in [-1..0] and rendered BLANK before the fix), the
flat-gray fallback for an untextured model, and the stand-pose fallback when no clips resolve.
Real-install renders (Vivi & co.) are exercised via the CLI / the GUI thumb cache, not here.
"""
import math

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

from ff9mapkit.models import preview


def _tex(colors):
    """A tiny RGBA texture from a row-major color grid, e.g. [[red, blue]]."""
    h, w = len(colors), len(colors[0])
    im = Image.new("RGBA", (w, h))
    for y, row in enumerate(colors):
        for x, c in enumerate(row):
            im.putpixel((x, y), c)
    return im


def _quad_model(uv_shift=(0.0, 0.0), z=0.0, stem="t0", tex=None):
    """One mesh: a unit quad (2 tris) at depth z, UVs covering the texture (optionally tile-shifted)."""
    du, dv = uv_shift
    verts = [[0.0, 0.0, z], [10.0, 0.0, z], [10.0, 10.0, z], [0.0, 10.0, z]]
    uvs = [[0.0 + du, 1.0 + dv], [1.0 + du, 1.0 + dv], [1.0 + du, 0.0 + dv], [0.0 + du, 0.0 + dv]]
    mesh = {"name": "mesh0", "verts": verts, "normals": [[0.0, 0.0, -1.0]] * 4, "uvs": uvs,
            "submeshes": [{"material_idx": 0, "tris": [[0, 1, 2], [0, 2, 3]]}]}
    return {"meshes": [mesh], "materials": [{"name": "m0", "texture": stem}],
            "textures": {stem: tex} if tex is not None else {}}


RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 255)


def _pixels(img):
    return [img.getpixel((x, y)) for y in range(img.size[1]) for x in range(img.size[0])]


def test_renders_textured_quad_with_both_colors():
    m = _quad_model(tex=_tex([[RED, BLUE], [RED, BLUE]]))
    img = preview.render_model(m, size=64, yaw=0, pitch=0, shade=False, supersample=1)
    assert img.size == (64, 64)
    px = _pixels(img)
    assert any(p[0] > 200 and p[2] < 60 and p[3] > 0 for p in px), "red texels missing"
    assert any(p[2] > 200 and p[0] < 60 and p[3] > 0 for p in px), "blue texels missing"


def test_uv_tile_offset_renders_identically():
    """UVs a whole tile off (Unity REPEAT wrap) must render the same pixels as in-tile UVs."""
    tex = _tex([[RED, BLUE], [BLUE, RED]])
    base = preview.render_model(_quad_model(tex=tex), size=48, yaw=0, pitch=0,
                                shade=False, supersample=1)
    shifted = preview.render_model(_quad_model(uv_shift=(1.0, -1.0), tex=tex), size=48, yaw=0,
                                   pitch=0, shade=False, supersample=1)
    assert base.getbbox() is not None
    assert _pixels(base) == _pixels(shifted)


def test_painter_draws_nearer_triangle_on_top():
    """Two stacked quads: the one with the SMALLER z is nearer the camera and must win the overlap."""
    tex_near = _tex([[RED]])
    tex_far = _tex([[BLUE]])
    near = _quad_model(z=-5.0, stem="near", tex=tex_near)["meshes"][0]
    far = _quad_model(z=5.0, stem="far", tex=tex_far)["meshes"][0]
    far["submeshes"][0]["material_idx"] = 1
    m = {"meshes": [near, far],
         "materials": [{"name": "n", "texture": "near"}, {"name": "f", "texture": "far"}],
         "textures": {"near": tex_near, "far": tex_far}}
    img = preview.render_model(m, size=32, yaw=0, pitch=0, shade=False, supersample=1)
    cx = img.getpixel((16, 16))
    assert cx[0] > 200 and cx[2] < 60, f"near (red) quad should cover far (blue): {cx}"


def test_untextured_model_flat_fills():
    m = _quad_model(stem=None)
    m["textures"] = {}
    img = preview.render_model(m, size=32, yaw=0, pitch=0, shade=False, supersample=1)
    assert img.getbbox() is not None
    cx = img.getpixel((16, 16))
    assert cx[3] == 255 and 100 < cx[0] < 200, f"expected the flat gray fill: {cx}"


def test_empty_model_is_transparent():
    img = preview.render_model({"meshes": [], "materials": [], "textures": {}}, size=40)
    assert img.size == (40, 40) and img.getbbox() is None


def test_shading_darkens_a_grazing_face():
    """A face lit head-on must come out brighter than one nearly parallel to the light."""
    lit = _quad_model(tex=_tex([[(200, 200, 200, 255)]]))
    img_lit = preview.render_model(lit, size=32, yaw=0, pitch=0, shade=True, supersample=1)
    grazing = _quad_model(tex=_tex([[(200, 200, 200, 255)]]))
    # the light dir is (-.37,-.61,-.70); a normal perpendicular to it gets only the ambient floor
    grazing["meshes"][0]["normals"] = [[0.70 / 0.79, -0.37 / 0.79, 0.0]] * 4
    img_gr = preview.render_model(grazing, size=32, yaw=0, pitch=0, shade=True, supersample=1)
    assert img_lit.getpixel((16, 16))[0] > img_gr.getpixel((16, 16))[0]


def test_affine_solver_roundtrips_and_rejects_degenerate():
    s = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
    t = [(5.0, 7.0), (25.0, 7.0), (5.0, 27.0)]
    a, b, c, d, e, f = preview._affine_screen_to_tex(s, t)
    for (sx, sy), (tx, ty) in zip(s, t):
        assert math.isclose(a * sx + b * sy + c, tx, abs_tol=1e-9)
        assert math.isclose(d * sx + e * sy + f, ty, abs_tol=1e-9)
    assert preview._affine_screen_to_tex([(0, 0), (1, 1), (2, 2)], t) is None   # collinear screen tri


def test_trs_compose_identity_and_translation():
    ident = preview._trs4([0, 0, 0], [0, 0, 0, 1], [1, 1, 1])
    assert preview._mv4(ident, [3.0, 4.0, 5.0]) == [3.0, 4.0, 5.0]
    moved = preview._trs4([1, 2, 3], [0, 0, 0, 1], [1, 1, 1])
    assert preview._mv4(preview._mm4(ident, moved), [0.0, 0.0, 0.0]) == [1.0, 2.0, 3.0]


def test_stand_pose_falls_back_on_a_bad_env():
    """No clips reachable (env raises / has none) -> the rest bones come back unchanged."""
    bones = [{"name": "bone000", "parent": None, "pos": [0, 0, 0], "rot": [0, 0, 0, 1],
              "scale": [1, 1, 1]}]

    class _Boom:
        @property
        def container(self):
            raise RuntimeError("no p0data5 here")

    assert preview._stand_pose(310, bones, env5=_Boom()) is bones

    class _Empty:
        container = {}

    assert preview._stand_pose(310, bones, env5=_Empty()) is bones


def test_stand_pose_applies_frame0_keys():
    """A fake env5 + monkeypatched read_clip: the stand clip's first keys re-pose the bones."""
    bones = [{"name": "bone000", "parent": None, "pos": [0, 0, 0], "rot": [0, 0, 0, 1],
              "scale": [1, 1, 1]},
             {"name": "bone001", "parent": "bone000", "pos": [0, 5, 0], "rot": [0, 0, 0, 1],
              "scale": [1, 1, 1]}]

    class _FakeType:
        name = "AnimationClip"

    class _FakeObj:
        type = _FakeType()

    class _Env:
        container = {"assets/resources/animations/310/4708.anim": _FakeObj()}

    import ff9mapkit.models._gltf_io as gio
    real = gio.read_clip
    try:
        gio.read_clip = lambda env, gid, key: {
            "name": "stand", "sample_rate": 30.0, "length": 1.0,
            "bones": {"bone000/bone001": {"bone": 1,
                                          "rot": [(0.0, (0.0, 1.0, 0.0, 0.0))],
                                          "pos": [(0.0, (1.0, 2.0, 3.0))]}}}
        posed = preview._stand_pose(310, bones, env5=_Env())
    finally:
        gio.read_clip = real
    assert posed[0]["rot"] == [0, 0, 0, 1]            # unkeyed bone keeps its rest TRS
    assert posed[1]["rot"] == [0.0, 1.0, 0.0, 0.0]    # keyed bone takes the clip's frame 0
    assert posed[1]["pos"] == [1.0, 2.0, 3.0]
    assert bones[1]["rot"] == [0, 0, 0, 1]            # the input list is not mutated
