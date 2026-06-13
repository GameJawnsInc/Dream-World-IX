#!/usr/bin/env python3
"""Offline rebuild of a field's per-overlay background PNGs from its atlas + .bgs.

This reproduces Memoria's ``[Export] Field=1`` dump (``FieldSceneExporter.ExportOverlay``,
FieldSceneExporter.cs:177) WITHOUT the in-game step. The engine export is a single blocking
startup pass over EVERY field (``SceneDirector.MemoriaExport`` -> ``FieldSceneExporter.ExportSafe``
walks ``mapList.txt``), which is the multi-minute "hang"; here each overlay is composited straight
from the atlas the kit already reads out of p0data.

Byte-exactness (proven on FBG_N00_TSHP_MAP001_TH_CGR_0, overlay 0): cropping the cell this module
computes out of the engine's OWN dumped ``atlas.png`` reproduces ``Overlay0.png`` with diff == 0 --
the cell math, the (absent) flip, and the placement are exact. The only delta on a live install
comes from re-DECODING the p0data atlas offline: a DXT-compressed atlas (Moguri ships the field
atlas as DXT5 / TextureFormat 12) decodes a hair differently through UnityPy than through Unity's
runtime, a uniform sub-2/255 per-channel noise that is imperceptible and structurally irrelevant
(every tile's position/size/index is identical). An uncompressed (vanilla) atlas decodes exactly.

The engine packs the upscaled atlas as a grid of ``(TileSize+4)`` cells (a 2px bleed margin each
side) addressed by a single global sprite index across overlays in order; ``bgs.resolve_sprites``
already computes that cell (``2 + idx % cpr * (TileSize+4)``, matching ``ExtractSpriteData``,
BGSCENE_DEF.cs:740). This module is the inverse blit: crop each cell, paste it into the overlay's
tight canvas at ``(offX*factor, offY*factor)`` (``factor = TileSize/16``), exactly as the engine
does after its double Y-flip nets out.
"""
from __future__ import annotations

from .bgs import TILE


def assemble_overlay(atlas_img, sprites, tile_size: int):
    """One overlay's ``Overlay{i}.png`` as a PIL RGBA image, matching ``FieldSceneExporter.ExportOverlay``.

    ``sprites`` are the overlay's resolved tile-sprites (``bgs.resolve_sprites`` against
    ``atlas_img.width`` at ``tile_size``), each carrying ``atlasX``/``atlasY`` (the atlas source cell)
    and ``offX``/``offY`` (the tile's 16px-unit position within the overlay). ``tile_size`` is the
    ACTIVE field-map TileSize (vanilla 32 / Moguri 64) -- it MUST match the atlas the cells were
    resolved against, else the grid steps land on the wrong cells (garbled art).
    """
    from PIL import Image  # noqa: PLC0415 - only the art path needs PIL

    factor = tile_size // TILE
    # The engine sizes a >1-sprite overlay to its tight tile bbox; a 0/1-sprite overlay is a single
    # SPRITE_W x SPRITE_H tile (FieldSceneExporter.cs:184-191). Mirror that exactly so dims match.
    if len(sprites) > 1:
        w = max(s.offX for s in sprites) * factor + tile_size
        h = max(s.offY for s in sprites) * factor + tile_size
    else:
        w = h = tile_size
    # the engine inits the canvas to Color(1,1,1,0) == white-under-zero-alpha (FieldSceneExporter.cs:215),
    # NOT black; regions no tile covers keep it. Match it for byte-parity (the RGB is invisible at a=0, but
    # the engine export carries it, so a black init would diff 255 per channel across every uncovered pixel).
    canvas = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    for s in sprites:
        cell = atlas_img.crop((s.atlasX, s.atlasY, s.atlasX + tile_size, s.atlasY + tile_size))
        # paste (overwrite, incl. alpha) == the engine's SetPixels; co-located sprites = last wins.
        canvas.paste(cell, (s.offX * factor, s.offY * factor))
    return canvas


def assemble_overlays(atlas_img, overlays, tile_size: int) -> dict:
    """``{overlay_index: PIL RGBA image}`` for every overlay (the offline ``Overlay{i}.png`` set).

    ``overlays`` must already be sprite-resolved (``bgs.resolve_sprites(data, overlays, atlas_img.width,
    tile_size)``) so each carries its atlas cells. Index ``i`` is the overlay list index -- the same
    ``i`` the engine names ``Overlay{i}.png`` by and that ``extract.compose_background``/``extract_layers``
    key off.
    """
    return {i: assemble_overlay(atlas_img, ov.sprites, tile_size) for i, ov in enumerate(overlays)}
