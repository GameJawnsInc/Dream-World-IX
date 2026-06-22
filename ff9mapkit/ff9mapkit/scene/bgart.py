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


def overlay_size(sprites, tile_size: int):
    """The ``(w, h)`` :func:`assemble_overlay` produces for these sprites at ``tile_size``.

    The engine sizes a >1-sprite overlay to its tight tile bbox; a 0/1-sprite overlay is a single
    SPRITE_W x SPRITE_H tile (FieldSceneExporter.cs:184-191). Factored out so the repaint repack can
    validate a hand-edited ``Overlay{i}.png`` against the exact dims its tiles were exported at."""
    factor = tile_size // TILE
    if len(sprites) > 1:
        return (max(s.offX for s in sprites) * factor + tile_size,
                max(s.offY for s in sprites) * factor + tile_size)
    return (tile_size, tile_size)


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
    w, h = overlay_size(sprites, tile_size)
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


def _bleed_cell(atlas_img, ax, ay, ts: int, pad: int = 2) -> None:
    """Replicate a freshly-written cell's edge pixels ``pad`` px outward into the surrounding atlas
    margin (clamped to the atlas). The native upscaled render path point-samples with a -0.5 texel UV
    shift (BGSCENE_DEF.cs:1322), so when the background is drawn LARGER than the atlas tile (a hi-res
    display), the first/last screen pixel of a tile reads ONE texel into the 2px margin. The shipped
    atlas reserves that margin with a bled copy of the edge for exactly this reason; a repainted tile
    must re-bleed so its edge -- not the stale old tile -- is what bleeds in (else a 1px seam shows)."""
    W, H = atlas_img.size
    x0, x1 = max(0, ax - pad), min(W, ax + ts + pad)              # widened, clamped span for top/bottom
    for d in range(1, pad + 1):                                   # left/right columns within the cell rows
        if ax - d >= 0:
            atlas_img.paste(atlas_img.crop((ax, ay, ax + 1, ay + ts)), (ax - d, ay))
        if ax + ts - 1 + d < W:
            atlas_img.paste(atlas_img.crop((ax + ts - 1, ay, ax + ts, ay + ts)), (ax + ts - 1 + d, ay))
    for d in range(1, pad + 1):                                   # top/bottom rows over the widened span -> corners
        if ay - d >= 0:
            atlas_img.paste(atlas_img.crop((x0, ay, x1, ay + 1)), (x0, ay - d))
        if ay + ts - 1 + d < H:
            atlas_img.paste(atlas_img.crop((x0, ay + ts - 1, x1, ay + ts)), (x0, ay + ts - 1 + d))


def repack_overlay(atlas_img, overlay_png, sprites, tile_size: int, *, bleed: int = 2) -> int:
    """Blit a (re)painted ``Overlay{i}.png`` back INTO the atlas -- the inverse of :func:`assemble_overlay`.
    ``atlas_img`` is BOTH the base and the target (mutated in place); returns the count of CHANGED cells.

    For each sprite this crops the same ``tile_size`` square the assembler pasted FROM the atlas (at
    ``(offX*factor, offY*factor)`` in the overlay PNG) and -- only if it differs from the atlas cell
    already there -- writes it back to that sprite's atlas cell ``(atlasX, atlasY)`` and re-bleeds the
    cell edge into its margin (:func:`_bleed_cell`). Skipping unchanged cells keeps an UNMODIFIED layer
    a byte-exact no-op (crop/paste are pure copies) AND makes a re-pack idempotent, with no separate
    pristine copy to corrupt -- the atlas itself is the base.

    CO-LOCATED sprites (two tiles sharing one ``(offX, offY)``) are handled like the assembler's
    in-order paste: only the LAST (visible) owner cell is considered; earlier hidden cells -- which the
    engine never samples -- keep their original atlas bytes.

    ``overlay_png`` MUST be sized exactly :func:`overlay_size` for ``sprites`` at ``tile_size`` (the
    caller reconciles a hand-edited PNG first); a mismatch raises ``ValueError`` rather than garble.
    """
    if not sprites:
        return 0
    exp = overlay_size(sprites, tile_size)
    if tuple(overlay_png.size) != exp:
        raise ValueError(f"repaint overlay is {tuple(overlay_png.size)}, expected {exp} "
                         f"(tile_size {tile_size}); re-export or rescale it to match")
    factor = tile_size // TILE
    owner = {}                                    # (offX, offY) -> last sprite index == the visible tile
    for j, s in enumerate(sprites):
        owner[(s.offX, s.offY)] = j
    changed = 0
    for j, s in enumerate(sprites):
        if owner[(s.offX, s.offY)] != j:
            continue
        x0, y0 = s.offX * factor, s.offY * factor
        cell = overlay_png.crop((x0, y0, x0 + tile_size, y0 + tile_size))
        box = (s.atlasX, s.atlasY, s.atlasX + tile_size, s.atlasY + tile_size)
        if cell.tobytes() == atlas_img.crop(box).tobytes():
            continue                              # unchanged tile -> leave the cell + its margin byte-exact
        atlas_img.paste(cell, (s.atlasX, s.atlasY))   # overwrite incl. alpha == assemble's source cell
        if bleed:
            _bleed_cell(atlas_img, s.atlasX, s.atlasY, tile_size, bleed)
        changed += 1
    return changed
