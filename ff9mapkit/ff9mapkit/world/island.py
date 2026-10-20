"""Fully-SYNTHETIC overworld islands / landmasses -- the in-game-proven builder (2026-07-07), productized.

Composes everything the synth-island session proved, layer by layer:

* **Coastline**: :func:`ff9mapkit.world.mesh.blob_outline` -- FF9's measured shape language (gentle
  ~25u-radius curves + occasional corner dents), any radius, deterministic per seed.
* **Rock wall**: the faithful ~73 deg cliff profile (``rim_run`` 1.0 at ``land_height`` 3.2) textured by
  the measured rock-band rule -- U advances with GLOBAL along-shore arc-length (constant density, window-
  translated so the strip's sawtooth wrap lands on triangle boundaries, never mid-tri: the smear fix),
  V climbs the face.
* **Grass**: the real tile language from :mod:`ff9mapkit.world.grassland` -- lattice mains
  (quadrant+rotation, direction-aware bleed), verbatim meadow STAMPS, OPT-IN rolling RELIEF
  (a deterministic world-XZ value-noise height field, off by default -- see ``relief_amp``),
  position-welded smoothed normals.
* **Placement**: winding is enforced at emit and the build is gated by the offline engine simulator
  (:mod:`ff9mapkit.world.placement`) -- the old synth blob stranded the player 3x in-game because its top
  was wound down-facing; MISS anywhere in a cell is a stranding spot or an invisible vehicle wall.

**Multi-cell by construction**: the landmass is built as ONE watertight triangle soup in WORLD
coordinates, then every triangle is CLIPPED at the 64u block borders (the engine raycasts only the block
containing the query point -- a cross-border triangle is a collision hole) and partitioned into per-block
``Terrain`` overrides. Both halves of a straddling triangle share the same cut points, so watertightness
across borders holds by construction; the wall's arc-length U is global, so the rock band chains
seamlessly across cells. Each touched block also gets a hole-patched full-cell deep Sea4 plane
(:func:`ff9mapkit.world.mesh.fill_missing_grid_quads` -- the real (12,0) plane is missing one quad),
blanked Object/Sea1/2/3/5 parts, and a ``Donor.txt`` naming a Terrain-carrying donor for the s34 divert.

Needs the custom engine (s34 world overrides); a NEW block id needs a world re-entry to stream the
override. Full story: project memories ``project-ff9-overworld-coast-mosaic`` +
``project-ff9-overworld-placement-rules``.
"""
from __future__ import annotations

import collections
import dataclasses
import math
import random

from . import grassland as G
from . import placement as P

BLOCK = 64.0
GRID = 4.0
LAND_TOPO = 0
CLIFF_TOPO = 58
MAX_FLANK = 28.6                                         # measured lowland-grass slope p99 (= interior.MAX_FLANK);
#                                                         the OPT-IN relief ceiling -- ground tris must stay under it
ROCK_U = (0.699, 0.947)                                  # the measured grey-rock atlas band
ROCK_V = (0.923, 0.893)                                  # V: base -> top (the rock climbs the face)
ROCK_DENSITY = 0.0125                                    # texels/u along the shore (measured constant)
SEA_PLANE_SOURCE = (12, 0)                               # the game's only full-cell deep Sea4 plane
DEFAULT_DONOR = (0, 0)                                   # Uaho: a Terrain-carrying donor for the s34 divert
HIDDEN_PARTS = ("Object", "Sea1", "Sea2", "Sea3", "Sea5", "Beach1")
#: THE CELL-CLIPPED LIP (the lip-streak fix): a crest vertex this near a 4u lattice line is moved ONTO it (stock's
#: crease sits on the lattice lines: 1216 of 1540 disc-1 crest verts), and a grass clip point this near a lattice
#: corner onto the corner -- a vertex just off a line leaves a sliver cell piece. Crest CUTS are never moved: they
#: stay on the crest edge, so the wall keeps its own rock texture.
LATTICE_SNAP = 0.15
#: a cell-lip wall quad takes its o0-r1 diagonal when the o1-r0 one would lean under this |normal.y| (a kit wall
#: leans ~0.29; the engine's walk filter drops <= 0.1) and the other leans less
WALL_LEAN_FLOOR = 0.2
#: a JOIN segment's cuts (a crest edge ending at a stock-pinned column) sit this far landward along their own line,
#: so the chain into the column is not plan-collinear: river's open zip fans round the column over these very crest
#: points, and a collinear triple there is a plan-flat step it must route round -- it folded over the stock wall
#: (cluster C's G4). The cut stays exactly on its lattice line.
JOIN_CUT_DENT = 0.01
#: the lip's own mains stream: a cell-lip mint's NEW lip cells draw from ``mains_seed`` plus this
LIP_MAINS_SEED = 0x11F
#: per-family beach reference blocks (language pins AND the beach block's divert
#: donor -- both host Terrain+Sea1/2/4/5+Beach1 transforms, verified 2026-07-15)
BEACH_PINS = {"grass": (7, 17), "desert": (20, 5)}


# --------------------------------------------------------------------------- geometry helpers

def _delaunay(pts):
    """Bowyer-Watson in the XZ plane over ``[(x, z), ...]``; returns index triples."""
    minx = min(p[0] for p in pts)
    maxx = max(p[0] for p in pts)
    minz = min(p[1] for p in pts)
    maxz = max(p[1] for p in pts)
    d = max(maxx - minx, maxz - minz) * 10 + 10
    mx = (minx + maxx) / 2
    mz = (minz + maxz) / 2
    P_ = list(pts) + [(mx - 2 * d, mz - d), (mx, mz + 2 * d), (mx + 2 * d, mz - d)]
    n = len(pts)
    tris = {(n, n + 1, n + 2)}

    def incirc(a, b, c, p):
        ax, az = P_[a]
        bx, bz = P_[b]
        cx, cz = P_[c]
        px, pz = P_[p]
        ax -= px; az -= pz; bx -= px; bz -= pz; cx -= px; cz -= pz
        det = ((ax*ax+az*az)*(bx*cz-cx*bz) - (bx*bx+bz*bz)*(ax*cz-cx*az) + (cx*cx+cz*cz)*(ax*bz-bx*az))
        o = (bx - ax) * (cz - az) - (bz - az) * (cx - ax)
        return det > 0 if o > 0 else det < 0

    for i in range(n):
        bad = [t for t in tris if incirc(t[0], t[1], t[2], i)]
        ec = {}
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (min(e), max(e))
                ec[k] = ec.get(k, 0) + 1
        tris -= set(bad)
        for (a, b), c in ec.items():
            if c == 1:
                tris.add((a, b, i))
    return [t for t in tris if all(v < n for v in t)]


def _seg_cross(p, q, r, s):
    """True PROPER crossing of XZ segments pq / rs (strict: shared endpoints and touches don't count)."""
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(p, q, r), orient(p, q, s)
    d3, d4 = orient(r, s, p), orient(r, s, q)
    return d1 * d2 < 0 and d3 * d4 < 0


def _recover_ring_edges(xz, tri_idx, nring):
    """Constrained-edge recovery: force every rim ring edge ``(i, i+1 mod nring)`` to be an edge of the
    triangulation (Sloan-style diagonal flips). The Delaunay is UNCONSTRAINED -- at a concave corner
    dent it may legally pick the OTHER diagonal of the quad spanning the notch; the centroid keep-filter
    then drops both cover triangles, and the face between the wall top and the grass ships MISSING (the
    seed-42 one-triangle grass hole, in-game 2026-07-13). Returns ``(tris, flips)``; with ``flips == 0``
    the input list is returned UNTOUCHED, so every already-proven mint (island E, the world-forest /
    world-hill byte-identity baseline) rebuilds bit-identically."""
    def edge_map(tris):
        em = collections.defaultdict(list)
        for t in tris:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                em[(min(e), max(e))].append(t)
        return em

    work, flips = None, 0                                # copy lazily: no flips -> tri_idx untouched
    em = edge_map(tri_idx)
    for i in range(nring):
        a, b = i, (i + 1) % nring
        want = (min(a, b), max(a, b))
        guard = 0
        while want not in em:
            guard += 1
            if guard > 4 * len(tri_idx) + 16:
                raise ValueError(f"ring edge {a}-{b} at {xz[a]}-{xz[b]} unrecoverable (flip cascade "
                                 f"did not terminate) -- change --seed/--radius")
            for (c, d), owners in em.items():
                if len(owners) != 2 or a in (c, d) or b in (c, d):
                    continue
                if not _seg_cross(xz[a], xz[b], xz[c], xz[d]):
                    continue
                t1, t2 = owners
                e_ = next(v for v in t1 if v != c and v != d)
                f_ = next(v for v in t2 if v != c and v != d)
                if not _seg_cross(xz[e_], xz[f_], xz[c], xz[d]):
                    continue                             # non-convex quad: this flip would fold
                if work is None:
                    work = list(tri_idx)
                work.remove(t1)
                work.remove(t2)
                work.append((e_, f_, c))
                work.append((e_, f_, d))
                flips += 1
                em = edge_map(work)
                break
            else:
                raise ValueError(f"ring edge {a}-{b} at {xz[a]}-{xz[b]} unrecoverable (no flippable "
                                 f"crossing edge; a point may sit exactly on it) -- change --seed/--radius")
    return (tri_idx, 0) if work is None else (work, flips)


def _inset_ring(ring, d):
    """A closed ``[(x, z), ...]`` ring's rim: each vertex moved ``d`` along its inward normal (the mean of its two
    edges' inward normals), whichever way the ring winds."""
    n = len(ring)
    area2 = sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))
    sgn = 1.0 if area2 > 0 else -1.0                     # > 0: counter-clockwise in (x, z), the inside on the left
    out = []
    for i in range(n):
        (ax, az), (bx, bz), (cx, cz) = ring[i - 1], ring[i], ring[(i + 1) % n]
        nx, nz = 0.0, 0.0
        for (px, pz), (qx, qz) in (((ax, az), (bx, bz)), ((bx, bz), (cx, cz))):
            L = math.hypot(qx - px, qz - pz)
            if L > 0:
                nx += sgn * -(qz - pz) / L               # the left normal (-dz, dx), flipped for a clockwise ring
                nz += sgn * (qx - px) / L
        L = math.hypot(nx, nz)
        if L < 1e-12:
            raise ValueError(f"outline vertex {i} at ({bx:.2f}, {bz:.2f}) folds back on itself")
        out.append((bx + d * nx / L, bz + d * nz / L))
    return out


def _lat_snap(c: float) -> float:
    """``c`` moved onto its nearest 4u lattice line when within :data:`LATTICE_SNAP` of it, else unchanged."""
    g = GRID * round(c / GRID)
    return g if abs(c - g) < LATTICE_SNAP else c


def _lat_cross(a, b, axis: int, g: float, other: int, snap: bool = True):
    """Where the segment ``a``-``b`` meets the lattice line ``axis = g``: computed from the endpoints in a CANONICAL
    order (both tris sharing the edge get the identical floats), the line's coordinate exact, and the ``other``
    coordinate snapped onto a crossing line when the point is that near a lattice corner."""
    if (a[0], a[-1]) > (b[0], b[-1]):                   # (x, z) of a 2D or a 3D point
        a, b = b, a
    t = (g - a[axis]) / (b[axis] - a[axis])
    p = [a[k] + t * (b[k] - a[k]) for k in range(len(a))]
    p[axis] = g
    if snap:
        p[other] = _lat_snap(p[other])
    return tuple(p)


def _lattice_cuts(a, b):
    """THE CELL-CLIPPED LIP, the crest half: the points (in order from ``a``) where the XZ segment ``a -> b`` strictly
    crosses a 4u lattice line, each computed from ``a`` and ``b`` themselves and exactly on its line -- so every cut
    lies ON the crest edge (a crossing through a lattice corner is that corner). The crest's ends are already snapped
    (:func:`_lat_snap`), so a crest vertex is either on a line or clear of it, and the grass clip (:func:`_cell_clip`)
    never has to split a crest edge."""
    hits = []
    for axis in (0, 1):
        if a[axis] == b[axis]:
            continue
        lo, hi = sorted((a[axis], b[axis]))
        for k in range(math.floor(lo / GRID), math.floor(hi / GRID) + 2):
            g = GRID * k
            if (a[axis] - g) * (b[axis] - g) < 0:
                hits.append(((g - a[axis]) / (b[axis] - a[axis]), _lat_cross(a, b, axis, g, 1 - axis, snap=False)))
    cuts = []
    for _t, q in sorted(hits):
        if cuts and math.dist(cuts[-1], q) < 1e-9:      # both families at one point: the lattice corner itself
            cuts[-1] = (GRID * round(q[0] / GRID), GRID * round(q[1] / GRID))
        else:
            cuts.append(q)
    return cuts


def _wall_lean(tris) -> float:
    """The smallest |normal.y| over ``tris`` (1 = level, 0 = vertical)."""
    worst = 1.0
    for a, b, c in tris:
        e1 = [b[q] - a[q] for q in range(3)]
        e2 = [c[q] - a[q] for q in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        worst = min(worst, abs(n[1]) / (math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0))
    return worst


def _plane_y(tri, x: float, z: float) -> float:
    """The height of the plane through ``tri`` at plan point ``(x, z)``."""
    (ax, ay, az), (bx, by, bz), (qx, qy, qz) = tri
    d = (bz - qz) * (ax - qx) + (qx - bx) * (az - qz)
    w0 = ((bz - qz) * (x - qx) + (qx - bx) * (z - qz)) / d
    w1 = ((qz - az) * (x - qx) + (ax - qx) * (z - qz)) / d
    return w0 * ay + w1 * by + (1.0 - w0 - w1) * qy


def _cell_clip(tri):
    """THE CELL-CLIPPED LIP, the grass half: a grass tri ``((x, y, z) x3)`` as ``[(cell, tri), ...]``, one piece per 4u
    cell it covers. A tri inside one cell (the whole lattice interior) is returned untouched; a lip tri spanning a line
    is cut on it (Sutherland-Hodgman, a vertex ON a line kept on both sides), so every piece wears its own cell's
    mains map exactly, no corner clamped. Each cut on a side of the tri is computed from THAT SIDE's own two ends
    (:func:`_lat_cross`, canonical order) -- never from an earlier cut -- so every piece of this tri and of the tri
    across that side holds the identical floats there."""
    xs = [p[0] for p in tri]
    zs = [p[2] for p in tri]
    ci = math.floor(sum(xs) / 3.0 / GRID)
    cj = math.floor(sum(zs) / 3.0 / GRID)
    if all(GRID * ci <= x <= GRID * (ci + 1) for x in xs) and all(GRID * cj <= z <= GRID * (cj + 1) for z in zs):
        return [((ci, cj), tri)]
    sides = ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0]))
    out = []
    for i in range(math.floor(min(xs) / GRID), math.floor(max(xs) / GRID) + 1):
        for j in range(math.floor(min(zs) / GRID), math.floor(max(zs) / GRID) + 1):
            poly = list(zip(tri, ({0, 2}, {0, 1}, {1, 2})))  # (point, the tri sides it lies on)
            for axis, g, sgn in ((0, GRID * i, 1), (0, GRID * (i + 1), -1), (2, GRID * j, 1), (2, GRID * (j + 1), -1)):
                nxt = []
                for k in range(len(poly)):
                    (a, sa_), (b, sb_) = poly[k], poly[(k + 1) % len(poly)]
                    da, db = sgn * (a[axis] - g), sgn * (b[axis] - g)
                    if da >= 0:
                        nxt.append((a, sa_))
                    if da * db < 0:
                        side = sa_ & sb_                 # a stretch of a tri side, else of an earlier cut's line
                        if side:
                            q = _lat_cross(*sides[min(side)], axis, g, 2 - axis)
                        else:                            # a lattice corner inside the tri: y off the tri's plane
                            q = _lat_cross(a, b, axis, g, 2 - axis)
                            q = (q[0], _plane_y(tri, q[0], q[2]), q[2])
                        nxt.append((q, side))
                poly = [q for k, q in enumerate(nxt) if q[0] != nxt[k - 1][0]] if len(nxt) > 1 else nxt
                if len(poly) < 3:
                    break
            poly = [q for q, _s in poly]
            for k in range(1, len(poly) - 1):
                piece = (poly[0], poly[k], poly[k + 1])
                if abs((piece[1][0] - piece[0][0]) * (piece[2][2] - piece[0][2])
                       - (piece[2][0] - piece[0][0]) * (piece[1][2] - piece[0][2])) > 1e-9:
                    out.append(((i, j), piece))
    return out


def _pip(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz):
            if px < x1 + (pz - z1) / (z2 - z1) * (x2 - x1):
                inside = not inside
    return inside


def _clip_poly(poly, axis, val, keep_ge):
    """Sutherland-Hodgman half-plane clip of ``[(x, y, z, u, v), ...]`` (all attributes lerped)."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da = (a[axis] - val) if keep_ge else (val - a[axis])
        db = (b[axis] - val) if keep_ge else (val - b[axis])
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(5)))
    return out


def _split_at_borders(parent_tris):
    """Partition a WORLD-coord tri soup at the 64u block borders: each triangle is clipped to every block
    rectangle it overlaps (the engine raycasts only the containing block -- a straddler is a collision
    hole in its neighbour). ``parent_tris`` = ``[(corners[(x, y, z, u, v)] x3, idall, fam)]``. Returns
    ``{(bx, by): [(corners x3, idall, fam), ...]}`` -- watertight across borders by construction (both
    halves of a straddler share the same cut points)."""
    out = collections.defaultdict(list)
    for corners, idall, fam in parent_tris:
        xs = [c[0] for c in corners]
        zs = [c[2] for c in corners]
        bx0 = math.floor(min(xs) / BLOCK)
        bx1 = math.floor((max(xs) - 1e-9) / BLOCK)
        bz0 = math.floor(min(zs) / BLOCK)
        bz1 = math.floor((max(zs) - 1e-9) / BLOCK)
        for bx in range(bx0, bx1 + 1):
            for bz in range(bz0, bz1 + 1):
                poly = [tuple(c) for c in corners]
                if bx1 > bx0:
                    poly = _clip_poly(poly, 0, bx * BLOCK, True)
                    if len(poly) >= 3:
                        poly = _clip_poly(poly, 0, (bx + 1) * BLOCK, False)
                if bz1 > bz0 and len(poly) >= 3:
                    poly = _clip_poly(poly, 2, bz * BLOCK, True)
                    if len(poly) >= 3:
                        poly = _clip_poly(poly, 2, (bz + 1) * BLOCK, False)
                if len(poly) < 3:
                    continue
                for k in range(1, len(poly) - 1):        # fan triangulation (S-H output is convex)
                    tri = (poly[0], poly[k], poly[k + 1])
                    e1x, e1z = tri[1][0] - tri[0][0], tri[1][2] - tri[0][2]
                    e2x, e2z = tri[2][0] - tri[0][0], tri[2][2] - tri[0][2]
                    if abs(e1z * e2x - e1x * e2z) < 1e-7:
                        continue                         # degenerate sliver from the clip
                    by = -bz - 1                         # world z in [-64(by+1), -64by] <-> block row by
                    out[(bx, by)].append((tri, idall, fam))
    return out


# --------------------------------------------------------------------------- the builder

def build_landmass(*, center, base_radius: float = 24.0, seed=None, lobes: int = 1, land_height: float = 3.2,
                   rim_run: float = 1.0, undulation: float = 0.11, n_corners: int = 3,
                   corner_strength: float = 0.26, n_patches: int = 2, stamps=None,
                   mains_seed: int = 0xF91, stamp_seed: int = 0xF92, ground: str = "grass",
                   relief_amp: float = 0.0, relief_seed=None,
                   beach=None, disc: int = 1, game=None,
                   outline=None, rim_at=None, shore_origin: float = 0.0, cell_lip: bool = True) -> dict:
    """Build a synthetic cliff landmass around WORLD ``center = (cx, cz)`` as per-block ``Terrain``
    meshes. ``lobes=1`` = the perturbed-circle outline; ``lobes>=2`` = the ASYMMETRIC multi-lobe union
    (:func:`mesh.multi_blob_outline` -- elongation, waists, natural corner creases; the shape gate in
    :func:`verify_landmass` checks it against the measured FF9 coastline language). The interior is
    FLAT at ``land_height`` when ``relief_amp=0`` (the default -- explicit local height comes from the
    studied verbs world-hill / world-forest / world-mountain). ``relief_amp>0`` turns ON the OPT-IN
    ambient rolling relief (:func:`grassland.relief`): a deterministic WORLD-XZ value-noise field,
    scaled per ground family (``GROUNDS[..]["relief_scale"]``), faded to exactly 0 at the wall-top rim
    (welds hold) -- the RESURRECTION of the field RETIRED 2026-07-15 (THE DEAD-RELIEF DISCOVERY, a
    block-local-keyed field sampled with world coords; this one is world-keyed BY CONSTRUCTION so the
    frame bug cannot recur and cross-block seams weld). Relief is MUTUALLY EXCLUSIVE with the explicit-
    height verbs per island (the ROLLING-RELIEF ENVELOPE 2.4u gate is the backstop). ``relief_seed``
    defaults from the centre. ``stamps`` = a list / ``"auto"`` (load from the
    install) / ``None`` (hermetic). ``ground`` picks the walkable
    ground family from :data:`grassland.GROUNDS` (the byte-measured TRANSLATION LAWS): ``"grass"``
    (the identity -- bit-frozen) or ``"desert"`` (topo-17 mains + the desert cliff-wall band; meadow
    stamps are grass vocabulary and are disabled). Returns
    ``{"blocks": {(bx, by): BlockMesh}, "outline", "seed", "report"}`` -- run :func:`verify_landmass`
    (or let :func:`landmass` do it) before deploying.

    A CUSTOM OUTLINE (``world-river``, studies/terrain-malleability/watercarry/PLAN.md): ``outline`` is the coast
    ring ``[(x, z), ...]`` at y 0 (either winding) in place of the blob; its rim insets ``rim_run`` along each
    vertex's inward normal. ``rim_at = {index: (x, y, z)}`` fixes the crest above outline vertex ``index``
    exactly (a join column: the kit's wall meets a stock lip there, so its crest is the stock crest, bit for bit).
    ``shore_origin`` shifts the wall's arc-length origin, so the rock band's U lands a given value at a given
    vertex. All three default to the blob mint, byte for byte.

    THE CELL-CLIPPED LIP (``cell_lip=True``, the default; the lip-streak fix, see the comment at the crest cuts): the
    crest is snapped onto and cut at the 4u lattice lines and the grass clipped per cell, so no lip tri wears a
    collapsed mains map. ``cell_lip=False`` is the pre-fix mint byte for byte -- the input the July world-forest /
    world-hill / world-mountain benches were proven on, which their identity nets rebuild. A beach mint always keeps
    the old lip."""
    from . import mesh as M
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    gspec = G.GROUNDS[ground]
    # THE WALL-CONTEXT LAW (family_wall_envelope.py, 2026-07-15): a mint's rim walls are
    # SEA cliffs by construction, and a family whose wall band is measured INTERIOR-ONLY
    # (canyon: red-band wall tris map-wide, 0 open-sea coastal -- the Forgotten's sea
    # cliffs are topo-49 murals) can never dress them in-language.
    #
    # THE GATE FAILS CLOSED (fixed 2026-07-19). This test was `is False`, which let an
    # UNSET key through: scrub/brush/dunes omit wall_coastal entirely, so .get() returned
    # None, `None is False` is False, and the gate silently ALLOWED an island mint for
    # every unmeasured family -- the exact case it exists to catch. An unmeasured family
    # is not a permitted one. Sibling gate transplant.py GroundRetile.for_donor was always
    # `is not True` (fail-closed); the two chokepoints now agree.
    if gspec.get("wall_coastal") is not True:
        why = ("is INTERIOR-ONLY in stock (0 open-sea coastal faces map-wide)"
               if gspec.get("wall_coastal") is False
               else "has NO MEASURED open-sea coastal usage")
        raise ValueError(f"--ground {ground}: THE WALL-CONTEXT LAW -- the {ground} wall "
                         f"band {why}; a minted island's rim is a sea cliff, so a "
                         f"{ground} island is off-language. Use {ground} as interior "
                         f"ground behind a lawful coast instead. Coastal-wall grounds: "
                         f"{sorted(n for n, g in G.GROUNDS.items() if g.get('wall_coastal'))}")

    cx, cz = center
    if seed is None:
        seed = float(int(cx * 7 + cz * 13) % 997)
    if outline is not None:
        if lobes != 1 or beach is not None:
            raise ValueError("a custom outline mints its own ring: lobes and beach do not apply")
        outline = [(float(x), float(z)) for x, z in outline]
        if len(outline) < 3:
            raise ValueError("a custom outline needs at least 3 points")
        radii = None
    elif lobes >= 2:
        outline, radii = M.multi_blob_outline(cx, cz, lobes=lobes, base_radius=base_radius, seed=seed,
                                              undulation=undulation)
    else:
        # adaptive outline density (2026-07-15, the horseshoe-scale benches): the fixed
        # n=96 ring leaves >8u rim segments past ~r60 (undulation stretches arcs; the 8u
        # on-grain gate then fails). max(96, ceil(1.6*r)) keeps n = 96 for EVERY existing
        # radius (r <= 60 -- all frozen identity baselines) and densifies beyond.
        outline, radii = M.blob_outline(cx, cz, base_radius=base_radius, seed=seed, undulation=undulation,
                                        n=max(96, int(math.ceil(base_radius * 1.6))),
                                        n_corners=n_corners, corner_strength=corner_strength)
    nring = len(outline)
    # THE LADDER MINT (islandbeach): a beach arc pulls its rim back to the bank run,
    # so the berm profile replaces the wall there (beach=None = byte-identical mints)
    barc, arc_interior = None, set()
    if beach is not None:
        from . import islandbeach as IB
        barc = IB.plan_arc(outline, (cx, cz), beach["bearing"])
        arc_interior = set(barc["idx"])
        bank_run = float(beach.get("bank_run", 7.0))
    rim = []
    if radii is None:                                    # a custom ring: inset along each vertex's inward normal
        rim = _inset_ring(outline, rim_run)
    else:
        for i, ((ox, oz), r) in enumerate(zip(outline, radii)):
            ux, uz = (ox - cx) / r, (oz - cz) / r
            ins = bank_run if i in arc_interior else rim_run
            rim.append((cx + ux * (r - ins), cz + uz * (r - ins)))
    rim_y = {}                                           # THE JOIN CRESTS: fixed rim points, exact floats
    for i, (x, y, z) in sorted((rim_at or {}).items()):
        if not 0 <= i < nring:
            raise ValueError(f"rim_at index {i} is not on the {nring}-point outline")
        rim[i] = (float(x), float(z))
        rim_y[i] = float(y)
    cell_lip = cell_lip and beach is None
    top0 = [(x, rim_y.get(i, land_height), z) for i, (x, z) in enumerate(rim)]   # the pre-fix crest (see below)
    for i in range(nring if cell_lip else 0):            # THE CELL-CLIPPED LIP: the crest onto the lattice lines it
        if not {i, (i - 1) % nring, (i + 1) % nring} & set(rim_y):  # nearly sits on -- not a join crest (stock's own
            rim[i] = (_lat_snap(rim[i][0]), _lat_snap(rim[i][1]))  # float) nor its neighbours (its wall quads)
    top = [(x, rim_y.get(i, land_height), z) for i, (x, z) in enumerate(rim)]
    bch = None
    if barc is not None:
        bch = IB.build_beach(outline, radii, (cx, cz), barc, ground=ground,
                             land_height=land_height, rim=rim,
                             width=float(beach.get("width", 2.4)),
                             swash=float(beach.get("swash", 4.0)),
                             pins_from=tuple(beach.get("pins_from")
                                             or BEACH_PINS[ground]),
                             disc=disc, game=game)

    # global shore arc-length (continuous across cells -> the rock band chains block to block)
    cum = [0.0] * nring
    for i in range(1, nring):
        cum[i] = cum[i-1] + math.hypot(outline[i][0]-outline[i-1][0], outline[i][1]-outline[i-1][1])
    perim = cum[-1] + math.hypot(outline[0][0]-outline[-1][0], outline[0][1]-outline[-1][1])

    # THE CELL-CLIPPED LIP (the lip-streak fix). A mains UV is its 4u cell's own map, CLAMPED to the cell's window,
    # so a grass tri spanning two cells collapses: two corners clamp onto one edge and the tri wears a rank-1 stripe
    # -- the streaked grass band along the lip of every kit cliff (the live islands carried 23 such tris, cluster C's
    # mint 12). Stock never does it: its 2481 lip-grass tris on topo-58 crests (disc 1) hold the interior grass's
    # own density, Jacobian aspect p50 2.00 / max 5.8, none collapsed, and its crease carries a vertex where it
    # crosses a lattice line (1216 of its 1540 crest verts sit on one). So the kit cuts each crest edge where it
    # crosses a lattice line (the grass Delaunay takes the cuts as ring vertices; the wall tri holding that edge is
    # cut up at them in its own plane, wearing its own rock map -- below) and clips every grass tri at the cell lines
    # (THE TILE-RECT CONTAINMENT LAW's per-cell clip): each grass piece wears its own cell's map, nothing clamped.
    # The outline and every base vertex stay. A BEACH mint (THE LADDER MINT, falsified in game and superseded) keeps
    # the old lip whole: its berm welds to the arc's rim edges, so cutting them would split the berm too.
    crest_cuts = {}
    for i in range(nring if cell_lip else 0):
        j = (i + 1) % nring
        join = bool({i, j} & set(rim_y))
        cuts = _lattice_cuts(rim[i], rim[j])
        if join:
            dented = []
            for (x, z) in cuts:
                on_x = x == GRID * round(x / GRID)       # on an x-line: slide along z, else along x
                for sgn in (1.0, -1.0):
                    q = (x, z + sgn * JOIN_CUT_DENT) if on_x else (x + sgn * JOIN_CUT_DENT, z)
                    if _pip(q[0], q[1], rim):
                        break
                dented.append(q)
            cuts = dented
        if cuts:
            (ax, az), (bx, bz) = rim[i], rim[j]
            ya, yb = top[i][1], top[j][1]
            seg2 = (bx - ax) ** 2 + (bz - az) ** 2
            l_out = (perim if j == 0 else cum[j]) - cum[i]
            crest_cuts[i] = []
            for (x, z) in cuts:
                t = ((x - ax) * (bx - ax) + (z - az) * (bz - az)) / seg2
                crest_cuts[i].append((t, (x, ya if ya == yb else ya + t * (yb - ya), z), cum[i] + t * l_out))
    ring = []                                            # the crest chain: each rim vertex, then its edge's cuts
    for i in range(nring):
        ring.append(top[i])
        ring.extend(p for _t, p, _s in crest_cuts.get(i, ()))

    def grass_fill(ring_pts):
        """The grass over a crest chain: a lattice interior inside it, the Delaunay with the chain's edges
        recovered, the land kept, the big-mint refinement. -> ``(fill, ring_flips, was_land)``."""
        poly = [(p[0], p[2]) for p in ring_pts]

        def was_land(px, pz):
            return _pip(px, pz, poly)

        # grass interior: rim weld ring + a lattice-aligned interior grid
        xs = [p[0] for p in ring_pts]
        zs = [p[2] for p in ring_pts]
        interior = []
        gx = math.floor(min(xs) / GRID) * GRID
        while gx <= max(xs):
            gz = math.floor(min(zs) / GRID) * GRID
            while gz <= max(zs):
                if was_land(gx, gz) and all((gx-tx)**2 + (gz-tz)**2 > (GRID*0.4)**2 for (tx, _, tz) in ring_pts):
                    interior.append((gx, land_height, gz))
                gz += GRID
            gx += GRID
        allpts = list(ring_pts) + interior
        xz = [(p[0], p[2]) for p in allpts]
        tri_idx, flips = _recover_ring_edges(xz, _delaunay(xz), len(ring_pts))
        keep = []
        for (i, j, k) in tri_idx:
            ccx = (xz[i][0] + xz[j][0] + xz[k][0]) / 3
            ccz = (xz[i][1] + xz[j][1] + xz[k][1]) / 3
            keep.append(was_land(ccx, ccz))
        edge_tris = collections.defaultdict(list)
        for t, (i, j, k) in enumerate(tri_idx):
            for e in ((i, j), (j, k), (k, i)):
                edge_tris[(min(e), max(e))].append(t)
        outside, stack = set(), []
        for t, (i, j, k) in enumerate(tri_idx):
            if not keep[t] and any(len(edge_tris[(min(e), max(e))]) == 1 for e in ((i, j), (j, k), (k, i))):
                outside.add(t)
                stack.append(t)
        while stack:                                     # enclosed pinholes (steep-wall XZ shadows) re-fill
            t = stack.pop()
            (i, j, k) = tri_idx[t]
            for e in ((i, j), (j, k), (k, i)):
                for t2 in edge_tris[(min(e), max(e))]:
                    if not keep[t2] and t2 not in outside:
                        outside.add(t2)
                        stack.append(t2)
        for t in range(len(tri_idx)):
            if not keep[t] and t not in outside:
                keep[t] = True
        fill = [(allpts[i], allpts[j], allpts[k]) for t, (i, j, k) in enumerate(tri_idx) if keep[t]]

        # THE BIG-MINT REFINEMENT (conditional, 2026-07-15): a large-radius interior Delaunay
        # can leave a few grass tris with plan edges over the 8u on-grain gate (the
        # horseshoe-scale r69+ mints). Split the longest such edge at its midpoint in BOTH
        # owning tris (identical midpoint floats -> the weld holds) until none remain.
        # STRICTLY a no-op on any mint that never trips it -- every frozen identity baseline
        # (island E, the r31/r50/r52 benches) rebuilds bit-identically.
        _kkm = lambda p: (round(p[0], 3), round(p[2], 3))  # noqa: E731
        for _pass in range(64):
            worst = None
            for tri in fill:
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    d = math.hypot(tri[a][0] - tri[b][0], tri[a][2] - tri[b][2])
                    if d > 8.0 and (worst is None or d > worst[0]):
                        worst = (d, tuple(sorted((_kkm(tri[a]), _kkm(tri[b])))))
            if worst is None:
                break
            owners = []
            for fi, tri in enumerate(fill):
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    if tuple(sorted((_kkm(tri[a]), _kkm(tri[b])))) == worst[1]:
                        owners.append((fi, a, b))
                        break
            if len(owners) != 2:
                raise ValueError(f"an over-8u grass edge has {len(owners)} owner(s) -- "
                                 f"change --seed/--radius")
            (fi0, a0, b0) = owners[0]
            pa, pb = fill[fi0][a0], fill[fi0][b0]
            m = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, (pa[2] + pb[2]) / 2.0)
            done = {fi for fi, _, _ in owners}
            new_fill = [tri for fi, tri in enumerate(fill) if fi not in done]
            for fi, a, b in owners:
                tri = fill[fi]
                c = [v for k2, v in enumerate(tri) if k2 not in (a, b)][0]
                new_fill.append((tri[a], m, c))
                new_fill.append((m, tri[b], c))
            fill = new_fill
        return fill, flips, was_land

    fill, ring_flips, was_land = grass_fill(ring)
    # THE LIP-ONLY CHANGE: the mains field and the meadow stamps are drawn over the PRE-FIX mint's cells (its fill
    # over the uncut crest), so a cell-lip mint's interior is the pre-fix mint's byte for byte -- the same quadrants,
    # the same stamps, every world-forest / world-hill / world-mountain site still lawful -- and only the lip's new
    # cells draw (from their own seeded stream, against the interior's picks).
    fill0, _flips0, was_land0 = grass_fill(top0) if cell_lip else (fill, ring_flips, was_land)

    # OPT-IN rolling relief (world-XZ value noise; default relief_amp=0 => flat => byte-identity).
    r_amp = relief_amp * gspec.get("relief_scale", 1.0)
    r_seed = int(cx * 7 + cz * 13) & 0xFFFFFFFF if relief_seed is None else int(relief_seed)
    rim_keys = {(round(x, 3), round(z, 3)) for (x, _y, z) in ring}

    def _edge_dist(x, z):
        return math.sqrt(min((x - tx) ** 2 + (z - tz) ** 2 for (tx, _, tz) in top0))

    crest_y = {(round(top[i][0], 3), round(top[i][2], 3)): y for i, y in rim_y.items()}
    crest_y.update({(round(p[0], 3), round(p[2], 3)): p[1] for cuts in crest_cuts.values() for _t, p, _s in cuts
                    if p[1] != land_height})          # a cut beside a join crest keeps its lerped height

    def fill_y(x, z):
        if crest_y and (round(x, 3), round(z, 3)) in crest_y:
            return crest_y[(round(x, 3), round(z, 3))]   # a join crest keeps its stock height
        if r_amp == 0.0:
            return land_height                           # flat interior; exact weld at the wall top
        if (round(x, 3), round(z, 3)) in rim_keys:
            return land_height                           # THE RIM WELD: the wall-top ring never moves
        w = G.relief_fade(_edge_dist(x, z))              # fade to 0 at the rim (welds), full inland
        if w == 0.0:
            return land_height
        return land_height + w * G.relief(x, z, seed=r_seed, amp=r_amp)

    # THE CELL-CLIPPED LIP, the grass half: every grass tri as its per-cell pieces (an interior lattice tri is one
    # piece, itself; a beach mint keeps every tri whole, as before).
    pieces = []                                          # [(cell, ((x, y, z) x3))]
    for (a, b, c) in fill:
        tri = tuple((p[0], fill_y(p[0], p[2]), p[2]) for p in (a, b, c))
        if cell_lip:
            pieces.extend(_cell_clip(tri))
        else:
            pieces.append(((math.floor(sum(p[0] for p in tri) / 3.0 / GRID),
                            math.floor(sum(p[2] for p in tri) / 3.0 / GRID)), tri))
    cells_used = sorted({(math.floor((a[0]+b[0]+c[0])/3 / 4), math.floor((a[2]+b[2]+c[2])/3 / 4))
                         for (a, b, c) in fill0}
                        | (set(bch["berm_cells"]) if bch is not None else set()))
    cell_quad, cell_ori = G.assign_mains(cells_used, seed=mains_seed)
    lip_cells = sorted({cell for cell, _tri in pieces} - set(cells_used))
    if lip_cells:
        q2, o2 = G.assign_mains_seeded(lip_cells, cell_quad, cell_ori, seed=mains_seed + LIP_MAINS_SEED)
        cell_quad.update(q2)
        cell_ori.update(o2)

    if ground != "grass":
        stamps = None                                    # meadow stamps are GRASS vocabulary
    if stamps == "auto":
        stamps = G.extract_stamps(disc, game=game)

    def box_ok(box):
        for (i, j) in box:
            for (qx, qz) in ((4*i, 4*j), (4*i + 4, 4*j), (4*i, 4*j + 4), (4*i + 4, 4*j + 4)):
                if any((qx - tx) ** 2 + (qz - tz) ** 2 < 0.25 for (tx, _, tz) in top0):
                    return False
                if not was_land0(qx, qz):
                    return False
        cs = set(box)
        min_x = min(c[0] for c in box) * 4
        max_x = max(c[0] for c in box) * 4 + 4
        min_z = min(c[1] for c in box) * 4
        max_z = max(c[1] for c in box) * 4 + 4
        for (a, b, c) in fill0:
            inside_c = (math.floor((a[0]+b[0]+c[0])/3 / 4), math.floor((a[2]+b[2]+c[2])/3 / 4)) in cs
            for p in (a, b, c):
                p_in = min_x - 1e-6 <= p[0] <= max_x + 1e-6 and min_z - 1e-6 <= p[2] <= max_z + 1e-6
                p_strict = min_x + 1e-6 < p[0] < max_x - 1e-6 and min_z + 1e-6 < p[2] < max_z - 1e-6
                if (inside_c and not p_in) or (not inside_c and p_strict):
                    return False
        return True

    placements, stamped_cell = ([], {}) if not stamps else G.place_stamps(
        cells_used, stamps, box_ok=box_ok, seed=stamp_seed, n_patches=n_patches)

    def shore_s(x, z):
        bi, bd = 0, None
        for i, (ox, oz) in enumerate(outline):
            d = (x - ox) ** 2 + (z - oz) ** 2
            if bd is None or d < bd:
                bd, bi = d, i
        return cum[bi] + shore_origin if shore_origin else cum[bi]

    idw = float(encode_id(topograph=CLIFF_TOPO))
    idg = float(encode_id(topograph=gspec["topo"]))
    parent = []                                          # (corners[(x,y,z,u,v)]x3, idall, fam)

    def up(c0, c1, c2):
        ny = (c1[2]-c0[2])*(c2[0]-c0[0]) - (c1[0]-c0[0])*(c2[2]-c0[2])
        return (c0, c1, c2) if ny > 0 else (c0, c2, c1)

    # the cliff-wall band, shifted per ground family (THE WALL TRANSLATION LAW)
    ru0, ru1 = ROCK_U[0] + gspec["wall_du"], ROCK_U[1] + gspec["wall_du"]
    rv0, rv1 = ROCK_V[0] + gspec["wall_dv"], ROCK_V[1] + gspec["wall_dv"]
    strip_w = ru1 - ru0

    def rock_uvs(pts3):
        s = [shore_s(p[0], p[2]) for p in pts3]
        ref = s[0]
        s = [ref + ((sk - ref + perim / 2.0) % perim) - perim / 2.0 for sk in s]
        ph = [sk * ROCK_DENSITY for sk in s]
        base = math.floor(min(ph) / strip_w)
        off = min(ph) - base * strip_w
        span = max(ph) - min(ph)
        if off + span > strip_w:                         # window-translate: the wrap lands on a tri boundary
            off = max(0.0, strip_w - span)
        # THE WALL V CORNER-ROLE LAW: the V row is the corner's ROLE -- a crest (any height above the sea) is the
        # top row, a base the bottom -- so a join crest at a stock height still lands the language's row. Every
        # blob wall corner sits at 0 or land_height, where role and height give the same float.
        return [(ru0 + min(off + (p - min(ph)), strip_w),
                 rv0 + (1.0 if pt[1] > 0.0 else 0.0) * (rv1 - rv0))
                for p, pt in zip(ph, pts3)]

    wall_skip = bch["wall_skip"] if bch is not None else ()
    for i in range(nring):                               # the wall band
        j = (i + 1) % nring
        if (i, j) in wall_skip:
            continue                                     # the beach profile replaces the wall here
        o0 = (outline[i][0], 0.0, outline[i][1])
        o1 = (outline[j][0], 0.0, outline[j][1])
        r0 = (rim[i][0], top[i][1], rim[i][1])
        r1 = (rim[j][0], top[j][1], rim[j][1])
        # a beach TRANSITION segment mixes rim insets (1u wall -> the 7u bank); the
        # default diagonal can mint a near-vertical sliver, and the two arc ends
        # MIRROR -- pick the diagonal with the healthier worst lean (only ever
        # taken with a beach: existing mints stay byte-identical)
        if bch is not None and (i in arc_interior or j in arc_interior):
            def _min_ny(tris_):
                worst = 1.0
                for t_ in tris_:
                    (a_, b_, c_) = t_
                    e1_ = [b_[q] - a_[q] for q in range(3)]
                    e2_ = [c_[q] - a_[q] for q in range(3)]
                    gn_ = [e1_[1]*e2_[2]-e1_[2]*e2_[1], e1_[2]*e2_[0]-e1_[0]*e2_[2],
                           e1_[0]*e2_[1]-e1_[1]*e2_[0]]
                    gl_ = math.sqrt(sum(q*q for q in gn_)) or 1.0
                    worst = min(worst, abs(gn_[1]) / gl_)
                return worst
            cand_a = (up(o0, o1, r0), up(r0, o1, r1))
            cand_b = (up(o0, o1, r1), up(o0, r1, r0))
            split = cand_a if _min_ny(cand_a) >= _min_ny(cand_b) else cand_b
        elif cell_lip:
            # THE CREST CUTS on the wall: the quad split on one diagonal, as before the fix, and the tri that holds
            # the crest edge cut up along the crest chain r0 -> cuts -> r1, in its own plane (the cuts lie ON the crest
            # edge) and wearing ITS rock map: each piece's UVs are that uncut tri's, interpolated at the cut, the
            # strip's window-translate included -- so the wall shows exactly the rock it did. (Mapping each piece on
            # its own showed in game as seams down the rock: a fan to the other base vertex maps the strip
            # off-affine, and a piece translated alone at the strip's wrap stops matching its neighbour.) The
            # diagonal is the quad's o1-r0 (the pre-fix split) unless that tri would stand steeper than
            # WALL_LEAN_FLOOR where the o0-r1 one leans less: the lattice snap can swing a crest edge over a base
            # vertex at a corner. Beside a join column it is always o1-r0 -- the J gates judge that very plane.
            cuts = crest_cuts.get(i, ())
            chain = [r0] + [p for _t, p, _s in cuts] + [r1]
            ts = [0.0] + [t for t, _p, _s in cuts] + [1.0]
            on_o1 = (up(o0, o1, r0), up(r0, o1, r1))
            on_o0 = (up(o0, o1, r1), up(o0, r0, r1))
            lean1 = _wall_lean(on_o1)
            keep, holder = on_o1 if ({i, j} & set(rim_y) or lean1 >= WALL_LEAN_FLOOR
                                     or lean1 >= _wall_lean(on_o0)) else on_o0
            hold_uv = dict(zip(holder, rock_uvs(holder)))
            (ua, va), (ub, vb) = hold_uv[r0], hold_uv[r1]
            base = next(q for q in holder if q is not r0 and q is not r1)
            at = {q: (ua + t * (ub - ua), va + t * (vb - va)) for q, t in zip(chain, ts)}
            at[base] = hold_uv[base]
            parent.append((tuple((q[0], q[1], q[2], u, v) for q, (u, v) in zip(keep, rock_uvs(keep))), idw, "rock"))
            for m in range(len(chain) - 1):
                piece = up(chain[m], base, chain[m + 1])
                parent.append((tuple((q[0], q[1], q[2], *at[q]) for q in piece), idw, "rock"))
            continue
        else:
            split = (up(o0, o1, r0), up(r0, o1, r1))
        for tri in split:
            uvs = rock_uvs(tri)
            parent.append((tuple((p[0], p[1], p[2], u, v) for p, (u, v) in zip(tri, uvs)), idw, "rock"))

    for cell, tri in pieces:                             # the grass (mains cells; stamped cells replaced below)
        if cell in stamped_cell:
            continue
        quad, ori = cell_quad[cell], cell_ori[cell]
        tri = up(*tri)
        corners = tuple((p[0], p[1], p[2], *G.ground_uv(p[0], p[2], cell, quad, ori, ground))
                        for p in tri)
        parent.append((corners, idg, "main"))
    for corners, fam in G.stamp_geometry(placements):    # verbatim meadow stamps (exact real corner UVs)
        pts = [(x, fill_y(x, z), z) for (x, z, _, _) in corners]
        uvv = [(u, v) for (_, _, u, v) in corners]
        order = up(*pts)
        remap = [pts.index(p) for p in order]
        parent.append((tuple((p[0], p[1], p[2], *uvv[r]) for p, r in zip(order, remap)), idg, fam))

    if bch is not None:                                  # THE LADDER MINT's terrain half
        from . import islandbeach as IB
        id_sand = float(encode_id(topograph=IB.SAND_TOPO[ground]))
        for item, famname in bch["terrain"]:
            if famname == "berm":                        # the island's own ground family
                ccx = sum(p[0] for p in item) / 3.0
                ccz = sum(p[2] for p in item) / 3.0
                cell = (math.floor(ccx / 4), math.floor(ccz / 4))
                quad, ori = cell_quad[cell], cell_ori[cell]
                corners = tuple((p[0], p[1], p[2],
                                 *G.ground_uv(p[0], p[2], cell, quad, ori, ground))
                                for p in item)
                parent.append((corners, idg, "main"))
            else:                                        # sand: uvs already assigned
                parent.append((item, id_sand, "sand"))

    by_block = _split_at_borders(parent)

    # THE GRID-BOUNDS GATE, seam-aware since 2026-08-27 (was: 2026-07-21, the dunes off-grid
    # incident). ROWS stay EDGED: overrides on rows outside 0..19 are dead files and every census
    # there is vacuously clean -- the dunes refusal is unchanged. COLUMNS now WRAP: the engine's
    # world is an x-torus (WMWorld.Wrap shifts the whole world in 64u steps mod 1536; block
    # identity is only ever the wrapped InitialX in [0,24)), so an unwrapped column -1 is a lawful
    # mint into column 23 -- THE SEAM-WRAP GAP the composed-world judge named as the unblock for
    # the (48,-240) pocket. Keys stay UNWRAPPED through build+verify (texgates' world-coord
    # round-trip, sea-plan adjacency-by-key-increment, and the census centre check all need the
    # continuous frame); the label wraps once, at the deploy stage in landmass(). The engine
    # invariant that remains: exactly ONE Terrain mesh per wrapped cell, so two distinct unwrapped
    # columns colliding on one wrapped label (footprint >= 24 columns = the whole 1536u world)
    # must refuse.
    off_rows = sorted(blk for blk in by_block if not (0 <= blk[1] < M.GRID_ROWS))
    if off_rows:
        raise ValueError(
            f"landmass footprint {sorted(by_block)} spills OFF the {M.GRID_COLS}x{M.GRID_ROWS} "
            f"overworld block grid at rows {sorted({b[1] for b in off_rows})} (rows 0..{M.GRID_ROWS - 1}; "
            f"world z 0..{M.GRID_WORLD_Z_MIN}). The engine never streams off-grid rows (z wraps "
            f"engine-side, but edged-z is kit policy). Shift center=({cx:.0f},{cz:.0f}) / "
            f"base_radius={base_radius} so every touched block is on the map.")
    label_owner = {}
    for ublk in sorted(by_block):
        lab = (M.wrap_block_col(ublk[0]), ublk[1])
        prev = label_owner.setdefault(lab, ublk)
        if prev != ublk:
            raise ValueError(
                f"landmass footprint wraps onto itself: unwrapped columns {prev[0]} and "
                f"{ublk[0]} both land on wrapped cell {lab} -- the footprint spans >= "
                f"{M.GRID_COLS} columns (the whole 1536u world). One Terrain mesh per cell is "
                f"an engine invariant (WMWorldPrefabMaker); shrink base_radius={base_radius}.")

    # per-block BlockMesh in block-LOCAL coordinates, with globally-smoothed welded normals
    gpos, gtris, gmeta = [], [], []                      # the split soup, still in world coords
    for blk, items in sorted(by_block.items()):
        for corners, idall, fam in items:
            base = len(gpos)
            for c in corners:
                gpos.append([c[0], c[1], c[2]])
            gtris.append([base, base + 1, base + 2])
            gmeta.append((blk, idall, fam, [(c[3], c[4]) for c in corners]))
    gnrm = G.smooth_normals(gpos, gtris, range(len(gpos)))

    blocks = {}
    for blk in sorted(by_block):
        bx, by = blk
        pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
        for tidx, tri in enumerate(gtris):
            tblk, idall, fam, uvv = gmeta[tidx]
            if tblk != blk:
                continue
            base = len(pos)
            for vid, (u, v) in zip(tri, uvv):
                w = gpos[vid]
                pos.append([w[0] - BLOCK * bx, w[1], w[2] + BLOCK * (by + 1) - BLOCK])
                nrm.append(list(gnrm[vid]))
                uv.append([u, v])
                tan.append([idall, 0.0, 0.0, 1.0])
                flat.append(len(pos) - 1)
            tris.append([base, base + 1, base + 2])
        blocks[blk] = BlockMesh(name=f"Block[{bx}][{by}] Terrain", disc=disc, x=bx, y=by, lod="0_1",
                                vcount=len(pos), stride=48,
                                channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                                chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                                flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])

    return {"blocks": blocks, "outline": outline, "rim": rim, "rim_y": rim_y, "shore_origin": shore_origin,
            "crest_cuts": sum(len(c) for c in crest_cuts.values()),
            "seed": seed, "center": (cx, cz),
            "was_land": was_land, "top": top, "placements": placements, "ring_edge_flips": ring_flips,
            "ground": ground, "beach": bch,
            # THE MINTED (quad,ori) FIELD -- the very per-4u-cell window assignment every mains tri
            # above was emitted through (G.ground_uv(..., cell, quad, ori, ground)).  Handed to
            # texgates.one_window_gate by verify_landmass: THE ONE-WINDOW-PER-TRI LAW can only be
            # judged against the field the generator actually minted with (a blind lattice search
            # reproduces <20% of lawful stock ground -- see texgates' calibration docstring).
            "mains_field": {cell: (cell_quad[cell], cell_ori[cell]) for cell in cell_quad},
            "world": {"pos": gpos, "tris": gtris, "meta": gmeta, "nrm": gnrm}}


#: THE LIP-STREAK DETECTOR's thresholds: a flat (|normal.y| > 0.5), real (area > 0.05 u^2) Terrain tri whose in-plane
#: 3D->UV Jacobian has a singular-value ratio over this is the streaked grass band (its map near rank 1). Stock's
#: disc-1 lip grass peaks at 5.8 (p50 2.00, the atlas's own 2:1); the pre-fix kit lip reached 1e33.
LIP_STREAK_RATIO = 20.0


def uv_streak(pts, uvs, *, ratio: float = LIP_STREAK_RATIO, min_area: float = 0.05, min_ny: float = 0.5):
    """THE LIP-STREAK DETECTOR on one tri: its singular-value ratio when it is flat, real and over ``ratio`` (inf when
    the map is rank 1 outright), else ``None``. ``pts`` = three (x, y, z), ``uvs`` = three (u, v)."""
    (ax, ay, az), (bx, by, bz), (qx, qy, qz) = pts
    e1, e2 = (bx - ax, by - ay, bz - az), (qx - ax, qy - ay, qz - az)
    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
    nl = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    if nl / 2.0 <= min_area or abs(n[1]) / nl <= min_ny:
        return None
    l1 = math.sqrt(e1[0] ** 2 + e1[1] ** 2 + e1[2] ** 2)
    t1 = tuple(c / l1 for c in e1)                       # an in-plane orthonormal frame (t1, t2)
    t2 = (n[1] * t1[2] - n[2] * t1[1], n[2] * t1[0] - n[0] * t1[2], n[0] * t1[1] - n[1] * t1[0])
    t2 = tuple(c / nl for c in t2)
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]  # noqa: E731
    e11, e12, e21, e22 = dot(e1, t1), dot(e2, t1), dot(e1, t2), dot(e2, t2)
    det_e = e11 * e22 - e12 * e21
    (u0, v0), (u1, v1), (u2, v2) = uvs
    d11, d12, d21, d22 = u1 - u0, u2 - u0, v1 - v0, v2 - v0
    j11 = (d11 * e22 - d12 * e21) / det_e                # J = D E^-1
    j12 = (-d11 * e12 + d12 * e11) / det_e
    j21 = (d21 * e22 - d22 * e21) / det_e
    j22 = (-d21 * e12 + d22 * e11) / det_e
    f2 = j11 ** 2 + j12 ** 2 + j21 ** 2 + j22 ** 2       # sigma1^2 + sigma2^2
    dj = abs(j11 * j22 - j12 * j21)                      # sigma1 * sigma2
    root = math.sqrt(max(f2 * f2 - 4.0 * dj * dj, 0.0))
    s1, s2 = math.sqrt((f2 + root) / 2.0), math.sqrt(max((f2 - root) / 2.0, 0.0))
    r = s1 / s2 if s2 > 0.0 else math.inf
    return r if r > ratio else None


def lip_streak_tris(built: dict, **kw) -> list:
    """Every :func:`uv_streak` tri of a :func:`build_landmass` result, as ``[(ratio, area, (cx, cz), fam), ...]``."""
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    out = []
    for tri, (_blk, _idall, fam, uvv) in zip(gtris, gmeta):
        pts = [gpos[v] for v in tri]
        r = uv_streak(pts, uvv, **kw)
        if r is not None:
            e1 = [pts[1][k] - pts[0][k] for k in range(3)]
            e2 = [pts[2][k] - pts[0][k] for k in range(3)]
            area = 0.5 * math.sqrt((e1[1] * e2[2] - e1[2] * e2[1]) ** 2 + (e1[2] * e2[0] - e1[0] * e2[2]) ** 2
                                   + (e1[0] * e2[1] - e1[1] * e2[0]) ** 2)
            out.append((r, area, (sum(p[0] for p in pts) / 3.0, sum(p[2] for p in pts) / 3.0), fam))
    return out


def verify_landmass(built: dict, *, sea_plane=None, land_height: float = 3.2,
                    texgates: bool = True, enforce_texgates: bool = False,
                    allow_texgates: bool = False) -> dict:
    """The offline gate suite over a :func:`build_landmass` result: watertight (cracks), the
    closed-surface once-edge audit (``open_edges`` / ``missing_faces`` -- no boundary above the y=0
    sea skirt), winding (down-facing / engine walk-filter fails, wall AND grass), on-grain (grass
    tris > 8u), footprint holes, per-family UV bounds, and -- when ``sea_plane`` is given -- the
    ENGINE PLACEMENT census per block
    (MISS must be 0 everywhere; the centre must ground on walkable grass). Returns a report dict with
    ``clean``.

    THE TEXTURE + SEA GATES (``texgates=True``, the default -- the Rung-F UV/relief fold-back,
    2026-07-25): :func:`ff9mapkit.world.texgates.texture_sea_gates` also runs over the just-minted
    BlockMesh set and lands in ``report["texgates"]`` -- zero-uv-area, THE ONE-WINDOW-PER-TRI LAW
    (judged against ``built["mains_field"]``, the field this very mint emitted through),
    family mains-rect membership, and -- only when ``sea_plane`` is given -- the 3-predicate sea
    gate. They follow :func:`~ff9mapkit.world.transplant.wang_carry_gate`'s policy: **WARN by
    default** (``ok`` stays True, ``warn`` surfaces the finding, ``clean`` is unaffected),
    ``enforce_texgates=True`` folds a failure into ``clean``, ``allow_texgates=True`` waives even
    then. Purely read-only -- it mutates no byte of ``built`` and changes no output byte.

    ``lip_streaks`` counts :func:`lip_streak_tris` (THE LIP-STREAK DETECTOR, report-only: a cell-lip mint reads 0;
    a ``cell_lip=False`` or beach mint can read more, and ``clean`` does not move for it)."""
    from .extract import decode_id
    gpos = built["world"]["pos"]
    gtris = built["world"]["tris"]
    gmeta = built["world"]["meta"]
    ground = built.get("ground", "grass")
    gspec = G.GROUNDS[ground]
    g_topo = gspec["topo"]
    main_region = G.ground_main_region(ground)
    rock_lo_u = ROCK_U[0] + gspec["wall_du"]
    rock_hi_u = ROCK_U[1] + gspec["wall_du"]
    rock_lo_v = min(ROCK_V) + gspec["wall_dv"]
    rock_hi_v = max(ROCK_V) + gspec["wall_dv"]
    report = {}
    seen = {}
    cracks = 0
    for v in gpos:
        k = (round(v[0], 3), round(v[2], 3))
        if k in seen and abs(seen[k] - v[1]) > 1e-3:
            cracks += 1
        else:
            seen[k] = v[1]
    down = steep = big = oob = 0
    ground_slopes = []                                   # per-tri slope (deg) over walkable ground topo (relief gate)
    for tidx, tri in enumerate(gtris):
        a, b, c = gpos[tri[0]], gpos[tri[1]], gpos[tri[2]]
        ny2 = (b[2]-a[2])*(c[0]-a[0]) - (b[0]-a[0])*(c[2]-a[2])
        if ny2 <= 0:
            down += 1
        e1 = [b[k]-a[k] for k in range(3)]
        e2 = [c[k]-a[k] for k in range(3)]
        gn = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]]
        gl = math.sqrt(sum(q*q for q in gn)) or 1.0
        if gn[1]/gl <= 0.1:
            steep += 1                                   # the engine's walkmesh filter would drop it
        _, idall, fam, uvv = gmeta[tidx]
        topo = decode_id(int(round(idall)))["topograph"]
        if topo == g_topo:
            ground_slopes.append(math.degrees(math.acos(max(-1.0, min(1.0, abs(gn[1]) / gl)))))
            e = max(math.dist((a[0], a[2]), (b[0], b[2])), math.dist((b[0], b[2]), (c[0], c[2])),
                    math.dist((a[0], a[2]), (c[0], c[2])))
            if e > 8:
                big += 1
        lo_u, lo_v, hi_u, hi_v = (rock_lo_u - 1e-3, rock_lo_v - 1e-3, rock_hi_u + 1e-3, rock_hi_v + 1e-3) \
            if fam == "rock" else (main_region if fam == "main"
                                   else G.FAM_REGION.get(fam, G.FAM_REGION["?"]))
        for (u, v) in uvv:
            if not (lo_u - 1e-4 <= u <= hi_u + 1e-4 and lo_v - 1e-4 <= v <= hi_v + 1e-4):
                oob += 1
    # footprint holes: sample the rim polygon interior against the soup's XZ coverage
    was_land = built["was_land"]
    top = built["top"]
    xs = [p[0] for p in top]
    zs = [p[2] for p in top]
    holes = tot = 0
    for i in range(30):
        for j in range(30):
            px = min(xs) + (max(xs) - min(xs)) * i / 29
            pz = min(zs) + (max(zs) - min(zs)) * j / 29
            if not was_land(px, pz):
                continue
            tot += 1
            hit = False
            for tri in gtris:
                a, b, c = gpos[tri[0]], gpos[tri[1]], gpos[tri[2]]
                d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
                if abs(d) < 1e-9:
                    continue
                w0 = ((b[2]-c[2])*(px-c[0]) + (c[0]-b[0])*(pz-c[2])) / d
                w1 = ((c[2]-a[2])*(px-c[0]) + (a[0]-c[0])*(pz-c[2])) / d
                if w0 >= -.02 and w1 >= -.02 and 1-w0-w1 >= -.02:
                    hit = True
                    break
            if not hit:
                holes += 1
    # THE CLOSED-SURFACE GATE (the seed-42 grass sliver, 2026-07-13): a position-welded once-edge
    # (an edge used by exactly one triangle) may lie ONLY on the sea-skirt boundary -- the y=0
    # outline ring, where the wall base lawfully meets the separate Sea4 plane part. Any once-edge
    # with a vertex above the waterline is a real crack/hole; a closed 3-cycle of them is the
    # one-missing-face signature the sampled ``holes`` grid cannot see (the shipped sliver was
    # ~1.7 u^2 -- far under the ~1.4u sample spacing).
    ecnt = collections.Counter()
    for tri in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in tri]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue                                 # a rounded-zero-length key is not an edge: the
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1  # border clip mints ~0.0005u hairline
            # cut-vert pairs (real surface per THE HAIRLINE LAW; island E carries one at x=384)
    # a beach terrain lawfully ENDS at the sand seam (welded by the separate Beach1
    # part) -- once-edges with BOTH verts on the S chain are the beach analogue of
    # the y=0 skirt ring
    beach_seam = set()
    if built.get("beach"):
        beach_seam = {(round(p[0], 3), round(p[1], 3), round(p[2], 3))
                      for p in built["beach"]["chains"]["S"]}
    open_bad = [e for e, n in ecnt.items() if n == 1
                and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)
                and not (e[0] in beach_seam and e[1] in beach_seam)]
    open_adj = collections.defaultdict(set)
    for ea, eb in open_bad:
        open_adj[ea].add(eb)
        open_adj[eb].add(ea)
    miss_faces = {tuple(sorted((p, q, r))) for p in open_adj for q in open_adj[p] for r in open_adj[q]
                  if r != p and p in open_adj[r]}
    # THE RELIEF SLOPE ENVELOPE (2026-07-21): the walkable ground's per-tri slope p99 must stay under
    # the measured lowland-grass ceiling MAX_FLANK (28.6 deg). A FLAT mint reads p99 = 0 (every ground
    # tri is horizontal), so this is vacuously clean for every frozen identity baseline; it only bites
    # an OPT-IN relief mint whose amplitude was pushed off the calibrated band.
    ss = sorted(ground_slopes)
    if ss:
        kk = (len(ss) - 1) * 0.99
        lo = int(math.floor(kk))
        main_slope_p99 = ss[lo] if lo >= len(ss) - 1 else ss[lo] + (ss[lo + 1] - ss[lo]) * (kk - lo)
    else:
        main_slope_p99 = 0.0
    report.update(cracks=cracks, down_facing=down, walk_filter_fails=steep, grass_over_8u=big,
                  uv_out_of_region=oob, holes=holes, holes_sampled=tot,
                  open_edges=len(open_bad), missing_faces=len(miss_faces),
                  main_slope_p99=round(main_slope_p99, 2), lip_streaks=len(lip_streak_tris(built)))

    # the coastline SHAPE gate: the generated outline must sit inside the measured FF9 language
    # (real disc-1 coasts: med turn 22 deg/8u, corner(45-80) 15%, acute(>=80) 7%)
    from . import mesh as _M
    shape = _M.outline_shape_stats(built["outline"])
    shape["ok"] = 8.0 <= shape["med_turn"] <= 35.0 and shape["acute"] <= 0.12 and shape["max_turn"] < 150.0
    report["shape"] = shape

    def _meshlist(blk, bm):
        """The block's full deploy part list (Terrain + the sea/beach parts) in the engine's
        scan order (``placement.build_meshlist`` owns the sort -- audit rec 11; the beach
        branch used to hand-append Beach1 LAST, after every sea) -- ONE construction shared
        by the placement census and THE TEXTURE + SEA GATES below. Requires ``sea_plane``."""
        from . import mesh as M
        bx, by = blk
        beach = built.get("beach")
        hid = lambda nm: M.hidden_block_mesh(name=nm, disc=bm.disc, x=bx, y=by)  # noqa: E731
        parts = {"Object": hid("Object"), "Terrain": bm,
                 "Sea1": hid("Sea1"), "Sea2": hid("Sea2"), "Sea3": hid("Sea3"),
                 "Sea4": _cut_plane(sea_plane, bx, by, frozenset(), bm), "Sea5": hid("Sea5")}
        if beach is not None and tuple(beach["block"]) == blk:
            parts.update(
                Sea1=_part_blockmesh("Sea1", blk, beach["sea1"], bm.disc),
                Sea2=_part_blockmesh("Sea2", blk, beach["wash"], bm.disc),
                Sea4=_cut_plane(sea_plane, bx, by, beach["sea4_cut"], bm),
                Sea5=_part_blockmesh("Sea5", blk, beach["sea5"], bm.disc),
                Beach1=_part_blockmesh("Beach1", blk, beach["foam"], bm.disc))
        return P.build_meshlist(parts)

    # THE TEXTURE + SEA GATES (read-only; WARN unless enforce_texgates). The sea half needs the
    # real part list, so it runs only when a sea_plane was supplied -- the texture half always does.
    texgate_list = []
    if texgates:
        from . import texgates as TG
        blocks_in = ({blk: _meshlist(blk, bm) for blk, bm in built["blocks"].items()}
                     if sea_plane is not None
                     else {blk: [("Terrain", bm)] for blk, bm in built["blocks"].items()})
        texgate_list = TG.texture_sea_gates(blocks_in, set(built["blocks"]),
                                            quad_ori=built.get("mains_field"),
                                            enforce=enforce_texgates, allow=allow_texgates,
                                            sea=sea_plane is not None)
        report["texgates"] = texgate_list

    place_reports = {}
    if sea_plane is not None:
        cx, cz = built["center"]
        for blk, bm in built["blocks"].items():
            bx, by = blk
            meshlist = _meshlist(blk, bm)
            cen = P.census(meshlist, frame="block_local")
            entry = {"counts": cen["counts"], "miss": len(cen["miss"]),
                     "stacked": len(cen["stacked"])}
            lx, lz = cx - BLOCK * bx, cz + BLOCK * (by + 1) - BLOCK
            if 0.0 <= lx <= BLOCK and -BLOCK <= lz <= 0.0:
                gy, nm, _, topo = P.place(meshlist, lx, lz)
                entry["centre"] = (round(gy, 2), nm, topo)
                entry["centre_ok"] = nm == "Terrain" and topo == g_topo
            place_reports[blk] = entry
        report["placement"] = place_reports
    report["clean"] = (cracks == 0 and down == 0 and steep == 0 and big == 0 and oob == 0 and holes == 0
                       and len(open_bad) == 0 and shape["ok"] and main_slope_p99 <= MAX_FLANK + 1e-6
                       and all(e["miss"] == 0 and e.get("stacked", 0) == 0
                               and e.get("centre_ok", True) for e in place_reports.values())
                       # WARN-default: every texgate's own ``ok`` is True unless enforce_texgates
                       and all(g["ok"] for g in texgate_list))
    return report


# --------------------------------------------------------------------------- deploy

def _part_blockmesh(part, blk, tris, disc, label_x=None):
    """World-frame ``[(pos, nrm, uv, tan) x3]`` tris -> a block-local BlockMesh
    (the beach's Sea1/Sea2/Sea5/Beach1 parts). ``blk`` is the UNWRAPPED key the local conversion
    runs against; ``label_x`` (default: ``blk[0]``) is the wrapped column the identity carries."""
    from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    bx, by = blk
    lx = bx if label_x is None else label_x
    pos, nrm, uv, tan, flat, tidx = [], [], [], [], [], []
    for t3 in tris:
        base = len(pos)
        for (p, n, u, t4) in t3:
            pos.append([p[0] - BLOCK * bx, p[1], p[2] + BLOCK * by])
            nrm.append(list(n))
            uv.append([u[0], u[1]])
            tan.append(list(t4))
            flat.append(len(pos) - 1)
        tidx.append([base, base + 1, base + 2])
    return BlockMesh(name=f"Block[{lx}][{by}] {part}", disc=disc, x=lx, y=by, lod="0_1",
                     vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tidx, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def _xz_tri_cover(bm):
    """The block's Terrain triangles projected to LOCAL XZ, as ``(minx, maxx, minz, maxz, a, b, c)``
    rows -- the footprint test used by THE SEA4-UNDER-LAND LAW. ``bm`` and the Sea4 plane share the
    block-local frame (both span x 0..BLOCK, z -BLOCK..0), so no world transform is needed."""
    from .extract import CH_POS
    P = bm.chan_arrays[CH_POS]
    rows = []
    for tri in bm.tris:
        a, b, c = (P[tri[0]][0], P[tri[0]][2]), (P[tri[1]][0], P[tri[1]][2]), (P[tri[2]][0], P[tri[2]][2])
        rows.append((min(a[0], b[0], c[0]), max(a[0], b[0], c[0]),
                     min(a[1], b[1], c[1]), max(a[1], b[1], c[1]), a, b, c))
    return rows


def _xz_inside(cover, x, z) -> bool:
    """Is ``(x, z)`` inside any triangle of ``cover``? Barycentric, sign-agnostic (the land mesh's
    winding is not guaranteed), with an AABB reject first."""
    for minx, maxx, minz, maxz, a, b, c in cover:
        if x < minx or x > maxx or z < minz or z > maxz:
            continue
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (z - c[1])) / d
        w1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (z - c[1])) / d
        if w0 >= -1e-9 and w1 >= -1e-9 and (1.0 - w0 - w1) >= -1e-9:
            return True
    return False


def _sea4_override(plane, bx, by, cut_cells, under, wbx):
    """The block's Sea4 override: the cut plane, or -- when the land footprint consumed the WHOLE
    plane -- a hidden blanking stub.

    THE INTERIOR-BLOCK SEA (found by the first continent-scale mint, r144 at (1520,-464),
    2026-08-28): every prior mint (r20..r72) kept some sea in every footprint block, so
    ``_cut_plane`` never came back empty and the 0-vert mesh sailed into ``write_ff9mesh``'s
    loader-range refusal mid-deploy, stranding a partial write. A fully-interior land block's
    correct sea is NONE -- but the file must still exist: the cell's ``Donor.txt`` diverts it to
    the donor prefab, and an UN-overridden part FREE-RIDES that donor's own geometry verbatim
    (the free-ride trap), which here would render the donor's real sea beneath our land. The
    blanking stub is exactly how ``HIDDEN_PARTS`` already suppresses the donor's other parts."""
    from . import mesh as M
    sea = _cut_plane(plane, bx, by, cut_cells, under, label_x=wbx)
    if sea.vcount == 0:
        return M.hidden_block_mesh(name=f"Block[{wbx}][{by}] Sea4", disc=plane.disc, x=wbx, y=by)
    return sea


def _cut_plane(plane, bx, by, cut_cells, under=None, label_x=None):
    """The block's full-cell Sea4 plane MINUS the beach-claimed lattice cells (the ladder owns them:
    undropped deep tiles under new bands are off-language) and MINUS everything under ``under``'s
    footprint.

    **THE SEA4-UNDER-LAND LAW.** A deep-sea plane must never span beneath land. The ground query
    (:func:`ff9mapkit.world.placement.place`) rejects any triangle hit ABOVE the ray origin, and a
    sea-level actor casts from only ``y + 2.34375`` -- so on land standing at y=3.2 every Terrain
    tri is rejected and the ray falls through to whatever sits underneath. Leave the plane whole and
    it reads deep sea (topo 57), which is why a boat sailed straight through the Rung-5a island.
    Cut it and the sea-level ray MISSES instead, and a water-area miss IS the engine's invisible
    vehicle wall (placement.py rule 2, airship-proven). This is why the fix is NOT a beach: cliff
    coasts and beach coasts alike simply must not have ocean underneath them."""
    from .extract import CH_POS, CH_NRM, CH_UV, CH_TAN
    ca = plane.chan_arrays
    cover = _xz_tri_cover(under) if under is not None else None
    pos, nrm, uv, tan, flat, tidx = [], [], [], [], [], []
    for tri in plane.tris:
        cxl = sum(ca[CH_POS][j][0] for j in tri) / 3.0
        czl = sum(ca[CH_POS][j][2] for j in tri) / 3.0
        cxw, czw = cxl + BLOCK * bx, czl - BLOCK * by
        if (math.floor(cxw / 4.0), math.floor(czw / 4.0)) in cut_cells:
            continue
        # CONSERVATIVE cut: drop the tri only when ALL THREE corners are under land. A centroid test
        # removes tris that overhang the shoreline and tears a query/render hole just outside the
        # land -- caught by the placement census (MISS) the first time this was written that way.
        if cover is not None and all(_xz_inside(cover, ca[CH_POS][j][0], ca[CH_POS][j][2]) for j in tri):
            continue
        base = len(pos)
        for j in tri:
            pos.append(list(ca[CH_POS][j]))
            nrm.append(list(ca[CH_NRM][j]))
            uv.append(list(ca[CH_UV][j]))
            tan.append(list(ca[CH_TAN][j]))
            flat.append(len(pos) - 1)
        tidx.append([base, base + 1, base + 2])
    # THE DUAL FRAME (seam wrap): the cut-cell reconstruction above needs the UNWRAPPED column
    # (cxw must land in the same continuous frame as the beach's sea4_cut cells), while the
    # returned identity must carry the WRAPPED label the engine can actually probe.
    lx = bx if label_x is None else label_x
    return dataclasses.replace(plane, x=lx, y=by, name=f"Block[{lx}][{by}] Sea4",
                               vcount=len(pos),
                               chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                               flat_index=flat, tris=tidx, raw_vbuf=b"", raw_ibuf=b"")


def _sea_plane(disc: int = 1, game=None):
    from . import extract as X
    from . import mesh as M
    return M.fill_missing_grid_quads(X.read_block(*SEA_PLANE_SOURCE, disc=disc, part="sea4", game=game))


def _real_block_parts(blk, *, disc: int = 1, lod: str = "0_1", game=None) -> dict:
    """The REAL game's per-block mesh assets at ``blk`` as ``{part: tri_count}`` (empty = true open
    ocean, which renders from the shared SeaBlockPrefab). Non-empty means the block loads its OWN
    prefab -- and a sea-only prefab has no ``Terrain`` transform for the loose override to bind to,
    so an island fragment deployed there silently never renders (the (6,17) canvas incident,
    2026-07-12)."""
    from .transplant import PARTS, world_tris
    occ = {}
    for p in PARTS:
        n = len(world_tris(blk[0], blk[1], p, disc=disc, lod=lod, game=game))
        if n:
            occ[p] = n
    return occ


def landmass(mod_folder: str, *, center=None, cell=None, base_radius: float = 24.0, seed=None, lobes: int = 1,
             land_height: float = 3.2, rim_run: float = 1.0, n_patches: int = 2, flat: bool = False,
             ground: str = "grass", relief_amp: float = 0.0, relief_seed=None,
             beach=None, donor=DEFAULT_DONOR, disc: int = 1, lod: str = "0_1",
             game=None, dry_run: bool = False, skip_mirror: bool = False,
             target_disc: int | None = None, all_sea_target: bool = False,
             coastnav: bool = True, coastnav_policy: str = "land-anywhere",
             allow_overwrite: bool = False, area: int | None = None) -> dict:
    """Build, GATE, and deploy a synthetic landmass. ``cell=(bx, by)`` centres it on that block;
    ``center=(wx, wz)`` places it anywhere (a multi-block landmass splits per block automatically).
    Raises ``ValueError`` with the report if any gate fails. Deploys per touched block: the ``Terrain``
    override + a hole-patched full-cell deep ``Sea4`` + blanked ``Object``/``Sea1/2/3/5`` + a ``Donor.txt``
    naming ``donor`` (must carry a Terrain transform for the s34 divert), then auto-mirrors the written
    overrides to Disc4 (THE DISC-4 GAP; pass ``skip_mirror=True`` to opt out). RELAUNCH / re-enter the world
    for a first-time block.

    THE COAST-NAV EMITTER DEFAULT (``coastnav``, on by default): after the deploy, the island's own
    sea overrides are stamped with vehicle navigation classes (:func:`ff9mapkit.world.coastnav.stamp`
    -- keel-block under land, the 3.5u standoff belt, landability per ``coastnav_policy``). Without it
    a fresh mint ships boat-permeable straddling triangles, no standoff and no get-off classes -- the
    R5d/R5e lesson, re-derived from scratch once already. Runs BEFORE the disc-4 mirror so the mirror
    carries the stamped bytes. ``coastnav_policy``: ``"land-anywhere"`` (default -- the Southern
    Ring's plateau-isle property) or ``"cliffs-refuse"`` (stock grammar: a shore with no low ground
    can be sailed to but never disembarked on).

    THE AREA (terrain study policy R1): the island's ground -- Terrain and the Beach1 sand -- is stamped with ``area``,
    default :data:`ff9mapkit.world.mesh.SAFE_ROAD_AREA` (14, the safe road: no random battles on kit ground under the
    s60 engine patch; reads "Lindblum Plateau"). The open-ocean target law means an island never joins stock land, so
    there is no host area to inherit. Its sea keeps area 0, as the stock ocean does. Mints used to stamp area 0: zone 0,
    Mist Continent battles on the grass and "Gunitas Basin" in the title."""
    from . import mesh as M
    from . import discmirror as DM
    from .terrain import minted_area
    stamp = minted_area(area)
    if center is None:
        if cell is None:
            raise ValueError("give center=(wx, wz) or cell=(bx, by)")
        center = (BLOCK * cell[0] + BLOCK / 2, -BLOCK * cell[1] - BLOCK / 2)
    # canonicalize the centre into [0,1536): cx and cx+1536 name the SAME physical site, but the
    # relief noise field and the mains RNG run over UNWRAPPED coords, so they would mint
    # DIFFERENT terrain -- one canonical frame keeps a re-run reproducible from the recorded
    # summary (the summary's center is this canonical value).
    center = (center[0] % (BLOCK * M.GRID_COLS), center[1])
    built = build_landmass(center=center, base_radius=base_radius, seed=seed, lobes=lobes,
                           land_height=land_height, rim_run=rim_run, n_patches=n_patches,
                           stamps=None if flat else "auto",
                           ground=ground, relief_amp=relief_amp, relief_seed=relief_seed,
                           beach=beach, disc=disc, game=game)
    # THE OPEN-OCEAN TARGET LAW (the world-transplant gate, ported here 2026-07-12): every
    # footprint block must be TRUE open ocean. No escape hatch -- on a sea-only real block the
    # Terrain override has no transform to bind to (the fragment silently never renders), and
    # on a real land block the island would replace real continent geometry.
    #
    # ``all_sea_target`` opts out, and ONLY a genuinely all-sea target grid may set it. The law is a
    # PROXY: it probes the REAL disc's per-block assets to infer "is the target grid's WMBlock IsSea?".
    # On a Path D world in BLANK mode that proxy is broken in both directions -- s75 forces IsSea on all
    # 480 cells, so every coord is lawful, yet the probe would refuse most of the grid purely because the
    # unrelated disc-1 map has land at those coords; and "a land block would be shredded" is impossible
    # by construction, since the bytes land in a namespace s74 keeps disjoint from the real tree.
    # DELIBERATELY NOT keyed on ``target_disc != disc``: in s75 CLONE mode the synthetic grid's IsSea
    # flags ARE the stock flags this probe measures, so the law stays exactly correct there and must keep
    # running. Folding the skip into the retarget would fail-OPEN on precisely the mode that needs it.
    # THE SEAM WRAP: both install-probing gates below MUST see the WRAPPED labels -- the real
    # map and the mod tree are keyed on them, and probing an unwrapped (-1, y) returns [] /
    # scans a filename that cannot exist, making both gates VACUOUSLY green on exactly the
    # seam-side blocks (the dunes-class hole, engine edition).
    wlabels = sorted({(M.wrap_block_col(bx), by) for (bx, by) in built["blocks"]})
    occupied = {} if all_sea_target else {blk: occ for blk in wlabels
                                          if (occ := _real_block_parts(blk, disc=disc, lod=lod, game=game))}
    if occupied:
        raise ValueError(
            f"landmass footprint touches REAL world block(s) {occupied} -- the island cannot "
            f"deploy there (a sea-only prefab has no Terrain transform to override; a land "
            f"block would be shredded). Shift --center or change --seed/--radius until every "
            f"touched block is empty open ocean.")

    # THE MOD-OVERWRITE GATE, back-ported. The law above probes the STOCK tree, which answers
    # "does the REAL game ship assets here" -- a different question from "is this target free".
    # `transplant._mod_overwrite_gate` closed exactly this hole on 2026-07-15 (the dunes-islet
    # incident: a target already holding a PRIOR MOD DEPLOY sailed through and was silently
    # overwritten), but this lane had copied the pre-fix shape three days earlier (see "ported
    # here 2026-07-12" above) and the fix was never propagated. Measured cost: a `world-island`
    # at the recorded Aldermarch centre passes the stock law with all 19 footprint blocks
    # "free" while six of them hold the owner-confirmed R4 bench, on both discs.
    wdisc = disc if target_disc is None else int(target_disc)
    M.mod_overwrite_gate(wlabels, mod_folder, disc=wdisc, lod=lod, game=game,
                         allow_overwrite=allow_overwrite, what="landmass footprint")
    plane = _sea_plane(disc, game)
    report = verify_landmass(built, sea_plane=plane, land_height=land_height)
    if not report["clean"]:
        # name the failing placement probes too: the report minus 'placement' (it is long) once printed every
        # gate clean while a block's centre probe had failed -- an island centred on a block corner
        bad_place = {blk: {k: e[k] for k in ("miss", "stacked", "centre", "centre_ok") if k in e}
                     for blk, e in (report.get("placement") or {}).items()
                     if e["miss"] or e.get("stacked", 0) or not e.get("centre_ok", True)}
        raise ValueError(f"landmass NOT CLEAN -- refusing to deploy: { {k: v for k, v in report.items() if k != 'placement'} }"
                         + (f"; failing placement probes: {bad_place}" if bad_place else ""))
    summary = {"op": "landmass", "center": list(built["center"]), "seed": built["seed"],
               "radius": base_radius, "blocks": [], "report": report, "area": stamp}
    # THE READ/WRITE DISC SPLIT. `disc` stays the READ disc -- which stock tree the meshes, sea plane, stamps
    # and donor prefabs borrow real bytes from. It MUST remain 1 or 4: extract._worldmap_env has no other
    # `worldmap/disc{N}/` bundle tree to scan and raises for anything else. `target` is purely where the
    # produced overrides are DEPLOYED. The two differ only for a synthetic world (engine patch s74).
    target = disc if target_disc is None else int(target_disc)
    bch = built.get("beach")
    written = []
    for blk, bm in sorted(built["blocks"].items()):
        bx, by = blk
        # THE SEAM WRAP POINT. Geometry was built AND verified in continuous unwrapped world
        # coords (block-locals were computed against the unwrapped key, and 24*64 = the 1536u
        # world width, so the wrapped block's local frame is bit-identical); the engine's
        # namespace holds only wrapped labels (InitialX in [0,24) -- a Block[-1]/Block[24] file
        # is DEAD, never probed). Everything from here down that names, writes, stamps or
        # mirrors uses wbx; everything that reasons about the mint's own geometry (is_bch, the
        # sea4 cut cells) stays on the unwrapped key.
        wbx = M.wrap_block_col(bx)
        entry = {"block": [wbx, by], "verts": bm.vcount, "tris": len(bm.tris)}
        is_bch = bch is not None and tuple(bch["block"]) == blk
        if not dry_run:
            bmw = bm if wbx == bx else dataclasses.replace(bm, x=wbx, name=f"Block[{wbx}][{by}] Terrain")
            M.stamp_area(bmw, stamp["area"])
            written.append(M.deploy_override(bmw, mod_folder=mod_folder, game=game, lod=lod, disc=target, part="Terrain"))
            # THE SEA4-UNDER-LAND LAW -- the land footprint is cut from the plane on EVERY land block,
            # beach or cliff (see _cut_plane). Leaving it whole makes the island boat-permeable.
            sea = _sea4_override(plane, bx, by, bch["sea4_cut"] if is_bch else frozenset(), bm, wbx)
            written.append(M.deploy_override(sea, mod_folder=mod_folder, game=game, lod=lod, disc=target, part="Sea4"))
            if is_bch:
                # the beach block: real ladder parts + the beach-bearing divert donor
                for part, key in (("Sea1", "sea1"), ("Sea2", "wash"),
                                  ("Sea5", "sea5"), ("Beach1", "foam")):
                    pbm = _part_blockmesh(part, blk, bch[key], disc, label_x=wbx)
                    if part == "Beach1":                   # walkable sand: the island's area (the sea keeps 0)
                        M.stamp_area(pbm, stamp["area"])
                    written.append(M.deploy_override(pbm, mod_folder=mod_folder, game=game, lod=lod, disc=target,
                                                     part=part))
                for part in ("Object", "Sea3"):
                    written.append(M.deploy_override(M.hidden_block_mesh(name=f"Block[{wbx}][{by}] {part}",
                                                                         disc=disc, x=wbx, y=by),
                                                     mod_folder=mod_folder, game=game, lod=lod, disc=target, part=part))
                written.append(M.deploy_donor_sidecar(bch["pins_from"][0], bch["pins_from"][1],
                                                      mod_folder=mod_folder, disc=target, x=wbx, y=by,
                                                      lod=lod, game=game))
                entry["beach"] = {"tris": {k: len(bch[k]) for k in
                                           ("foam", "wash", "sea1", "sea5")},
                                  "sea4_cut": len(bch["sea4_cut"]),
                                  "divert": list(bch["pins_from"])}
            else:
                for part in HIDDEN_PARTS:
                    written.append(M.deploy_override(M.hidden_block_mesh(name=f"Block[{wbx}][{by}] {part}",
                                                                         disc=disc, x=wbx, y=by),
                                                     mod_folder=mod_folder, game=game, lod=lod, disc=target, part=part))
                written.append(M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=mod_folder, disc=target,
                                                      x=wbx, y=by, lod=lod, game=game))
        summary["blocks"].append(entry)
    if not dry_run and summary["blocks"]:
        if coastnav:
            # backup=False: the pre-stamp state is this very call's own output (re-run to reproduce).
            # The stamp mutates only files already in `written`, so the mirror below carries the
            # stamped bytes and Disc1/Disc4 parity holds without a second pass (DEFERRED: the
            # stamp's own auto-mirror stands down for it).
            from . import coastnav as CN
            summary["coastnav"] = CN.stamp(mod_folder, disc=target,
                                           cells=[tuple(b["block"]) for b in summary["blocks"]],
                                           policy=coastnav_policy, deploy=True, game=game,
                                           backup=False, skip_mirror=DM.DEFERRED)
        DM.auto_mirror(written, mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary
