"""Fully-SYNTHETIC overworld islands / landmasses -- the in-game-proven builder (2026-07-07), productized.

Composes everything the synth-island session proved, layer by layer:

* **Coastline**: :func:`ff9mapkit.world.mesh.blob_outline` -- FF9's measured shape language (gentle
  ~25u-radius curves + occasional corner dents), any radius, deterministic per seed.
* **Rock wall**: the faithful ~73 deg cliff profile (``rim_run`` 1.0 at ``land_height`` 3.2) textured by
  the measured rock-band rule -- U advances with GLOBAL along-shore arc-length (constant density, window-
  translated so the strip's sawtooth wrap lands on triangle boundaries, never mid-tri: the smear fix),
  V climbs the face.
* **Grass**: the real tile language from :mod:`ff9mapkit.world.grassland` -- lattice mains
  (quadrant+rotation, direction-aware bleed), verbatim meadow STAMPS, the verbatim rolling RELIEF field,
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
ROCK_U = (0.699, 0.947)                                  # the measured grey-rock atlas band
ROCK_V = (0.923, 0.893)                                  # V: base -> top (the rock climbs the face)
ROCK_DENSITY = 0.0125                                    # texels/u along the shore (measured constant)
SEA_PLANE_SOURCE = (12, 0)                               # the game's only full-cell deep Sea4 plane
DEFAULT_DONOR = (0, 0)                                   # Uaho: a Terrain-carrying donor for the s34 divert
HIDDEN_PARTS = ("Object", "Sea1", "Sea2", "Sea3", "Sea5")


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
                   corner_strength: float = 0.26, n_patches: int = 2, relief=None, stamps=None,
                   mains_seed: int = 0xF91, stamp_seed: int = 0xF92, disc: int = 1, game=None) -> dict:
    """Build a synthetic cliff landmass around WORLD ``center = (cx, cz)`` as per-block ``Terrain``
    meshes. ``lobes=1`` = the perturbed-circle outline; ``lobes>=2`` = the ASYMMETRIC multi-lobe union
    (:func:`mesh.multi_blob_outline` -- elongation, waists, natural corner creases; the shape gate in
    :func:`verify_landmass` checks it against the measured FF9 coastline language). ``relief`` = a
    :func:`grassland.relief_field` dict, ``"auto"`` (load from the install), or ``None`` (flat --
    hermetic). ``stamps`` likewise (a list / ``"auto"`` / ``None``). Returns
    ``{"blocks": {(bx, by): BlockMesh}, "outline", "seed", "report"}`` -- run :func:`verify_landmass`
    (or let :func:`landmass` do it) before deploying."""
    from . import mesh as M
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN

    cx, cz = center
    if seed is None:
        seed = float(int(cx * 7 + cz * 13) % 997)
    if lobes >= 2:
        outline, radii = M.multi_blob_outline(cx, cz, lobes=lobes, base_radius=base_radius, seed=seed,
                                              undulation=undulation)
    else:
        outline, radii = M.blob_outline(cx, cz, base_radius=base_radius, seed=seed, undulation=undulation,
                                        n_corners=n_corners, corner_strength=corner_strength)
    nring = len(outline)
    rim = []
    for (ox, oz), r in zip(outline, radii):
        ux, uz = (ox - cx) / r, (oz - cz) / r
        rim.append((cx + ux * (r - rim_run), cz + uz * (r - rim_run)))
    top = [(x, land_height, z) for (x, z) in rim]

    def was_land(px, pz):
        return _pip(px, pz, rim)

    # grass interior: rim weld ring + a lattice-aligned interior grid
    xs = [p[0] for p in top]
    zs = [p[2] for p in top]
    interior = []
    gx = math.floor(min(xs) / GRID) * GRID
    while gx <= max(xs):
        gz = math.floor(min(zs) / GRID) * GRID
        while gz <= max(zs):
            if was_land(gx, gz) and all((gx-tx)**2 + (gz-tz)**2 > (GRID*0.4)**2 for (tx, _, tz) in top):
                interior.append((gx, land_height, gz))
            gz += GRID
        gx += GRID
    allpts = top + interior
    xz = [(p[0], p[2]) for p in allpts]
    tri_idx, ring_flips = _recover_ring_edges(xz, _delaunay(xz), nring)
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
    while stack:                                         # enclosed pinholes (steep-wall XZ shadows) re-fill
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

    cells_used = sorted({(math.floor((a[0]+b[0]+c[0])/3 / 4), math.floor((a[2]+b[2]+c[2])/3 / 4))
                         for (a, b, c) in fill})
    cell_quad, cell_ori = G.assign_mains(cells_used, seed=mains_seed)

    if stamps == "auto":
        stamps = G.extract_stamps(disc, game=game)
    if relief == "auto":
        relief = G.relief_field(disc=disc, game=game)

    def box_ok(box):
        for (i, j) in box:
            for (qx, qz) in ((4*i, 4*j), (4*i + 4, 4*j), (4*i, 4*j + 4), (4*i + 4, 4*j + 4)):
                if any((qx - tx) ** 2 + (qz - tz) ** 2 < 0.25 for (tx, _, tz) in top):
                    return False
                if not was_land(qx, qz):
                    return False
        cs = set(box)
        min_x = min(c[0] for c in box) * 4
        max_x = max(c[0] for c in box) * 4 + 4
        min_z = min(c[1] for c in box) * 4
        max_z = max(c[1] for c in box) * 4 + 4
        for (a, b, c) in fill:
            inside_c = (math.floor((a[0]+b[0]+c[0])/3 / 4), math.floor((a[2]+b[2]+c[2])/3 / 4)) in cs
            for p in (a, b, c):
                p_in = min_x - 1e-6 <= p[0] <= max_x + 1e-6 and min_z - 1e-6 <= p[2] <= max_z + 1e-6
                p_strict = min_x + 1e-6 < p[0] < max_x - 1e-6 and min_z + 1e-6 < p[2] < max_z - 1e-6
                if (inside_c and not p_in) or (not inside_c and p_strict):
                    return False
        return True

    placements, stamped_cell = ([], {}) if not stamps else G.place_stamps(
        cells_used, stamps, box_ok=box_ok, seed=stamp_seed, n_patches=n_patches)

    rim_keys = {(round(x, 3), round(z, 3)) for (x, z) in rim}

    def edge_dist(x, z):
        return math.sqrt(min((x - tx) ** 2 + (z - tz) ** 2 for (tx, _, tz) in top))

    def fill_y(x, z):
        if (round(x, 3), round(z, 3)) in rim_keys:
            return land_height                           # exact weld at the wall top
        return land_height + G.relief_at(relief or {}, x, z, edge_dist=edge_dist(x, z))

    # global shore arc-length (continuous across cells -> the rock band chains block to block)
    cum = [0.0] * nring
    for i in range(1, nring):
        cum[i] = cum[i-1] + math.hypot(outline[i][0]-outline[i-1][0], outline[i][1]-outline[i-1][1])
    perim = cum[-1] + math.hypot(outline[0][0]-outline[-1][0], outline[0][1]-outline[-1][1])

    def shore_s(x, z):
        bi, bd = 0, None
        for i, (ox, oz) in enumerate(outline):
            d = (x - ox) ** 2 + (z - oz) ** 2
            if bd is None or d < bd:
                bd, bi = d, i
        return cum[bi]

    idw = float(encode_id(topograph=CLIFF_TOPO))
    idg = float(encode_id(topograph=LAND_TOPO))
    parent = []                                          # (corners[(x,y,z,u,v)]x3, idall, fam)

    def up(c0, c1, c2):
        ny = (c1[2]-c0[2])*(c2[0]-c0[0]) - (c1[0]-c0[0])*(c2[2]-c0[2])
        return (c0, c1, c2) if ny > 0 else (c0, c2, c1)

    strip_w = ROCK_U[1] - ROCK_U[0]

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
        return [(ROCK_U[0] + min(off + (p - min(ph)), strip_w),
                 ROCK_V[0] + min(max(pt[1] / land_height, 0.0), 1.0) * (ROCK_V[1] - ROCK_V[0]))
                for p, pt in zip(ph, pts3)]

    for i in range(nring):                               # the wall band
        j = (i + 1) % nring
        o0 = (outline[i][0], 0.0, outline[i][1])
        o1 = (outline[j][0], 0.0, outline[j][1])
        r0 = (rim[i][0], land_height, rim[i][1])
        r1 = (rim[j][0], land_height, rim[j][1])
        for tri in (up(o0, o1, r0), up(r0, o1, r1)):
            uvs = rock_uvs(tri)
            parent.append((tuple((p[0], p[1], p[2], u, v) for p, (u, v) in zip(tri, uvs)), idw, "rock"))

    for (a, b, c) in fill:                               # the grass (mains cells; stamped cells replaced below)
        ccx = (a[0]+b[0]+c[0])/3
        ccz = (a[2]+b[2]+c[2])/3
        cell = (math.floor(ccx / 4), math.floor(ccz / 4))
        if cell in stamped_cell:
            continue
        quad, ori = cell_quad[cell], cell_ori[cell]
        tri = up(*(( (p[0], fill_y(p[0], p[2]), p[2]) for p in (a, b, c) )))
        corners = tuple((p[0], p[1], p[2], *G.mains_uv(p[0], p[2], cell, quad, ori)) for p in tri)
        parent.append((corners, idg, "main"))
    for corners, fam in G.stamp_geometry(placements):    # verbatim meadow stamps (exact real corner UVs)
        pts = [(x, fill_y(x, z), z) for (x, z, _, _) in corners]
        uvv = [(u, v) for (_, _, u, v) in corners]
        order = up(*pts)
        remap = [pts.index(p) for p in order]
        parent.append((tuple((p[0], p[1], p[2], *uvv[r]) for p, r in zip(order, remap)), idg, fam))

    by_block = _split_at_borders(parent)

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

    return {"blocks": blocks, "outline": outline, "rim": rim, "seed": seed, "center": (cx, cz),
            "was_land": was_land, "top": top, "placements": placements, "ring_edge_flips": ring_flips,
            "world": {"pos": gpos, "tris": gtris, "meta": gmeta, "nrm": gnrm}}


def verify_landmass(built: dict, *, sea_plane=None, land_height: float = 3.2) -> dict:
    """The offline gate suite over a :func:`build_landmass` result: watertight (cracks), the
    closed-surface once-edge audit (``open_edges`` / ``missing_faces`` -- no boundary above the y=0
    sea skirt), winding (down-facing / engine walk-filter fails, wall AND grass), on-grain (grass
    tris > 8u), footprint holes, per-family UV bounds, and -- when ``sea_plane`` is given -- the
    ENGINE PLACEMENT census per block
    (MISS must be 0 everywhere; the centre must ground on walkable grass). Returns a report dict with
    ``clean``."""
    from .extract import decode_id
    gpos = built["world"]["pos"]
    gtris = built["world"]["tris"]
    gmeta = built["world"]["meta"]
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
        if topo == LAND_TOPO:
            e = max(math.dist((a[0], a[2]), (b[0], b[2])), math.dist((b[0], b[2]), (c[0], c[2])),
                    math.dist((a[0], a[2]), (c[0], c[2])))
            if e > 8:
                big += 1
        lo_u, lo_v, hi_u, hi_v = (ROCK_U[0] - 1e-3, min(ROCK_V) - 1e-3, ROCK_U[1] + 1e-3, max(ROCK_V) + 1e-3) \
            if fam == "rock" else G.FAM_REGION.get(fam, G.FAM_REGION["?"])
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
    open_bad = [e for e, n in ecnt.items() if n == 1 and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]
    open_adj = collections.defaultdict(set)
    for ea, eb in open_bad:
        open_adj[ea].add(eb)
        open_adj[eb].add(ea)
    miss_faces = {tuple(sorted((p, q, r))) for p in open_adj for q in open_adj[p] for r in open_adj[q]
                  if r != p and p in open_adj[r]}
    report.update(cracks=cracks, down_facing=down, walk_filter_fails=steep, grass_over_8u=big,
                  uv_out_of_region=oob, holes=holes, holes_sampled=tot,
                  open_edges=len(open_bad), missing_faces=len(miss_faces))

    # the coastline SHAPE gate: the generated outline must sit inside the measured FF9 language
    # (real disc-1 coasts: med turn 22 deg/8u, corner(45-80) 15%, acute(>=80) 7%)
    from . import mesh as _M
    shape = _M.outline_shape_stats(built["outline"])
    shape["ok"] = 8.0 <= shape["med_turn"] <= 35.0 and shape["acute"] <= 0.12 and shape["max_turn"] < 150.0
    report["shape"] = shape

    place_reports = {}
    if sea_plane is not None:
        from . import mesh as M
        cx, cz = built["center"]
        for blk, bm in built["blocks"].items():
            bx, by = blk
            hid = lambda nm: M.hidden_block_mesh(name=nm, disc=bm.disc, x=bx, y=by)  # noqa: E731
            meshlist = [("Object", hid("Object")), ("Terrain", bm),
                        ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")),
                        ("Sea4", sea_plane), ("Sea5", hid("Sea5"))]
            cen = P.census(meshlist)
            entry = {"counts": cen["counts"], "miss": len(cen["miss"])}
            lx, lz = cx - BLOCK * bx, cz + BLOCK * (by + 1) - BLOCK
            if 0.0 <= lx <= BLOCK and -BLOCK <= lz <= 0.0:
                gy, nm, _, topo = P.place(meshlist, lx, lz)
                entry["centre"] = (round(gy, 2), nm, topo)
                entry["centre_ok"] = nm == "Terrain" and topo == LAND_TOPO
            place_reports[blk] = entry
        report["placement"] = place_reports
    report["clean"] = (cracks == 0 and down == 0 and steep == 0 and big == 0 and oob == 0 and holes == 0
                       and len(open_bad) == 0 and shape["ok"]
                       and all(e["miss"] == 0 and e.get("centre_ok", True) for e in place_reports.values()))
    return report


# --------------------------------------------------------------------------- deploy

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
             donor=DEFAULT_DONOR, disc: int = 1, lod: str = "0_1", game=None, dry_run: bool = False) -> dict:
    """Build, GATE, and deploy a synthetic landmass. ``cell=(bx, by)`` centres it on that block;
    ``center=(wx, wz)`` places it anywhere (a multi-block landmass splits per block automatically).
    Raises ``ValueError`` with the report if any gate fails. Deploys per touched block: the ``Terrain``
    override + a hole-patched full-cell deep ``Sea4`` + blanked ``Object``/``Sea1/2/3/5`` + a ``Donor.txt``
    naming ``donor`` (must carry a Terrain transform for the s34 divert). RELAUNCH / re-enter the world
    for a first-time block."""
    from . import mesh as M
    if center is None:
        if cell is None:
            raise ValueError("give center=(wx, wz) or cell=(bx, by)")
        center = (BLOCK * cell[0] + BLOCK / 2, -BLOCK * cell[1] - BLOCK / 2)
    built = build_landmass(center=center, base_radius=base_radius, seed=seed, lobes=lobes,
                           land_height=land_height, rim_run=rim_run, n_patches=n_patches,
                           relief=None if flat else "auto", stamps=None if flat else "auto",
                           disc=disc, game=game)
    # THE OPEN-OCEAN TARGET LAW (the world-transplant gate, ported here 2026-07-12): every
    # footprint block must be TRUE open ocean. No escape hatch -- on a sea-only real block the
    # Terrain override has no transform to bind to (the fragment silently never renders), and
    # on a real land block the island would replace real continent geometry.
    occupied = {blk: occ for blk in sorted(built["blocks"])
                if (occ := _real_block_parts(blk, disc=disc, lod=lod, game=game))}
    if occupied:
        raise ValueError(
            f"landmass footprint touches REAL world block(s) {occupied} -- the island cannot "
            f"deploy there (a sea-only prefab has no Terrain transform to override; a land "
            f"block would be shredded). Shift --center or change --seed/--radius until every "
            f"touched block is empty open ocean.")
    plane = _sea_plane(disc, game)
    report = verify_landmass(built, sea_plane=plane, land_height=land_height)
    if not report["clean"]:
        raise ValueError(f"landmass NOT CLEAN -- refusing to deploy: { {k: v for k, v in report.items() if k != 'placement'} }")
    summary = {"op": "landmass", "center": list(built["center"]), "seed": built["seed"],
               "radius": base_radius, "blocks": [], "report": report}
    for blk, bm in sorted(built["blocks"].items()):
        bx, by = blk
        entry = {"block": [bx, by], "verts": bm.vcount, "tris": len(bm.tris)}
        if not dry_run:
            M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part="Terrain")
            sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
            M.deploy_override(sea, mod_folder=mod_folder, game=game, lod=lod, part="Sea4")
            for part in HIDDEN_PARTS:
                M.deploy_override(M.hidden_block_mesh(name=f"Block[{bx}][{by}] {part}", disc=disc, x=bx, y=by),
                                  mod_folder=mod_folder, game=game, lod=lod, part=part)
            M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=mod_folder, disc=disc, x=bx, y=by,
                                   lod=lod, game=game)
        summary["blocks"].append(entry)
    return summary
