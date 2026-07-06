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


_DIRS = [(-1, 0), (1, 0), (0, 1), (0, -1)]


def coast(mod_folder: str, *, cells, donor, disc: int = 1, lod: str = "0_1", game=None,
          dry_run: bool = False) -> dict:
    """FAITHFUL coast: reclaim each ``(x, y)`` in ``cells`` as a VERBATIM copy of the real coastal ``donor``=(dx, dy)
    block -- copy the donor's Terrain mesh (real land shape + shore rim + real UVs + walkable topographs) to the cell's
    Terrain override, AND write a ``Donor.txt`` sidecar naming the donor so the engine's per-cell divert loads that
    real coastal block prefab (its animated Beach/Sea/foam sub-meshes render on the cell). Unlike :func:`reclaim` (which
    SYNTHESIZES a stylized grass/sand island), this carries a genuine FF9 coastline -- the north-star "recreate from
    real bytes". A continent is assembled from real coast pieces (:func:`ff9mapkit.world.extract.list_coastal_donors`
    lists them). Requires the CUSTOM engine (per-cell coastal-donor s34). RELAUNCH to apply."""
    import dataclasses
    from . import extract as X, mesh as M
    dx, dy = donor
    cells = [tuple(c) for c in cells]
    for (bx, by) in cells:
        if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
            raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    if not (0 <= dx < GRID_X and 0 <= dy < GRID_Y):
        raise ValueError(f"donor ({dx},{dy}) out of the {GRID_X}x{GRID_Y} overworld grid")
    donor_bm = X.read_block(dx, dy, disc=disc, lod=lod, part="terrain", game=game)   # real coast terrain (raises if not land)
    summary = {"op": "coast", "donor": [dx, dy], "disc": disc, "dry_run": dry_run, "cells": []}
    for (bx, by) in cells:
        # verts are block-LOCAL (localPosition 0), so relocation is just re-tagging x/y/name; deploy_override +
        # RegisterBlockComponent place it by InitialX/InitialY. The donor's beach/sea come from the prefab (via the sidecar).
        bm = dataclasses.replace(donor_bm, x=bx, y=by, name=f"Block[{bx}][{by}] Terrain")
        if not dry_run:
            M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part="Terrain")
            M.deploy_donor_sidecar(dx, dy, mod_folder=mod_folder, disc=disc, x=bx, y=by, lod=lod, game=game)
        summary["cells"].append({"cell": [bx, by], "tris": len(bm.tris), "verts": bm.vcount})
    return summary


# The (7,17) grey-rock CLIFF-FACE texture vocabulary (byte-derived; see project-ff9-overworld-coast-mosaic): a
# horizontal atlas strip of rock tiles, U = along-shore arc (wraps the strip), V = height up the slope.
_CLIFF_ROCK_U = (0.699, 0.947)      # the rock strip u-span (~4 tiles) -- tiles + wraps along the shore
_CLIFF_ROCK_V = (0.923, 0.893)      # (V at the face BASE Y=0, V at the face TOP) -- V climbs the slope
_CLIFF_FACE_TOPO = 58               # the shore-rim / cliff-face topograph


def _apply_cliff_rock_uvs(bm, *, tile_u: float = 26.0):
    """Override the topo-58 cliff-FACE tris' UVs with the real grey-rock band: U = along-shore arc (wrapping the rock
    strip ~every ``tile_u`` world units), V = height up the face (base -> 0.923, top -> 0.893). Leaves the plateau
    (topo-0 grass) UVs as the palette set them. Reproduces the measured (7,17) cliff-texture rule instead of a guess."""
    import math
    from .extract import decode_id, CH_UV  # noqa: F401 (CH_UV documents the channel we mutate)
    verts, tans, uv = bm.verts, bm.tangents, bm.chan_arrays[CH_UV]
    cx = sum(v[0] for v in verts) / bm.vcount
    cz = sum(v[2] for v in verts) / bm.vcount
    face_max = max((verts[k][1] for tri in bm.tris for k in tri
                    if decode_id(int(round(tans[tri[0]][0])))["topograph"] == _CLIFF_FACE_TOPO), default=0.0)
    if face_max <= 1e-3:
        return bm
    xs = [v[0] for v in verts]; zs = [v[2] for v in verts]
    perim = 2.0 * ((max(xs) - min(xs)) + (max(zs) - min(zs)))
    wraps = max(1.0, round(perim / max(tile_u, 4.0)))            # how many times the rock strip wraps the shore
    ub, ut = _CLIFF_ROCK_U
    vb, vt = _CLIFF_ROCK_V
    two_pi = 2.0 * math.pi
    for tri in bm.tris:
        if decode_id(int(round(tans[tri[0]][0])))["topograph"] != _CLIFF_FACE_TOPO:
            continue
        a0 = math.atan2(verts[tri[0]][2] - cz, verts[tri[0]][0] - cx)
        ang = [a0 + ((math.atan2(verts[k][2] - cz, verts[k][0] - cx) - a0 + math.pi) % two_pi - math.pi) for k in tri]
        base = math.floor(min(ang) / two_pi * wraps)            # keep the tri's U window contiguous (no wrap-seam in-tri)
        for k, a in zip(tri, ang):
            frac = min(max(a / two_pi * wraps - base, 0.0), 1.0)
            hy = min(max(verts[k][1] / face_max, 0.0), 1.0)
            uv[k] = [ub + frac * (ut - ub), vb + hy * (vt - vb)]
    return bm


def reclaim(mod_folder: str, *, cells, disc: int = 1, profile: str = "island", topograph: int = 0,
            height: float | None = None, seg: int = 10, beach: float | None = None, grass_topo: int = 0,
            shore_topo: int | None = None, shore_frac: float | None = None, game=None, dry_run: bool = False) -> dict:
    """RECLAIM ocean cells as walkable LAND -- the Path-D new-continent primitive. Each ``(x, y)`` in ``cells`` (grid
    coords, 0..23 x 0..19) gets a fresh, walkable, textured terrain override so a designated SEA cell renders +
    collides as land. Unlike :func:`reshape` (which displaces a stock terrain mesh and SKIPS sea cells that have none),
    this SYNTHESIZES the mesh, stamps real terrain-atlas UVs (:func:`ff9mapkit.world.palette.apply_palette_uvs`), and
    deploys a ``Block[x][y] Terrain.ff9mesh`` override.

    ``profile`` shapes the land:
      * ``"island"`` (default) -- a NATURAL island: a walkable GREEN-GRASS plateau at ``Y=height`` that ramps down to a
        TAN-SAND shore ring at the waterline on every OPEN-WATER edge, so it blends into the sea like a real coast
        instead of a flat slab (:func:`ff9mapkit.world.mesh.island_block_mesh`; grass/sand topographs chosen by sampling
        real atlas pixel colors, not frequency). Water-facing edges are computed
        per cell from the reclaimed set + the real-land set (a cell edge whose neighbour is another reclaimed cell or
        real land gets NO beach -- interior/seam). Per-tri grass/shore topographs are palette-textured individually.
      * ``"cliff"`` -- a CLIFF coast: the plateau drops via a STEEP shore-rim ramp (topo 58) straight to the waterline
        (``Y=0``), textured with the REAL grey-rock band (``_apply_cliff_rock_uvs``: U = along-shore arc wrapping the
        rock strip, V = height up the face) -- the byte-derived (7,17) cliff seam, NOT a topograph palette guess. Cliff
        defaults: ``height`` 4, ``beach`` 6 (steep), ``shore_topo`` 58, ``shore_frac`` 0.6. No shallow ladder / foam.
      * ``"flat"`` -- a bare flat slab at ``Y=height`` of one ``topograph`` (0 = plains). Cheapest; z-fights the sea
        surface at ``height=0`` (lift it a few units for an open-ocean cell), fine flush (``height=0``) against a coast.

    Requires the CUSTOM engine: the shipped ``s34`` divert routes a sea cell carrying such an override onto a land
    donor prefab (``WorldMeshOverride.HasLandOverride`` gate) instead of ``SeaBlockPrefab`` -- a stock sea cell
    short-circuits before the override can fire, so on stock Memoria this is a no-op. A LONE reclaimed cell is an
    ISLAND (surrounding stock sea non-walkable on foot); build a contiguous BRIDGE of cells from the coast for an
    on-foot-reachable landmass, or reach a lone cell via F6->World->Teleport. RELAUNCH (or exit+re-enter) to load."""
    from . import mesh as M
    from . import palette as PAL
    from . import extract as X
    cells = [tuple(c) for c in cells]
    for (bx, by) in cells:
        if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
            raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    # per-profile shape defaults. island = gentle SAND beach; cliff = STEEP shore-rim drop to the waterline + the
    # real grey-rock texture on the face (the (7,17) teardown: topo-58 face ~40deg, plateau Y~4, base at Y=0).
    if height is None:
        height = {"island": 6.0, "cliff": 4.0}.get(profile, 0.0)
    if beach is None:
        beach = 6.0 if profile == "cliff" else 22.0        # ramp WIDTH: small = steep (cliff), large = gentle (beach)
    if shore_topo is None:
        shore_topo = 58 if profile == "cliff" else 20      # 58 = shore-rim/cliff (on-foot BLOCKED); 20 = walkable sand
    if shore_frac is None:
        shore_frac = 0.6 if profile == "cliff" else 0.3
    reclaimed = set(cells)
    land = set()
    if profile in ("island", "cliff"):
        try:                                              # real-land set: a neighbour that is real coast is NOT water
            land = set(X.list_blocks(disc=disc, game=game))
        except Exception:                                 # noqa: BLE001 -- offline/no install -> treat non-reclaimed as water
            land = set()
    summary = {"op": "reclaim", "profile": profile, "disc": disc, "topograph": topograph,
               "dry_run": dry_run, "cells": []}
    for (bx, by) in cells:
        if profile in ("island", "cliff"):
            water = [(dx, dy) for (dx, dy) in _DIRS if (bx + dx, by + dy) not in reclaimed
                     and (bx + dx, by + dy) not in land]
            bm = M.island_block_mesh(disc=disc, x=bx, y=by, water_dirs=water, seg=seg, height=height,
                                     beach=beach, grass_topo=grass_topo, shore_topo=shore_topo, shore_frac=shore_frac)
            bm = PAL.apply_palette_uvs(bm, topograph=None, disc=disc, part="terrain", game=game)  # per-tri grass/shore
            if profile == "cliff":
                bm = _apply_cliff_rock_uvs(bm)             # the real grey-rock band on the face (NOT the palette guess)
            info = {"cell": [bx, by], "tris": len(bm.tris), "verts": bm.vcount, "water_edges": len(water)}
        else:
            bm = M.flat_block_mesh(disc=disc, x=bx, y=by, seg=seg, topograph=topograph, height=height)
            bm = PAL.apply_palette_uvs(bm, topograph=topograph, disc=disc, part="terrain", game=game)
            info = {"cell": [bx, by], "tris": len(bm.tris), "verts": bm.vcount}
        if not dry_run:
            M.deploy_override(bm, mod_folder=mod_folder, game=game, part="Terrain")
        summary["cells"].append(info)
    return summary
