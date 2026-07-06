"""Author a CUSTOM-SHAPED overworld coastline by ribbon-warping a REAL beach block.

Where :mod:`ff9mapkit.world.terrain` ``coast()`` copies a real coastal block VERBATIM (its shoreline
stays exactly the donor's shape) and :mod:`ff9mapkit.world.water` synthesizes open ocean from a depth
field, this module BENDS a real beach onto an arbitrary shoreline curve the caller draws. It is the
synthesis path THE LAW demands: a per-cell mosaic of independent tiles can never make a *continuous novel*
coastline (independently-authored 3D cliffs never meet cleanly), but one warped ribbon of a single real
beach can -- so we take a donor's real land + real textures + real cross-shore profile and re-embed it
along a custom outline.

THE METHOD -- BACKWARD RESAMPLE (not a forward vertex push). For each target cell we build a regular
``seg x seg`` Terrain grid and, for every grid point, run the INVERSE ribbon map ``world -> (s, d)``:
project the world XZ point onto the shoreline polyline to get ``s`` (along-shore arc length) + signed
``d`` (cross-shore distance, seaward positive), then look up the donor's *straightened* field at
``(s mod period, d)``. Backward resampling is COMPLETE (every cell fully covered, no gaps), WATERTIGHT
(the sample is a pure function of world XZ, so adjacent cells + adjacent blocks agree on their shared
edges by construction -- the same seam guarantee ``water.py`` relies on), and has NO fold-over holes (the
nearest-arc projection degrades to a medial-axis crease on a too-tight concave bend, never a tear).

THE DONOR FRAME. A real coast donor's ``terrain`` sub-mesh is 100% LAND (topographs 0 plains / 31 sand /
49 blocked-cliff / 58 shore-rim); the water is separate animated sub-meshes (``beach1`` foam ramp,
``sea1..5`` bands). So we take the shore direction from ``beach1`` (the waterline strip): PCA its verts
for the along-shore axis, the perpendicular is cross-shore, signed so the land sits at ``d < 0``.

v1 DEPLOY (mirrors ``water.py``'s proven per-cell contract). Per target cell we write: (1) ONE complete
``Terrain`` override = land tiles (the donor's real Y + topograph + atlas UV, visible + walkable) blended
into submerged water tiles (topograph 57, Y just below the sea surface) -- this single mesh is both the
``s34`` land-override GATE and the cell's walkmesh (``RegisterBlockComponent`` feeds it to render AND
``AddWalkMeshForm1``, binding to the ``sea_donor``'s Terrain transform); (2) a full-cell deep ``Sea4``
override byte-copied from the ``DEEP_SEA_SOURCE`` (12,0) plane, so real animated deep ocean renders across
the whole cell at Y=0 with the land poking above it and the submerged water tiles hidden below; (3) BLANK
overrides for ``Sea1/Sea2/Sea3/Sea5`` so the ``sea_donor``'s own near-shore bands don't cover the land; and
(4) a ``Donor.txt`` naming ``sea_donor`` (which must carry a Terrain + Sea transforms -- (15,4) does). Naming
a plain deep block like (12,0) does NOT work: it has no Terrain transform for the land override to bind to.

v1 LIMITATION (documented, the frontier): the near-shore water is a flat deep plane -- there is NO warped
foam/shallow GRADIENT hugging the bent shore yet, so the coastline reads as land meeting deep water at a
crisp (foamless) waterline. Warping ``beach1``/``sea1``/``sea2`` to follow the curve is the next iteration
(``water.py`` proves an overridden Sea sub-mesh still animates by transform name, so it is tractable).

Needs the CUSTOM engine (the ``s34`` sea->land divert). Deploy from a save NOT parked on a target cell
(editing geometry under the parked on-foot actor bricks the save -- see project-ff9-overworld-actor-brick).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

BLOCK = 64
GRID_X, GRID_Y = 24, 20
WATER_TOPOGRAPH = 57          # deep-sea IDALL: boat-traversable, on-foot blocked (matches water.py)
WATER_Y = -0.1                # walkmesh just under the Y=0 sea render so a boat floats hidden at surface
DEFAULT_BEACH_DONOR = (17, 15)   # single clean straight coastline, grass->sand->foam proven (memory)
DEFAULT_SEA_DONOR = (15, 4)      # the water.py donor: has a Terrain transform (receives our land override) + the
                                 # animated sea material binding. Its own partial sea is BLANKED + replaced below.
DEEP_SEA_SOURCE = (12, 0)        # the SeaBlockPrefab source: a FULL 64x64 deep Sea4 plane (topo 57, Y=0) we byte-copy
SEA_BLANK = ("Sea1", "Sea2", "Sea3", "Sea5")   # the donor's near-shore bands, hidden so they don't cover the land


# --------------------------------------------------------------------------------------------------
# The shoreline outline (a world-XZ polyline the caller draws).
# --------------------------------------------------------------------------------------------------
class Outline:
    """A world-XZ polyline (the shoreline) with arc-length parameterization + nearest-point projection.

    Points are ``(worldX, worldZ)`` in the engine world frame (Z negative going "down" the block grid).
    ``land_side`` names which side of the drawn line is LAND ("left"/"right" relative to the direction of
    travel p0->p1->...); it fixes the sign of the returned cross-shore ``d`` so that land is ``d < 0`` (to
    match the donor frame) and open water is ``d > 0`` (seaward)."""

    def __init__(self, pts, *, land_side: str = "left"):
        pts = [(float(x), float(z)) for (x, z) in pts]
        if len(pts) < 2:
            raise ValueError("outline needs at least 2 points")
        if land_side not in ("left", "right"):
            raise ValueError("land_side must be 'left' or 'right'")
        # drop consecutive duplicates (zero-length segments break the projection)
        clean = [pts[0]]
        for p in pts[1:]:
            if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-6:
                clean.append(p)
        if len(clean) < 2:
            raise ValueError("outline collapses to a single point")
        self.pts = clean
        self.land_side = land_side
        # per-segment direction, length; cumulative arc length at each vertex
        self.segs = []
        cum = [0.0]
        for a, b in zip(clean, clean[1:]):
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz)
            self.segs.append((a, b, (dx / L, dz / L), L))
            cum.append(cum[-1] + L)
        self.cum = cum
        self.length = cum[-1]

    def project(self, px, pz):
        """Nearest point on the polyline to ``(px, pz)``. Returns ``(sigma, d, dist)``:
        ``sigma`` = arc length of the foot (0..length), ``d`` = SIGNED cross-shore distance (land<0,
        seaward>0 after the land_side flip), ``dist`` = |distance| (always >= 0).

        ``|d| == dist`` (the true clamped distance to the polyline as a capsule) -- NOT the perpendicular
        distance to an infinite line: a point beyond an endpoint gets |d| growing with its real distance,
        so the coastline has FINITE extent (no phantom shore off the drawn ends)."""
        best = None
        for k, (a, b, (tx, tz), L) in enumerate(self.segs):
            rx, rz = px - a[0], pz - a[1]
            t = (rx * tx + rz * tz)
            t = 0.0 if t < 0.0 else (L if t > L else t)
            fx, fz = a[0] + tx * t, a[1] + tz * t
            dist = math.hypot(px - fx, pz - fz)
            if best is None or dist < best[0]:
                cross = tx * (pz - fz) - tz * (px - fx)         # sign of the side (CCW +) only
                sigma = self.cum[k] + t
                best = (dist, sigma, cross)
        dist, sigma, cross = best
        sign = 1.0 if cross >= 0 else -1.0
        d = sign * dist                                         # |d| == true distance to the polyline
        # land_side='left' means land is on the +cross (CCW) side -> flip so land is d<0
        if self.land_side == "left":
            d = -d
        return sigma, d, dist

    def min_turn_radius(self):
        """Smallest local radius of curvature over the interior vertices (inf for a straight/2-pt line).
        Used to warn when the outline bends tighter than the donor's cross-shore reach (fold-over)."""
        best = math.inf
        for i in range(1, len(self.pts) - 1):
            (t0x, t0z) = self.segs[i - 1][2]
            (t1x, t1z) = self.segs[i][2]
            dot = max(-1.0, min(1.0, t0x * t1x + t0z * t1z))
            theta = math.acos(dot)                              # exterior turn angle at vertex i
            if theta < 1e-6:
                continue
            avg_len = 0.5 * (self.segs[i - 1][3] + self.segs[i][3])
            best = min(best, avg_len / theta)
        return best


# --------------------------------------------------------------------------------------------------
# The straightened donor field: a real beach block queried as f(s, d) -> land sample | water.
# --------------------------------------------------------------------------------------------------
@dataclass
class _LandTri:
    s: tuple      # (s0,s1,s2) along-shore coords of the 3 corners
    d: tuple      # (d0,d1,d2) cross-shore coords
    y: tuple      # (y0,y1,y2) donor heights
    uv: tuple     # ((u,v)x3) donor atlas UVs
    topo: int     # per-tri topograph (walkability)


class DonorField:
    """A real beach donor read once and straightened into an ``(s, d)`` field of land triangles.

    ``sample(s, d)`` returns a dict ``{y, uv, topo}`` if the point falls on donor land, else ``None``
    (open water). ``s`` is wrapped into the donor's along-shore window (``period``) so a long shoreline
    tiles the same beach motif; ``d`` is used directly (land near/below 0, seaward positive)."""

    def __init__(self, beach_donor=DEFAULT_BEACH_DONOR, *, disc: int = 1, lod: str = "0_1", game=None):
        from . import extract as X

        self.donor = tuple(beach_donor)
        self.disc = disc
        terr = X.read_block(self.donor[0], self.donor[1], disc=disc, lod=lod, part="terrain", game=game)
        try:
            beach = X.read_block(self.donor[0], self.donor[1], disc=disc, lod=lod, part="beach1", game=game)
        except (ValueError, FileNotFoundError) as e:
            raise ValueError(
                f"beach donor {self.donor} has no 'beach1' waterline mesh -- pick a donor with a beach "
                f"(ff9mapkit list-fields / world-coast --list); got: {e}")

        # --- shore frame from the beach1 (waterline) strip: PCA -> along-shore s_hat ---
        bxz = [(v[0], v[2]) for v in beach.verts]
        (sx, sz), (self.ox, self.oz) = _pca_axis(bxz)
        ux, uz = -sz, sx                                        # cross-shore = perpendicular
        # sign u_hat so the terrain-land centroid sits at d < 0
        tcx = sum(v[0] for v in terr.verts) / terr.vcount
        tcz = sum(v[2] for v in terr.verts) / terr.vcount
        if (tcx - self.ox) * ux + (tcz - self.oz) * uz > 0:
            ux, uz = -ux, -uz
        self.shat = (sx, sz)
        self.uhat = (ux, uz)

        # --- straighten the beach1 window -> the along-shore period the land tiles over ---
        bs = [self._s(x, z) for (x, z) in bxz]
        self.s_lo, self.s_hi = min(bs), max(bs)
        self.period = self.s_hi - self.s_lo
        if self.period < 1.0:
            raise ValueError(f"donor {self.donor} beach1 has a degenerate along-shore extent")

        # --- project the land tris into (s,d); crop to the beach1 s-window; bucket by s ---
        self.tris = []
        fallback_uv = []
        for t in range(len(terr.flat_index) // 3):
            c = terr.flat_index[3 * t:3 * t + 3]
            s3, d3, y3, uv3 = [], [], [], []
            for idx in c:
                vx, vy, vz = terr.verts[idx]
                s3.append(self._s(vx, vz)); d3.append(self._d(vx, vz)); y3.append(vy)
                uv3.append(tuple(terr.uvs[idx]) if terr.uvs else (0.0, 0.0))
            topo = X.decode_id(int(round(terr.tangents[c[0]][0])))["topograph"] if terr.tangents else 0
            # crop: keep tris that overlap the beach1 window in s (tile domain)
            if max(s3) < self.s_lo - 2.0 or min(s3) > self.s_hi + 2.0:
                continue
            self.tris.append(_LandTri(tuple(s3), tuple(d3), tuple(y3), tuple(uv3), topo))
            if topo in (30, 31, 58):                            # sand / shore-rim: a good "submerged" uv
                fallback_uv.append(uv3[0])
        if not self.tris:
            raise ValueError(f"donor {self.donor} yielded no land tris in the beach1 window")

        # a representative sand UV for the (hidden) water tiles, so the thin visible waterline sliver
        # samples a real atlas texel instead of the [0,0] white corner
        if not fallback_uv:
            fallback_uv = [self.tris[0].uv[0]]
        self.water_uv = (sum(u for u, _ in fallback_uv) / len(fallback_uv),
                         sum(v for _, v in fallback_uv) / len(fallback_uv))

        # cross-shore reach (for the fold-over warning)
        self.d_min = min(min(t.d) for t in self.tris)           # most inland (<0)
        self.d_max = max(max(t.d) for t in self.tris)           # most seaward

        # s-buckets for fast containment
        self._bw = 4.0
        self._buckets = {}
        for i, t in enumerate(self.tris):
            b0 = int((min(t.s) - self.s_lo) // self._bw)
            b1 = int((max(t.s) - self.s_lo) // self._bw)
            for b in range(b0, b1 + 1):
                self._buckets.setdefault(b, []).append(i)

    def _s(self, x, z):
        return (x - self.ox) * self.shat[0] + (z - self.oz) * self.shat[1]

    def _d(self, x, z):
        return (x - self.ox) * self.uhat[0] + (z - self.oz) * self.uhat[1]

    def sample(self, s, d):
        """Look up donor land at along-shore ``s`` (wrapped into the tile window) + cross-shore ``d``.
        Returns ``{y, uv, topo}`` on land, else ``None`` (water).

        Tiling is REFLECTIVE (ping-pong), not a hard modulo: the donor motif mirrors at each period boundary
        so the sampled height + shoreline are CONTINUOUS across the repeat (a hard modulo jumps s_hi->s_lo and
        tears any triangle straddling the seam into a near-vertical spike, since a real beach is not periodic)."""
        p = self.period
        t = (s - self.s_lo) % (2.0 * p)
        if t > p:
            t = 2.0 * p - t                                     # ping-pong reflect -> value + slope continuous
        sw = self.s_lo + t                                      # in [s_lo, s_hi]
        b = int((sw - self.s_lo) // self._bw)
        cand = self._buckets.get(b)
        if not cand:
            return None
        for i in cand:
            t = self.tris[i]
            bary = _bary(sw, d, t.s, t.d)
            if bary is None:
                continue
            w0, w1, w2 = bary
            y = w0 * t.y[0] + w1 * t.y[1] + w2 * t.y[2]
            u = w0 * t.uv[0][0] + w1 * t.uv[1][0] + w2 * t.uv[2][0]
            v = w0 * t.uv[0][1] + w1 * t.uv[1][1] + w2 * t.uv[2][1]
            return {"y": y, "uv": (u, v), "topo": t.topo}
        return None


def _pca_axis(pts):
    """Principal (largest-variance) unit axis of 2D points + their centroid.

    The eigenvector sign is canonicalized (x>0, or z>0 when x==0) so the along-shore frame is DETERMINISTIC.
    NOTE: this canonical sign is NOT aligned to the caller's outline draw direction, so the tiled donor motif
    may run either way along the shore -- a cosmetic nuance (it never tears the mesh), not a correctness bug."""
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cz = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - cx) ** 2 for p in pts) / n
    szz = sum((p[1] - cz) ** 2 for p in pts) / n
    sxz = sum((p[0] - cx) * (p[1] - cz) for p in pts) / n
    tr = sxx + szz
    lam = tr / 2 + math.sqrt(max(0.0, (tr / 2) ** 2 - (sxx * szz - sxz * sxz)))
    if abs(sxz) > 1e-9:
        vx, vz = lam - szz, sxz
    else:
        vx, vz = (1.0, 0.0) if sxx >= szz else (0.0, 1.0)
    m = math.hypot(vx, vz) or 1.0
    vx, vz = vx / m, vz / m
    if vx < 0 or (abs(vx) < 1e-12 and vz < 0):              # canonical sign -> deterministic frame
        vx, vz = -vx, -vz
    return (vx, vz), (cx, cz)


def _bary(px, pz, sx, dx):
    """Barycentric weights of point (px,pz) in triangle with corners (sx[i],dx[i]); None if outside."""
    x0, y0 = sx[0], dx[0]
    x1, y1 = sx[1], dx[1]
    x2, y2 = sx[2], dx[2]
    det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(det) < 1e-9:
        return None
    w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (pz - y2)) / det
    w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (pz - y2)) / det
    w2 = 1.0 - w0 - w1
    e = -1e-6
    if w0 < e or w1 < e or w2 < e:
        return None
    return w0, w1, w2


# --------------------------------------------------------------------------------------------------
# Per-cell Terrain builder (the backward resample) + BlockMesh assembly.
# --------------------------------------------------------------------------------------------------
def build_cell(field: DonorField, outline: Outline, bx: int, by: int, *,
               seg: int = 16, water_y: float = WATER_Y, lod: str = "0_1"):
    """Backward-resample one cell (bx,by) into a complete Terrain BlockMesh (land + submerged water).

    Returns ``(BlockMesh, stats)`` where stats = ``{land_tris, water_tris}``. Emits ``None`` mesh when the
    cell has no land (all open water -- no override needed, stock ocean already sails). The grid winding
    matches ``flat_block_mesh`` so every tri keeps a +Y geometric normal (walkable)."""
    from . import mesh as M

    if seg < 1:
        raise ValueError(f"seg must be >= 1 (got {seg})")
    step = float(BLOCK) / seg
    ox, oz = bx * BLOCK, -by * BLOCK

    # sample every grid vertex once: land -> (True, y, uv); water -> (False, water_y, field.water_uv).
    # a water node is placed at water_y here, so a fully-submerged tri (all corners water) is already flat.
    vinfo = {}
    for i in range(seg + 1):
        for j in range(seg + 1):
            lx, lz = i * step, -j * step
            sigma, d, _ = outline.project(ox + lx, oz + lz)
            hit = field.sample(sigma, d)
            if hit is not None:
                vinfo[(i, j)] = (True, hit["y"], hit["uv"])
            else:
                vinfo[(i, j)] = (False, water_y, field.water_uv)

    tris = []                                                   # (corners[3] of (pos, uv), topograph)
    land_tris = water_tris = 0
    for i in range(seg):
        for j in range(seg):
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -j * step, -(j + 1) * step
            corners = {                                         # (i,j) grid index per quad corner
                (x0, z0): (i, j), (x1, z0): (i + 1, j),
                (x1, z1): (i + 1, j + 1), (x0, z1): (i, j + 1),
            }
            c00, c10, c11, c01 = (x0, z0), (x1, z0), (x1, z1), (x0, z1)
            for (a, b, c) in ((c00, c11, c01), (c00, c10, c11)):   # both UP-wound (matches flat_block_mesh)
                verts = [((cx, vinfo[corners[(cx, cz)]][1], cz), vinfo[corners[(cx, cz)]][2])
                         for (cx, cz) in (a, b, c)]              # per-vertex (pos with sampled Y, uv)
                # per-tri topograph from the tri centroid (land -> donor topo, water -> 57). A tri centroid
                # on water but with a land corner keeps the land Y -> a natural beach ramp into the water.
                mx = (a[0] + b[0] + c[0]) / 3.0
                mz = (a[1] + b[1] + c[1]) / 3.0
                sigma, d, _ = outline.project(ox + mx, oz + mz)
                hit = field.sample(sigma, d)
                if hit is not None:
                    topo = hit["topo"]; land_tris += 1
                else:
                    topo = WATER_TOPOGRAPH; water_tris += 1
                tris.append((verts, topo))

    if land_tris == 0:
        return None, {"land_tris": 0, "water_tris": water_tris}

    bm = _terrain_blockmesh(tris, disc=field.disc, x=bx, y=by, lod=lod)
    M.recompute_normals(bm)
    return bm, {"land_tris": land_tris, "water_tris": water_tris}


def _terrain_blockmesh(tris, *, disc: int, x: int, y: int, lod: str):
    """Assemble a walkable Terrain BlockMesh from ``tris`` = list of ``(corners, topograph)`` where each
    corners entry is 3 ``((px,py,pz),(u,v))`` pairs in block-LOCAL frame. Fresh verts per triangle
    (unindexed, vcount==indexCount) + per-tri ``tangent.x = encode_id(topograph=...)`` (matches the stock
    flat/unindexed world blocks; sharing verts would desync the flat index buffer)."""
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN

    pos, nrm, uv, tan, flat, tri_idx = [], [], [], [], [], []
    vi = 0
    for (corners, topo) in tris:
        idall = float(encode_id(event=0, area=0, topograph=topo))
        base = vi
        for ((px, py, pz), (u, v)) in corners:
            pos.append([px, py, pz]); nrm.append([0.0, 1.0, 0.0])
            uv.append([u, v]); tan.append([idall, 0.0, 0.0, 1.0])
            flat.append(vi); vi += 1
        tri_idx.append([base, base + 1, base + 2])
    chan = {CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}
    channels = {CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}
    return BlockMesh(name=f"Block[{x}][{y}] Terrain", disc=disc, x=x, y=y, lod=lod, vcount=vi, stride=48,
                     channels=channels, chan_arrays=chan, flat_index=flat, tris=tri_idx,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


# --------------------------------------------------------------------------------------------------
# Orchestrator + cell derivation + offline preview.
# --------------------------------------------------------------------------------------------------
def _derive_cells(outline: Outline, field: DonorField):
    """Every grid cell the shoreline (+ the donor's cross-shore reach) could touch."""
    reach = max(abs(field.d_min), abs(field.d_max)) + BLOCK     # inland/seaward reach + a cell margin
    xs = [p[0] for p in outline.pts]
    zs = [p[1] for p in outline.pts]
    x0 = max(0, int((min(xs) - reach) // BLOCK))
    x1 = min(GRID_X - 1, int((max(xs) + reach) // BLOCK))
    # world Z is negative; grid y = -z / 64
    y0 = max(0, int((-(max(zs) + reach)) // BLOCK))
    y1 = min(GRID_Y - 1, int((-(min(zs) - reach)) // BLOCK))
    return [(bx, by) for bx in range(x0, x1 + 1) for by in range(y0, y1 + 1)]


def coast_custom(mod_folder: str, *, outline, beach_donor=DEFAULT_BEACH_DONOR,
                 sea_donor=DEFAULT_SEA_DONOR, cells=None, land_side: str = "left",
                 seg: int = 16, disc: int = 1, lod: str = "0_1", height: float = WATER_Y,
                 game=None, preview=None, dry_run: bool = False) -> dict:
    """Ribbon-warp a real beach donor onto the ``outline`` shoreline, deploying per-cell Terrain overrides.

    ``outline`` = a list of ``(worldX, worldZ)`` points (the shoreline curve). ``beach_donor`` = the real
    coastal block whose land shape/texture is warped; ``sea_donor`` = the block named in each cell's
    ``Donor.txt`` (must carry a Terrain + Sea transforms -- (15,4)); its own near-shore sea is blanked and
    replaced by a full deep ``Sea4`` plane so it can't cover the land. ``cells`` (optional) restricts output;
    when None the touched cells are derived from the outline. ``preview`` = a PNG path for an offline
    top-down render (works under ``dry_run`` and without a deploy). Returns a JSON-able summary dict."""
    if seg < 1:
        raise ValueError(f"--seg must be >= 1 (got {seg})")
    beach_donor = tuple(beach_donor)
    sea_donor = tuple(sea_donor)
    for (dx, dy) in (beach_donor, sea_donor):                    # validate BEFORE any p0data read
        if not (0 <= dx < GRID_X and 0 <= dy < GRID_Y):
            raise ValueError(f"donor {(dx, dy)} out of the {GRID_X}x{GRID_Y} grid")

    ol = Outline(outline, land_side=land_side)
    field = DonorField(beach_donor, disc=disc, lod=lod, game=game)

    if cells is None:
        target = _derive_cells(ol, field)
        if not target:
            xs = [p[0] for p in ol.pts]; zs = [p[1] for p in ol.pts]
            raise ValueError(
                f"outline (x {min(xs):.0f}..{max(xs):.0f}, z {min(zs):.0f}..{max(zs):.0f}) plus the donor's "
                f"cross-shore reach lands entirely off the {GRID_X}x{GRID_Y} overworld grid -- no cells derived. "
                f"World Z must be NEGATIVE: a cell center is (bx*64+32, -(by*64+32)); e.g. cell (7,17) = "
                f"(480, -1120). Give an on-grid outline or pass explicit --cells.")
    else:
        target = [tuple(c) for c in cells]
        for (bx, by) in target:
            if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
                raise ValueError(f"cell {(bx, by)} out of the {GRID_X}x{GRID_Y} grid")

    # fold-over warning: a bend tighter than the donor's cross-shore reach folds the ribbon inside-out
    reach = max(abs(field.d_min), abs(field.d_max))
    r_min = ol.min_turn_radius()
    fold_warn = r_min < reach

    summary = {
        "op": "coast-custom", "beach_donor": list(beach_donor), "sea_donor": list(sea_donor),
        "disc": disc, "land_side": land_side, "seg": seg, "dry_run": dry_run,
        "outline_len": round(ol.length, 2), "period": round(field.period, 2),
        "fold_warning": fold_warn, "min_turn_radius": (None if math.isinf(r_min) else round(r_min, 2)),
        "cross_shore_reach": round(reach, 2), "cells": [], "skipped": [],
    }

    built = []
    for (bx, by) in target:
        bm, stats = build_cell(field, ol, bx, by, seg=seg, water_y=height, lod=lod)
        if bm is None:
            summary["skipped"].append([bx, by])
            continue
        built.append((bx, by, bm))
        summary["cells"].append({"cell": [bx, by], **stats})

    if not dry_run:
        import dataclasses
        from . import mesh as M
        from . import extract as X
        # a full-cell deep Sea4 plane (byte-copied from the SeaBlockPrefab source) renders animated deep ocean
        # across each cell at Y=0; the land pokes above, the submerged water tiles hide below. Mirrors water.py.
        deep_sea4 = X.read_block(DEEP_SEA_SOURCE[0], DEEP_SEA_SOURCE[1], disc=disc, lod=lod, part="sea4", game=game)
        for (bx, by, bm) in built:
            M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part="Terrain")
            s4 = dataclasses.replace(deep_sea4, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
            M.deploy_override(s4, mod_folder=mod_folder, game=game, lod=lod, part="Sea4")
            for name in SEA_BLANK:                              # hide the donor's own near-shore bands
                blank = M.hidden_block_mesh(name=f"Block[{bx}][{by}] {name}", disc=disc, x=bx, y=by, lod=lod)
                M.deploy_override(blank, mod_folder=mod_folder, game=game, lod=lod, part=name)
            M.deploy_donor_sidecar(sea_donor[0], sea_donor[1], mod_folder=mod_folder, disc=disc,
                                   x=bx, y=by, lod=lod, game=game)

    if preview:
        render_preview(ol, field, built, preview, seg=seg)
        summary["preview"] = str(preview)

    return summary


def render_preview(outline: Outline, field: DonorField, built, path, *, seg: int = 16, ppu: int = 6):
    """Top-down PNG of the warped coastline: land tiles colored by topograph, the shoreline curve, the
    cell grid. Lets a human eyeball the shape before playtesting (the dev cannot see the game)."""
    from PIL import Image, ImageDraw

    TOPO_COLOR = {0: (86, 152, 74), 31: (206, 187, 120), 58: (224, 214, 170),
                  49: (120, 120, 120), 30: (210, 200, 150)}
    LAND_DEFAULT = (110, 150, 90)
    WATER = (40, 78, 120)

    # world bbox: union of built cells + a margin, else the outline bbox
    if built:
        bxs = [c[0] for c in built]; bys = [c[1] for c in built]
        wx0, wx1 = min(bxs) * BLOCK, (max(bxs) + 1) * BLOCK
        wz1, wz0 = -min(bys) * BLOCK, -(max(bys) + 1) * BLOCK   # z: less negative .. more negative
    else:
        xs = [p[0] for p in outline.pts]; zs = [p[1] for p in outline.pts]
        wx0, wx1 = min(xs) - 32, max(xs) + 32
        wz0, wz1 = min(zs) - 32, max(zs) + 32
    W = max(1, int((wx1 - wx0) * ppu))
    H = max(1, int((wz1 - wz0) * ppu))
    img = Image.new("RGB", (W, H), WATER)
    dr = ImageDraw.Draw(img)

    def to_px(wx, wz):
        return ((wx - wx0) * ppu, (wz1 - wz) * ppu)             # flip Z so north (z->0) is up

    step = float(BLOCK) / seg
    for (bx, by, bm) in built:
        ox, oz = bx * BLOCK, -by * BLOCK
        for t in range(len(bm.flat_index) // 3):
            c = bm.flat_index[3 * t:3 * t + 3]
            topo = _tri_topo(bm, c[0])
            if topo == WATER_TOPOGRAPH:
                continue                                        # water drawn as the background
            col = TOPO_COLOR.get(topo, LAND_DEFAULT)
            poly = [to_px(ox + bm.verts[i][0], oz + bm.verts[i][2]) for i in c]
            dr.polygon(poly, fill=col)

    # cell grid
    for (bx, by, _bm) in built:
        ox, oz = bx * BLOCK, -by * BLOCK
        p0 = to_px(ox, oz); p1 = to_px(ox + BLOCK, oz - BLOCK)
        dr.rectangle([p0[0], p0[1], p1[0], p1[1]], outline=(70, 90, 110))

    # the shoreline curve
    dr.line([to_px(x, z) for (x, z) in outline.pts], fill=(220, 70, 70), width=2)
    img.save(path)
    return path


def _tri_topo(bm, first_corner_idx):
    from .extract import decode_id
    return decode_id(int(round(bm.tangents[first_corner_idx][0])))["topograph"]
