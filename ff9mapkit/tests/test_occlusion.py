"""Per-tile occlusion for editable forks (the "Zidane drew UNDER the boxes" fix).

Real FF9 fields occlude the player per 16px TILE: the engine draws each tile-sprite at its OWN depth
(BGSCENE_DEF.cs:1742/1846). A pure-`.bgx` OVERLAY carries only ONE depth per PNG, so the kit used to
collapse a whole overlay to `min(sprite.depth)` -- the NEAREST tile -- and a multi-depth overlay (a box)
drew entirely in front of the player even where he stood before it. The fix splits each overlay into one
sub-PNG per distinct tile depth. These tests pin: the depth split (root-cause regression), the tile crop
geometry, the per-tile composite + position/size emission, depth bucketing, and the build round-trip.

Provenance-clean: all art here is synthetic PIL; no Square-Enix bytes.
"""
from __future__ import annotations

import pytest

from ff9mapkit import build, extract
from ff9mapkit.scene import bgs, bgx, cam


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False

NONE = extract._ABR_NONE
ADD = "PSX/FieldMap_Abr_1"


def _sprite(offX, offY, depth, trans=0, alpha=0):
    return bgs.Sprite(offX, offY, depth, trans, alpha)


def _overlay(sprites, orgX=0, orgY=0, orgZ=0):
    o = bgs.Overlay(orgX=orgX, orgY=orgY, orgZ=orgZ)
    o.sprites = sprites
    return o


# --- the tile-crop arithmetic -------------------------------------------------------------
def test_tile_box():
    # tile (offX,offY) sits (offX-mnX, offY-mnY) tiles into its overlay's Overlay{i}.png, each 16px x4.
    assert bgs.tile_box(_sprite(0, 0, 0), 0, 0, 4) == (0, 0, 64, 64)
    assert bgs.tile_box(_sprite(16, 0, 0), 0, 0, 4) == (64, 0, 128, 64)
    assert bgs.tile_box(_sprite(32, 48, 0), 16, 16, 4) == (64, 128, 128, 192)   # minus the overlay min
    assert bgs.tile_box(_sprite(16, 16, 0), 16, 16, 1, tile=16) == (0, 0, 16, 16)


# --- the depth split (DIRECT root-cause regression) ---------------------------------------
def test_depth_groups_split_per_tile_not_min_flatten():
    # An overlay whose tiles span depths {100, 400} must yield TWO groups at z=100 AND z=400 --
    # NOT one group at min()=100 (the old flatten that drew the player under the far tile).
    o = _overlay([_sprite(0, 0, 400), _sprite(16, 0, 100)])
    groups, skipped = extract._depth_groups([o], 0, 0, 0, lambda i: True)
    assert skipped == 0
    assert {k[0] for k in groups} == {100, 400}              # both depths kept, no min-collapse
    assert all(k[1] == NONE for k in groups)
    # each group's z is its OWN tile depth; the far tile (400) is NOT pulled to the near 100
    assert len(groups[(400, NONE)]) == 1 and len(groups[(100, NONE)]) == 1


def test_depth_groups_merge_same_depth_tiles():
    # tiles at the SAME depth (a tiled plane) share one layer; a different depth splits off.
    o = _overlay([_sprite(0, 0, 200), _sprite(16, 0, 200), _sprite(32, 0, 900)])
    groups, _ = extract._depth_groups([o], 0, 0, 0, lambda i: True)
    assert {k[0] for k in groups} == {200, 900}
    assert len(groups[(200, NONE)]) == 2 and len(groups[(900, NONE)]) == 1


def test_depth_groups_apply_scene_and_overlay_origin():
    # z = sceneOrgZ + overlay.orgZ + sprite.depth; scene_x/y carry scene + overlay origin too.
    o = _overlay([_sprite(5, 7, 100)], orgX=1000, orgY=2000, orgZ=50)
    groups, _ = extract._depth_groups([o], 10, 20, 3, lambda i: True)
    (key,) = groups
    bz, shader = key
    assert bz == 3 + 50 + 100                                # 153
    (i, s, sx, sy, mnX, mnY) = groups[key][0]
    assert (sx, sy) == (10 + 1000 + 5, 20 + 2000 + 7)        # scene + overlay + sprite offset
    assert (mnX, mnY) == (5, 7)


def test_depth_groups_bucket_tolerance():
    o = _overlay([_sprite(0, 0, 100), _sprite(16, 0, 400)])
    # a coarse tolerance buckets nearby depths into one layer (caps layer count)
    groups, _ = extract._depth_groups([o], 0, 0, 0, lambda i: True, depth_tolerance=512)
    assert {k[0] for k in groups} == {0}                     # 100//512==400//512==0
    assert len(groups[(0, NONE)]) == 2


def test_depth_groups_include_blend_filter():
    opaque = _overlay([_sprite(0, 0, 100, trans=0)])
    blend = _overlay([_sprite(0, 0, 200, trans=1, alpha=1)])
    g_all, sk_all = extract._depth_groups([opaque, blend], 0, 0, 0, lambda i: True)
    assert {k[1] for k in g_all} == {NONE, ADD} and sk_all == 0
    g_op, sk_op = extract._depth_groups([opaque, blend], 0, 0, 0, lambda i: True, include_blend=False)
    assert {k[1] for k in g_op} == {NONE} and sk_op == 1     # the blend overlay is skipped + counted


def test_depth_groups_skip_overlay_without_exported_png():
    o0 = _overlay([_sprite(0, 0, 100)])
    o1 = _overlay([_sprite(0, 0, 200)])
    groups, _ = extract._depth_groups([o0, o1], 0, 0, 0, lambda i: i == 0)   # only overlay 0 exported
    assert {gt[0] for v in groups.values() for gt in v} == {0}              # no tiles from overlay 1


# --- the per-tile composite (synthetic PIL: crop + placement + z + position/size) ---------
def test_render_per_tile_layers(tmp_path):
    from PIL import Image
    RED, BLUE = (255, 0, 0, 255), (0, 0, 255, 255)
    # Overlay0.png = the engine export: tileA (left, depth 400) red, tileB (right, depth 100) blue.
    png = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    png.paste(Image.new("RGBA", (64, 64), RED), (0, 0))
    png.paste(Image.new("RGBA", (64, 64), BLUE), (64, 0))
    tileA, tileB = _sprite(0, 0, 400), _sprite(16, 0, 100)
    o = _overlay([tileA, tileB])
    groups, _ = extract._depth_groups([o], 0, 0, 0, lambda i: True)
    layers, blend = extract._render_depth_groups(groups, lambda i: png, tmp_path, bleed=0)  # pure geometry

    assert blend == 0 and len(layers) == 2
    back, front = layers                                     # sorted back (large z) -> front
    assert back["z"] == 400 and front["z"] == 100
    # tight sub-PNGs at their own tile bbox (NOT a full canvas at [0,0])
    assert back["position"] == [0, 0] and back["size"] == [16, 16]
    assert front["position"] == [16, 0] and front["size"] == [16, 16]
    # the FAR tile is the red one at z=400 and the NEAR tile is blue at z=100 -- proving the two
    # depths are separated, not flattened to min()=100 (which would draw red in front of the player).
    assert Image.open(tmp_path / back["image"]).convert("RGBA").getpixel((32, 32)) == RED
    assert Image.open(tmp_path / front["image"]).convert("RGBA").getpixel((32, 32)) == BLUE
    # each sub-PNG is size x4 (the kit's upscale convention)
    assert Image.open(tmp_path / back["image"]).size == (64, 64)


# --- edge-bleed (kills the bilinear tile-cut seams) --------------------------------------
def test_edge_bleed_grows_opaque_into_transparent():
    from PIL import Image
    img = Image.new("RGBA", (6, 6), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (2, 2), (10, 20, 30, 255)), (2, 2))   # 2x2 opaque core, transparent border
    out = extract._edge_bleed(img, 1)
    assert out.getpixel((1, 1))[3] == 255 and out.getpixel((1, 1))[:3] == (10, 20, 30)   # grew 1px (colour)
    assert out.getpixel((4, 4))[3] == 255
    assert out.getpixel((0, 0))[3] == 0      # 2px out from the core stays transparent (1 pass = 1px)


def test_render_bleed_expands_opaque_layer_and_fills_margin(tmp_path):
    from PIL import Image
    RED = (200, 30, 30, 255)
    png = Image.new("RGBA", (64, 64), RED)                # one opaque tile, fully painted
    o = _overlay([_sprite(0, 0, 100)])
    groups, _ = extract._depth_groups([o], 0, 0, 0, lambda i: True)
    layers, _ = extract._render_depth_groups(groups, lambda i: png, tmp_path, bleed=1)
    L = layers[0]
    # an opaque layer expands by a 1px logical margin (position -1, size +2) so the bilinear cut seam has
    # real edge colour to sample instead of transparent.
    assert L["position"] == [-1, -1] and L["size"] == [18, 18]
    im = Image.open(tmp_path / L["image"]).convert("RGBA")
    assert im.size == (72, 72)                             # (16 + 2) * 4
    assert im.getpixel((1, 1))[3] == 255                  # the margin (outside the 64x64 tile) is filled
    assert im.getpixel((36, 36))[:3] == RED[:3]           # tile interior intact


def test_render_blend_layer_not_bled(tmp_path):
    from PIL import Image
    png = Image.new("RGBA", (64, 64), (80, 80, 200, 255))
    o = _overlay([_sprite(0, 0, 200, trans=1, alpha=1)])  # additive light overlay
    groups, _ = extract._depth_groups([o], 0, 0, 0, lambda i: True)
    layers, blend = extract._render_depth_groups(groups, lambda i: png, tmp_path, bleed=1)
    assert blend == 1
    # blend layers get NO margin (a bleed margin would double-add the glow where layers overlap)
    assert layers[0]["position"] == [0, 0] and layers[0]["size"] == [16, 16]
    assert layers[0]["shader"] == ADD


# --- build round-trip: the emitted layers -> one .bgx OVERLAY each, right Position z + Size --
def test_built_overlays_carry_per_tile_depth(tmp_path):
    layers = [
        {"image": "layer_00400_None.png", "z": 400, "position": [0, 0], "size": [16, 16]},
        {"image": "layer_00100_None.png", "z": 100, "position": [16, 0], "size": [16, 16]},
        {"image": "layer_00050_1.png", "z": 50, "position": [0, 0], "size": [32, 16], "shader": ADD},
    ]

    class _Proj:
        raw = {"layers": layers}

    overlays = build.build_overlays(_Proj())
    assert len(overlays) == 3
    assert overlays[0].position == (0, 0, 400) and overlays[0].size == (16, 16)
    assert overlays[1].position == (16, 0, 100)
    assert overlays[2].shader == ADD and overlays[2].position == (0, 0, 50)
    # serialize to a .bgx and confirm three OVERLAY blocks survive with their depth in Position
    text = bgx.build(cam.Cam(), overlays)
    parsed = bgx.BgxScene.parse(text)
    zs = [o.position[2] for o in parsed.overlays]
    assert zs == [400, 100, 50]


# --- NATIVE custom scene (the Moguri-faithful path: atlas + .bgs, no .bgx, no seams) -------
def test_native_scene_ships_bgs_atlas_no_bgx(tmp_path):
    # A native fork ships atlas.png + <FBG>.bgs.bytes + <FBG>.bgi.bytes and NO .bgx, so the engine's
    # LoadResources takes the seamless native branch (point-sampled atlas, per-tile depth) -- exactly how
    # Moguri ships. This is the faithful answer to the .bgx bilinear tile seams.
    from ff9mapkit import build
    from ff9mapkit.config import ModLayout
    from ff9mapkit.scene import bgi as _bgi
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "scene.bgs.bytes").write_bytes(b"FAKE_NATIVE_BGS")        # build copies it verbatim
    (proj / "atlas.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    wm = _bgi.build([(-100, 0, -100), (100, 0, -100), (100, 0, 100), (-100, 0, 100)], [(0, 1, 2), (0, 2, 3)])
    (proj / "walkmesh.bgi").write_bytes(wm.to_bytes())
    (proj / "n.field.toml").write_text(
        '[field]\nid = 4003\nname = "NAT"\narea = 11\ntext_block = 1073\n'
        'bgs = "scene.bgs.bytes"\natlas = "atlas.png"\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nbgi = "walkmesh.bgi"\n\n'
        '[player]\nspawn = [0, 0]\n', encoding="utf-8")
    p = build.FieldProject.load(proj / "n.field.toml")
    assert build.validate(p) == []                                   # native lint clean
    out = tmp_path / "mod"
    info = build.build_mod([p], out, mod_name="FF9CustomMap")
    fm = ModLayout(out).fieldmap_dir("FBG_N11_NAT")
    assert (fm / "FBG_N11_NAT.bgs.bytes").read_bytes() == b"FAKE_NATIVE_BGS"   # native .bgs shipped verbatim
    assert (fm / "atlas.png").is_file()                              # atlas shipped
    assert (fm / "FBG_N11_NAT.bgi.bytes").is_file()                  # custom walkmesh
    assert not (fm / "FBG_N11_NAT.bgx").exists()                     # NO .bgx -> seamless native path
    assert info["dictionary"] == ["FieldScene 4003 11 NAT NAT 1073"]


def test_native_scene_ships_mapconfig_lighting(tmp_path):
    # A native fork ships the field's MapConfigData (3D-model LIGHTING: per-floor lights + shadows + per-
    # object colors) under the fork's EVENT name -- EVT_<name>.bytes in commonasset/mapconfigdata -- so the
    # engine lights the models like the real field (else they render bright/untinted). Loaded by the SAME
    # event name as the .eb (MapConfiguration.LoadMapConfigData).
    from ff9mapkit.config import ModLayout
    from ff9mapkit.scene import bgi as _bgi
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scene.bgs.bytes").write_bytes(b"BGS")
    (proj / "atlas.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    (proj / "mapconfig.bytes").write_bytes(b"FAKE_MAPCONFIG_LIGHT")        # build ships it verbatim
    wm = _bgi.build([(-100, 0, -100), (100, 0, -100), (100, 0, 100), (-100, 0, 100)], [(0, 1, 2), (0, 2, 3)])
    (proj / "walkmesh.bgi").write_bytes(wm.to_bytes())
    (proj / "n.field.toml").write_text(
        '[field]\nid = 4003\nname = "NAT"\narea = 11\ntext_block = 1073\n'
        'bgs = "scene.bgs.bytes"\natlas = "atlas.png"\nmapconfig = "mapconfig.bytes"\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n[walkmesh]\nbgi = "walkmesh.bgi"\n\n[player]\nspawn = [0, 0]\n',
        encoding="utf-8")
    p = build.FieldProject.load(proj / "n.field.toml")
    assert build.validate(p) == []                                   # mapconfig present -> lint clean
    out = tmp_path / "mod"
    build.build_mod([p], out, mod_name="FF9CustomMap")
    mc = ModLayout(out).mapconfig_path("EVT_NAT")                     # shipped under the EVENT name
    assert mc.is_file() and mc.read_bytes() == b"FAKE_MAPCONFIG_LIGHT"


def test_native_scene_mapconfig_missing_file_is_flagged(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scene.bgs.bytes").write_bytes(b"x")
    (proj / "atlas.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (proj / "walkmesh.bgi").write_bytes(b"")
    (proj / "n.field.toml").write_text(
        '[field]\nid=4003\nname="NAT"\narea=11\ntext_block=1073\n'
        'bgs="scene.bgs.bytes"\natlas="atlas.png"\nmapconfig="missing.bytes"\n\n'
        '[camera]\npitch=45\nfov=42.2\n\n[walkmesh]\nbgi="walkmesh.bgi"\n\n[player]\nspawn=[0,0]\n',
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(proj / "n.field.toml"))
    assert any("mapconfig" in x for x in probs)                      # referenced-but-missing -> flagged


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_extract_mapconfig_for_real_field():
    # the real field 122 carries a MapConfigData lighting asset (the dim Dali storage-room lighting)
    mc = extract.extract_mapconfig("fbg_n08_udft_map122_uf_sto_0")
    assert mc and len(mc) > 0


def test_native_scene_validate_flags_missing_atlas(tmp_path):
    from ff9mapkit import build
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "scene.bgs.bytes").write_bytes(b"x")
    (proj / "walkmesh.bgi").write_bytes(b"")
    (proj / "n.field.toml").write_text(
        '[field]\nid = 4003\nname = "NAT"\narea = 11\ntext_block = 1073\nbgs = "scene.bgs.bytes"\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n[walkmesh]\nbgi = "walkmesh.bgi"\n\n[player]\nspawn = [0, 0]\n',
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(proj / "n.field.toml"))
    assert any("atlas" in x for x in probs)                          # native scene needs an atlas


def test_validate_layer_art_clean_for_tight_sublayers(tmp_path):
    from PIL import Image
    # a tight sub-PNG of size [16,16] is 64x64px (size x4) -> aspect matches -> no stretch warning.
    (tmp_path / "layer.png").write_bytes(b"")                # placeholder, overwritten below
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(tmp_path / "layer.png")

    class _Proj:
        raw = {"layers": [{"image": "layer.png", "z": 100, "position": [16, 0], "size": [16, 16]}]}
        def path(self, rel):
            return tmp_path / rel

    warnings = []
    build._validate_layer_art(_Proj(), (384, 448), warnings)
    assert warnings == []
