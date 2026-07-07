"""Pure tests for [[playable]] portrait -- the custom menu-portrait (Face Atlas override) emitter."""
from __future__ import annotations

from PIL import Image

from ff9mapkit.content import portrait as P


def _img(w=132, h=190, c=(255, 0, 0, 255)):
    return Image.new("RGBA", (w, h), c)


def test_sprite_name():
    assert P.sprite_name(12) == "face_cu12" and P.sprite_name(13) == "face_cu13"


def test_build_face_atlas_single():
    sheet, tp = P.build_face_atlas([{"name": "face_cu12", "image": _img()}])
    assert sheet.size == (132, 190)
    lines = tp.strip().splitlines()
    assert lines[:3] == [":format=40000", ":size=132x190", ":append=true"]     # Moguri-proven append grammar
    assert lines[3] == "face_cu12;0;0;132;190;0;0;0;0;0;0;0;0;0;0"              # name;x;y;w;h;pads;borders


def test_build_face_atlas_multi_strip():
    sheet, tp = P.build_face_atlas([{"name": "face_cu12", "image": _img()},
                                    {"name": "face_cu13", "image": _img(w=100)}])
    assert sheet.size == (232, 190)                                            # packed horizontally
    lines = tp.strip().splitlines()
    assert lines[3].startswith("face_cu12;0;0;132;190;")
    assert lines[4].startswith("face_cu13;132;0;100;190;")                     # second sprite at x=132


def test_build_face_atlas_empty():
    sheet, tp = P.build_face_atlas([])
    assert sheet is None and tp == ""


def test_write_face_atlas(tmp_path):
    from ff9mapkit.config import ModLayout
    layout = ModLayout(tmp_path / "mod")
    w = P.write_face_atlas(layout, [{"name": "face_cu12", "image": _img(c=(0, 0, 255, 255))}])
    assert (layout.face_atlas_dir / "Face Atlas.png").is_file()
    assert (layout.face_atlas_dir / "Face Atlas.png.tpsheet").is_file()
    assert w and any("RELAUNCH" in m for m in w)                              # the launch-time-load warning


def test_load_portrait_size_warning(tmp_path):
    _img(w=64, h=64).save(tmp_path / "small.png")
    img, warns = P.load_portrait("small.png", base_dir=tmp_path)
    assert img.size == (64, 64) and any("132x190" in m for m in warns)        # off-size -> a warning, not an error
    _img().save(tmp_path / "ok.png")
    _img2, w2 = P.load_portrait(tmp_path / "ok.png")
    assert w2 == []                                                           # exact size -> clean
    import pytest
    with pytest.raises(P.PortraitError):
        P.load_portrait("nope.png", base_dir=tmp_path)                        # missing file
