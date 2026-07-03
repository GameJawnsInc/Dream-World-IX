"""Author walkable overworld TERRAIN -- raise/lower/flatten/ridge the ground by RESHAPING the stock mesh (no DLL).

Hard-won in-game lessons this encodes:
  * RESHAPE, don't OVERLAY. Displacing the EXISTING terrain verts keeps a SINGLE walkmesh surface, so the player
    walks on it. Overlaying a NEW mesh on top leaves the stock ground underneath, and the movement ground-raycast
    (from ``player.y + 2.34`` down, plus a per-frame triangle cache, ``ff9.cs:7141`` / ``WMPhysics.cs``) keeps hitting
    that stock surface -> the overlay is non-walkable decoration, never ground you climb.
  * WORLD-SPACE, MULTI-BLOCK. A reshape wider than one 64u block is applied to EVERY block it touches with the SAME
    world center/radius/amount, so shared block-edge verts move identically -> seamless (no cut/crack at the grid).
  * Blocks are LOCAL-frame; ``deform_*`` take ``world_origin`` and read a block's verts (local) + origin to test the
    world distance, so the frame is handled here.

Each touched land block gets a loose Terrain ``.ff9mesh`` override (the ``s34`` engine patch loads it); sea blocks are
skipped. RELAUNCH to apply. Reshape keeps tangents/UVs, so the ground keeps its stock texture + walkability topograph.
"""
from __future__ import annotations

import math

BLOCK = 64
GRID_X, GRID_Y = 24, 20                                  # the fixed overworld block grid


def _block_index_range(minx: float, maxx: float, minz: float, maxz: float):
    """Block ``(bx, by)`` index ranges whose 64u footprints overlap the world-XZ box (Z negated: by = floor(-z/64))."""
    bx0, bx1 = int(math.floor(minx / BLOCK)), int(math.floor(maxx / BLOCK))
    by0, by1 = int(math.floor(-maxz / BLOCK)), int(math.floor(-minz / BLOCK))
    return bx0, bx1, by0, by1


def reshape(mod_folder: str, *, radius: float, at=None, seg=None, amount: float | None = None,
            flatten: bool = False, height: float | None = None, disc: int = 1, falloff: str = "smooth",
            game=None, dry_run: bool = False) -> dict:
    """Reshape overworld terrain within ``radius`` world units, across every block it touches. Exactly one SHAPE:
    ``at=(x, z)`` (a radial hill/crater/plateau) or ``seg=((x0,z0),(x1,z1))`` (a ridge/valley). Exactly one OP:
    ``amount`` (signed: ``+`` raise, ``-`` lower) or ``flatten=True`` (level toward ``height``, default the local mean).
    Returns a summary; deploys a Terrain override per touched land block (unless ``dry_run``). RELAUNCH to apply."""
    from . import extract as X, mesh as M
    if (at is None) == (seg is None):
        raise ValueError("give exactly one shape: at=(x,z) OR seg=((x0,z0),(x1,z1))")
    if not flatten and amount is None:
        raise ValueError("give an op: amount=<signed> (raise/lower) OR flatten=True")
    if seg is not None and flatten:
        raise ValueError("flatten is radial (use at=), not a ridge op")
    if seg is not None:
        (ax, az), (bx_, bz) = seg
        minx, maxx, minz, maxz = min(ax, bx_), max(ax, bx_), min(az, bz), max(az, bz)
    else:
        minx = maxx = at[0]; minz = maxz = at[1]
    bx0, bx1, by0, by1 = _block_index_range(minx - radius, maxx + radius, minz - radius, maxz + radius)
    op = "flatten" if flatten else ("raise" if amount >= 0 else "lower") if seg is None else \
        ("ridge+" if amount >= 0 else "ridge-")
    summary = {"op": op, "radius": radius, "dry_run": dry_run, "blocks": [], "skipped_sea": []}
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
                continue
            try:
                ter = X.read_block(bx, by, disc=disc, part="terrain", game=game)
            except (ValueError, FileNotFoundError):
                summary["skipped_sea"].append([bx, by]); continue         # sea / no terrain mesh
            wo = X.block_world_origin(bx, by)
            if flatten:
                moved = M.flatten_region(ter, radius=radius, center=at, height=height, falloff=falloff, world_origin=wo)
            elif seg is not None:
                moved = M.deform_ridge(ter, p0=seg[0], p1=seg[1], amount=amount, radius=radius, falloff=falloff,
                                       world_origin=wo)
            else:
                moved = M.deform_radial(ter, amount=amount, radius=radius, center=at, falloff=falloff, world_origin=wo)
            if not moved:
                continue
            if not dry_run:
                M.deploy_override(ter, mod_folder=mod_folder, game=game, part="Terrain")
            summary["blocks"].append({"block": [bx, by], "moved": moved})
    return summary


def reclaim(mod_folder: str, *, cells, disc: int = 1, topograph: int = 0, seg: int = 8, height: float = 0.0,
            game=None, dry_run: bool = False) -> dict:
    """RECLAIM ocean cells as walkable LAND -- the Path-D new-continent primitive. Each ``(x, y)`` in ``cells`` (grid
    coords, 0..23 x 0..19) gets a fresh flat, walkable, textured terrain override so a designated SEA cell renders +
    collides as land. Unlike :func:`reshape` (which reads + displaces a stock terrain mesh, and SKIPS sea cells that
    have none), this SYNTHESIZES the mesh from scratch (:func:`ff9mapkit.world.mesh.flat_block_mesh`) at the cell's
    own local block origin, stamps real terrain-atlas UVs (:func:`ff9mapkit.world.palette.apply_palette_uvs`), and
    deploys a ``Block[x][y] Terrain.ff9mesh`` override.

    Requires the CUSTOM engine: the shipped ``s34`` divert routes a sea cell carrying such an override onto a land
    donor prefab (``WorldMeshOverride.HasLandOverride`` gate) instead of the ocean ``SeaBlockPrefab`` -- a stock sea
    cell short-circuits before the override can fire, so on stock Memoria this is a no-op. A LONE reclaimed cell is an
    ISLAND (the surrounding stock sea stays non-walkable on foot); build a contiguous BRIDGE of cells from the coast
    for an on-foot-reachable landmass, or reach a lone cell via F6->World->Teleport / a world entrance. RELAUNCH (or
    exit+re-enter the overworld) to load. ``topograph`` default 0 = walkable plains (topo 49/58/59 are BLOCKED)."""
    from . import mesh as M
    from . import palette as PAL
    cells = [tuple(c) for c in cells]
    for (bx, by) in cells:
        if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
            raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    summary = {"op": "reclaim", "disc": disc, "topograph": topograph, "dry_run": dry_run, "cells": []}
    for (bx, by) in cells:
        bm = M.flat_block_mesh(disc=disc, x=bx, y=by, seg=seg, topograph=topograph, height=height)
        bm = PAL.apply_palette_uvs(bm, topograph=topograph, disc=disc, part="terrain", game=game)
        if not dry_run:
            M.deploy_override(bm, mod_folder=mod_folder, game=game, part="Terrain")
        summary["cells"].append({"cell": [bx, by], "tris": len(bm.tris), "verts": bm.vcount})
    return summary
