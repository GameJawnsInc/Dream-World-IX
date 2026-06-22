#!/usr/bin/env python3
"""Native-art repaint round-trip (scene.bgart.repack_overlay + extract.export_native_repaint /
repack_native_atlas) -- the SPATIAL<->ATLAS loop that makes a native fork's tile-packed atlas
repaintable seamlessly. -> project-ff9-native-repaint-workflow.

Three layers of proof, all but the last install-free:
  * Pure inverse-blit identity: assemble_overlay -> repack_overlay reproduces every owner cell
    byte-exact (the guarantee the whole workflow rests on).
  * Synthetic project: a hand-built minimal .bgs + atlas + field.toml round-trips through
    export_native_repaint -> repack_native_atlas to a byte-identical atlas; a repaint of one tile
    lands in exactly that tile's atlas cell.
  * Install-gated: a real native fork's atlas survives the full export->repack loop byte-exact.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.scene import bgart, bgs


def _spr(offX, offY, atlasX, atlasY):
    return bgs.Sprite(offX, offY, 0, 0, 0, atlasX=atlasX, atlasY=atlasY)


def _atlas(colors, size=(256, 256), tile=16):
    """A PIL atlas with each (atlasX, atlasY) cell flat-filled at `tile`x`tile`."""
    from PIL import Image
    im = Image.new("RGBA", size, (123, 123, 123, 255))         # a backdrop distinct from every cell color
    for (ax, ay), col in colors.items():
        im.paste(Image.new("RGBA", (tile, tile), col), (ax, ay))
    return im


# --------------------------------------------------------------------- pure inverse-blit identity
def test_repack_overlay_is_exact_inverse_of_assemble():
    from PIL import ImageChops
    RED, GREEN, BLUE = (255, 0, 0, 255), (0, 200, 0, 255), (0, 0, 255, 255)
    cells = {(2, 2): RED, (20, 2): GREEN, (2, 20): BLUE}
    atlas = _atlas(cells)
    sprites = [_spr(0, 0, 2, 2), _spr(16, 0, 20, 2), _spr(0, 16, 2, 20)]   # tile_size 16 -> factor 1
    overlay = bgart.assemble_overlay(atlas, sprites, 16)
    # repack into a BLANK atlas: every owner cell must come back byte-exact at its (atlasX, atlasY)
    blank = _atlas({})
    n = bgart.repack_overlay(blank, overlay, sprites, 16)
    assert n == 3
    for (ax, ay), col in cells.items():
        assert blank.load()[ax, ay] == col
        assert blank.load()[ax + 15, ay + 15] == col          # the whole 16x16 cell, not just a corner
    # and it is a true crop -> the repacked region equals the original atlas cells exactly
    for (ax, ay) in cells:
        box = (ax, ay, ax + 16, ay + 16)
        assert ImageChops.difference(blank.crop(box), atlas.crop(box)).getbbox() is None


def test_repack_overlay_round_trip_at_tile_size_64():
    # factor 4: a tile at offX=16 occupies pixels [64,128); cells at TileSize-64 spacing
    cells = {(2, 2): (9, 9, 9, 255), (70, 2): (8, 8, 8, 255)}
    atlas = _atlas(cells, tile=64)
    sprites = [_spr(0, 0, 2, 2), _spr(16, 0, 70, 2)]
    overlay = bgart.assemble_overlay(atlas, sprites, 64)
    assert overlay.size == (16 * 4 + 64, 64)
    blank = _atlas({}, tile=64)
    bgart.repack_overlay(blank, overlay, sprites, 64)
    assert blank.load()[2, 2] == (9, 9, 9, 255)
    assert blank.load()[70, 2] == (8, 8, 8, 255)
    assert blank.load()[70 + 63, 63] == (8, 8, 8, 255)


def test_repack_overlay_colocated_writes_only_the_visible_owner():
    # two sprites share (offX, offY): assemble pastes them in order (last wins), so only the LAST
    # owner cell is written back; the earlier (hidden, never-sampled) cell keeps its original bytes.
    FRONT, HIDDEN = (5, 5, 5, 255), (250, 250, 250, 255)
    atlas = _atlas({(2, 2): HIDDEN, (20, 2): FRONT})           # idx0 -> (2,2), idx1 -> (20,2)
    sprites = [_spr(0, 0, 2, 2), _spr(0, 0, 20, 2)]            # both at slot (0,0); the SECOND is the owner
    overlay = bgart.assemble_overlay(atlas, sprites, 16)
    assert overlay.load()[0, 0] == FRONT                       # the visible tile in the layer
    blank = _atlas({})
    n = bgart.repack_overlay(blank, overlay, sprites, 16)
    assert n == 1                                              # only the owner cell written
    assert blank.load()[20, 2] == FRONT                        # owner cell got the painted tile
    assert blank.load()[2, 2] == (123, 123, 123, 255)          # hidden cell untouched (blank backdrop)


def test_repack_overlay_rejects_wrong_sized_layer():
    from PIL import Image
    sprites = [_spr(0, 0, 2, 2), _spr(16, 0, 20, 2)]
    atlas = _atlas({(2, 2): (1, 2, 3, 255), (20, 2): (4, 5, 6, 255)})
    good = bgart.assemble_overlay(atlas, sprites, 16)          # 32x16 expected
    assert good.size == (32, 16)
    with pytest.raises(ValueError):
        bgart.repack_overlay(atlas, Image.new("RGBA", (30, 14)), sprites, 16)
    assert bgart.repack_overlay(atlas, good, sprites, 16) == 0  # right size, UNCHANGED vs atlas -> 0 written
    assert bgart.repack_overlay(_atlas({}), good, sprites, 16) == 2  # into a blank -> both cells change


def test_repack_overlay_bleeds_a_changed_tile_edge_into_its_margin():
    # the native upscaled render can graze 1px into the 2px margin (BGSCENE_DEF UVBorderShift=0.5), so a
    # repainted tile must re-bleed its edge into that margin -- else a 1px seam of the OLD edge shows.
    from PIL import Image
    atlas = _atlas({(2, 2): (10, 10, 10, 255)})               # one cell; backdrop is (123,123,123,255)
    sprites = [_spr(0, 0, 2, 2)]
    overlay = bgart.assemble_overlay(atlas, sprites, 16)
    NEW = (200, 50, 90, 255)
    overlay.paste(Image.new("RGBA", (16, 16), NEW), (0, 0))    # repaint the whole tile
    assert bgart.repack_overlay(atlas, overlay, sprites, 16) == 1
    px = atlas.load()
    assert px[2, 2] == NEW and px[17, 17] == NEW              # cell interior
    assert px[1, 5] == NEW and px[0, 5] == NEW               # left 2px margin = bled NEW edge, not backdrop
    assert px[18, 5] == NEW and px[19, 5] == NEW             # right 2px margin
    assert px[5, 1] == NEW and px[5, 0] == NEW               # top 2px margin
    assert px[5, 18] == NEW and px[5, 19] == NEW             # bottom 2px margin


def test_overlay_size_matches_assemble():
    sprites = [_spr(0, 0, 2, 2), _spr(48, 16, 20, 2)]
    for ts in (16, 32, 64):
        atlas = _atlas({(2, 2): (0, 0, 0, 255), (20, 2): (0, 0, 0, 255)}, tile=ts)
        assert bgart.overlay_size(sprites, ts) == bgart.assemble_overlay(atlas, sprites, ts).size
    assert bgart.overlay_size([_spr(9, 9, 2, 2)], 32) == (32, 32)   # the <=1-sprite single-tile case
    assert bgart.overlay_size([], 64) == (64, 64)


# --------------------------------------------------------------------- synthetic project round-trip
def _make_bgs(overlays):
    """A minimal valid <fbg>.bgs for `overlays` (a list of overlays, each a list of (offX, offY)
    opaque tile positions). Enough for bgs.parse_overlays + resolve_sprites; no cameras/lights."""
    H = struct.Struct("<6H4I12h")
    OV = struct.Struct("<I HH hhhh hhhh hh hh hh I I I I I")
    n = len(overlays)
    header_size, ov_size = 52, 56
    cur = header_size + ov_size * n
    blocks, tail = b"", b""
    for sprites in overlays:
        count = len(sprites)
        prm_off = cur
        prm = b"".join(struct.pack("<II", 0, 0) for _ in sprites)   # opaque: alpha=0, trans=0
        cur += len(prm)
        loc_off = cur
        loc = b"".join(struct.pack("<I", ((ox & 0x3FF) << 22) | ((oy & 0x3FF) << 12)) for ox, oy in sprites)
        cur += len(loc)
        tail += prm + loc
        buf2 = (count & 0xFFFF) << 16                           # camNdx=0 | spriteCount=count
        # field order: buf,w,h,orgX,orgY, +10 zeros, buf2(f17), locOffset(f18), prmOffset(f19), 0,0
        blocks += OV.pack(0, 16, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                          buf2, loc_off, prm_off, 0, 0)
    header = H.pack(0, 0, 0, n, 0, 0, 0, header_size, 0, 0, *([0] * 12))
    return header + blocks + tail


def test_make_bgs_parses_back_to_its_sprites():
    # sanity: the synthetic .bgs builder produces a blob bgs.py reads back to the same tile layout.
    # offX/offY are base-16 PIXEL offsets (a tile one slot over is offX=16, not 1).
    data = _make_bgs([[(0, 0), (16, 0)], [(0, 0)]])
    _, ov = bgs.parse_overlays(data)
    assert [o.spriteCount for o in ov] == [2, 1]
    bgs.resolve_sprites(data, ov, 64, 16)
    assert [(s.offX, s.offY) for s in ov[0].sprites] == [(0, 0), (16, 0)]
    assert len(ov[1].sprites) == 1


def _synth_native_project(tmp_path, tile=16, atlas_size=(64, 64)):
    """A self-contained native project dir: scene.bgs.bytes + atlas.png (distinct per-cell colors) +
    a *.field.toml. Returns (project_dir, expected_cells {(ax,ay): color})."""
    # one overlay, 4 tiles in an L (base-16 pixel offsets) -> 4 distinct atlas cells (cpr=3 at tile 16)
    positions = [(0, 0), (16, 0), (32, 0), (0, 16)]
    data = _make_bgs([positions])
    _, ov = bgs.parse_overlays(data)
    bgs.resolve_sprites(data, ov, atlas_size[0], tile)
    cells = {}
    for k, s in enumerate(ov[0].sprites):
        cells[(s.atlasX, s.atlasY)] = (40 + k * 30, 10, 200 - k * 20, 255)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "scene.bgs.bytes").write_bytes(data)
    _atlas(cells, size=atlas_size, tile=tile).save(proj / "atlas.png")
    (proj / "NAT.field.toml").write_text(
        '[field]\nid = 4003\nname = "NAT"\narea = 11\n'
        'bgs = "scene.bgs.bytes"\natlas = "atlas.png"\natlas_tile_size = %d\n' % tile,
        encoding="utf-8")
    return proj, cells


def test_project_round_trip_unmodified_atlas_is_byte_identical(tmp_path):
    from PIL import Image, ImageChops
    from ff9mapkit import extract
    proj, _cells = _synth_native_project(tmp_path)
    before = Image.open(proj / "atlas.png").convert("RGBA").copy()

    rep = extract.export_native_repaint(proj)
    assert rep["overlays"] == 1 and rep["tile_size"] == 16
    assert (proj / "repaint" / "Overlay0.png").is_file()
    assert (proj / "repaint" / "repaint.manifest.json").is_file()

    res = extract.repack_native_atlas(proj)
    assert res["overlays_repacked"] == 1 and res["cells_written"] == 0   # unmodified -> nothing changed
    after = Image.open(proj / "atlas.png").convert("RGBA")
    assert ImageChops.difference(before, after).getbbox() is None, "unmodified round-trip changed the atlas"
    assert not (proj / "backups").exists()                    # a no-op pack makes no backup


def test_project_repaint_lands_in_the_right_atlas_cell(tmp_path):
    from PIL import Image
    from ff9mapkit import extract
    proj, cells = _synth_native_project(tmp_path)
    extract.export_native_repaint(proj)

    # repaint: paint the FIRST tile (overlay slot (0,0) -> atlas cell of sprite idx 0) bright magenta
    NEW = (255, 0, 255, 255)
    ov_png = Image.open(proj / "repaint" / "Overlay0.png").convert("RGBA")
    ov_png.paste(Image.new("RGBA", (16, 16), NEW), (0, 0))     # tile at offX=0, offY=0
    ov_png.save(proj / "repaint" / "Overlay0.png")

    res = extract.repack_native_atlas(proj)
    assert res["cells_written"] == 1                            # exactly one tile changed
    assert (proj / "backups").is_dir() and list((proj / "backups").glob("atlas.png.*"))   # backed up on change
    atlas = Image.open(proj / "atlas.png").convert("RGBA")
    sprite0_cell = (2, 2)                                       # idx 0 -> atlasX/atlasY = (2, 2)
    assert sprite0_cell in cells                                # (sanity: that's a real packed cell)
    assert atlas.load()[2, 2] == NEW                            # the repaint landed in sprite 0's cell
    assert atlas.load()[2 + 15, 2 + 15] == NEW
    # a DIFFERENT tile's cell (sprite idx 1 -> atlasX 22) is unchanged
    assert atlas.load()[22, 2] == cells[(22, 2)]


def test_repack_is_idempotent(tmp_path):
    from PIL import Image, ImageChops
    from ff9mapkit import extract
    proj, _ = _synth_native_project(tmp_path)
    extract.export_native_repaint(proj)
    ov = Image.open(proj / "repaint" / "Overlay0.png").convert("RGBA")
    ov.paste(Image.new("RGBA", (16, 16), (255, 0, 255, 255)), (0, 0))   # actually change a tile
    ov.save(proj / "repaint" / "Overlay0.png")
    extract.repack_native_atlas(proj)
    once = Image.open(proj / "atlas.png").convert("RGBA").copy()
    res2 = extract.repack_native_atlas(proj)                   # re-run: the layers now MATCH the atlas -> no change
    twice = Image.open(proj / "atlas.png").convert("RGBA")
    assert res2["cells_written"] == 0                          # idempotent: nothing to write the 2nd time
    assert ImageChops.difference(once, twice).getbbox() is None


def test_repack_rescales_an_upscaled_layer(tmp_path):
    from PIL import Image
    from ff9mapkit import extract
    proj, _ = _synth_native_project(tmp_path)
    extract.export_native_repaint(proj)
    ov = Image.open(proj / "repaint" / "Overlay0.png").convert("RGBA")
    ov.resize((ov.width * 2, ov.height * 2), Image.NEAREST).save(proj / "repaint" / "Overlay0.png")
    res = extract.repack_native_atlas(proj)
    assert res["rescaled"] == 1 and res["notes"]


def test_export_requires_a_native_project(tmp_path):
    from ff9mapkit import extract
    (tmp_path / "bare").mkdir()
    with pytest.raises(FileNotFoundError):
        extract.export_native_repaint(tmp_path / "bare")


def test_repaint_prefers_the_native_toml_in_a_mixed_folder(tmp_path):
    # a native AND an editable fork of the same field can share a folder (the real ALXT_NATIVE + ALXT_EDIT
    # case): the repaint must target the NATIVE one, not the editable .bgx fork that merely shares atlas.png.
    from ff9mapkit import extract
    proj, _ = _synth_native_project(tmp_path)                  # writes NAT.field.toml (native) + bgs + atlas
    (proj / "AAA_EDIT.field.toml").write_text(                 # alphabetically BEFORE "NAT" -- the old bug picked this
        '[field]\nid = 4003\nname = "AAA_EDIT"\narea = 11\n[[layers]]\nimage = "layer_0.png"\nz = 0\n',
        encoding="utf-8")
    rep = extract.export_native_repaint(proj)                  # must pick the native fork
    assert rep["overlays"] == 1 and rep["tile_size"] == 16


def test_repaint_rejects_an_editable_only_project(tmp_path):
    # an editable/.bgx fork (field.toml with [[layers]], no [field] bgs/atlas) -- even with a stray atlas.png
    # in the folder -- must be REFUSED with a pointer to native, not silently repacked.
    from ff9mapkit import extract
    from PIL import Image
    d = tmp_path / "edit"
    d.mkdir()
    (d / "E.field.toml").write_text(
        '[field]\nid = 4003\nname = "E"\narea = 11\n[[layers]]\nimage = "l.png"\nz = 0\n', encoding="utf-8")
    Image.new("RGBA", (64, 64)).save(d / "atlas.png")         # a stray atlas (as in the user's mixed folder)
    (d / "scene.bgs.bytes").write_bytes(_make_bgs([[(0, 0)]]))
    with pytest.raises(FileNotFoundError, match="editable"):
        extract.export_native_repaint(d)


def test_repaint_accepts_an_explicit_field_toml(tmp_path):
    from ff9mapkit import extract
    proj, _ = _synth_native_project(tmp_path)
    rep = extract.export_native_repaint(proj / "NAT.field.toml")   # point at the file directly
    assert rep["overlays"] == 1
    assert (proj / "repaint" / "Overlay0.png").is_file()


def test_derive_native_tile_size_picks_the_largest_that_fits(tmp_path):
    from ff9mapkit import extract
    data = _make_bgs([[(0, 0), (16, 0), (32, 0), (0, 16)]])     # 4 tiles, base-16 pixel offsets
    # a 64x64 atlas holds these at tile 16 only (tile 32 = 1 cell/row would overflow the 2nd row) -> 16
    assert extract._derive_native_tile_size(data, 64, 64) == 16
    # a 64x144 atlas is tightly sized for tile 32 (1 cell/row, stride 36, 4 rows) -> 32 (64 can't pack: cpr 0)
    assert extract._derive_native_tile_size(data, 64, 144) == 32


# --------------------------------------------------------------------- install-gated full loop
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_native_fork_atlas_survives_round_trip(tmp_path):
    """Fork a real field native, then export -> repack: the atlas comes back byte-identical (the
    repaint loop is lossless on real data). Self-consistent decode -> exact even for a DXT atlas."""
    from PIL import Image, ImageChops
    from ff9mapkit import extract
    rows = extract.list_fields(game=None)
    if not rows:
        pytest.skip("no fields in index")
    folder = rows[0][0]
    try:
        extract.write_native_project(folder, tmp_path / "nat", name="NAT", field_id=30099, game=None)
    except RuntimeError as e:
        pytest.skip(f"no native atlas for {folder}: {e}")
    proj = tmp_path / "nat"
    before = Image.open(proj / "atlas.png").convert("RGBA").copy()
    rep = extract.export_native_repaint(proj)
    assert rep["overlays"] > 0
    extract.repack_native_atlas(proj)                          # unmodified layers -> identity
    after = Image.open(proj / "atlas.png").convert("RGBA")
    assert ImageChops.difference(before, after).getbbox() is None
