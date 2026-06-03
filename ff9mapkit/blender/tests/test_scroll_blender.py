"""Offline validation of the bpy-free Blender scrolling support (NO bpy import).

Mirrors the kit's scrolling feature in the Blender front-end:
  * a scrolling camera (wide Range, normal focal via window_width) round-trips Blender<->FF9,
  * the paint template sizes to the full painting + carries height (vertical) guides,
  * the floor frame fills the wide canvas; normal cameras are unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # .../ff9mapkit/blender
from ff9mapkit_blender import bridge                            # noqa: E402
from ff9mapkit_blender.vendor import cam as C                   # noqa: E402
from ff9mapkit_blender.vendor import guide as G                 # noqa: E402

WIN_W = 384


def _scroll_cam(range_wh=(768, 448)):
    proj = G.proj_from_fov_x(42.2, WIN_W)                       # focal from the 384 window, not 768
    return G.make_camera(40, 4500, proj=proj, range_wh=range_wh,
                         viewport=C.scroll_bounds(range_wh))


def test_scrolling_camera_roundtrips_with_window_width():
    c = _scroll_cam()
    b = bridge.ff9_cam_to_blender(c, window_width=WIN_W)
    c2 = bridge.blender_cam_to_ff9(b["location"], b["rotation"], b["lens"],
                                   sensor_width=b["sensor_width"], range_wh=(768, 448),
                                   viewport=C.scroll_bounds((768, 448)), window_width=WIN_W)
    assert c2.range == [768, 448]
    assert abs(c2.proj - c.proj) <= 1                          # focal preserved (NOT doubled)
    for i in range(3):
        for j in range(3):
            assert abs(c2.r[i][j] - c.r[i][j]) <= 1
        assert abs(c2.t[i] - c.t[i]) <= 1


def test_normal_camera_lens_unchanged_by_default():
    # window_width defaults to range width, so a normal field is untouched
    c = G.make_camera(40, 4500, fov_x_deg=42.2)                # range 384x448
    b = bridge.ff9_cam_to_blender(c)
    c2 = bridge.blender_cam_to_ff9(b["location"], b["rotation"], b["lens"],
                                   sensor_width=b["sensor_width"])
    assert c2.range == [384, 448] and abs(c2.proj - c.proj) <= 1


def test_paint_template_sizes_to_full_painting_with_height():
    c = _scroll_cam()
    t = bridge.paint_template_lines(c, 235, 432, scale=2)
    assert t["size"] == (768 * 2, 448 * 2)                     # full painting, not one screen
    assert t["height"], "scrolling template must include vertical height guides"
    # the floor outline fills the wide canvas at the front (near both edges)
    xs = [p[0] for seg in t["outline"] for p in seg]
    assert min(xs) < 60 * 2 and max(xs) > (768 - 60) * 2


def test_normal_template_is_one_screen():
    c = G.make_camera(40, 4500, fov_x_deg=42.2)
    t = bridge.paint_template_lines(c, 205, 432, scale=2)
    assert t["size"] == (384 * 2, 448 * 2)
    assert t["height"]                                         # height guides on every room


def test_floor_guide_has_wall_wireframe():
    c = _scroll_cam()
    g = bridge.floor_guide_geometry(c, 235, 432)
    assert g["wall_verts"] and g["wall_edges"]
    # 6 poles (2 verts each) -> 12 verts; 6 pole edges + 4 ceiling edges
    assert len(g["wall_verts"]) == 12 and len(g["wall_edges"]) == 10


def test_scroll_floor_frame_fills_canvas():
    c = _scroll_cam()
    fr = bridge.scroll_floor_frame(c, 235, 432)
    # front corners land near the canvas edges (0 and 768)
    fl = C.to_canvas(fr.corners_world[3], c)[0]
    frr = C.to_canvas(fr.corners_world[2], c)[0]
    assert fl < 60 and frr > 768 - 60


def test_scroll_export_feeds_ffmapkit_build(tmp_path):
    """The Blender scroll export (camera.bgx with wide Range + a [camera.scroll] toml) compiles, and
    the kit injects the BGCACTIVE enable so the engine scrolls. Mirrors the Export Field operator."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # .../ff9mapkit (the package)
    from ff9mapkit_blender.vendor import bgx
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import ModLayout, LANGS
    from ff9mapkit.eb import EbScript, disasm

    proj = tmp_path / "proj"; proj.mkdir()
    c = _scroll_cam()
    (proj / "camera.bgx").write_text(bgx.build(c, []), encoding="utf-8")
    verts = [(-2000.0, -2000.0, 0.0), (2000.0, -2000.0, 0.0), (2000.0, 0.0, 0.0), (-2000.0, 0.0, 0.0)]
    (proj / "walkmesh.obj").write_text(bridge.mesh_to_ff9_obj(verts, [(0, 1, 2), (0, 2, 3)]),
                                       encoding="utf-8")
    (proj / "room.field.toml").write_text(
        '[field]\nid = 4009\nname = "SCROLL_BL"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\nborrow = "camera.bgx"\n[camera.scroll]\nenabled = true\n\n'
        '[walkmesh]\nobj = "walkmesh.obj"\n\n[player]\nspawn = [0, -1000]\n', encoding="utf-8")

    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(proj / "room.field.toml")], out, mod_name="FF9CustomMap")
    L = ModLayout(out)
    # the borrowed camera carries the wide Range + scroll Viewport
    sc = C.parse_bgx_cameras(str(L.fieldmap_dir(info["fields"][0]) / f"{info['fields'][0]}.bgx"))[0]
    assert sc.range == [768, 448] and list(sc.viewport) == [160, 608, 112, 336]
    # and every language's script got the BGCACTIVE enable
    for lang in LANGS:
        eb = L.eb_path(lang, "EVT_SCROLL_BL.eb.bytes").read_bytes()
        s = EbScript.from_bytes(eb); f = s.entry(0).func_by_tag(0)
        assert 0x71 in [i.op for i in disasm.iter_code(eb, f.abs_start, f.abs_end)]
