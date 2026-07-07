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


def _apply_cliff_rock_uvs(bm, *, density: float = 0.0125, outline=None):
    """Override the topo-58 cliff-FACE tris' UVs with the real grey-rock band: U advances with ALONG-SHORE ARC-LENGTH
    at a constant texel ``density`` (per world unit), V = height up the face (base -> 0.923, top -> 0.893). This is the
    measured real-cliff rule (survey of 7808 real wall tris: UV density is tight ~0.0115-0.013 texels/u -- i.e.
    CONSTANT, so U is arc-length-driven, each ~5u wall tri = one ~0.062-wide rock tile tiling around the shore, one
    tile tall). It replaces atan2-ANGLE, which is only arc-length on a CIRCLE (on a rectangle angle barely moves along
    a straight edge then swings fast at a corner -> the rock STRETCHED at corners).

    ``outline`` (a list of ``(x, z)`` around the SHORE, e.g. from :func:`ff9mapkit.world.mesh.blob_cliff_block_mesh`)
    -> U = arc-length along THAT curve (each wall vert takes its nearest outline point's cumulative length). This is the
    faithful path for a SMOOTH organic coast: the curve has no hard corner, so density stays uniform with no warp.
    Without it, U falls back to arc-length around the cell-RECTANGLE perimeter (the old square-island path).

    Single-cell scope: arc-length resets per cell, so a MULTI-cell coast gets one tile-seam at each cell border (the
    along-shore chaining is a later increment); one subtle seam also falls where the loop closes (the length is rarely
    an integer number of tiles) -- both are how real rock cliffs read too."""
    import math
    from .extract import decode_id, CH_UV  # noqa: F401 (CH_UV documents the channel we mutate)
    verts, tans, uv = bm.verts, bm.tangents, bm.chan_arrays[CH_UV]
    face = [tri for tri in bm.tris if decode_id(int(round(tans[tri[0]][0])))["topograph"] == _CLIFF_FACE_TOPO]
    if not face:
        return bm
    face_max = max((verts[k][1] for tri in face for k in tri), default=0.0)
    if face_max <= 1e-3:
        return bm

    if outline:                                                # arc-length along the SMOOTH shore curve
        n = len(outline)
        cum = [0.0] * n
        for i in range(1, n):
            cum[i] = cum[i - 1] + math.hypot(outline[i][0] - outline[i - 1][0], outline[i][1] - outline[i - 1][1])
        perim = cum[-1] + math.hypot(outline[0][0] - outline[-1][0], outline[0][1] - outline[-1][1]) or 1.0

        def shore_s(x, z):                                     # nearest outline vertex's cumulative arc-length
            bi, bd = 0, None
            for i, (ox, oz) in enumerate(outline):
                d = (x - ox) ** 2 + (z - oz) ** 2
                if bd is None or d < bd:
                    bd, bi = d, i
            return cum[bi]
    else:                                                      # arc-length around the cell-RECTANGLE perimeter
        xs = [v[0] for v in verts]; zs = [v[2] for v in verts]
        xmin, xmax, zmin, zmax = min(xs), max(xs), min(zs), max(zs)
        hh, ww = (zmax - zmin), (xmax - xmin)
        perim = 2.0 * (hh + ww) or 1.0

        def shore_s(x, z):                                     # CW around the rectangle (unit rate)
            dW, dE, dN, dS = x - xmin, xmax - x, zmax - z, z - zmin
            m = min(dW, dE, dN, dS)
            if m == dW:
                return zmax - z
            if m == dS:
                return hh + (x - xmin)
            if m == dE:
                return hh + ww + (z - zmin)
            return 2.0 * hh + ww + (xmax - x)

    ub, ut = _CLIFF_ROCK_U
    vb, vt = _CLIFF_ROCK_V
    strip_w = ut - ub
    for tri in face:
        s = [shore_s(verts[k][0], verts[k][2]) for k in tri]
        ref = s[0]
        s = [ref + ((sk - ref + perim / 2.0) % perim) - perim / 2.0 for sk in s]   # unwrap across the loop-close seam
        phase = [sk * density for sk in s]
        base = math.floor(min(phase) / strip_w)                # keep the tri's U window contiguous, tile the rock strip
        for k, ph in zip(tri, phase):
            frac = min(max(ph - base * strip_w, 0.0), strip_w)
            hy = min(max(verts[k][1] / face_max, 0.0), 1.0)
            uv[k] = [ub + frac, vb + hy * (vt - vb)]
    return bm


def reclaim(mod_folder: str, *, cells, disc: int = 1, profile: str = "island", topograph: int = 0,
            height: float | None = None, seg: int = 10, beach: float | None = None, grass_topo: int = 0,
            shore_topo: int | None = None, shore_frac: float | None = None, rim_run: float | None = None,
            game=None, dry_run: bool = False) -> dict:
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
      * ``"cliff"`` -- a CLIFF coast: a rolling walkable land top that drops to the waterline (``Y=0``) via a STEEP
        near-vertical ROCK WALL on each water edge (:func:`ff9mapkit.world.mesh.cliff_block_mesh`), textured with the
        REAL grey-rock band (``_apply_cliff_rock_uvs``: U = along-shore arc wrapping the rock strip, V = height up the
        face). This is the FAITHFUL byte-derived (7,17) cliff (measured 100% of face tris >45deg, median 72deg, ~4u drop
        over ~1.2u run) -- NOT ``island_block_mesh``'s gentle grid-smeared apron (24deg over 9u, the wrong shape) nor a
        topograph palette guess. Cliff defaults (survey of 208 real cliffs): ``height`` 3.2 (~ the interior-land Y you
        stand on: rim med 3.7 but land med 3.1, so a 4u mesa reads too high), ``rim_run`` 1.0 (wall run -> ~73deg). The
        wall is topo 58 (on-foot BLOCKED -- the player stops at the rim); no shallow ladder / foam.
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
        height = {"island": 6.0, "cliff": 3.2}.get(profile, 0.0)   # cliff 3.2 ~ real interior-land Y (survey: rim med 3.7, land med 3.1)
    if beach is None:
        beach = 6.0 if profile == "cliff" else 22.0        # ramp WIDTH: small = steep (cliff), large = gentle (beach)
    if shore_topo is None:
        shore_topo = 58 if profile == "cliff" else 20      # 58 = shore-rim/cliff (on-foot BLOCKED); 20 = walkable sand
    if shore_frac is None:
        shore_frac = 0.6 if profile == "cliff" else 0.3
    if rim_run is None:
        rim_run = 1.0                                      # cliff wall run (u); atan(height/run): 3.2/1.0 -> ~73deg (real med 72)
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
            if profile == "cliff":                         # STEEP rock wall (faithful), not island's gentle apron
                if len(water) == 4:                        # a LONE island -> a SMOOTH organic outline (not the 64u square)
                    bm, outline = M.blob_cliff_block_mesh(disc=disc, x=bx, y=by, land_height=height, rim_run=rim_run,
                                                          land_topo=grass_topo)
                    bm = PAL.apply_palette_uvs(bm, topograph=None, disc=disc, part="terrain", game=game)  # top: grass
                    bm = _apply_cliff_rock_uvs(bm, outline=outline)   # rock U along the smooth curve's arc-length
                else:                                      # part of a multi-cell landmass -> rectangle wall on water edges
                    bm = M.cliff_block_mesh(disc=disc, x=bx, y=by, cliff_dirs=water, seg=seg, land_height=height,
                                            rim_run=rim_run, land_topo=grass_topo)
                    bm = PAL.apply_palette_uvs(bm, topograph=None, disc=disc, part="terrain", game=game)  # top: grass
                    bm = _apply_cliff_rock_uvs(bm)         # arc-length around the cell rectangle
            else:
                bm = M.island_block_mesh(disc=disc, x=bx, y=by, water_dirs=water, seg=seg, height=height,
                                         beach=beach, grass_topo=grass_topo, shore_topo=shore_topo, shore_frac=shore_frac)
                bm = PAL.apply_palette_uvs(bm, topograph=None, disc=disc, part="terrain", game=game)  # per-tri grass/shore
            info = {"cell": [bx, by], "tris": len(bm.tris), "verts": bm.vcount, "water_edges": len(water)}
        else:
            bm = M.flat_block_mesh(disc=disc, x=bx, y=by, seg=seg, topograph=topograph, height=height)
            bm = PAL.apply_palette_uvs(bm, topograph=topograph, disc=disc, part="terrain", game=game)
            info = {"cell": [bx, by], "tris": len(bm.tris), "verts": bm.vcount}
        if not dry_run:
            M.deploy_override(bm, mod_folder=mod_folder, game=game, part="Terrain")
        summary["cells"].append(info)
    return summary
