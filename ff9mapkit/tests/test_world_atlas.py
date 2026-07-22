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


def test_find_free_region_and_paint_tile():
    # 128x128 atlas, all opaque except a transparent bottom-right 48x48 corner
    im = Image.new("RGBA", (128, 128), (10, 20, 30, 255))
    for y in range(80, 128):
        for x in range(80, 128):
            im.putpixel((x, y), (0, 0, 0, 0))
    box = A.find_free_region(im, 48, cell=16)
    assert box is not None
    l, t, r, b = box
    assert l >= 80 and t >= 80 and (r - l) == 48                # the free corner
    assert A.find_free_region(Image.new("RGBA", (64, 64), (1, 1, 1, 255)), 48) is None   # no gap -> None
    # paint a tile in -> region becomes opaque, uv rect is INSET (strictly inside the painted box)
    painted, uv = A.paint_tile(im, A.make_test_tile(48), box, inset=1)
    from PIL import ImageStat
    assert ImageStat.Stat(painted.crop(box).getchannel("A")).mean[0] > 250   # now opaque
    u0, v0, u1, v1 = uv
    assert l / 128 < u0 < u1 < r / 128                         # umin inset in from the box's left edge
    assert 0.0 <= v0 < v1 <= 1.0


def test_make_test_tile():
    t = A.make_test_tile(32)
    assert t.size == (32, 32) and t.mode == "RGBA"
    assert t.getpixel((0, 0))[3] == 255                        # opaque


def test_add_tile_stubbed(tmp_path, monkeypatch):
    from ff9mapkit import config
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    im = Image.new("RGBA", (128, 128), (10, 20, 30, 255))
    for y in range(80, 128):
        for x in range(80, 128):
            im.putpixel((x, y), (0, 0, 0, 0))
    monkeypatch.setattr(A, "load_atlas", lambda part="object", game=None: im)
    info = A.add_tile(A.make_test_tile(48), "object", mod_folder="FF9CustomMap", tile_px=48)
    assert "uv_rect" in info and len(info["uv_rect"]) == 4
    dest = tmp_path / "FF9CustomMap" / "StreamingAssets/assets/resources/worldmap/textures/res(1_24)_objects.png"
    assert dest.is_file()                                      # the reskinned atlas was deployed


# ---------------------------------------------------------------- engine-true source resolution + keyed cache
# The 2026-07-22 trap: a stale vanilla extract cache silently shadowed the Moguri HD atlas the game renders,
# so texture-judging instruments measured pixels the game never shows. load_atlas now resolves the source the
# way the ENGINE does (SearchAssetOnDisc over the FolderNames stack) and only trusts the cache for the bundle,
# keyed to its source p0data file.

def _mk_game(tmp_path, folders=("ModA", "ModB")):
    g = tmp_path / "game"
    (g / "StreamingAssets").mkdir(parents=True)
    if folders is not None:
        names = ", ".join(f'"{f}"' for f in folders)
        (g / "Memoria.ini").write_text(f"[Mod]\nFolderNames = {names}\n", encoding="utf-8")
    return g


def _put_loose(g, folder, part="terrain", color=(0, 0, 255, 255), size=128, lower=True, ff9data=False):
    rel = "FF9_Data/WorldMap/Textures" if ff9data else "StreamingAssets/Assets/Resources/WorldMap/Textures"
    if lower and not ff9data:                                             # Moguri ships lowercase assets/...
        rel = "StreamingAssets/" + rel.split("/", 1)[1].lower()
    d = (g / folder / rel) if folder else (g / rel)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{A.ATLAS_NAMES[part]}.png"
    Image.new("RGBA", (size, size), color).save(p)
    return p


def test_resolve_atlas_source_foldernames_order(tmp_path, monkeypatch):
    g = _mk_game(tmp_path)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: g)
    assert A.resolve_atlas_source("terrain") == ("bundle", None)          # nothing loose -> the p0data atlas
    pb = _put_loose(g, "ModB", lower=True)                                # Moguri-style lowercase casing
    assert A.resolve_atlas_source("terrain") == ("loose", pb)
    pa = _put_loose(g, "ModA", lower=False)                               # a HIGHER folder now overrides
    assert A.resolve_atlas_source("terrain") == ("loose", pa)
    assert A.resolve_atlas_source("object") == ("bundle", None)           # parts resolve independently


def test_resolve_atlas_source_root_and_ff9data_sweeps(tmp_path, monkeypatch):
    g = _mk_game(tmp_path)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: g)
    # the game root ("" folder) is swept after every mod folder
    proot = _put_loose(g, "", lower=False)
    assert A.resolve_atlas_source("terrain") == ("loose", proot)
    # a LOWER folder's StreamingAssets hit beats a higher folder's FF9_Data one (sweep 1 completes first)
    pff9 = _put_loose(g, "ModA", ff9data=True)
    assert (g / "ModA" / "FF9_Data" / "WorldMap" / "Textures" / f"{A.ATLAS_NAMES['terrain']}.png") == pff9
    assert A.resolve_atlas_source("terrain") == ("loose", proot)
    proot.unlink()
    assert A.resolve_atlas_source("terrain") == ("loose", pff9)           # FF9_Data sweep as the fallback


def test_resolve_atlas_source_honors_modfilelist(tmp_path, monkeypatch):
    g = _mk_game(tmp_path)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: g)
    pa = _put_loose(g, "ModA")
    pb = _put_loose(g, "ModB")
    listed = "assets/resources/worldmap/textures/" + A.ATLAS_NAMES["terrain"].lower() + ".png"
    # a ModFileList.txt that does NOT list the atlas gates it OFF even though the file exists on disk
    (g / "ModA" / "ModFileList.txt").write_text("memoria.ini\nsome/other/file.png\n", encoding="utf-8")
    assert A.resolve_atlas_source("terrain") == ("loose", pb)
    # listing it turns ModA back on
    (g / "ModA" / "ModFileList.txt").write_text(f"memoria.ini\n{listed}\n", encoding="utf-8")
    assert A.resolve_atlas_source("terrain") == ("loose", pa)
    # entries after a <bundle> header are in-bundle, and an all-bundle list means an EMPTY loose set ->
    # the engine falls back to File.Exists (AssetList.Count == 0)
    (g / "ModA" / "ModFileList.txt").write_text(f"<p0data3.bin>\n{listed}\n", encoding="utf-8")
    assert A.resolve_atlas_source("terrain") == ("loose", pa)


def test_load_atlas_stale_cache_cannot_shadow_loose(tmp_path, monkeypatch):
    """THE regression: a sidecar-less vanilla cache must never shadow the loose atlas the game renders."""
    g = _mk_game(tmp_path)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: g)
    stale = g / "StreamingAssets" / ".ff9atlas_terrain.png"
    Image.new("RGBA", (64, 64), (255, 0, 0, 255)).save(stale)             # the vanilla-extract artifact
    _put_loose(g, "ModB", color=(0, 0, 255, 255), size=128)               # the Moguri-style HD override
    img = A.load_atlas("terrain")
    assert img.size == (128, 128) and img.getpixel((5, 5)) == (0, 0, 255, 255)
    assert not stale.is_file()                                            # the legacy artifact is healed away


def test_load_atlas_bundle_cache_keyed_to_source(tmp_path, monkeypatch):
    g = _mk_game(tmp_path, folders=None)                                  # no Memoria.ini: modless install
    monkeypatch.setattr(config, "find_game_path", lambda game=None: g)
    fake_bin = g / "StreamingAssets" / "p0data3.bin"
    fake_bin.write_bytes(b"v1")
    calls = []

    def fake_extract(sa, name):
        calls.append(name)
        return Image.new("RGBA", (64, 64), (0, 255, 0, 255)), fake_bin

    monkeypatch.setattr(A, "_extract_from_bundles", fake_extract)
    assert A.load_atlas("terrain").getpixel((0, 0)) == (0, 255, 0, 255)
    assert len(calls) == 1
    assert (g / "StreamingAssets" / ".ff9atlas_terrain.png.src.json").is_file()
    A.load_atlas("terrain")
    assert len(calls) == 1                                                # keyed cache hit, no re-extract
    fake_bin.write_bytes(b"v2-longer")                                    # the source bundle changed
    A.load_atlas("terrain")
    assert len(calls) == 2                                                # fingerprint mismatch -> re-extract
    (g / "StreamingAssets" / ".ff9atlas_terrain.png.src.json").unlink()
    A.load_atlas("terrain")
    assert len(calls) == 3                                                # sidecar-less cache is NEVER trusted


def test_load_atlas_source_bundle_ignores_loose(tmp_path, monkeypatch):
    g = _mk_game(tmp_path)
    monkeypatch.setattr(config, "find_game_path", lambda game=None: g)
    _put_loose(g, "ModA", color=(0, 0, 255, 255))
    monkeypatch.setattr(A, "_extract_from_bundles",
                        lambda sa, name: (Image.new("RGBA", (64, 64), (0, 255, 0, 255)),
                                          g / "StreamingAssets" / "p0data3.bin"))
    assert A.load_atlas("terrain").getpixel((0, 0)) == (0, 0, 255, 255)               # engine -> the override
    assert A.load_atlas("terrain", source="bundle", cache=False).getpixel((0, 0)) == (0, 255, 0, 255)
    with pytest.raises(ValueError):
        A.load_atlas("terrain", source="live")


def _game_ready() -> bool:
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
@pytest.mark.parametrize("part", ["terrain", "object"])
def test_real_atlas_extracts_1024(part, tmp_path):
    img = A.load_atlas(part, cache=False, source="bundle")
    assert img.size == (1024, 1024) and img.mode == "RGBA"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install")
def test_real_engine_atlas_is_what_renders():
    kind, loose = A.resolve_atlas_source("terrain")
    assert kind in ("loose", "bundle")
    if kind == "loose":
        assert loose.is_file()
    img = A.load_atlas("terrain", cache=False)
    # NOT necessarily square: Moguri's HD terrain atlas is 2048x4096. UVs are normalized, so any dims render.
    assert img.mode == "RGBA" and img.width >= 1024 and img.height >= 1024
