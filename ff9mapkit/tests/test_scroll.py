"""Larger-than-screen SCROLLING fields (Phase 1-2).

Covers the offline half of the scrolling feature, validated against engine-derived facts +
the in-game-proven 768x448 spike (field 4003):
  * cam.scroll_bounds — the Viewport that lets the view pan across the whole painting.
  * guide canvas size keys off cam.range (so the paint guide is the full painting, not one screen).
  * build — [camera.scroll] sets the scroll Viewport, decouples focal from a wide Range
    (window_width), and injects BGCACTIVE so the engine actually scrolls.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ff9mapkit.build import FieldProject, build_mod, is_scrolling
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.eb import EbScript, disasm
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G

BGCACTIVE = 0x71


# ---------------- scroll bounds ----------------
def test_scroll_bounds_matches_default_viewport_for_a_screen():
    # a screen-sized painting reproduces the kit's static DEFAULT_VIEWPORT (no real scroll)
    assert C.scroll_bounds((384, 448)) == tuple(G.DEFAULT_VIEWPORT)


def test_scroll_bounds_real_field_sample():
    # real FF9 multi-cam field TSHP camera 0: Range 480x320 -> Viewport 160,320,112,208
    assert C.scroll_bounds((480, 320)) == (160, 320, 112, 208)


def test_scroll_bounds_spike_value():
    # the in-game-proven 2x-wide spike (field 4003)
    assert C.scroll_bounds((768, 448)) == (160, 608, 112, 336)


# ---------------- guide canvas size ----------------
def test_guide_canvas_size_follows_range():
    cam = G.make_camera(40, 4500, proj=498, range_wh=(768, 448),
                        viewport=C.scroll_bounds((768, 448)))
    assert G._canvas_wh(cam) == (768, 448)


def test_paint_template_renders_at_full_canvas(tmp_path):
    cam = G.make_camera(40, 4500, proj=498, range_wh=(768, 448),
                        viewport=C.scroll_bounds((768, 448)))
    frame = G.frame_floor(cam, back_canvas_y=120, front_canvas_y=430)
    png = tmp_path / "tpl.png"
    G.render_paint_template(cam, frame, png, scale=2)
    assert Image.open(png).size == (768 * 2, 448 * 2)


# ---------------- build ----------------
def _scroll_project(tmp_path) -> Path:
    Image.new("RGBA", (768 * 2, 448 * 2), (40, 40, 40, 255)).save(tmp_path / "back.png")
    Image.new("RGBA", (768 * 2, 448 * 2), (0, 80, 0, 255)).save(tmp_path / "floor.png")
    toml = tmp_path / "scroll.field.toml"
    toml.write_text(
        '[field]\nid=4003\nname="SCROLL01"\narea=11\ntext_block=1073\n\n'
        "[camera]\npitch=40\ndistance=4500\nfov=42.2\nrange=[768,448]\nwindow_width=384\n\n"
        "[camera.scroll]\nenabled=true\n\n"
        "[walkmesh]\nquad=[[-2129,2136],[2129,2136],[2129,-2030],[-2129,-2030]]\ncharacter_offset=0\n\n"
        '[[layers]]\nimage="back.png"\nz=4000\n[[layers]]\nimage="floor.png"\nz=3000\n\n'
        "[player]\nspawn=[0,53]\n",
        encoding="utf-8")
    return toml


def test_is_scrolling_flag(tmp_path):
    assert is_scrolling(FieldProject.load(_scroll_project(tmp_path)))


def test_build_scroll_camera_and_overlays(tmp_path):
    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(_scroll_project(tmp_path))], out, mod_name="FF9CustomMap")
    fm = ModLayout(out).fieldmap_dir(info["fields"][0])
    cam = C.parse_bgx_cameras(str(fm / f"{info['fields'][0]}.bgx"))[0]
    # wide painting + scroll clamp, but normal focal length (proj from the 384 window, not 768)
    assert cam.range == [768, 448]
    assert list(cam.viewport) == [160, 608, 112, 336]
    assert cam.proj == G.proj_from_fov_x(42.2, 384)        # 498, NOT proj_from_fov_x(42.2, 768)
    # full-cover layers default to the canvas (Range) size
    from ff9mapkit.scene import bgx
    scene = bgx.BgxScene.from_file(fm / f"{info['fields'][0]}.bgx")
    assert all(tuple(o.size) == (768, 448) for o in scene.overlays)


def test_build_injects_bgcactive_all_langs(tmp_path):
    out = tmp_path / "mod"
    build_mod([FieldProject.load(_scroll_project(tmp_path))], out, mod_name="FF9CustomMap")
    L = ModLayout(out)
    for lang in LANGS:
        eb = L.eb_path(lang, "EVT_SCROLL01.eb.bytes").read_bytes()
        s = EbScript.from_bytes(eb)
        f = s.entry(0).func_by_tag(0)
        ops = [i.op for i in disasm.iter_code(eb, f.abs_start, f.abs_end)]
        assert BGCACTIVE in ops, f"{lang}: BGCACTIVE missing"


def test_non_scroll_field_unchanged():
    # a plain front-facing field still derives proj from its (screen-sized) range and no scroll
    cam = G.make_camera(40, 4500, fov_x_deg=42.2)
    assert list(cam.viewport) == list(G.DEFAULT_VIEWPORT)
    assert cam.range == [384, 448]
