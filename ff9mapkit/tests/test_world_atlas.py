"""Overworld atlas extract + tile picker (world/atlas.py) -- UV->pixel mapping, blank(alpha) detection, crop,
palette blank-filter, the T2 reskin override path, and the visual catalog.

Hermetic via synthetic PIL atlases (Pillow is a hard dep). The p0data-backed extract is game-gated.
"""
from __future__ import annotations

import pytest
from PIL import Image

from ff9mapkit import config
from ff9mapkit.world import atlas as A


def _atlas(opaque=True, size=64):
    """A synthetic RGBA atlas: fully opaque (alpha 255) or fully transparent (alpha 0)."""
    return Image.new("RGBA", (size, size), (120, 80, 40, 255 if opaque else 0))


def test_uv_to_px_flips_v_and_clamps():
    w = h = 101
    assert A._uv_to_px(0.0, 0.0, w, h) == (0, h - 1)         # V=0 is the BOTTOM row (Unity bottom-up -> PIL top-down)
    assert A._uv_to_px(1.0, 1.0, w, h) == (w - 1, 0)         # V=1 is the TOP row
    assert A._uv_to_px(0.5, 0.5, w, h) == (50, 50)
    assert A._uv_to_px(2.0, -1.0, w, h) == (w - 1, h - 1)    # clamped


def test_tile_bbox_and_crop():
    tri = ((0.10, 0.80), (0.20, 0.80), (0.20, 0.90))
    l, t, r, b = A.tile_bbox_px(tri, 100, 100, pad=0)
    assert l < r and t < b                                   # a real box
    img = _atlas(size=100)
    crop = A.crop_tile(img, tri, pad=1)
    assert crop.width >= 1 and crop.height >= 1


def test_tile_is_blank_uses_alpha():
    tri = ((0.1, 0.1), (0.2, 0.1), (0.2, 0.2))
    assert A.tile_is_blank(_atlas(opaque=False), tri) is True   # transparent -> blank (renders white)
    assert A.tile_is_blank(_atlas(opaque=True), tri) is False   # opaque -> a real tile
    # a mixed atlas: opaque left, transparent right half
    im = Image.new("RGBA", (64, 64), (100, 100, 100, 255))
    for x in range(32, 64):
        for y in range(64):
            im.putpixel((x, y), (0, 0, 0, 0))
    assert A.tile_is_blank(im, ((0.05, 0.5), (0.15, 0.5), (0.15, 0.6))) is False   # left = opaque
    assert A.tile_is_blank(im, ((0.80, 0.5), (0.90, 0.5), (0.90, 0.6))) is True    # right = transparent


def test_filter_blank_drops_transparent_tiles(monkeypatch):
    real = ((0.05, 0.5), (0.15, 0.5), (0.15, 0.6))
    blank = ((0.80, 0.5), (0.90, 0.5), (0.90, 0.6))
    im = Image.new("RGBA", (64, 64), (100, 100, 100, 255))
    for x in range(32, 64):
        for y in range(64):
            im.putpixel((x, y), (0, 0, 0, 0))
    monkeypatch.setattr(A, "load_atlas", lambda part="terrain", game=None: im)
    pal = {10: [(real, 5), (blank, 3)], 59: [(blank, 9)]}
    out = A.filter_blank(pal, "object")
    assert out[10] == [(real, 5)]                            # blank variant dropped
    assert 59 not in out                                     # topo with only-blank tiles removed entirely


def test_filter_blank_is_noop_without_atlas(monkeypatch):
    def boom(*a, **k):
        raise ValueError("no atlas")
    monkeypatch.setattr(A, "load_atlas", boom)
    pal = {10: [(((0.1, 0.1),) * 3, 1)]}
    assert A.filter_blank(pal, "terrain") == pal             # graceful: can't filter -> unchanged


def test_override_path_and_deploy(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    p = A.atlas_override_path("terrain", mod_folder="FF9CustomMap")
    assert p == (tmp_path / "FF9CustomMap" / "StreamingAssets/assets/resources/worldmap/textures"
                 / "res(1_24)_terrain.png").resolve()
    src = tmp_path / "repaint.png"
    _atlas().save(src)
    dest = A.deploy_atlas(src, "object", mod_folder="FF9CustomMap")
    assert dest.name == "res(1_24)_objects.png" and dest.is_file()
    with pytest.raises(ValueError):
        A.deploy_atlas(tmp_path / "missing.png", "terrain", mod_folder="FF9CustomMap")


def test_tile_catalog_renders(tmp_path, monkeypatch):
    from ff9mapkit.world import palette as P
    monkeypatch.setattr(A, "load_atlas", lambda part="terrain", game=None: _atlas(size=256))
    monkeypatch.setattr(P, "build_palette",
                        lambda disc=1, part="terrain", game=None, **k:
                        {10: [(((0.1, 0.8), (0.2, 0.8), (0.2, 0.9)), 5)],
                         59: [(((0.5, 0.4), (0.6, 0.4), (0.6, 0.5)), 3)]})
    out = A.tile_catalog("object", out=tmp_path / "cat.png", per_topo=4)
    assert out.is_file()
    im = Image.open(out)
    assert im.width > 50 and im.height > 20                  # a real contact sheet (2 topo rows)


def _game_ready() -> bool:
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
@pytest.mark.parametrize("part", ["terrain", "object"])
def test_real_atlas_extracts_1024(part, tmp_path):
    img = A.load_atlas(part, cache=False)
    assert img.size == (1024, 1024) and img.mode == "RGBA"
