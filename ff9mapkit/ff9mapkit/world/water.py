"""Synthesize custom GRADED OCEAN WATER for the overworld -- a faithful shallow->deep sea surface authored from a depth
field (no DLL beyond the shipped s34 divert). This is the ``world-water`` pillar: the counterpart of :func:`terrain.coast`
(which carries a REAL coastline verbatim) for OPEN water you author from scratch.

**The proven recipe** (byte-derived from a survey of all 15 disc-1 open-ocean blocks, then validated tile-for-tile at
17/17 shape-match against the real game, and confirmed in-game 2026-07-05):

* **Alphabet = 3 shades.** Open ocean uses ONLY ``Sea3`` (light/shallow) / ``Sea5`` (transition) / ``Sea4``
  (dark/deep). ``Sea1``/``Sea2`` are COAST-only (0 of 3583 surveyed open-ocean tiles) -- painting them in open water is
  the "river tiles supplanted into the ocean" look, so we BLANK them (:func:`ff9mapkit.world.mesh.hidden_block_mesh`).
* **Placement = a MARCHING BAND.** Sample the depth field at each 4u cell's four EDGE MIDPOINTS; an edge is "deep" if
  its depth exceeds ``threshold``. 0 deep edges -> ``Sea3``; 4 -> ``Sea4``; 1-3 -> a ``Sea5`` transition tile. Because
  the sample points are the SHARED cell-edge midpoints (evaluated in WORLD coordinates), neighbouring cells agree by
  construction -> the sea3/sea4/sea5 seams line up, ``Sea3`` can never touch ``Sea4``, AND this holds ACROSS block
  boundaries too (adjacent cells sample the same world-space edges), so a multi-cell region is seamless.
* **Transition UV = a Wang tile** keyed by WHICH edges face deep (:data:`DEEPSET2TILE`): 1 deep edge -> a "tip" strip
  rotated to point at the deep side; 3 deep -> a strip pointing at the lone shallow; 2 adjacent (a corner) -> one of two
  seam-variants. The deep-edge-set -> (v-strip, rotation) map is the byte-derived transition language.
* **Mains UV = quadrant + 4-rotation anti-tiling.** ``Sea3``/``Sea4`` tiles pick one of the texture's 2x2 quadrants
  (stochastic-checkerboard parity flip ~68% between neighbours) and one of 4 rotations (prefer-same clustering ~45%),
  reproducing the real caustic shuffle. Depth is carried by WHICH SHADE, never by orientation.

All UV rectangles / v-strips / the water normal are byte-exact constants reconstructed from real block (8,4). The mesh
is position + UV only (the ``WorldMap/Terrain`` shader binds only vertex + texcoord; normals/tangents are irrelevant to
water rendering, so a single byte-proven :data:`NORMAL` is stamped on every vertex).

**Mechanism / requirements** (shared with :func:`ff9mapkit.world.terrain.reclaim`/:func:`~ff9mapkit.world.terrain.coast`):
each target sea cell gets a flat submerged ``Terrain`` override (the s34 land-override GATE, so the divert fires) plus
the three ``Sea3``/``Sea5``/``Sea4`` water sub-meshes, the two blanked coast shades, and a ``Donor.txt`` naming a real
deep-ocean block whose base sea prefab supplies everything we don't override. **Requires the CUSTOM engine (s34).**
RELAUNCH (or exit+re-enter the overworld) to load. A lone cell is reachable via the debug menu (~) -> World -> Teleport.

Hard-won lessons this encodes (do NOT relitigate -- offline rendering + marginal statistics CANNOT judge water quality;
these were found only by byte-analysis + the human's in-game read):
  * Real ocean uses all **4** rotations of each texture quadrant, not just 0/180 -- invisible to rendering + stats.
  * The transition tile identity is the deep-edge-SET, not a shallow/deep depth bias (that heuristic regressed).
  * ``Sea1``/``Sea2`` in open water read as misplaced river tiles -- blank them.
-> project-memory ``project-ff9-overworld-terrain-authoring`` / ``project-ff9-overworld-coast-mosaic``.
"""
from __future__ import annotations

import math
import random

BLOCK = 64                                              # a 64x64 Unity-unit overworld block (extract.BLOCK_SIZE)
from .mesh import GRID_COLS as GRID_X, GRID_ROWS as GRID_Y  # noqa: E402  the authoritative 24x20 grid
G = 16                                                  # 16x16 sub-tiles per block
CELL = BLOCK / G                                        # 4.0u per sub-tile

LADDER = ["Sea3", "Sea5", "Sea4"]                       # rank 0 shallow / 1 transition / 2 deep (the open-ocean alphabet)
BLANK = ["Sea1", "Sea2"]                                # coast-only shades -> blanked so the donor's don't render
RANK = {"sea3": 0, "sea5": 1, "sea4": 2}

# The reclaimed cell's WALKMESH is our flat Terrain override (it wins the raycast -- registered before the Sea meshes,
# WMWorld.cs LoadBlock order; verified in the s34 patch + a source RE). Real ocean's walkmesh IS its Sea mesh at Y=0
# carrying a SEA topograph: sea3(shallow)=54, sea4(deep)=57 (IDALL tangent.x bits 2-7). A BOAT (movement mode 7) is a
# surface follower whose Y = the walkmesh raycast hit, and its traversal mask admits topographs 53/54/57; ON-FOOT (mode
# 0) and chocobos are BLOCKED on 54/57. So to make a synthesized cell behave like real ocean -- a boat floats on top
# (model visible), on-foot blocked -- the walkmesh must sit at the surface and carry a sea topograph.
WATER_TOPOGRAPH = 57    # deep-sea IDALL topograph: boat-traversable (mode 7 mask bit 25), on-foot/chocobo BLOCKED
WATER_Y = -0.1          # ocean walkmesh Y: just below the Y=0 water render, so a boat floats ~at the surface (hidden
#                         under the opaque water -> no z-fight; a bigger negative sinks the vehicle, 0 z-fights the sea)

# byte-proven per-shade UV rects + v-strips (reconstructed from real block (8,4) exactly) + the water normal
URECT = [(0.0, 0.50394), (0.50394, 0.99213)]            # mains: 2x2 quadrant u-halves
VRECT = [(0.0, 0.49606), (0.50794, 1.0)]                # mains: 2x2 quadrant v-halves
UFULL = (0.0, 0.98413)                                  # transition: full texture width in u (never rotated in u)
VSTRIP = [(0.0, 0.25197), (0.25197, 0.49606), (0.50794, 0.74016), (0.75591, 1.0)]   # 4 measured quarter-strips
NORMAL = (-0.12, 0.98, 0.17)
ROTS = ["r0", "r90", "r180", "r270"]

# deep-edge-set (frozenset of 'N'/'E'/'S'/'W') -> [(v-strip index, rotation-name), ...] (a list = seam-variants).
# 1 deep = strip0 ("tip", rotation points the deep edge); 3 deep = strip2 (points the lone shallow);
# 2 adjacent = strip1/strip3 (a corner, two byte-observed variants). The byte-derived transition language.
DEEPSET2TILE = {
    frozenset("E"): [(0, "r0")], frozenset("S"): [(0, "r90")], frozenset("W"): [(0, "r180")], frozenset("N"): [(0, "r270")],
    frozenset("ES"): [(1, "r0"), (3, "r90")], frozenset("SW"): [(1, "r90"), (3, "r180")],
    frozenset("NW"): [(1, "r180"), (3, "r270")], frozenset("NE"): [(1, "r270"), (3, "r0")],
    frozenset("NES"): [(2, "r0")], frozenset("ESW"): [(2, "r90")], frozenset("NSW"): [(2, "r180")], frozenset("NEW"): [(2, "r270")],
}


def _orient_maps() -> dict:
    """The 4 rotation maps ``(fx, fz) in {0,1}^2 -> (a, b) in {0,1}^2`` (position within the quadrant/strip rect).
    ``r0`` = identity; each successive one is a 90-degree rotation ``(a, b) -> (b, 1-a)``. (Reproduces real block
    (8,4)'s UV orientations exactly -- the 90/270 rotations an id+180-only model dropped.)"""
    def rot(a, b):
        return (b, 1 - a)
    maps = {}
    f = (lambda fx, fz: (fx, fz))
    for r in range(4):
        maps[f"r{r * 90}"] = f
        f = (lambda p: (lambda fx, fz: rot(*p(fx, fz))))(f)
    return maps


OMAPS = _orient_maps()


def _vnoise(x: float, z: float) -> float:
    """A cheap deterministic multi-frequency wobble (world XZ -> ~[-1.3, 1.3]) that gives the shallow|deep contour an
    organic edge instead of a straight line. Continuous in world space, so it agrees across cell + block seams."""
    return math.sin(x * 0.11 + 1.3) * 0.6 + math.sin(z * 0.08 - 0.7) * 0.4 + math.sin(x * 0.23 + z * 0.19) * 0.3


def default_depth_field(cells, *, deep_dir: str = "S", span: float = 2.0, noise: float = 0.5):
    """A built-in graded depth field over the world bounding box of ``cells``: a smooth ramp from shallow (0) at one
    edge to deep (``span``) at the opposite edge in the ``deep_dir`` direction ("N"/"S"/"E"/"W"), plus organic noise.
    Returns ``depth(world_x, world_z) -> float`` (higher = deeper). It is a pure function of WORLD position, so adjacent
    cells sample identical shared edges -> the shallow/deep placement is seamless across the region. For a single cell
    (``span`` 2, ``threshold`` 1) the shallow|deep seam sits mid-cell -- the proven demo look. Pass your own callable to
    :func:`water` for a hand-authored depth map / real contour instead."""
    if deep_dir not in ("N", "S", "E", "W"):
        raise ValueError(f"deep_dir must be one of N/S/E/W, got {deep_dir!r}")
    xs = [bx for (bx, by) in cells]
    ys = [by for (bx, by) in cells]
    x0, x1 = min(xs) * BLOCK, (max(xs) + 1) * BLOCK          # world-x span of the region (west..east)
    z_south, z_north = -(max(ys) + 1) * BLOCK, -min(ys) * BLOCK   # world-z: south is more negative, north nearer 0
    dx = max(x1 - x0, 1e-6)
    dz = max(z_north - z_south, 1e-6)

    def frac(wx: float, wz: float) -> float:                # 0 at the shallow edge -> 1 at the deep edge
        if deep_dir == "S":
            return (z_north - wz) / dz                       # deeper going south (wz decreasing)
        if deep_dir == "N":
            return (wz - z_south) / dz
        if deep_dir == "E":
            return (wx - x0) / dx
        return (x1 - wx) / dx                                 # "W"

    def depth(wx: float, wz: float) -> float:
        return frac(wx, wz) * span + _vnoise(wx, wz) * noise

    return depth


_PATCH_FREQ = 0.5   # lower-frequency noise -> coherent shallow PATCHES (not per-cell speckle), like real open ocean


def open_ocean_depth_field(cells, *, shallows: float = 0.05, noise: float = 0.5, threshold: float = 1.0):
    """A faithful OPEN-OCEAN depth field: mostly deep (like real FF9 open ocean, ~94% ``Sea4``) with a light, organic
    scatter of shallow PATCHES (a fraction ~``shallows`` of the region), each ringed by transition water -- and NO
    directional gradient (that's :func:`default_depth_field`, for a coast/bay). ``shallows=0`` -> uniform deep ``Sea4``.
    The shallow fraction is set by offsetting a low-frequency noise so ~``shallows`` of the region dips below
    ``threshold``, so the look is stable regardless of which cells you fill (and seam-continuous across them, since it's
    a pure function of world position)."""
    if shallows <= 0:
        return lambda wx, wz: threshold + 1.0                # everything deep
    seen = {tuple(c) for c in cells}
    samples = sorted(_vnoise((bx * BLOCK + (i + 0.5) * CELL) * _PATCH_FREQ, (-by * BLOCK - (j + 0.5) * CELL) * _PATCH_FREQ) * noise
                     for (bx, by) in seen for i in range(G) for j in range(G))
    q = samples[min(int(shallows * (len(samples) - 1)), len(samples) - 1)]
    base = threshold - q
    return lambda wx, wz: base + _vnoise(wx * _PATCH_FREQ, wz * _PATCH_FREQ) * noise


def _edge_mids(bx: int, by: int, i: int, j: int) -> dict:
    """The four edge-midpoint WORLD coordinates of sub-tile ``(i, j)`` in block ``(bx, by)``. World frame:
    ``worldVert = (bx*64 + localX, y, -by*64 + localZ)`` with ``localZ`` in ``[-64, 0]`` (grid row marches -Z), so the
    shared edge between two cells resolves to the IDENTICAL world point from both sides (the seam-matching guarantee)."""
    ox, oz = bx * BLOCK, -by * BLOCK
    return {"N": (ox + (i + 0.5) * CELL, oz - j * CELL),
            "S": (ox + (i + 0.5) * CELL, oz - (j + 1) * CELL),
            "E": (ox + (i + 1) * CELL, oz - (j + 0.5) * CELL),
            "W": (ox + i * CELL, oz - (j + 0.5) * CELL)}


def _deep_edges(depth, threshold: float, bx: int, by: int, i: int, j: int) -> frozenset:
    return frozenset(d for d, (mx, mz) in _edge_mids(bx, by, i, j).items() if depth(mx, mz) > threshold)


def build_arrangement(depth, threshold: float, bx: int, by: int, rng: random.Random):
    """Marching-band placement for one block: returns ``grid[i][j] in {sea3, sea4, sea5}`` and
    ``sea5tile{(i, j): (strip, rotation)}`` from the world-edge-sampled deep-edge-set. A 2-opposite ("channel") set has
    no single Wang tile, so it degrades to the strongest single/triple deep edge (the tile pointing at the deepest side)."""
    grid = [["sea4"] * G for _ in range(G)]
    sea5tile = {}
    for i in range(G):
        for j in range(G):
            de = _deep_edges(depth, threshold, bx, by, i, j)
            n = len(de)
            if n == 0:
                grid[i][j] = "sea3"
            elif n == 4:
                grid[i][j] = "sea4"
            else:
                key = de
                if key not in DEEPSET2TILE:                  # 2-opposite channel: drop the weaker deep edge(s)
                    mids = _edge_mids(bx, by, i, j)
                    dep = sorted(de, key=lambda d: -depth(*mids[d]))
                    key = frozenset(dep[:1]) if n == 2 else frozenset(dep[:3])
                variants = DEEPSET2TILE[key]
                grid[i][j] = "sea5"
                sea5tile[(i, j)] = variants[rng.randrange(len(variants))]
    return grid, sea5tile


def assign_quadrants(grid, rng: random.Random) -> dict:
    """Mains anti-tiling: each ``sea3``/``sea4`` tile picks a 2x2 quadrant ``(u_half, v_half)``. Parity ``u ^ v`` flips
    ~68% between neighbours (a stochastic checkerboard) -> the real caustic shuffle, no visible repeat."""
    quad = {}
    for j in range(G):
        for i in range(G):
            if grid[i][j] not in ("sea3", "sea4"):
                continue
            nb = [q for q in (quad.get((i - 1, j)), quad.get((i, j - 1))) if q]
            if not nb:
                quad[(i, j)] = (rng.randint(0, 1), rng.randint(0, 1))
            else:
                pn = nb[rng.randrange(len(nb))]
                par = pn[0] ^ pn[1]
                target = (1 - par) if rng.random() < 0.68 else par
                opts = [(0, 0), (1, 1)] if target == 0 else [(1, 0), (0, 1)]
                quad[(i, j)] = opts[rng.randrange(2)]
    return quad


def assign_rotations(grid, rng: random.Random) -> dict:
    """Mains anti-tiling: each ``sea3``/``sea4`` tile picks one of 4 rotations, prefer-same clustering (copy a placed
    neighbour ~52% -> adjacent-same ~45% like the real data, else a weighted marginal)."""
    rot = {}
    for j in range(G):
        for i in range(G):
            if grid[i][j] not in ("sea3", "sea4"):
                continue
            nb = [r for r in (rot.get((i - 1, j)), rot.get((i, j - 1))) if r]
            if nb and rng.random() < 0.52:
                rot[(i, j)] = nb[rng.randrange(len(nb))]
            else:
                rot[(i, j)] = rng.choices(ROTS, weights=[0.32, 0.25, 0.21, 0.21])[0]
    return rot


def _tile_uv(grid, quad, rot, sea5tile, i, j):
    """A ``(fx, fz) -> [u, v]`` sampler for sub-tile ``(i, j)`` (``fx``/``fz`` = the 0/1 quad corner). Transition tiles
    use the full-width-u x hashed v-strip (rotated to face deep); mains use their quadrant rect + rotation."""
    if grid[i][j] == "sea5":
        t = sea5tile[(i, j)]
        strip, oname = t[0], t[1]
        if len(t) >= 6:                                  # a reproduced REAL tile carries its exact (u0,u1,v0,v1) rect
            u0, u1, v0, v1 = t[2], t[3], t[4], t[5]
        else:                                            # a synthesized tile uses the canonical full-u x VSTRIP band
            u0, u1 = UFULL
            v0, v1 = VSTRIP[strip]
    else:
        ub, vb = quad[(i, j)]
        u0, u1 = URECT[ub]
        v0, v1 = VRECT[vb]
        oname = rot[(i, j)]
    m = OMAPS[oname]
    return lambda fx, fz: [u0 + m(fx, fz)[0] * (u1 - u0), v0 + m(fx, fz)[1] * (v1 - v0)]


def _bands_from_arrangement(grid, sea5tile, bx: int, by: int, seed) -> dict:
    """Generate the three water bands (``bands[rank]`` = triangle lists, rank 0 ``Sea3`` / 1 ``Sea5`` / 2 ``Sea4``, each
    triangle a 3-list of ``((localX, 0, localZ), [u, v])`` pairs in the block's LOCAL frame) for a PREBUILT arrangement
    (``grid`` + ``sea5tile``), applying fresh mains quadrant+rotation anti-tiling seeded from ``(seed, bx, by)``."""
    rng_m = random.Random(f"ff9water:{seed}:{bx}:{by}:mains")
    quad = assign_quadrants(grid, rng_m)
    rot = assign_rotations(grid, rng_m)
    vg = {(i, j): (i * CELL, 0.0, -(j * CELL)) for i in range(G + 1) for j in range(G + 1)}
    bands = {0: [], 1: [], 2: []}
    for i in range(G):
        for j in range(G):
            rk = RANK[grid[i][j]]
            uv = _tile_uv(grid, quad, rot, sea5tile, i, j)
            corner = {(0, 0): vg[(i, j)], (1, 0): vg[(i + 1, j)], (1, 1): vg[(i + 1, j + 1)], (0, 1): vg[(i, j + 1)]}
            for tri in ([(0, 0), (1, 0), (1, 1)], [(0, 0), (1, 1), (0, 1)]):
                bands[rk].append([(corner[c], uv(*c)) for c in tri])
    return bands


def build_cell(bx: int, by: int, *, depth, threshold: float = 1.0, seed=0):
    """Build the three water bands for one cell from the depth field (marching-band arrangement + anti-tiling). Returns
    ``(bands, grid, sea5tile)``. The per-cell PRNGs are seeded deterministically from ``(seed, bx, by)`` so adjacent
    cells vary (no macro-repeat) while the run stays reproducible."""
    rng_t = random.Random(f"ff9water:{seed}:{bx}:{by}:trans")
    grid, sea5tile = build_arrangement(depth, threshold, bx, by, rng_t)
    bands = _bands_from_arrangement(grid, sea5tile, bx, by, seed)
    return bands, grid, sea5tile


def shade_counts(grid) -> dict:
    from collections import Counter
    c = Counter(grid[i][j] for i in range(G) for j in range(G))
    return {s: c.get(s, 0) for s in ("sea3", "sea5", "sea4")}


def adjacency_violations(grid) -> int:
    """Count DIRECT ``sea3``|``sea4`` 4-neighbour adjacencies -- the marching-band invariant guarantees 0 (a transition
    band always bridges them); any nonzero means a bug in the placement."""
    return sum(1 for i in range(G) for j in range(G) for di, dj in ((1, 0), (0, 1))
               if 0 <= i + di < G and 0 <= j + dj < G and {grid[i][j], grid[i + di][j + dj]} == {"sea3", "sea4"})


def _deploy_ocean_cell(mod_folder: str, bx: int, by: int, *, sea: dict, donor, disc: int, lod: str, height: float,
                       game, dry_run: bool) -> tuple:
    """Deploy ONE cell's ocean, the shape shared by :func:`water` (synthesized Sea meshes) and :func:`deploy_verbatim`
    (real Sea meshes): a flat ``Terrain`` override at ``Y=height`` (the s34 land-override GATE **and** the cell's
    WALKMESH -- carries :data:`WATER_TOPOGRAPH` so a boat sails on top / on-foot is blocked, at the water surface), the
    ``Sea3``/``Sea5``/``Sea4`` meshes from ``sea`` (a ``part -> BlockMesh`` map; a missing part is BLANKED), blanked
    ``Sea1``/``Sea2``, and the ``Donor.txt`` naming the deep-ocean ``donor``. Returns ``(parts, written)`` -- the
    ``part -> BlockMesh`` deployed, and the list of Paths actually written (empty on ``dry_run``)."""
    from . import mesh as M
    parts = {"Terrain": M.flat_block_mesh(disc=disc, x=bx, y=by, seg=8, topograph=WATER_TOPOGRAPH, height=height, lod=lod)}
    for name in LADDER:
        parts[name] = sea.get(name) or M.hidden_block_mesh(name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by, lod=lod)
    for name in BLANK:
        parts[name] = M.hidden_block_mesh(name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by, lod=lod)
    written = []
    if not dry_run:
        for name, bm in parts.items():
            written.append(M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part=name))
        written.append(M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=mod_folder, disc=disc, x=bx, y=by,
                                              lod=lod, game=game))
    return parts, written


def _deploy_bands(mod_folder: str, bx: int, by: int, bands: dict, *, donor, disc: int, lod: str, height: float,
                  game, dry_run: bool) -> list:
    """Turn synthesized ``bands`` into the ``Sea3``/``Sea5``/``Sea4`` render sub-meshes and deploy the cell (shared by
    :func:`water` and :func:`reproduce`). Returns the written Paths (empty on ``dry_run``)."""
    from . import mesh as M
    sea = {name: M.tri_soup_block_mesh(bands[rk], name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by,
                                       lod=lod, normal=NORMAL)
           for rk, name in enumerate(LADDER) if bands[rk]}
    _parts, written = _deploy_ocean_cell(mod_folder, bx, by, sea=sea, donor=donor, disc=disc, lod=lod,
                                        height=height, game=game, dry_run=dry_run)
    return written


def water(mod_folder: str, *, cells, donor=(15, 4), depth=None, deep_dir: str | None = None, shallows: float = 0.05,
          threshold: float = 1.0, span: float = 2.0, noise: float = 0.5, seed=0, disc: int = 1, lod: str = "0_1",
          height: float = WATER_Y, game=None, dry_run: bool = False, skip_mirror: bool = False) -> dict:
    """Synthesize faithful ocean water on each sea cell in ``cells`` (``(x, y)`` grid coords, 0..23 x 0..19).

    ``depth`` is a caller-supplied ``depth(world_x, world_z) -> float`` (higher = deeper). When ``None``, the built-in
    field depends on ``deep_dir``: omitted (``None``) -> faithful OPEN OCEAN (:func:`open_ocean_depth_field`, mostly
    deep like real FF9 open water ~94% Sea4, with a ~``shallows`` scatter of shallow patches); a direction "N"/"S"/"E"/
    "W" -> a graded shallow->deep RAMP toward it (:func:`default_depth_field`, for a coast/bay; uses ``span``/``noise``).
    Because the field is sampled at shared world-space cell edges, a contiguous ``cells`` region is seamless across
    cells AND blocks. Each cell deploys: a flat ``Terrain`` override at ``Y=height`` (the s34 land-override gate AND the
    cell's WALKMESH, carrying a sea topograph so a boat floats on top at the surface and on-foot is blocked -- like real
    ocean), the ``Sea3``/``Sea5``/``Sea4`` water sub-meshes, blanked ``Sea1``/``Sea2``, and a ``Donor.txt`` naming the
    real deep-ocean ``donor`` block whose base sea prefab supplies the rest.

    Requires the CUSTOM engine (the s34 sea->land divert); a stock sea cell short-circuits to ``SeaBlockPrefab`` before
    the override fires. RELAUNCH (or exit+re-enter the overworld) to load; reach a lone cell via the debug menu (~) -> World -> Teleport.
    Returns a summary; deploys nothing when ``dry_run``. A real deploy auto-mirrors the written overrides to Disc4
    (``skip_mirror=True`` opts out)."""
    cells = [tuple(c) for c in cells]
    if not cells:
        raise ValueError("give at least one cell")
    for (bx, by) in cells:
        if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
            raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    dx, dy = donor
    if not (0 <= dx < GRID_X and 0 <= dy < GRID_Y):
        raise ValueError(f"donor ({dx},{dy}) out of the {GRID_X}x{GRID_Y} overworld grid")
    if depth is None:
        depth = (default_depth_field(cells, deep_dir=deep_dir, span=span, noise=noise) if deep_dir
                 else open_ocean_depth_field(cells, shallows=shallows, noise=noise, threshold=threshold))
    summary = {"op": "water", "mode": deep_dir or "open", "donor": [dx, dy], "disc": disc, "deep_dir": deep_dir,
               "threshold": threshold, "dry_run": dry_run, "cells": []}
    written = []
    for (bx, by) in cells:
        bands, grid, sea5tile = build_cell(bx, by, depth=depth, threshold=threshold, seed=seed)
        written.extend(_deploy_bands(mod_folder, bx, by, bands, donor=(dx, dy), disc=disc, lod=lod, height=height,
                                     game=game, dry_run=dry_run))
        summary["cells"].append({"cell": [bx, by], "shades": shade_counts(grid), "sea5": len(sea5tile),
                                 "adjacency_violations": adjacency_violations(grid)})
    if not dry_run:
        from . import discmirror as DM
        DM.auto_mirror(written, mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary


def deploy_island_sea(mod_folder: str, *, cells, donor=(15, 4), disc: int = 1, lod: str = "0_1", seed=0,
                      game=None, dry_run: bool = False) -> dict:
    """Deploy DEEP open-ocean sea sub-meshes (``Sea4`` at ``Y=0``) + blanked ``Sea1``/``Sea2`` + a ``Donor.txt`` AROUND a
    synthesized island, WITHOUT a ``Terrain`` override -- the caller keeps its own LAND Terrain (e.g. a reclaim blob
    island). A lone reclaimed island whose land does NOT fill the cell needs a sea surface in the cell's water area,
    because the s34 divert removes the stock cell sea (a full-cell reclaim never needed this: it WAS the whole cell).
    The island's land Terrain stays the s34 gate + walkmesh; this adds only the water RENDER around it. Deep-only
    (open ocean) for now -- shore shallows/foam hugging the curved coast are a later increment. Returns a summary."""
    from . import mesh as M
    cells = [tuple(c) for c in cells]
    depth = open_ocean_depth_field(cells, shallows=0.0)                 # uniform deep -> all Sea4
    summary = {"op": "island_sea", "donor": list(donor), "disc": disc, "cells": []}
    for (bx, by) in cells:
        bands, _grid, _s5 = build_cell(bx, by, depth=depth, threshold=1.0, seed=seed)
        sea = {name: M.tri_soup_block_mesh(bands[rk], name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by,
                                           lod=lod, normal=NORMAL)
               for rk, name in enumerate(LADDER) if bands[rk]}
        if not dry_run:
            for name in LADDER:                                        # Sea3/Sea5 empty (all-deep) -> blanked
                bm = sea.get(name) or M.hidden_block_mesh(name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by, lod=lod)
                M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part=name)
            for name in BLANK:
                M.deploy_override(M.hidden_block_mesh(name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by, lod=lod),
                                  mod_folder=mod_folder, game=game, lod=lod, part=name)
            M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=mod_folder, disc=disc, x=bx, y=by, lod=lod, game=game)
        summary["cells"].append({"cell": [bx, by], "sea4_tris": len(bands[2])})
    return summary


def deploy_verbatim(mod_folder: str, *, cells, source=(8, 4), donor=(15, 4), disc: int = 1, lod: str = "0_1",
                    height: float = WATER_Y, game=None, dry_run: bool = False,
                    skip_mirror: bool = False) -> dict:
    """Deploy a REAL open-ocean block's water sub-meshes VERBATIM onto each target cell -- the NORTH-STAR A/B reference
    for validating :func:`water`. Copies ``source``=(bx, by)'s real ``Sea3``/``Sea4``/``Sea5`` meshes UNCHANGED (only
    relocated to the cell), then deploys them through the EXACT same shape as :func:`water` (flat submerged Terrain gate
    + blanked Sea1/Sea2 + donor sidecar) -- so a side-by-side at the same cell isolates the SYNTHESIS quality from the
    deploy pipeline (a byte-copy of a real block is proven to render faithfully in-game). ``source`` defaults to block
    (8,4), the byte-proven reference the synthesizer was validated 17/17 against. Requires the game install (reads the
    real block) + the custom engine (s34). Returns a summary; deploys nothing when ``dry_run``. A real deploy
    auto-mirrors the written overrides to Disc4 (``skip_mirror=True`` opts out)."""
    import dataclasses
    from . import extract as X
    cells = [tuple(c) for c in cells]
    if not cells:
        raise ValueError("give at least one cell")
    for (bx, by) in cells:
        if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
            raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    sx, sy = source
    dx, dy = donor
    if not (0 <= dx < GRID_X and 0 <= dy < GRID_Y):
        raise ValueError(f"donor ({dx},{dy}) out of the {GRID_X}x{GRID_Y} overworld grid")
    src = {}                                                 # the real Sea sub-meshes the source actually has
    for name in LADDER:
        try:
            src[name] = X.read_block(sx, sy, disc=disc, lod=lod, part=name.lower(), game=game)
        except (ValueError, FileNotFoundError):
            src[name] = None
    if not any(src.values()):
        raise ValueError(f"source block ({sx},{sy}) has no Sea3/Sea4/Sea5 sub-mesh -- pick an OPEN-OCEAN block")
    summary = {"op": "water-verbatim", "source": [sx, sy], "donor": [dx, dy], "disc": disc,
               "dry_run": dry_run, "cells": []}
    written = []
    for (bx, by) in cells:
        sea = {name: dataclasses.replace(bm, x=bx, y=by, name=f"Block[{bx}][{by}] {name}")
               for name, bm in src.items() if bm is not None}
        _parts, w = _deploy_ocean_cell(mod_folder, bx, by, sea=sea, donor=(dx, dy), disc=disc, lod=lod,
                                       height=height, game=game, dry_run=dry_run)
        written.extend(w)
        summary["cells"].append({"cell": [bx, by], "carried": sorted(sea),
                                 "verts": sum(bm.vcount for bm in sea.values())})
    if not dry_run:
        from . import discmirror as DM
        DM.auto_mirror(written, mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary


_NEIGH = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}   # (di, dj); N/-j is the top edge (matches _edge_mids)


def _neighbor(grid, i, j, d):
    di, dj = _NEIGH[d]
    ni, nj = i + di, j + dj
    return grid[ni][nj] if 0 <= ni < G and 0 <= nj < G else None


def read_shade_grid(sx: int, sy: int, *, disc: int = 1, lod: str = "0_1", game=None):
    """The per-cell shade layout of a REAL block: ``grid[i][j] in {sea3, sea4, sea5}``, by binning each Sea sub-mesh's
    triangles to their 4u cell. A cell with no Sea geometry defaults to ``sea4`` (the deep open-ocean base). Requires
    the game install."""
    from . import extract as X
    seen = [[None] * G for _ in range(G)]
    for part in ("sea3", "sea4", "sea5"):
        try:
            bm = X.read_block(sx, sy, disc=disc, lod=lod, part=part, game=game)
        except (ValueError, FileNotFoundError):
            continue
        for tri in bm.tris:
            i = int((sum(bm.verts[q][0] for q in tri) / 3) // CELL)
            j = int((-sum(bm.verts[q][2] for q in tri) / 3) // CELL)
            if 0 <= i < G and 0 <= j < G:
                seen[i][j] = part
    return [[seen[i][j] or "sea4" for j in range(G)] for i in range(G)]


def _repro_deepset(grid, i, j) -> frozenset:
    """The marching-band deep-edge-set for reproducing a real ``sea5`` cell: the edges facing a DEEP (sea4) neighbour
    (the byte-proven rule -- a transition tile's deep edges abut sea4 100% of the time). Degrade an invalid set (a
    peninsula tip with 0 sea4 neighbours, or a channel) to the nearest representable Wang tile."""
    deep = [d for d in "NESW" if _neighbor(grid, i, j, d) == "sea4"]
    de = frozenset(deep)
    if de in DEEPSET2TILE:
        return de
    if len(deep) >= 3:                                   # 4 deep (lone shallow poke) -> a deep-tip
        return frozenset(deep[:3])
    if len(deep) == 2:                                   # opposite channel -> a single tip toward the deeper side
        return frozenset(deep[:1])
    s5 = [d for d in "NESW" if _neighbor(grid, i, j, d) == "sea5"]   # 0 sea4: point along the peninsula
    return frozenset(s5[:1]) if s5 else frozenset("E")


def _strip_of(v0: float) -> int:
    """Which of the 4 quarter-strips a fitted ``v0`` (the tile's minimum v) belongs to."""
    return min(range(4), key=lambda k: abs(VSTRIP[k][0] - v0))


def _fit_tile(corners: dict):
    """Fit a cell's 4 corner UVs (``{(fx, fz): (u, v)}``) to ``(bounding rect, one of the 4 rotations)`` and return
    ``(u0, u1, v0, v1, rotation-name)``, or ``None`` if no pure rotation reproduces every corner within tolerance (a
    transpose/reflection tile -- the rare ~1% class my vocabulary can't represent). This is the exact fit that scored
    the offline 17/17 shape-match; the rect it returns is the tile's real UV extent (carried through for an exact
    reproduction, not just quantized to a strip index)."""
    us = [uv[0] for uv in corners.values()]
    vs = [uv[1] for uv in corners.values()]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    if u1 == u0 or v1 == v0:
        return None
    for name in ROTS:
        m = OMAPS[name]
        if all(abs((u0 + m(fx, fz)[0] * (u1 - u0)) - u) <= 0.01 and abs((v0 + m(fx, fz)[1] * (v1 - v0)) - v) <= 0.01
               for (fx, fz), (u, v) in corners.items()):
            return (u0, u1, v0, v1, name)
    return None


def classify_sea5_cell(corners: dict, *, min_corners: int = 4, min_uv_span: float = 0.0):
    """THE one Sea5 tile classifier (audit rec 7). ``corners`` = ``{(fx, fz): (u, v)}`` for one 4u
    cell. Returns ``(strip, rotation, u0, u1, v0, v1)`` or ``None``.

    Three copies of this question ("which deepset/transition tile is this cell?") had diverged into
    three arity rules -- all-4-corners (the reference reader), >=3 + a degeneracy guard (the carry
    gate), and NO guard (the rim audit) -- so the same deployed cell could be unclassified to one
    instrument, dropped by another, and confidently classified by the third, which then iterated to
    a fixed point on it. The arity is now an EXPLICIT argument at every call site:

    - ``min_corners=4``: the canonical four corners must be present (reference semantics).
    - ``min_corners=3``: the shore-sliver relaxation (a 1-triangle sliver still classifies).
    - below 3 is REFUSED outright: a 2-corner fit is under-constrained -- ``_fit_tile`` returns the
      FIRST rotation in ``ROTS`` order, i.e. an essentially arbitrary answer.

    ``min_uv_span`` rejects near-degenerate UV rects (the carry gate uses ``1e-6``; ``0.0`` keeps
    ``_fit_tile``'s own exact-equality reject, the reference behaviour)."""
    if min_corners < 3:
        raise ValueError("classify_sea5_cell: min_corners < 3 is an under-constrained fit "
                         "(_fit_tile would return the first rotation in ROTS order -- an "
                         "arbitrary answer on a sliver); 3 is the floor")
    if min_corners >= 4:
        if not all(c in corners for c in ((0, 0), (1, 0), (1, 1), (0, 1))):
            return None
    elif len(corners) < min_corners:
        return None
    if min_uv_span > 0.0:
        us = [uv[0] for uv in corners.values()]
        vs = [uv[1] for uv in corners.values()]
        if max(us) - min(us) <= min_uv_span or max(vs) - min(vs) <= min_uv_span:
            return None
    fit = _fit_tile(corners)                             # its own exact-degeneracy reject stands
    if fit is None:
        return None
    u0, u1, v0, v1, name = fit
    return (_strip_of(v0), name, u0, u1, v0, v1)


def sea5_deepset_of(corners: dict, *, min_corners: int = 3, min_uv_span: float = 1e-6):
    """The cell's DEEPSET (frozenset of deep sides) via :func:`classify_sea5_cell` + the
    ``DEEPSET2TILE`` inverse -- the shared spelling both deepset readers (transplant's carry
    gate, rimretile's rim audit) now use, so they agree BY CONSTRUCTION."""
    cls = classify_sea5_cell(corners, min_corners=min_corners, min_uv_span=min_uv_span)
    if cls is None:
        return None
    key = (cls[0], cls[1])
    for ds, variants in DEEPSET2TILE.items():
        if key in [tuple(o) for o in variants]:
            return ds
    return None


def read_sea5_tiles(sx: int, sy: int, *, disc: int = 1, lod: str = "0_1", game=None) -> dict:
    """Read the ACTUAL transition tile of every real ``Sea5`` cell from its UVs (bin the sub-mesh's triangles to cells,
    fit the 4 corner UVs). Returns ``{(i, j): (strip, rotation, u0, u1, v0, v1)}`` for cells whose tile fits a pure
    rotation -- the ``(strip, rotation)`` classify it, and the ``(u0, u1, v0, v1)`` rect is its EXACT real UV extent (so
    the reproduction matches the real tile pixel-for-pixel, not just to the nearest canonical strip). Unfittable (rare
    transpose) cells are omitted. Requires the game install."""
    from collections import defaultdict
    from . import extract as X
    try:
        bm = X.read_block(sx, sy, disc=disc, lod=lod, part="sea5", game=game)
    except (ValueError, FileNotFoundError):
        return {}
    corners = defaultdict(dict)
    for tri in bm.tris:
        i = int((sum(bm.verts[q][0] for q in tri) / 3) // CELL)
        j = int((-sum(bm.verts[q][2] for q in tri) / 3) // CELL)
        for k in tri:
            v = bm.verts[k]
            corners[(i, j)][(round((v[0] - i * CELL) / CELL), round((-v[2] - j * CELL) / CELL))] = bm.uvs[k]
    out = {}
    for (i, j), d in corners.items():
        cls = classify_sea5_cell(d, min_corners=4)
        if cls is not None:
            out[(i, j)] = cls
    return out


def arrangement_from_block(sx: int, sy: int, *, disc: int = 1, lod: str = "0_1", game=None, seed=0,
                           real_tiles: bool = True):
    """Reconstruct a real block's arrangement for the synthesizer: its per-cell shade ``grid`` (:func:`read_shade_grid`)
    plus a ``sea5tile`` map. With ``real_tiles`` (default), each transition tile is the block's ACTUAL ``(strip,
    rotation)`` read from its UVs (:func:`read_sea5_tiles`) -- an EXACT reproduction, so thin peninsulas/features come
    out right. A cell whose real tile can't be represented (the rare transpose) falls back to the shade-derived
    :data:`DEEPSET2TILE` rule (:func:`_repro_deepset`), which is also used for every cell when ``real_tiles=False``.
    Requires the game install."""
    grid = read_shade_grid(sx, sy, disc=disc, lod=lod, game=game)
    real = read_sea5_tiles(sx, sy, disc=disc, lod=lod, game=game) if real_tiles else {}
    rng = random.Random(f"ff9water:repro:{seed}:{sx}:{sy}")
    sea5tile = {}
    for i in range(G):
        for j in range(G):
            if grid[i][j] != "sea5":
                continue
            if (i, j) in real:
                sea5tile[(i, j)] = real[(i, j)]                   # the EXACT real transition tile
            else:
                variants = DEEPSET2TILE[_repro_deepset(grid, i, j)]
                sea5tile[(i, j)] = variants[rng.randrange(len(variants))]
    return grid, sea5tile


def reproduce(mod_folder: str, *, cells, source=(8, 4), donor=(15, 4), seed=0, disc: int = 1, lod: str = "0_1",
              height: float = WATER_Y, game=None, dry_run: bool = False,
              skip_mirror: bool = False) -> dict:
    """Reproduce a REAL block's shallow/deep arrangement with SYNTHESIZED tiles onto each target cell -- the in-game
    fidelity proof for :func:`water`. Reads ``source``=(bx, by)'s per-cell shade layout (:func:`arrangement_from_block`)
    and regenerates it through the synth's tile-selection + mains anti-tiling, so it lands the SAME layout as the real
    block but drawn with synthesized tiles. Deploy it beside :func:`deploy_verbatim` of the same block: they should look
    alike (the offline 17/17 shape-match, made visible). Requires the game install + the custom engine (s34). Returns a
    summary; deploys nothing when ``dry_run``. A real deploy auto-mirrors the written overrides to Disc4
    (``skip_mirror=True`` opts out)."""
    cells = [tuple(c) for c in cells]
    if not cells:
        raise ValueError("give at least one cell")
    for (bx, by) in cells:
        if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
            raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    sx, sy = source
    dx, dy = donor
    if not (0 <= dx < GRID_X and 0 <= dy < GRID_Y):
        raise ValueError(f"donor ({dx},{dy}) out of the {GRID_X}x{GRID_Y} overworld grid")
    grid, sea5tile = arrangement_from_block(sx, sy, disc=disc, lod=lod, game=game, seed=seed)
    summary = {"op": "water-reproduce", "source": [sx, sy], "donor": [dx, dy], "disc": disc,
               "dry_run": dry_run, "cells": []}
    written = []
    for (bx, by) in cells:
        bands = _bands_from_arrangement(grid, sea5tile, bx, by, seed)
        written.extend(_deploy_bands(mod_folder, bx, by, bands, donor=(dx, dy), disc=disc, lod=lod, height=height,
                                     game=game, dry_run=dry_run))
        summary["cells"].append({"cell": [bx, by], "shades": shade_counts(grid), "sea5": len(sea5tile),
                                 "adjacency_violations": adjacency_violations(grid)})
    if not dry_run:
        from . import discmirror as DM
        DM.auto_mirror(written, mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary
