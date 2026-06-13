#!/usr/bin/env python3
"""Offline overlay-art assembler (scene.bgart) -- reproduces Memoria's [Export] Field=1 dump.

Two layers of proof:
  * Synthetic (no install): the assembler's placement / dims / transparent-init logic, against a
    hand-built atlas with known cell colors.
  * Install-gated: assemble real fields and diff vs Memoria's own on-disk FieldMaps dump. The
    BYTE-EXACT assertion crops the engine's OWN dumped atlas.png (codec-independent) -> diff 0; the
    OFFLINE assertion goes through the real p0data path and allows the sub-LSB noise of re-decoding a
    DXT-compressed atlas (Moguri ships the field atlas as DXT5).
"""
from __future__ import annotations

import pytest

from ff9mapkit.scene import bgart, bgs


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _spr(offX, offY, atlasX, atlasY):
    return bgs.Sprite(offX, offY, 0, 0, 0, atlasX=atlasX, atlasY=atlasY)


# --------------------------------------------------------------------- synthetic (no install)
def _atlas(colors):
    """A PIL atlas with each (atlasX, atlasY) cell flat-filled (tile_size=16)."""
    from PIL import Image
    im = Image.new("RGBA", (256, 256), (123, 123, 123, 255))   # distinct from white-init + tile colors
    for (ax, ay), col in colors.items():
        im.paste(Image.new("RGBA", (16, 16), col), (ax, ay))
    return im


def test_assemble_places_each_tile_at_its_own_slot():
    RED, GREEN, BLUE = (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)
    atlas = _atlas({(2, 2): RED, (20, 2): GREEN, (2, 20): BLUE})
    # tile_size 16 -> factor 1, so offX/offY (16-unit) map straight to pixels
    sprites = [_spr(0, 0, 2, 2), _spr(16, 0, 20, 2), _spr(0, 16, 2, 20)]
    img = bgart.assemble_overlay(atlas, sprites, 16)
    assert img.size == (32, 32)                                # max off 16 *1 + 16
    px = img.load()
    assert px[0, 0] == RED                                     # tile (0,0)
    assert px[16, 0] == GREEN                                  # tile (16,0)
    assert px[0, 16] == BLUE                                   # tile (0,16)


def test_uncovered_region_is_white_under_zero_alpha():
    # the engine inits the canvas to Color(1,1,1,0); a quadrant no tile covers must read (255,255,255,0).
    atlas = _atlas({(2, 2): (10, 20, 30, 255)})
    img = bgart.assemble_overlay(atlas, [_spr(0, 0, 2, 2), _spr(16, 16, 2, 2)], 16)
    assert img.size == (32, 32)
    assert img.load()[16, 0] == (255, 255, 255, 0)             # never-covered tile slot


def test_single_and_zero_sprite_overlays_are_one_tile():
    atlas = _atlas({(2, 2): (1, 2, 3, 255)})
    # the engine special-cases <=1 sprite to a single SPRITE_W x SPRITE_H tile, ignoring offset-based dims
    assert bgart.assemble_overlay(atlas, [_spr(48, 48, 2, 2)], 16).size == (16, 16)
    assert bgart.assemble_overlay(atlas, [], 16).size == (16, 16)
    assert bgart.assemble_overlay(atlas, [], 16).load()[0, 0] == (255, 255, 255, 0)


def test_factor_scales_placement_with_tile_size():
    atlas = _atlas({(2, 2): (9, 9, 9, 255), (70, 2): (8, 8, 8, 255)})   # cells at TileSize 64 spacing
    # tile_size 64 -> factor 4: a tile at offX=16 lands at pixel 64
    sprites = [_spr(0, 0, 2, 2), _spr(16, 0, 70, 2)]
    img = bgart.assemble_overlay(atlas, sprites, 64)
    assert img.size == (16 * 4 + 64, 64)                       # 128 x 64
    assert img.load()[0, 0] == (9, 9, 9, 255)
    assert img.load()[64, 0] == (8, 8, 8, 255)


def test_colocated_sprites_last_wins():
    # two sprites at the same slot -> the later one overwrites (matches the engine's SetPixels)
    atlas = _atlas({(2, 2): (1, 1, 1, 255), (20, 2): (2, 2, 2, 255)})
    img = bgart.assemble_overlay(atlas, [_spr(0, 0, 2, 2), _spr(0, 0, 20, 2)], 16)
    assert img.load()[0, 0] == (2, 2, 2, 255)


# --------------------------------------------------------------------- install-gated parity
def _first_exported_field():
    from ff9mapkit import config, extract
    fmroot = config.find_game_path(None) / "StreamingAssets" / "FieldMaps"
    if not fmroot.is_dir():
        return None
    for d in sorted(fmroot.iterdir()):
        if d.is_dir() and (d / "Overlay0.png").is_file() and (d / "atlas.png").is_file():
            try:
                extract.find_field(d.name.lower())            # resolvable through the field index
                return d
            except Exception:
                continue
    return None


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_byte_exact_vs_engine_atlas_crop():
    """Cropping the engine's OWN dumped atlas.png at our computed cell reproduces Overlay{i}.png
    EXACTLY (codec-independent): proves the cell math, the (absent) flip, dims, and placement."""
    from PIL import Image, ImageChops
    from ff9mapkit import extract
    fdir = _first_exported_field()
    if fdir is None:
        pytest.skip("no exported field with atlas.png on disk")
    ts = extract._active_tilesize(None)
    _, _, roles, env = extract.find_field(fdir.name.lower())
    bgs_bytes = extract._raw_bytes(env.container[roles["bgs"]].read())
    atlas = Image.open(fdir / "atlas.png").convert("RGBA")     # the engine's own readable copy
    _, overlays = bgs.parse_overlays(bgs_bytes)
    bgs.resolve_sprites(bgs_bytes, overlays, atlas.size[0], ts)
    imgs = bgart.assemble_overlays(atlas, overlays, ts)
    checked = 0
    for i, got in imgs.items():
        png = fdir / f"Overlay{i}.png"
        if not png.is_file():
            continue
        ref = Image.open(png).convert("RGBA")
        assert got.size == ref.size, f"{fdir.name}/Overlay{i}: {got.size} != {ref.size}"
        assert ImageChops.difference(got, ref).getbbox() is None, f"{fdir.name}/Overlay{i} not byte-exact"
        checked += 1
    assert checked > 0


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_offline_path_matches_export_within_codec_noise():
    """The real offline path (_overlay_art, atlas read from p0data) reproduces the on-disk export
    within the sub-LSB noise of re-decoding a (possibly DXT-compressed) atlas -- size-exact, tiny delta."""
    import numpy as np
    from PIL import Image
    from ff9mapkit import extract
    fdir = _first_exported_field()
    if fdir is None:
        pytest.skip("no exported field on disk")
    res = extract._overlay_art(fdir.name.lower())
    assert res is not None
    overlays, provider, factor, source, _atlas = res
    assert source == "offline"                                # the offline assembler, not the fallback
    worst = 0
    checked = 0
    for i in range(len(overlays)):
        png = fdir / f"Overlay{i}.png"
        got = provider(i)
        if got is None or not png.is_file():
            continue
        ref = Image.open(png).convert("RGBA")
        assert got.size == ref.size, f"{fdir.name}/Overlay{i}: {got.size} != {ref.size}"
        d = np.abs(np.asarray(got).astype(int) - np.asarray(ref).astype(int))
        worst = max(worst, int(d.max()))
        checked += 1
    assert checked > 0
    assert worst <= 16, f"{fdir.name}: offline vs export max per-channel delta {worst} > 16"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_export_writers_emit_layers_and_composite(tmp_path):
    """export_field_art writes per-overlay Overlay{i}.png (+ atlas.png); export_field_composite writes
    ONE flat <FBG>.png. Both produce real, non-trivial images for a resolvable field."""
    from PIL import Image
    from ff9mapkit import extract
    fdir = _first_exported_field()
    if fdir is None:
        pytest.skip("no exported field on disk")
    tok = fdir.name.lower()
    # raw per-overlay layers + atlas
    raw = extract.export_field_art(tok, tmp_path / "raw", game=None)
    assert raw["overlays"] > 0 and raw["atlas"]
    dest = tmp_path / "raw" / raw["folder"].upper()
    assert (dest / "Overlay0.png").is_file() and (dest / "atlas.png").is_file()
    # composite glimpse: one flat <FBG>.png, viewable size
    comp = extract.export_field_composite(tok, tmp_path / "gallery", game=None)
    png = tmp_path / "gallery" / f"{comp['folder'].upper()}.png"
    assert png.is_file()
    w, h = Image.open(png).size
    assert (w, h) == tuple(comp["size"]) and w > 16 and h > 16
