"""VERBATIM overworld TRANSPLANT: carry a complete real block -- land + beach + the full Wang'd
ocean, every sub-mesh -- to a custom ocean cell, with 0-mod-4 in-cell SHIFT + 90-degree ROTATION
knobs, then optionally EDIT it component-wise. Everything stays byte-verbatim donor data (real
Wang peninsulas, stipple tiles, off-lattice shore-conforming tiles) and every build is
offline-GATED before deploy. Productized from the in-game-proven ``island_morph`` v16
(2026-07-08: donor island (7,17) + its (8,17) tongue at cell (4,2), ROT 90, de-quested +
beach-shrunk -- "that's it").

THE LAWS this module encodes (learned over 11 in-game passes -- do not relearn them):

* 90-degree rotations and 0-mod-4 shifts keep the 4u tile lattice EXACT, so the whole block --
  ocean included -- stays fully verbatim: tiles land on lattice cells and rotate into their own
  legal rotation variants (the mains anti-tiling and the Wang strips already use all four).
  Free angles / arbitrary shifts strain the tile language and are NOT offered here.
* A coast component is a GEOMETRY+TEXTURE+TOPO unit -- no cross-class retexture (rock painted on
  a sand ramp reads as a flat rock plane). Junctions are whole ASSEMBLIES whose boundary
  polylines are load-bearing WELDS: slide them whole, never re-draw their boundaries.
* NEVER hand-type mesh geometry: real donor verts are off-lattice floats; a rounded coordinate
  renders as a hairline crack. :class:`PatchRecover` CAPTURES exact floats from the tris it
  drops, and :func:`ff9mapkit.world.mesh.weld_audit` gates every build (expect 0 pairs).

Tweaks are objects with ``part`` (the sub-mesh they edit), ``apply(part, poly) -> poly | None``
(donor WORLD coords, pre-rotation -- so a tweak is rotation-invariant), ``emit() -> [poly]``
(new tris injected after the part's gather), and ``gate() -> dict`` (an exact-scope count gate).
:class:`TileRetexture` and :class:`PatchRecover` are the two in-game-proven classes.

Needs the CUSTOM engine (the s34 divert + the ``Donor.txt`` sidecar): deploys every sub-mesh
override plus the donor sidecar. RELAUNCH (or exit + re-enter the overworld) to apply.
"""
from __future__ import annotations

import collections
import math

from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
from .terrain import GRID_X, GRID_Y

#: The block sub-mesh parts a coastal transplant carries, in the engine's registration order
#: (Terrain first -- placement's first-hit-wins ground query depends on it).
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4")
#: Parts whose normals encode real slopes and must ROTATE with the block (sea normals are a
#: uniform byte-constant shared by every tile regardless of tile rotation -- they stay).
LAND_PARTS = frozenset({"terrain", "beach1"})
FRAME_EPS = 0.05                     # bounds-gate tolerance at the cell frame planes
MAX_CUT_RELIEF = 6.0                 # cut-line law: max on-line LAND y-span a RowInsert may cross
#   (in-game 2026-07-09, the (9,5) mountain: a cut's fill is the seam profile extruded 4u -- through
#   STEEP relief that is a flat terrace band + skipped-segment holes, "seaming errors on both sides
#   of the mountain". Proven cuts crossed <= 3.5u (grass/sand/coastal-cliff lip); the mountain was
#   26.5u. High relief is a COMPONENT, like the beach: cut around it, never through.)
MIN_TRI_AREA2 = 1e-6                 # post-clip degenerate-sliver filter (2x the TRUE 3D area:
#   a clip sliver's verts are collinear in 3D, but a real VERTICAL wall tri -- forest sides,
#   topo-38, the (9,5) island -- has ZERO PLAN area and real 3D area; a plan-area test silently
#   drops it ("the top renders, the vertical portion doesn't", in-game 2026-07-09)).
#   THE HAIRLINE LAW (in-game 2026-07-09, the (0,4) z-slide: "a seam in the cliff" at a row
#   border): a shifted off-lattice vert 0.004u from a re-partition plane makes the clip mint a
#   THIN-BUT-REAL fragment; the old 0.02 threshold dropped it = a hairline coverage hole along
#   the border (the proven x-slide survived only because ITS fragments were ~0.02u wide). True
#   collinear clip degenerates measure ~1e-9; real hairline fragments are surface and carry.
PROVEN_DONOR = (7, 17)               # the in-game-proven beach island (E tongue in (8,17))
#: The synthesizable OPEN-WATER tile languages (world-water-proven). Shore-bound bands
#: (beach1/sea1/sea2) are COPY-ONLY components; these three are fair game for fills.
OPEN_WATER_PARTS = frozenset({"sea3", "sea5", "sea4"})

_DIRS = {"E": (1, 0), "N": (0, 1), "W": (-1, 0), "S": (0, -1)}
_DIR_OF = {v: k for k, v in _DIRS.items()}


def part_name(part: str) -> str:
    """``terrain`` -> ``Terrain`` etc. -- the engine ``transform.name`` the override binds to."""
    return part.capitalize()


def world_tris(bx: int, by: int, part: str, *, disc: int = 1, lod: str = "0_1", game=None) -> list:
    """Read block ``(bx, by)``'s ``part`` sub-mesh as a WORLD-coordinate triangle soup: a list of
    triangles, each a list of ``(pos, normal, uv, tangent)`` vertex tuples (``tangent[0]`` carries
    the IDALL). A missing sub-mesh reads as ``[]`` -- open-ocean cells render from the shared
    SeaBlockPrefab and have no per-block mesh assets."""
    from . import extract as X
    try:
        m = X.read_block(bx, by, disc=disc, lod=lod, part=part, game=game)
    except ValueError as e:
        if "mesh not found" in str(e):
            return []
        raise
    if not m.verts:
        return []
    out = []
    for t in range(len(m.flat_index) // 3):
        idx = m.flat_index[3 * t:3 * t + 3]
        out.append([((m.verts[i][0] + 64.0 * bx, m.verts[i][1], m.verts[i][2] - 64.0 * by),
                     tuple(m.normals[i]), tuple(m.uvs[i]), tuple(m.tangents[i])) for i in idx])
    return out


def _lerp_vert(a, b, t):
    p = tuple(a[0][k] + t * (b[0][k] - a[0][k]) for k in range(3))
    nr = tuple(a[1][k] + t * (b[1][k] - a[1][k]) for k in range(3))
    uvv = (a[2][0] + t * (b[2][0] - a[2][0]), a[2][1] + t * (b[2][1] - a[2][1]))
    return (p, nr, uvv, a[3])


def clip_poly(poly, axis: int, plane: float, keep_below: bool) -> list:
    """Sutherland-Hodgman clip at an axis plane (``axis`` 0 = x, 2 = z). Lattice tiles pass whole;
    shore-conforming tiles straddling a border keep their inside part EXACTLY (positions, normals
    and UVs lerped on the cut edge) -- whole-tri dropping leaves census holes at the border."""
    res = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        va, vb = a[0][axis], b[0][axis]
        da = (plane - va) if keep_below else (va - plane)
        db = (plane - vb) if keep_below else (vb - plane)
        if da >= 0:
            res.append(a)
        if (da < 0) != (db < 0):
            res.append(_lerp_vert(a, b, da / (da - db)))
    return res


def _tri_area2_3d(t3) -> float:
    """2x a triangle's TRUE 3D area (the cross-product magnitude) -- the degenerate-sliver
    discriminator. Never test PLAN area here: real vertical faces (forest walls) are
    plan-degenerate but real geometry."""
    (ax, ay, az) = t3[0][0]
    (ux, uy, uz) = (t3[1][0][0] - ax, t3[1][0][1] - ay, t3[1][0][2] - az)
    (vx, vy, vz) = (t3[2][0][0] - ax, t3[2][0][1] - ay, t3[2][0][2] - az)
    (cx, cy, cz) = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    return math.sqrt(cx * cx + cy * cy + cz * cz)


def _rot_xz(x: float, z: float, nrot: int):
    """Rotate a block-LOCAL point (frame x 0..64, z -64..0) about the cell centre by ``nrot`` 90-degree
    steps -- the 4u lattice maps to itself."""
    dx, dz = x - 32.0, z + 32.0
    for _ in range(nrot):
        dx, dz = -dz, dx
    return 32.0 + dx, -32.0 + dz


def _rot_dir(nx: float, nz: float, nrot: int):
    for _ in range(nrot):
        nx, nz = -nz, nx
    return nx, nz


class TileRetexture:
    """Tweak class 1 -- the proven DE-QUEST edit (island_morph v5, in-game proven 2026-07-08: the
    donor island's two chocobo Hot&Cold track cells -> plain grass, "no obvious indicator").

    Retexture whole 4u lattice cells of one part to a different tile in the learned tile language:
    geometry, heights and normals stay VERBATIM -- only the UVs + ``tangent.x`` (the IDALL:
    event/area/topograph) change. Match is by IDALL (never by UV rect -- rects vary per-tri) plus
    the DONOR-frame 4u cell ``(floor(x/4), floor(z/4))``, so the tweak is rotation-invariant; the
    ``new_idall`` should be copied from a REAL neighbouring tile of the target family. ``cells``
    maps a cell to its ``(quadrant, orientation)`` for the default mains-grass UV language
    (:func:`ff9mapkit.world.grassland.mains_uv`; pick quadrants under the real neighbour policy --
    never repeat an adjacent cell's quadrant). Pass ``uv_fn(x, z, cell, quad, ori) -> (u, v)`` for
    a different tile family. ``expected`` gates the edit's scope (default: 2 tris per cell)."""

    def __init__(self, *, cells, match_idall: int, new_idall: float, part: str = "terrain",
                 uv_fn=None, expected: int | None = None):
        self.part = part
        self.cells = {tuple(k): tuple(v) for k, v in dict(cells).items()}
        self.match_idall = int(match_idall)
        self.new_idall = float(new_idall)
        self.uv_fn = uv_fn
        self.expected = (2 * len(self.cells)) if expected is None else int(expected)
        self.applied = 0

    def apply(self, part: str, poly):
        if part != self.part or int(round(poly[0][3][0])) != self.match_idall:
            return poly
        cx = sum(v[0][0] for v in poly) / len(poly)
        cz = sum(v[0][2] for v in poly) / len(poly)
        cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        tw = self.cells.get(cell)
        if tw is None:
            return poly
        (quad, ori) = tw
        if self.uv_fn is None:
            from . import grassland as G
            uv_fn = G.mains_uv
        else:
            uv_fn = self.uv_fn
        self.applied += 1
        return [(wpos, nrm, tuple(uv_fn(wpos[0], wpos[2], cell, quad, ori)),
                 (self.new_idall,) + tuple(tan[1:]))
                for (wpos, nrm, _uv, tan) in poly]

    def emit(self) -> list:
        return []

    def gate(self) -> dict:
        return {"gate": f"retile[{self.part}]", "applied": self.applied,
                "expected": self.expected, "ok": self.applied == self.expected}


class PatchRecover:
    """Tweak class 2 -- the proven BEACH-END RE-COVER (island_morph v15/v16, in-game proven
    2026-07-08: the beach one column shorter, its footprint re-covered by a cap-band hexagon
    whose every boundary polyline is byte-original -- "that's it").

    Drop the tris of one part matching ``drop(poly) -> bool`` (donor WORLD coords) and re-cover
    their footprint with a ``fan`` whose corner verts are captured EXACTLY -- bit-exact pos+nrm
    floats -- from the very tris being dropped. THE WELD LAW this encodes: real donor verts are
    off-lattice floats, and every hand-rounded coordinate renders as a hairline crack (the v15
    in-game seams), so geometry is never typed, only captured -- ``corners`` are 1-decimal LOOKUP
    keys, not geometry. Keep every boundary chain byte-original: re-cover a footprint, never
    re-draw its boundary polylines (the slide-the-assembly law).

    ``corners`` name -> approximate ``(x, z)`` (rounded to ``key_decimals`` for the lookup);
    ``fan`` = triangles as corner-name triplets (winding = the local up-face convention);
    ``uv`` name -> ``(u, v)`` in the covering tile; ``idall`` -> the new tris' ``tangent.x``;
    ``expected_drops`` gates the edit's scope exactly. ``emit`` raises if any corner went
    uncaptured (the drop predicate missed its tris)."""

    def __init__(self, *, part: str, drop, corners: dict, fan, uv: dict, idall: float,
                 expected_drops: int, key_decimals: int = 1):
        self.part = part
        self.drop = drop
        self.corners = {str(k): tuple(v) for k, v in dict(corners).items()}
        self.fan = [tuple(t) for t in fan]
        self.uv = {str(k): tuple(v) for k, v in dict(uv).items()}
        self.idall = float(idall)
        self.expected_drops = int(expected_drops)
        self.key_decimals = int(key_decimals)
        self.captured: dict = {}
        self.dropped = 0

    def _key(self, x: float, z: float):
        return (round(x, self.key_decimals), round(z, self.key_decimals))

    def apply(self, part: str, poly):
        if part != self.part or not self.drop(poly):
            return poly
        self.dropped += 1
        for v in poly:
            self.captured.setdefault(self._key(v[0][0], v[0][2]), (v[0], v[1]))
        return None

    def emit(self) -> list:
        missing = [k for k, xz in self.corners.items() if self._key(*xz) not in self.captured]
        if missing:
            raise ValueError(f"PatchRecover[{self.part}]: fan corners not captured from the "
                             f"dropped tris: {missing}")
        out = []
        for tri in self.fan:
            poly = []
            for k in tri:
                (pos, nrm) = self.captured[self._key(*self.corners[k])]
                poly.append((tuple(pos), tuple(nrm), tuple(self.uv[k]),
                             (self.idall, 0.0, 0.0, 0.0)))
            out.append(poly)
        return out

    def gate(self) -> dict:
        return {"gate": f"recover[{self.part}]", "applied": self.dropped,
                "expected": self.expected_drops, "ok": self.dropped == self.expected_drops}


class VertexDisplace:
    """Tweak class 3 (frontier: the multi-column GEOMETRIC waterline move) -- displace exact
    donor verts, weld-preserving by construction: every instance of a keyed position, in EVERY
    part (``part=None``), moves by the same delta, so coincident beach1/sea2/... weld verts stay
    coincident and the weld audit stays at zero. UVs, tangents and normals are left VERBATIM --
    the texture STRETCHES over the moved geometry, which is exactly how real shore-conforming
    tiles absorb lateral waterline variation (measured: real interior waterline verts sit up to
    ~1.5u off the 4u lattice; the swash ribbon's width varies 3.3-6.7u; sea2's wash is uniform
    so its strain is invisible).

    ``moves`` maps an exact donor-frame position ``(x, y, z)`` (a ``key_decimals``-rounding
    LOOKUP key, like :class:`PatchRecover` corners -- the true float is read from the mesh,
    never retyped) to a ``(dx, dy, dz)`` delta. THE ENVELOPE LAWS (do not exceed blindly):
    move only INTERIOR verts (end-assembly welds -- cap bands, corner/sea1 contacts -- are
    load-bearing); keep amplitudes within the measured real envelope; displacement must not
    fold a tile (the per-tri WINDING gate here trips if a touched tri's XZ orientation flips
    or collapses). ``expected`` gates the exact number of moved vert INSTANCES."""

    def __init__(self, *, moves: dict, expected: int, part: str | None = None,
                 key_decimals: int = 4):
        self.part = part
        self.key_decimals = int(key_decimals)
        self.moves = {self._key(k): tuple(v) for k, v in dict(moves).items()}
        self.expected = int(expected)
        self.applied = 0
        self.folds = 0

    def _key(self, p):
        return (round(p[0], self.key_decimals), round(p[1], self.key_decimals),
                round(p[2], self.key_decimals))

    @staticmethod
    def _area2(poly):
        a = 0.0
        for i in range(1, len(poly) - 1):
            a += ((poly[i][0][0] - poly[0][0][0]) * (poly[i + 1][0][2] - poly[0][0][2])
                  - (poly[i + 1][0][0] - poly[0][0][0]) * (poly[i][0][2] - poly[0][0][2]))
        return a

    def apply(self, part: str, poly):
        if self.part is not None and part != self.part:
            return poly
        out = []
        touched = False
        for (pos, nrm, uv, tan) in poly:
            d = self.moves.get(self._key(pos))
            if d is not None:
                pos = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
                touched = True
                self.applied += 1
            out.append((pos, nrm, uv, tan))
        if not touched:
            return poly
        a0, a1 = self._area2(poly), self._area2(out)
        # a plan-degenerate source tri (a real wall face) cannot "fold" in plan -- skip those
        if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
            self.folds += 1                        # flipped or collapsed tile -- gate fails
        return out

    def emit(self) -> list:
        return []

    def gate(self) -> dict:
        return {"gate": f"displace[{self.part or 'all'}]", "applied": self.applied,
                "expected": self.expected, "folds": self.folds,
                "ok": self.applied == self.expected and self.folds == 0}


def _quad_of_uv(uv):
    """Which mains 2x2 quadrant a grass tile's uv sits in (the neighbour-avoid policy's probe)."""
    return (0 if uv[0] < 0.0654 else 1, 0 if uv[1] < 0.7993 else 1)


def _h01(x: float, z: float) -> float:
    """Deterministic position hash (the shader-style frac(sin) convention -- resume-safe)."""
    s = math.sin(x * 12.9898 + z * 78.233) * 43758.5453
    return s - math.floor(s)


def _affine_uv(poly):
    """Plan-affine (u,v) field from a tri's first 3 verts -- exact at its verts. Only valid
    where the real mapping IS plan-affine (flat lattice tiles); steep faces and
    handedness-bearing families need their decoded vocabulary instead."""
    (p0, p1, p2) = [poly[i][0] for i in range(3)]
    (t0, t1, t2) = [poly[i][2] for i in range(3)]
    d = (p1[0] - p0[0]) * (p2[2] - p0[2]) - (p2[0] - p0[0]) * (p1[2] - p0[2])
    if abs(d) < 1e-9:
        return lambda x, z: tuple(t0)
    def f(x, z):
        w1 = ((x - p0[0]) * (p2[2] - p0[2]) - (p2[0] - p0[0]) * (z - p0[2])) / d
        w2 = ((p1[0] - p0[0]) * (z - p0[2]) - (x - p0[0]) * (p1[2] - p0[2])) / d
        w0 = 1.0 - w1 - w2
        return (w0 * t0[0] + w1 * t1[0] + w2 * t2[0], w0 * t0[1] + w1 * t1[1] + w2 * t2[1])
    return f


def _cell_rect(poly):
    """The full UV rect a lattice tile's plan-affine field implies over its OWN 4u cell
    (evaluated at the cell corners -- a single tri's uv extent under-reads the rect).
    Returns ``(key, exact)``: a 3dp-rounded identity key + the exact-float rect, or
    ``None`` for plan-degenerate polys. The rect fingerprints a tile's mains FAMILY
    variant (grass/meadow quadrants, the 1x4 v-strip scrub set, ...)."""
    uvf = _affine_uv(poly)
    n = len(poly)
    cx = 4.0 * math.floor(sum(v[0][0] for v in poly) / n / 4.0)
    cz = 4.0 * math.floor(sum(v[0][2] for v in poly) / n / 4.0)
    us, vs = [], []
    for dx in (0.0, 4.0):
        for dz in (0.0, 4.0):
            u, v = uvf(cx + dx, cz + dz)
            us.append(u); vs.append(v)
    if max(us) - min(us) < 1e-6 and max(vs) - min(vs) < 1e-6:
        return None                                       # degenerate field (steep wall tri)
    exact = (min(us), min(vs), max(us), max(vs))
    return ((round(exact[0], 3), round(exact[1], 3), round(exact[2], 3), round(exact[3], 3)),
            exact)


def _strip_rect(poly):
    """The Wang transition-strip UV rect a tile belongs to (full-u x one v-quarter), or
    ``None`` for a non-strip tile. Strips are DIRECTIONAL: their fills must translate-clone,
    never mirror (a mirrored tip points the wrong way -- in-game 2026-07-09)."""
    rct = _cell_rect(poly)
    if rct is None:
        return None
    (ru0, rv0, ru1, rv1) = rct[1]
    if ru1 - ru0 <= 0.6:
        return None
    from .water import UFULL, VSTRIP
    vmid = (max(0.0, rv0) + min(1.0, rv1)) / 2.0
    k = min(range(4), key=lambda i: abs((VSTRIP[i][0] + VSTRIP[i][1]) / 2.0 - vmid))
    if VSTRIP[k][0] - 0.06 <= vmid <= VSTRIP[k][1] + 0.06:
        return (UFULL[0], VSTRIP[k][0], UFULL[1], VSTRIP[k][1])
    return None


class RowInsert:
    """Tweak class 4 -- the GROWTH SEED (structural; in-game proven 2026-07-08: the (9,17)
    island grown by one lattice column, measured +4u between landmarks, seam invisible).

    Insert a whole ``delta``-unit lattice column at donor-frame plane ``x = line``: every tri
    whose centroid lies east of the line shifts ``+delta`` (soups are unindexed, so
    shared-position verts split per tri -- everything east, junction assemblies included,
    moves INTACT with zero surgery), and the vacated gap is filled by an EXTRUSION of the
    seam profile: seam verts are collected from BOTH halves' tris on the line, z-ordered and
    paired into quads whose west edge = the exact seam verts and east edge = the same verts
    ``+delta`` -- bit-identical welds to both halves BY IDENTITY (no interpolation, no hand
    geometry). Pick ``line`` with a crossing census: it must cross ZERO shore-conforming
    structures (lattice lines through grass/lip/open water qualify; never through a beach
    or a painted wash -- :func:`cut_census` bakes the full component law). ``line`` is
    x-only, and tweaks run BEFORE rotation, so the transplant's ``rot`` cannot re-aim the
    cut at a donor z-line -- a z-axis insertion is :class:`RowInsertZ` (the exact-rotation
    adapter over this class).

    Fill UVs are per structure class (the in-game-proven laws): topo-58 cliff = the decoded
    rock vocabulary (a u-mirror of the west owner -- "both senses used" is real -- with V
    riding each vert's height, never plan-affine); topo-0 GRASS = real mains language
    (neighbour-aware quadrant choice avoiding the ACTUAL west/east tiles + the previous cell,
    one handedness); topo-0 NON-grass (the painted-wash families, e.g. the (9,17) scrub band)
    = a CLONE of the west owner's field translated into the gap (continuing the local wash --
    a variant-avoid pick there maximizes contrast = hard rectangles, in-game 2026-07-09).
    Every topo-0 fill gets a RELIEF centre vert per quad (a +-0.2u deterministic hash, the
    measured real 4u-neighbour roll; the quad boundary -- every weld -- stays bit-exact).
    Everything else (flat water/apron tiles) = the plan-affine mirror, exact there.

    MULTI-BOUNDARY seam extrusion (``boundaries``, the gap-vacation kill, 2026-07-09): a
    REGION cut's shift is global but the line extrusion fills only AT the line -- an EMPTY
    donor cell whose east neighbour has data leaves a delta-wide bare strip at their border
    (the ``gap-vacation`` law). Each ``(plane, z0, z1)`` triple names such a border plane and
    the empty cell's row z-window: the east side's seam profile is collected ON the plane
    (pre-shift -- so the fill's west edge reproduces the original SeaBlockPrefab boundary
    profile bit-exactly) and extruded ``+delta``, welding to the shifted content BY IDENTITY,
    exactly the line mechanic at a second plane. Fills emit only inside the z-window (the
    data rows are covered by the shift itself); UVs come from the SHIFTED east owner --
    mirror about the weld plane ``plane + delta`` (the proven flat-water law, continuous at
    the weld), or the translate-clone for a directional Wang strip. Take the triples from
    :func:`cut_census` ``boundary_fills`` (it certifies the boundary is pure OPEN WATER --
    a fill in any other language is uncertified); a plane west of the line is refused
    (content west of the line never moves, no gap can open there).

    One instance per PART (the tweak protocol emits per part):
    ``tweaks=[RowInsert(p, line=608.0) for p in PARTS]``."""

    def __init__(self, part: str, *, line: float, delta: float = 4.0, eps: float = 1e-4,
                 relief: float = 0.4, seed: int = 0xF95, boundaries=()):
        self.part = part
        self.line = float(line)
        self.delta = float(delta)
        self.eps = float(eps)
        self.relief = float(relief)
        self.seed = int(seed)
        self.shifted = 0
        self.kept = 0
        self.seam: dict = {}              # rounded pos -> exact (pos, nrm)
        self.west_edges: list = []        # (vert_a, vert_b, owner_poly) from WEST tris
        self.east_grass_q: dict = {}      # cell_z -> the shifted east grass tile's quadrant
        self.east_edges: list = []        # (vert_a, vert_b, SHIFTED poly) from EAST tris
        self.cell_rects: dict = {}        # final (cellx, cellz) -> topo-0 family rect key
        self.emitted = 0
        self._bnd: list = []              # empty-cell boundary fills, grouped per plane
        by_plane: dict = {}
        for (b, z0, z1) in boundaries:
            b, z0, z1 = float(b), float(z0), float(z1)
            if b < self.line - self.eps:
                raise ValueError(f"fill boundary {b:g} lies west of the cut line "
                                 f"{self.line:g} -- content west of the line never moves, "
                                 f"no gap can open there")
            by_plane.setdefault(b, []).append((min(z0, z1), max(z0, z1)))
        for b in sorted(by_plane):
            self._bnd.append({"plane": b, "windows": by_plane[b], "seam": {},
                              "east": [], "emitted": 0})

    def _key(self, p):
        return (round(p[0], 4), round(p[1], 4), round(p[2], 4))

    def apply(self, part: str, poly):
        if part != self.part:
            return poly
        from .extract import decode_id
        cx = sum(v[0][0] for v in poly) / len(poly)
        on_line = [v for v in poly if abs(v[0][0] - self.line) <= self.eps]
        topo0 = decode_id(int(round(poly[0][3][0])))["topograph"] == 0
        if cx > self.line:
            self.shifted += 1
            for v in on_line:             # the shifted half's seam verts (pre-shift positions)
                self.seam.setdefault(self._key(v[0]), (v[0], v[1]))
            if on_line and topo0:
                cz = math.floor((sum(v[0][2] for v in poly) / len(poly)) / 4.0)
                self.east_grass_q.setdefault(cz, _quad_of_uv(poly[0][2]))
            shifted = [((p[0] + self.delta, p[1], p[2]), n, uv, tan)
                       for (p, n, uv, tan) in poly]
            if len(on_line) >= 2:
                self.east_edges.append((on_line[0], on_line[1], shifted))
            for st in self._bnd:          # empty-cell boundary seams (pre-shift positions)
                if cx <= st["plane"]:
                    continue
                on_b = [v for v in poly if abs(v[0][0] - st["plane"]) <= self.eps]
                for v in on_b:            # seam verts only inside the empty-cell z-windows
                    if any(z0 - 1e-6 <= v[0][2] <= z1 + 1e-6 for (z0, z1) in st["windows"]):
                        st["seam"].setdefault(self._key(v[0]), (v[0], v[1]))
                if len(on_b) >= 2:
                    st["east"].append((on_b[0], on_b[1], shifted))
            if topo0:
                self._map_cell(shifted)
            return shifted
        self.kept += 1
        for v in on_line:
            self.seam.setdefault(self._key(v[0]), (v[0], v[1]))
        if len(on_line) >= 2:
            self.west_edges.append((on_line[0], on_line[1], poly))
        if topo0:
            self._map_cell(poly)
        return poly

    def _map_cell(self, poly):
        """Record a topo-0 lattice tile's family rect at its FINAL cell (for the emit-time
        neighbour-family probe -- which side of a wash fill is the family boundary)."""
        r = _cell_rect(poly)
        if r is None:
            return
        n = len(poly)
        cell = (math.floor(sum(v[0][0] for v in poly) / n / 4.0),
                math.floor(sum(v[0][2] for v in poly) / n / 4.0))
        self.cell_rects.setdefault(cell, r[0])

    def _pick(self, edges, zmid):
        best = None
        for (a, b, poly) in edges:
            z0, z1 = sorted((a[0][2], b[0][2]))
            if z0 - 0.05 <= zmid <= z1 + 0.05:
                span = z1 - z0
                if best is None or span < best[0]:
                    best = (span, poly)
        return best[1] if best else None

    def _owner(self, zmid):
        return self._pick(self.west_edges, zmid)

    def emit(self) -> list:
        if not self.seam and not any(st["seam"] for st in self._bnd):
            return []
        import random
        from . import grassland as G
        from .extract import decode_id
        rng = random.Random(self.seed)
        pts = sorted(self.seam.values(), key=lambda pn: pn[0][2])
        cell_x = math.floor((self.line + self.delta / 2.0) / 4.0)
        cell_fill: dict = {}    # cell -> ("mains", quad, ori) | ("rect", exact sibling rect)
        prev_q = None
        for (pa, na), (pb, nb) in zip(pts, pts[1:]):
            owner = self._owner((pa[2] + pb[2]) / 2.0)
            if owner is None or decode_id(int(round(owner[0][3][0])))["topograph"] != 0:
                continue
            cell = (cell_x, math.floor(((pa[2] + pb[2]) / 2.0) / 4.0))
            if cell in cell_fill:
                continue
            r = _cell_rect(owner)
            if r is not None and not (0.0 <= r[0][0] and r[0][2] <= 0.13):
                # NON-GRASS mains family (the (9,17) scrub band + kin): a PAINTED WASH, not an
                # interchangeable anti-tiling set -- per-cell re-picks or re-orients fight the
                # paint (hard rectangles / reversed ramps, in-game 2026-07-09). The faithful
                # fill STRETCHES a neighbour tile's half to 2x width, restoring the original
                # painted seam at one fill boundary and hiding the self-tear inside the tile.
                # SIDE RULE: the self-tear must land in UNIFORM material -- if the owner is
                # the family's boundary tile (gradient) and the east tile is wash interior,
                # stretch from the EAST tile instead (in-game 2026-07-09: the west fill's
                # gradient stutter vs the clean east fill).
                okey = r[0]
                east_poly = self._pick(self.east_edges, (pa[2] + pb[2]) / 2.0)
                er = _cell_rect(east_poly) if east_poly is not None else None
                ekey = er[0] if er else None
                fam = lambda a, b: (a is not None and b is not None
                                    and (a[0], a[2]) == (b[0], b[2]))
                owner_bnd = not fam(self.cell_rects.get((cell[0] - 2, cell[1])), okey)
                east_bnd = not fam(self.cell_rects.get((cell[0] + 2, cell[1])), ekey)
                side = "E" if (owner_bnd and not east_bnd and fam(okey, ekey)) else "W"
                cell_fill[cell] = ("stretch", side)
                continue
            avoid = {_quad_of_uv(owner[0][2]), self.east_grass_q.get(cell[1]), prev_q}
            choices = [q for q in ((0, 0), (0, 1), (1, 0), (1, 1)) if q not in avoid]
            prev_q = choices[rng.randrange(len(choices))]
            cell_fill[cell] = ("mains", prev_q, (0, 90, 180, 270)[rng.randrange(4)])

        out = []
        for (pa, na), (pb, nb) in zip(pts, pts[1:]):
            if abs(pb[2] - pa[2]) < 0.05:
                continue                  # coincident-z duplicates (a wall seam) -- nothing to fill
            owner = self._owner((pa[2] + pb[2]) / 2.0)
            if owner is None:
                continue                  # no west tile spans this z-range
            uvf = _affine_uv(owner)
            idall = owner[0][3]
            topo = decode_id(int(round(idall[0])))["topograph"]
            pe_a = (pa[0] + self.delta, pa[1], pa[2])
            pe_b = (pb[0] + self.delta, pb[1], pb[2])
            center = None
            cell = (cell_x, math.floor(((pa[2] + pb[2]) / 2.0) / 4.0))
            if topo == 58:
                far = max((v for v in owner), key=lambda v: abs(v[0][0] - self.line))
                u_far = far[2][0]
                wa = (pa, na, uvf(pa[0], pa[2]))
                wb = (pb, nb, uvf(pb[0], pb[2]))
                ea = (pe_a, na, (u_far, wa[2][1]))
                eb = (pe_b, nb, (u_far, wb[2][1]))
            elif topo == 0 and cell in cell_fill:
                mode = cell_fill[cell]
                if mode[0] == "mains":
                    quad, ori = mode[1], mode[2]
                    mu = lambda p: tuple(G.mains_uv(p[0], p[2], cell, quad, ori))
                else:
                    # painted-wash fill = the STRETCH law (the co-move apron precedent): map
                    # the fill onto a neighbour tile's half at 2x width. One fill boundary
                    # then carries that tile's original edge UVs -- the real painted seam is
                    # RESTORED byte-for-byte there -- and the self-tear hides inside the tile
                    # (the side rule above puts it in uniform material).
                    side = mode[1]
                    src = owner
                    if side == "E":
                        src = self._pick(self.east_edges, (pa[2] + pb[2]) / 2.0) or owner
                        if src is owner:
                            side = "W"
                    uvf_s = uvf if src is owner else _affine_uv(src)
                    rct = _cell_rect(src)
                    (ou0, ov0, ou1, ov1) = rct[1] if rct else (0.0, 0.0, 1.0, 1.0)
                    x_src = (self.line - self.delta / 2.0 if side == "W"
                             else self.line + self.delta)
                    def mu(p, uvf_s=uvf_s, x_src=x_src, ou0=ou0, ov0=ov0, ou1=ou1, ov1=ov1):
                        fu, fv = uvf_s(x_src + (p[0] - self.line) / 2.0, p[2])
                        return (min(ou1, max(ou0, fu)), min(ov1, max(ov0, fv)))
                wa = (pa, na, mu(pa))
                wb = (pb, nb, mu(pb))
                ea = (pe_a, na, mu(pe_a))
                eb = (pe_b, nb, mu(pe_b))
                pcx, pcz = self.line + self.delta / 2.0, (pa[2] + pb[2]) / 2.0
                pcy = (pa[1] + pb[1]) / 2.0 + (_h01(pcx, pcz) - 0.5) * self.relief
                nm = tuple((a + b) / 2.0 for a, b in zip(na, nb))
                nl = math.sqrt(sum(c * c for c in nm)) or 1.0
                center = ((pcx, pcy, pcz), tuple(c / nl for c in nm), mu((pcx, pcy, pcz)))
            else:
                # a WANG transition strip (sea5/sea1: full-u x one v-quarter) is DIRECTIONAL --
                # the plan-affine mirror reverses its orientation (a tip pointing east becomes
                # one pointing west = "the sea isn't properly tiled", in-game 2026-07-09).
                # Real bands repeat their strip along the band with orientation preserved, so
                # the strip fill is a translate-CLONE clamped into the strip rect. Pure
                # quadrant bands + the sand apron keep the mirror (proven, avoids repeats).
                strip_rect = _strip_rect(owner)
                if strip_rect is not None:
                    (su0, sv0, su1, sv1) = strip_rect
                    def mu(p, uvf=uvf, su0=su0, sv0=sv0, su1=su1, sv1=sv1):
                        fu, fv = uvf(p[0] - self.delta, p[2])
                        return (min(su1, max(su0, fu)), min(sv1, max(sv0, fv)))
                    wa = (pa, na, mu(pa))
                    wb = (pb, nb, mu(pb))
                    ea = (pe_a, na, mu(pe_a))
                    eb = (pe_b, nb, mu(pe_b))
                else:
                    wa = (pa, na, uvf(pa[0], pa[2]))
                    wb = (pb, nb, uvf(pb[0], pb[2]))
                    ea = (pe_a, na, uvf(2 * self.line - pe_a[0], pa[2]))
                    eb = (pe_b, nb, uvf(2 * self.line - pe_b[0], pb[2]))
            tris = (((wa, wb, center), (wb, eb, center), (eb, ea, center), (ea, wa, center))
                    if center is not None else ((wa, wb, ea), (eb, ea, wb)))
            for tri in tris:
                t3 = [(p, n, uv, tuple(idall)) for (p, n, uv) in tri]
                ux, uz = t3[1][0][0] - t3[0][0][0], t3[1][0][2] - t3[0][0][2]
                vx, vz = t3[2][0][0] - t3[0][0][0], t3[2][0][2] - t3[0][0][2]
                if uz * vx - ux * vz <= 0:                     # enforce up-facing winding
                    t3 = [t3[0], t3[2], t3[1]]
                out.append(t3)
                self.emitted += 1

        # the MULTI-BOUNDARY fills: extrude the east side's seam profile at each empty-cell
        # border plane, inside the empty cell's row z-window only (data rows are covered by
        # the shift itself). The owner is the SHIFTED east tile: mirror about the weld plane
        # (continuous there, the proven flat-water law) or translate-clone for a Wang strip
        # (samples the owner's field at p.x + delta = the tile's ORIGINAL texels in place).
        for st in self._bnd:
            if not st["seam"]:
                continue
            plane = st["plane"]
            weld_x = plane + self.delta
            pts = sorted(st["seam"].values(), key=lambda pn: pn[0][2])
            for (pa, na), (pb, nb) in zip(pts, pts[1:]):
                if abs(pb[2] - pa[2]) < 0.05:
                    continue              # coincident-z duplicates (a wall seam)
                zmid = (pa[2] + pb[2]) / 2.0
                if not any(z0 - 1e-6 <= zmid <= z1 + 1e-6 for (z0, z1) in st["windows"]):
                    continue              # a data row: the shift keeps it contiguous
                owner = self._pick(st["east"], zmid)
                if owner is None:
                    continue              # no east tile spans this z-range
                uvf = _affine_uv(owner)
                idall = owner[0][3]
                pe_a = (pa[0] + self.delta, pa[1], pa[2])
                pe_b = (pb[0] + self.delta, pb[1], pb[2])
                strip_rect = _strip_rect(owner)
                if strip_rect is not None:
                    (su0, sv0, su1, sv1) = strip_rect
                    def mu(p, uvf=uvf, su0=su0, sv0=sv0, su1=su1, sv1=sv1):
                        fu, fv = uvf(p[0] + self.delta, p[2])
                        return (min(su1, max(su0, fu)), min(sv1, max(sv0, fv)))
                else:
                    def mu(p, uvf=uvf, weld_x=weld_x):
                        return uvf(2.0 * weld_x - p[0], p[2])
                wa = (pa, na, mu(pa))
                wb = (pb, nb, mu(pb))
                ea = (pe_a, na, mu(pe_a))
                eb = (pe_b, nb, mu(pe_b))
                for tri in ((wa, wb, ea), (eb, ea, wb)):
                    t3 = [(p, n, uv, tuple(idall)) for (p, n, uv) in tri]
                    ux, uz = t3[1][0][0] - t3[0][0][0], t3[1][0][2] - t3[0][0][2]
                    vx, vz = t3[2][0][0] - t3[0][0][0], t3[2][0][2] - t3[0][0][2]
                    if uz * vx - ux * vz <= 0:                 # enforce up-facing winding
                        t3 = [t3[0], t3[2], t3[1]]
                    out.append(t3)
                    self.emitted += 1
                    st["emitted"] += 1
        return out

    def inverse_x(self, x: float) -> float:
        """Map a POST-cut x back to its donor-frame witness (the census miss-backmap's tweak
        inverse): shifted content maps back ``-delta``; a point in the FILL column maps to the
        seam line (the fill's donor witness is the seam profile itself)."""
        if x >= self.line + self.delta:
            return x - self.delta
        if x > self.line:
            return self.line
        return x

    def gate(self) -> dict:
        # line obligation: content split AT the line (a non-empty seam, both sides present)
        # must have produced fill. A part nothing of which touches the line (a water line
        # through a terrain-free column) owes no fill -- the on-line part fills there.
        ok = (self.shifted == 0 or self.kept == 0 or not self.seam or self.emitted > 0)
        d = {"gate": f"rowinsert[{self.part}]", "shifted": self.shifted,
             "emitted": self.emitted, "ok": ok}
        if self._bnd:
            # boundary obligation: a plane with east seam content on a shifted build must
            # fill (holes are also census-caught; this names the responsible tweak)
            d["boundary_fills"] = {f"{st['plane']:g}": st["emitted"] for st in self._bnd}
            d["ok"] = ok and (self.shifted == 0
                              or all(st["emitted"] > 0 or not st["seam"]
                                     for st in self._bnd))
        return d


def _split_frame_pairs(weld, planes_x, planes_z, tol: float = 0.05):
    """Split a weld-audit pair list into (interior, frame) pairs. A pair whose BOTH verts lie
    within ``tol`` of the SAME frame plane is a T-JUNCTION AT THE CLIP BOUNDARY -- the frame
    cut runs through off-lattice donor verts (a shifted build puts real shore floats next to
    the frame), leaving two near verts on a surface that is still continuous up to the frame,
    where the neighbouring cell's own render takes over. Benign by construction (learned
    2026-07-09: the 672-cut's single pair, flat water at x=128). INTERIOR near-misses remain
    the crack law and must stay zero."""
    def near(p, v, axis):
        return abs(p[axis] - v) <= tol
    interior, frame = [], []
    for (a, b) in weld:
        onframe = (any(near(a, v, 0) and near(b, v, 0) for v in planes_x)
                   or any(near(a, v, 2) and near(b, v, 2) for v in planes_z))
        (frame if onframe else interior).append((a, b))
    return interior, frame


def _split_border_pairs(pairs, planes_x, planes_z, tol: float = 0.05, exact: float = 1e-6):
    """Split interior weld pairs at INTERIOR block-border planes into ``(cracks, t_pairs)``
    -- the non-easternmost-cut law (the rejected 592 build's two undiagnosed x=64 pairs,
    2026-07-09). A region cut's shift slides off-lattice donor floats next to an interior
    border; the re-partition clip mints bit-exact ON-plane verts, so a float within ``tol``
    of the border pairs with a clip vert while the SURFACE stays continuous through it (the
    float lies on the clipped edge both cells share) -- a benign clip T-junction, same class
    as the frame variant. Border pairs are judged as CLUSTERS (union-find on shared verts):
    a float so close to the border that BOTH its edges' cut verts land within ``tol`` of
    each other also mints an on-plane/on-plane pair, but its cluster carries the off-plane
    WITNESS vert (the (9,5) z-cut's A-C-B corner sliver, 2026-07-09) -- benign, duplicated
    identically on both cells. A cluster whose EVERY vert is bit-exactly ON the plane is two
    cells DISAGREEING about the shared border profile -- impossible while the clip ``t`` is
    bit-identical on both sides, so it stays a CRACK and fails."""
    def plane_of(a, b):
        for axis, planes in ((0, planes_x), (2, planes_z)):
            for v in planes:
                if abs(a[axis] - v) <= tol and abs(b[axis] - v) <= tol:
                    return (axis, v)
        return None
    cracks, border = [], []
    for (a, b) in pairs:
        pl = plane_of(a, b)
        if pl is None:
            cracks.append((a, b))          # away from every border: the plain crack law
        else:
            border.append(((a, b), pl))
    parent: dict = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ((a, b), _pl) in border:
        parent[find(a)] = find(b)
    clusters: dict = {}
    for entry in border:
        clusters.setdefault(find(entry[0][0]), []).append(entry)
    ts = []
    for plist in clusters.values():
        benign = any(abs(w[axis] - v) > exact
                     for ((a, b), (axis, v)) in plist for w in (a, b))
        (ts if benign else cracks).extend(p for (p, _pl) in plist)
    return cracks, ts


def _tweak_inverse_x(tweaks):
    """The composed x-INVERSE of a tweak list's RowInsert cuts (east-to-west, undoing the
    west-to-east application), for the census miss-backmap: a miss at a post-cut x must be
    tested against the donor at its PRE-cut witness, else the donor's own in-situ misses
    shift out from under the backmap and misread as introduced."""
    cuts = sorted({(tw.line, tw.delta) for tw in tweaks if isinstance(tw, RowInsert)},
                  reverse=True)

    def inv(x: float) -> float:
        for (line, delta) in cuts:
            if x >= line + delta:
                x -= delta
            elif x > line:
                x = line
        return x
    return inv


def cut_census(donor, *, size=(1, 1), parts=PARTS, extra: float = 8.0, disc: int = 1,
               lod: str = "0_1", game=None, axis: str = "x") -> list:
    """Component-aware RowInsert cut-line census over a donor block (+ its 8u neighbour
    strips) -- or, with ``size = (nx, ny)``, over a whole DONOR RECT (the multi-cell carry's
    frame): every donor cell is gathered whole, strips come from beyond the REGION's outer
    borders only, and the sweep covers every interior 4u line of the region -- INCLUDING the
    interior block borders (they are ordinary lattice lines to a region cut; the component
    laws below judge them like any other). ``axis="z"`` sweeps the region's interior
    z-lattice planes instead (for :class:`RowInsertZ` cuts: content SOUTH of a line shifts
    southward) via the exact-rotation adapter -- the gathered soup rotates into the frame
    where z-lines are x-lines, the ONE proven sweep runs, and lines/windows map back, so
    every component law transposes automatically (``line`` is then a z plane and
    ``boundary_fills`` triples are ``(plane_z, x0, x1)``). For each line returns a dict:
    ``line``, ``straddlers`` (tris crossing the line -- must be 0), ``grows_land`` (the line
    passes through grass/sand/cliff, so an insertion actually lengthens the island), and
    ``risks``:

    - ``crosses-beach``: the beach1 system has tris strictly on BOTH sides -- the line
      passes through the beach assembly (end welds are load-bearing; never cut it).
    - ``touches-shallows``: the line crosses OR touches the SHORE-BOUND shallow system
      (sea1/sea2 -- shore-conforming Wang bands, COPY-ONLY like the beach): a fill there
      duplicates a transition column = the "inner band" artifact (in-game 2026-07-09).
      Open-water bands (sea3/sea5/sea4) are synthesizable language and stay fair game.
    - ``crosses-wash``: a CONNECTED patch of non-grass topo-0 tiles (a painted wash,
      e.g. the (9,17) scrub blob) has cells on both sides. A wash is PAINT -- per-cell
      fills cannot continue it faithfully (four fill strategies falsified in-game
      2026-07-09); treat it as a component and cut around it.
    - ``crosses-baked-terrain``: the line has an on-line TERRAIN tile from a family
      RowInsert has no dedicated fill for (not grass/sand/cliff) whose UV rect is a
      SINGLETON in the scanned donor+strip area (no sibling tile shares it). The
      highland/rock-wall topos (17/38/49 -- the "highland vocabulary" investigated
      2026-07-09) turned out to have NO discrete tile language to decode: measured across
      an 80-block map sample, topo 49 is 97% unique per-cell UV placement and topo 38 is
      65% unique (within one donor the ratio is starker still) -- these are hand-PAINTED
      murals, the same class as a wash, just detected by uniqueness instead of a
      hardcoded topo id (so a genuinely tileable rock PATCH elsewhere stays fair game).
    - ``displaces-object-ground``: the donor has a prefab-anchored Object whose footprint
      lies east of the line (its ground would shift under the static object).
    - ``conforming-on-line``: an open-water part has an OFF-LATTICE vert ON the line -- a
      shore-conforming water tile touches it, and the water fill's unclamped plan-affine
      mirror extrapolates between off-lattice seam verts (wrapped-atlas "stretched" tiles,
      in-game 2026-07-09). Terrain off-lattice verts stay legal (those fill families are
      position-generated or clamped).
    - ``gap-vacation`` / ``spills-into-empty``: the EMPTY-CELL laws (a region cut's shift
      is global but the seam extrusion fills only at its planes). ``gap-vacation`` -- an
      empty cell's east-neighbour data slides off their shared border -- is now flagged
      ONLY when the boundary is UNFILLABLE: a boundary whose on-plane content in the empty
      row is pure OPEN WATER (sea3/sea5/sea4) is instead reported in ``boundary_fills`` as
      ``(plane, z0, z1)`` triples -- feed them to :func:`chain_row_inserts`
      ``boundaries=`` and the multi-boundary seam extrusion fills the gap in proven water
      language. Any other language on the boundary (land/beach/shallows) keeps the risk:
      those fills are uncertified. ``spills-into-empty`` (west-neighbour content slides
      INTO the empty cell -- a nearly-empty deployed cell over what was sailable prefab
      ocean) has no fill mechanic and always disqualifies.

    A usable GROWTH line has ``ok`` (``straddlers == 0``, ``grows_land``, no ``risks``);
    ``clean`` drops the ``grows_land`` requirement -- a clean pure-water line is a legal
    SLIDE cut (it widens the water and repositions everything east of it, growing the
    assembly without lengthening the land)."""
    from .extract import decode_id
    (dbx, dby) = donor
    (rnx, rny) = (int(size[0]), int(size[1]))
    x0, x1 = 64.0 * dbx, 64.0 * (dbx + rnx)
    strip_specs = []
    for j in range(rny):
        strip_specs.append(((dbx + rnx, dby + j), 0, x1 + extra, True))
        strip_specs.append(((dbx - 1, dby + j), 0, x0 - extra, False))
    for i in range(rnx):
        strip_specs.append(((dbx + i, dby - 1), 2, -64.0 * dby + extra, True))
        strip_specs.append(((dbx + i, dby + rny), 2, -64.0 * (dby + rny) - extra, False))
    polys = []
    cell_has_data = {(i, j): False for i in range(rnx) for j in range(rny)}
    for p in parts:
        for j in range(rny):
            for i in range(rnx):
                for tri in world_tris(dbx + i, dby + j, p, disc=disc, lod=lod, game=game):
                    cell_has_data[(i, j)] = True
                    polys.append((p, list(tri)))
        for (nx, ny), caxis, plane, below in strip_specs:
            if not (0 <= nx < GRID_X and 0 <= ny < GRID_Y):
                continue
            for tri in world_tris(nx, ny, p, disc=disc, lod=lod, game=game):
                c = clip_poly(list(tri), caxis, plane, below)
                if len(c) >= 3:
                    polys.append((p, c))
    obj = [t for j in range(rny) for i in range(rnx)
           for t in world_tris(dbx + i, dby + j, "object", disc=disc, lod=lod, game=game)]
    if axis not in ("x", "z"):
        raise ValueError("axis must be 'x' or 'z'")
    if axis == "z":
        # THE EXACT-ROTATION ADAPTER (see RowInsertZ): rotate the gathered soup into the
        # frame where z-planes are x-planes and run the one proven sweep on it. The donor
        # rect re-indexes to the fake anchor (dby, _ZC/64 - dbx - rnx), size (rny, rnx);
        # lines + boundary windows map back after the sweep.
        polys = [(p, _z_in_poly(poly)) for (p, poly) in polys]
        obj = [_z_in_poly(t) for t in obj]
        cell_has_data = {(j, rnx - 1 - i): v for (i, j), v in cell_has_data.items()}
        (dbx, dby) = (dby, int(_ZC) // 64 - dbx - rnx)
        (rnx, rny) = (rny, rnx)
        x0 = 64.0 * dbx
    obj_xmax = max(v[0][0] for t in obj for v in t) if obj else None
    foam = [poly for (p, poly) in polys if p == "beach1"]
    wash_cells = set()
    for (p, poly) in polys:
        if p != "terrain" or decode_id(int(round(poly[0][3][0])))["topograph"] != 0:
            continue
        r = _cell_rect(poly)
        if r and not r[0][2] <= 0.13:
            n = len(poly)
            wash_cells.add((math.floor(sum(v[0][0] for v in poly) / n / 4.0),
                            math.floor(sum(v[0][2] for v in poly) / n / 4.0)))
    patches = []
    left = set(wash_cells)
    while left:
        comp = {left.pop()}
        stack = list(comp)
        while stack:
            (cx, cz) = stack.pop()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (cx + d[0], cz + d[1])
                if nb in left:
                    left.discard(nb); comp.add(nb); stack.append(nb)
        patches.append(comp)
    # THE BAKED-TERRAIN LAW (the topo 17/38/49 "highland vocabulary" decode, 2026-07-09):
    # unlike grass (topo 0, a small reusable quadrant set) and cliff (topo 58, a decoded
    # rock language), the highland/rock-wall families have NO discrete tile vocabulary to
    # discover -- measured across an 80-block map sample, topo 49 is 97% UNIQUE per-cell UV
    # placement and topo 38 is 65% unique; within a single donor the ratio is even starker
    # (the (9,5) island's own topo 17/38/49 measure 92-100% unique). These are hand-PAINTED
    # murals, structurally the SAME CLASS as a non-grass topo-0 wash -- no per-cell UV
    # synthesis (mirror, clone, or otherwise) can continue them faithfully, independent of
    # relief. Detected generically (not by hardcoded topo id, matching how a real donor
    # elsewhere might reuse a small tileable rock patch legitimately): any TERRAIN family
    # RowInsert has no dedicated fill for (not 0/31/58) whose family rect has NO sibling
    # anywhere in the scanned donor+strip area is baked-unique.
    baked_cells_of_rect = collections.defaultdict(set)
    for (p, poly) in polys:
        if p != "terrain":
            continue
        if decode_id(int(round(poly[0][3][0])))["topograph"] in (0, 31, 58):
            continue
        r = _cell_rect(poly)
        if r is None:
            continue
        n = len(poly)
        cell = (math.floor(sum(v[0][0] for v in poly) / n / 4.0),
               math.floor(sum(v[0][2] for v in poly) / n / 4.0))
        baked_cells_of_rect[r[0]].add(cell)          # a quad's 2 tris share ONE cell -- dedupe
    # the boundary WATER-SAFETY scan (the multi-boundary extrusion's certification): an
    # empty cell's east border is FILLABLE iff every on-plane edge inside the empty row's
    # z-window speaks open water -- the languages the boundary fill is proven in -- AND its
    # on-plane verts sit on the 4u lattice along the plane (the lattice-seam law below:
    # the mirror fill extrapolates between off-lattice seam verts). Any land/beach/shallow
    # edge or off-lattice vert there makes the gap unfillable (gap-vacation stands).
    bnd_info: dict = {}
    for (ci, cj), has in cell_has_data.items():
        if has or not cell_has_data.get((ci + 1, cj)):
            continue
        plane = 64.0 * (dbx + ci + 1)
        z0, z1 = -64.0 * (dby + cj + 1), -64.0 * (dby + cj)
        onb_parts = set()
        onb_lattice = True
        for (p, poly) in polys:
            onb = [v for v in poly if abs(v[0][0] - plane) <= 1e-4]
            if not onb:
                continue
            zm = sum(v[0][2] for v in onb) / len(onb)
            if not (z0 - 1e-4 <= zm <= z1 + 1e-4):
                continue
            if len(onb) >= 2:
                onb_parts.add(p)
            if any(abs(v[0][2] / 4.0 - round(v[0][2] / 4.0)) > 2.5e-4 for v in onb):
                onb_lattice = False
        bnd_info[(ci, cj)] = {"plane": plane, "z": (z0, z1),
                              "safe": bool(onb_parts) and onb_parts <= OPEN_WATER_PARTS
                              and onb_lattice}
    out = []
    for i in range(1, 16 * rnx):
        line = x0 + 4.0 * i
        strad = sum(1 for (p, poly) in polys
                    if min(v[0][0] for v in poly) < line - 1e-4
                    and max(v[0][0] for v in poly) > line + 1e-4)
        grows = any(p == "terrain"
                    and decode_id(int(round(poly[0][3][0])))["topograph"] in (0, 31, 58)
                    and sum(1 for v in poly if abs(v[0][0] - line) <= 1e-4) >= 2
                    for (p, poly) in polys)
        risks = []
        # the RELIEF law: a cut's fill is the seam profile extruded delta-wide -- through steep
        # relief that is a terrace band + holes. Gate the on-line LAND y-span (proven <= 3.5u).
        on_ys = []
        for (p, poly) in polys:
            if p in LAND_PARTS and sum(1 for w in poly if abs(w[0][0] - line) <= 1e-4) >= 2:
                on_ys.extend(v[0][1] for v in poly)
        if on_ys and max(on_ys) - min(on_ys) > MAX_CUT_RELIEF:
            risks.append("crosses-relief")
        fw = sum(1 for t in foam if max(v[0][0] for v in t) <= line + 1e-4)
        fe = sum(1 for t in foam if min(v[0][0] for v in t) >= line - 1e-4)
        if foam and fw and fe:
            risks.append("crosses-beach")
        # the beach END-CAP rule (the (9,17) x=632 disqualification): foam/sand tiles ENDING
        # exactly on the line -- a seam extrusion there re-draws the end-weld assembly
        if any((p == "beach1" or (p == "terrain"
                                  and decode_id(int(round(poly[0][3][0])))["topograph"] == 31))
               and sum(1 for v in poly if abs(v[0][0] - line) <= 1e-4) >= 2
               for (p, poly) in polys):
            risks.append("beach-end-on-line")
        # the SHALLOW-SYSTEM rule: sea1/sea2 are shore-bound (COPY-ONLY) -- disqualify a line
        # that crosses them (straddle can't happen on a clean line; edges ON the line count:
        # extruding the system's boundary column duplicates a transition strip)
        if any(p in ("sea1", "sea2")
               and (sum(1 for v in poly if abs(v[0][0] - line) <= 1e-4) >= 2
                    or (min(v[0][0] for v in poly) < line - 1e-4
                        and max(v[0][0] for v in poly) > line + 1e-4))
               for (p, poly) in polys):
            risks.append("touches-shallows")
        if any(any(4.0 * c[0] + 4.0 <= line + 1e-6 for c in comp)
               and any(4.0 * c[0] >= line - 1e-6 for c in comp) for comp in patches):
            risks.append("crosses-wash")
        baked = False
        for (p, poly) in polys:
            if p != "terrain" or decode_id(int(round(poly[0][3][0])))["topograph"] in (0, 31, 58):
                continue
            if sum(1 for v in poly if abs(v[0][0] - line) <= 1e-4) < 2:
                continue
            r = _cell_rect(poly)
            if r and len(baked_cells_of_rect.get(r[0], ())) <= 1:
                baked = True
                break
        if baked:
            risks.append("crosses-baked-terrain")
        # THE LATTICE-SEAM LAW (in-game 2026-07-09, the (9,5) z=-352 cut: "stretched"
        # cliff-adjacent water tiles): open water's DEFAULT fill is the UNCLAMPED
        # plan-affine mirror -- between OFF-LATTICE seam verts (a shore-conforming water
        # tile touching the line) it extrapolates outside the owner tile and wraps the
        # atlas. An off-lattice on-line vert in an open-water part INSIDE the region frame
        # = shore-conforming geometry ON the line = a component crossing (a strip vert
        # beyond the frame is excluded -- its fills clip away at the frame). Terrain
        # off-lattice verts stay legal (grass/rock/wash fills are position-generated or
        # clamped -- the proven (16,17) 1060 cut; conservative: 1056's shore-contact
        # water now flags).
        zr0, zr1 = -64.0 * (dby + rny), -64.0 * dby
        if any(p in OPEN_WATER_PARTS
               and any(abs(v[0][0] - line) <= 1e-4
                       and zr0 - 1e-4 <= v[0][2] <= zr1 + 1e-4
                       and abs(v[0][2] / 4.0 - round(v[0][2] / 4.0)) > 2.5e-4
                       for v in poly)
               for (p, poly) in polys):
            risks.append("conforming-on-line")
        if obj_xmax is not None and line < obj_xmax - 1e-6:
            risks.append("displaces-object-ground")
        # the EMPTY-CELL laws (a REGION cut's shift is global -- learned 2026-07-09, the
        # (9,5)+2x3 row-0 hole): the seam extrusion fills only at its planes, so any other
        # coverage discontinuity the shift creates goes unfilled. An empty donor cell whose
        # EAST in-rect neighbour has data: a line at-or-west of their border slides the
        # neighbour's content off it -- a delta-wide bare strip. WATER-SAFE boundaries are
        # fillable by the multi-boundary extrusion (reported in `boundary_fills`); any other
        # language keeps `gap-vacation`. An empty cell whose WEST in-rect neighbour has
        # data: a line at-or-west of the empty cell's west border pushes content INTO it --
        # a nearly-empty deployed cell (`spills-into-empty`, no fill mechanic).
        bfills = []
        for (ci, cj), has in cell_has_data.items():
            if has:
                continue
            info = bnd_info.get((ci, cj))
            if info is not None and line <= info["plane"] + 1e-6:
                if info["safe"]:
                    t = [info["plane"], info["z"][0], info["z"][1]]
                    if t not in bfills:
                        bfills.append(t)
                elif "gap-vacation" not in risks:
                    risks.append("gap-vacation")
            if (ci - 1, cj) in cell_has_data and cell_has_data[(ci - 1, cj)] \
                    and line <= 64.0 * (dbx + ci) + 1e-6:
                if "spills-into-empty" not in risks:
                    risks.append("spills-into-empty")
        out.append({"line": line, "straddlers": strad, "grows_land": grows, "risks": risks,
                    "boundary_fills": sorted(bfills),
                    "clean": strad == 0 and not risks,
                    "ok": strad == 0 and grows and not risks})
    for c in out:
        c["axis"] = axis
        if axis == "z":                # map the rotated frame back to world z / x-windows
            c["line"] = -c["line"]
            c["boundary_fills"] = sorted([-b, w0 + _ZC, w1 + _ZC]
                                         for (b, w0, w1) in c["boundary_fills"])
    return out


def chain_row_inserts(lines, *, parts=PARTS, delta: float = 4.0, relief: float = 0.4,
                      seed: int = 0xF95, eps: float = 1e-4, boundaries=()) -> list:
    """Compose several RowInsert cuts into one ``tweaks=`` list (multi-column growth).

    ``lines`` are DONOR-frame x cut lines, each census-clean per the RowInsert law.
    Tweaks apply in list order, so a later (more eastern) cut sees geometry the earlier
    cuts have already shifted: its effective line is its donor line plus every earlier
    cut's delta. This helper sorts the lines west-to-east and applies that cumulative
    correction -- callers think only in the unmodified donor frame. Each cut derives a
    distinct seed so its grass fill rolls its own quadrants and relief.

    ``boundaries`` are the census's ``boundary_fills`` triples ``(plane, z0, z1)`` in the
    DONOR frame (an empty cell's east border + its row z-window): each cut at-or-west of
    a plane extrudes one delta-band there, with the same cumulative ``+ i*delta``
    correction as the lines -- the per-cut bands tile ``[B, B+d], [B+d, B+2d], ...``
    against the stationary empty side, each welding BY IDENTITY to the content the
    previous cut left behind (RowInsert emissions bypass later tweaks, which is exactly
    why the correction lands each band where the prior band's east edge sits).

    A line given twice composes correctly (the second lands one column east) but yields
    two adjacent flat fill bands off one seam profile -- prefer spread-out lines.
    """
    bnds = [(float(b), float(z0), float(z1)) for (b, z0, z1) in boundaries]
    out = []
    for i, ln in enumerate(sorted(float(l) for l in lines)):
        cut_b = [(b + i * delta, z0, z1) for (b, z0, z1) in bnds if ln <= b + 1e-6]
        for p in parts:
            out.append(RowInsert(p, line=ln + i * delta, delta=delta, relief=relief,
                                 seed=seed + 0x9E37 * i, eps=eps, boundaries=cut_b))
    return out


#: The z-adapter frame constant: the proper rotation ``(x, z) -> (-z, x - _ZC)`` maps world
#: coords (x >= 0, z <= 0) onto the same conventions (rotated x' = -z >= 0, z' = x - _ZC < 0
#: for any world x < _ZC = 64*32, beyond the 24x20 grid) -- so a donor-frame z-plane becomes
#: an x-plane and the whole PROVEN x-cut machinery applies verbatim. Swap + sign flip + a
#: power-of-two shift are all BIT-EXACT in float64 on float32-derived donor coords, so the
#: round trip preserves every weld-by-identity law.
_ZC = 2048.0


def _z_in_poly(poly):
    """World -> the z-adapter frame (positions only; normals/uvs/tangents pass through --
    RowInsert copies them vert-to-fill without interpreting axes)."""
    return [((-p[2], p[1], p[0] - _ZC), n, uv, tan) for (p, n, uv, tan) in poly]


def _z_out_poly(poly):
    """The z-adapter frame -> world (exact inverse of :func:`_z_in_poly`)."""
    return [((p[2] + _ZC, p[1], -p[0]), n, uv, tan) for (p, n, uv, tan) in poly]


class RowInsertZ:
    """Tweak class 4z -- the z-axis GROWTH SEED: insert a whole ``delta``-unit lattice ROW at
    donor-frame plane ``z = line``. Everything SOUTH of the line (centroid z < line) shifts
    ``-delta`` (southward, toward the south frame -- the slack side), and the vacated row is
    filled by the seam-profile extrusion, exactly the :class:`RowInsert` laws.

    Implemented as the EXACT-ROTATION ADAPTER: positions rotate into a frame where the cut IS
    the proven x-cut (``(x, z) -> (-z, x - _ZC)`` -- a swap + sign flip + power-of-two shift,
    bit-exact both ways, so seam welds stay identity-exact), the inner :class:`RowInsert` does
    all the work, and emissions rotate back. Normals/UVs/tangents pass through untouched;
    fill UVs are authored in the rotated frame, i.e. legal 90-degree-rotated tile variants
    (the real anti-tiling and Wang sets use all four orientations). Every x-law -- fill
    families, windows, the boundary extrusion -- transposes automatically and inherits future
    fixes.

    ``boundaries`` triples are ``(plane_z, x0, x1)``: an empty cell's SOUTH border (its
    south neighbour's data slides off it) + the empty cell's column x-window -- take them
    from :func:`cut_census` ``axis="z"`` ``boundary_fills``."""

    def __init__(self, part: str, *, line: float, delta: float = 4.0, eps: float = 1e-4,
                 relief: float = 0.4, seed: int = 0xF95, boundaries=()):
        self.part = part
        self.line = float(line)
        self.delta = float(delta)
        self._rw = RowInsert(part, line=-self.line, delta=self.delta, eps=eps, relief=relief,
                             seed=seed,
                             boundaries=[(-float(b), float(x0) - _ZC, float(x1) - _ZC)
                                         for (b, x0, x1) in boundaries])

    def apply(self, part: str, poly):
        if part != self.part:
            return poly
        rp = self._rw.apply(part, _z_in_poly(poly))
        return None if rp is None else _z_out_poly(rp)

    def emit(self) -> list:
        return [_z_out_poly(t) for t in self._rw.emit()]

    def inverse_z(self, z: float) -> float:
        """Map a POST-cut z back to its donor-frame witness (shifted content maps back
        ``+delta``; the fill row maps to the seam line)."""
        return -self._rw.inverse_x(-z)

    def gate(self) -> dict:
        d = self._rw.gate()
        d["gate"] = f"rowinsertz[{self.part}]"
        if "boundary_fills" in d:      # inner keys are rotated planes -- present world z
            d["boundary_fills"] = {f"{-float(k):g}": v for k, v in d["boundary_fills"].items()}
        return d


def chain_row_inserts_z(lines, *, parts=PARTS, delta: float = 4.0, relief: float = 0.4,
                        seed: int = 0xF95, eps: float = 1e-4, boundaries=()) -> list:
    """z-axis :func:`chain_row_inserts`: ``lines`` are DONOR-frame z cut planes, sorted
    NORTH-to-SOUTH; content shifts southward, so a later (more southern) cut's donor line
    rides ``- i*delta`` (the mirror of the x chain's ``+ i*delta``), and each boundary
    plane a cut owes (its line at-or-north of it) rides the same correction."""
    bnds = [(float(b), float(x0), float(x1)) for (b, x0, x1) in boundaries]
    out = []
    for i, ln in enumerate(sorted((float(l) for l in lines), reverse=True)):
        cut_b = [(b - i * delta, x0, x1) for (b, x0, x1) in bnds if ln >= b - 1e-6]
        for p in parts:
            out.append(RowInsertZ(p, line=ln - i * delta, delta=delta, relief=relief,
                                  seed=seed + 0x9E37 * i, eps=eps, boundaries=cut_b))
    return out


def _tweak_inverse_z(tweaks):
    """The composed z-INVERSE of a tweak list's RowInsertZ cuts (south-to-north, undoing the
    north-to-south application) -- the census miss-backmap's z counterpart."""
    cuts = sorted({(tw.line, tw.delta) for tw in tweaks if isinstance(tw, RowInsertZ)})

    def inv(z: float) -> float:
        for (line, delta) in cuts:
            if z <= line - delta:
                z += delta
            elif z < line:
                z = line
        return z
    return inv


def _rot_region_xz(x: float, z: float, nrot: int, ext, ext_r):
    """Rotate a REGION-LOCAL point (frame x 0..ext[0], z -ext[1]..0) about the region centre by
    ``nrot`` 90-degree steps into the ROTATED frame (x 0..ext_r[0], z -ext_r[1]..0). Region extents
    are multiples of 64, so the half-extent pivot sits on the 4u lattice and the lattice maps to
    itself. A 1x1 region (ext = ext_r = (64, 64)) is arithmetically :func:`_rot_xz`."""
    dx, dz = x - ext[0] / 2.0, z + ext[1] / 2.0
    for _ in range(nrot):
        dx, dz = -dz, dx
    return ext_r[0] / 2.0 + dx, -ext_r[1] / 2.0 + dz


def _soup_block_mesh(name: str, cell, tris, *, disc: int, lod: str) -> BlockMesh:
    """A BlockMesh from (pos, nrm, uv, tan) triangles in the block-LOCAL frame -- fresh verts per
    tri (unindexed, matching the stock world blocks), all four channels carried."""
    (bx, by) = cell
    pos, nrm, uv, tan, flat, tridx = [], [], [], [], [], []
    for tri in tris:
        base = len(pos)
        for (p, n, u, t) in tri:
            pos.append(list(p)); nrm.append(list(n)); uv.append(list(u)); tan.append(list(t))
            flat.append(len(pos) - 1)
        tridx.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=disc, x=bx, y=by, lod=lod, vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tridx, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def transplant(mod_folder: str, *, cell, donor, rot: int = 0, shift="auto", parts=PARTS,
               tweaks=(), strips="auto", extra: float = 8.0, land_margin: float = 2.0,
               disc: int = 1, lod: str = "0_1", game=None, census_samples: int = 24,
               allow_real_target: bool = False, allow_object_misalign: bool = False,
               dry_run: bool = False) -> dict:
    """Carry the complete real ``donor`` block to ocean ``cell``, rotated by ``rot`` (0/90/180/270
    about the cell centre) and rigid-shifted by ``shift`` (0-mod-4 units; ``"auto"`` centres the
    LAND within the coverage-feasible window), with optional component ``tweaks``. All sub-mesh
    ``parts`` come along verbatim: the donor's own tris plus an ``extra``-unit edge strip from the
    neighbour blocks selected by ``strips`` (the proven (8,17) island tongue, generalized),
    Sutherland-Hodgman clipped at the cell frame so shore-conforming tiles keep their inside part
    exactly.

    ``strips="auto"`` (default) gathers an edge strip from EVERY data-bearing neighbour for
    BORDER COVERAGE (in situ, a neighbour's shore-conforming tiles straddle the border; without
    them the border sub-tile slivers read as census holes) -- but the SHIFT WINDOW opens only
    toward borders the donor's own LAND reaches (the island-tongue rule). Neighbour blocks are
    real world-map blocks with their own content (a FOREIGN landmass' edge): at zero shift their
    strips clip away entirely, and a shift can only pull in the donor's own land continuation --
    so foreign content never enters the frame. ``"none"`` disables strips; ``"all"`` opens the
    window to every data-bearing strip; an explicit set (e.g. ``("E", "N")``) gathers + windows
    exactly those (expert mode).

    GATES (every one must pass or the deploy is REFUSED -- inspect ``summary["gates"]``):
    frame bounds; land fit within ``land_margin`` (an ISLAND default -- pass ``land_margin=0`` for
    a donor whose land legitimately reaches the block border); each tweak's exact edit-scope count;
    the :func:`ff9mapkit.world.mesh.weld_audit` (0 near-miss vertex pairs, like the verbatim donor);
    and the engine-placement census (``miss == 0`` -- full walk/sail coverage). ``dry_run`` builds
    and gates without writing. A donor part whose tris all clip away is BLANKED (a hidden override)
    so the donor prefab's original sub-mesh cannot render unrotated underneath.

    Returns a summary dict (``clean``, ``gates``, ``carried``, ``shift``, ``deployed`` paths)."""
    (bx, by) = cell
    (dbx, dby) = donor
    if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
        raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    if not (0 <= dbx < GRID_X and 0 <= dby < GRID_Y):
        raise ValueError(f"donor ({dbx},{dby}) out of the {GRID_X}x{GRID_Y} overworld grid")
    # THE TARGET must be OPEN OCEAN (no per-block mesh assets -- it renders from the shared
    # SeaBlockPrefab). A cell with real data is part of the game's world: overriding it replaces
    # real continent/coast geometry and shreds the whole area (proven the hard way, 2026-07-08).
    if not allow_real_target:
        occupied = {p: len(world_tris(bx, by, p, disc=disc, lod=lod, game=game))
                    for p in parts}
        occupied = {p: n for p, n in occupied.items() if n}
        if occupied:
            raise ValueError(f"target cell ({bx},{by}) is a REAL world block ({occupied}) -- "
                             f"transplanting onto it would replace real game geometry. Pick an "
                             f"empty open-ocean cell (no block mesh data), or pass "
                             f"allow_real_target=True if you really mean it")
    if rot not in (0, 90, 180, 270):
        raise ValueError("rot must be 0, 90, 180 or 270 -- 90-degree multiples keep the 4u tile "
                         "lattice (and the Wang ocean) fully verbatim; free angles do not")
    nrot = rot // 90
    tweaks = list(tweaks)
    parts = tuple(parts)
    # THE OBJECT ANCHOR (proven the hard way 2026-07-09): a donor's Object sub-mesh (cave /
    # town / trees) renders from the donor PREFAB at its original block-local pose -- the kit
    # neither carries nor transforms it. Any net displacement of the GROUND under its
    # footprint (rotation, shift, or a RowInsert whose line lies west of the footprint's east
    # edge) tears the world around a static object. Gated below with the other gates.
    obj_tris = world_tris(dbx, dby, "object", disc=disc, lod=lod, game=game)

    # 1) GATHER (donor WORLD coords): the donor block + an `extra`-wide edge strip from the
    #    selected neighbours, tweaks applied per poly, emissions appended after their part.
    strip_specs = {"E": ((dbx + 1, dby), 0, 64.0 * (dbx + 1) + extra, True),
                   "W": ((dbx - 1, dby), 0, 64.0 * dbx - extra, False),
                   "N": ((dbx, dby - 1), 2, -64.0 * dby + extra, True),
                   "S": ((dbx, dby + 1), 2, -64.0 * (dby + 1) - extra, False)}
    donor_by_part = {p: world_tris(dbx, dby, p, disc=disc, lod=lod, game=game) for p in parts}
    # the island-tongue rule: a strip belongs to the donor's own land UNIT iff its land
    # reaches that border -- only those strips may open the shift window
    borders = {"E": (0, 64.0 * (dbx + 1), -1.0), "W": (0, 64.0 * dbx, 1.0),
               "N": (2, -64.0 * dby, -1.0), "S": (2, -64.0 * (dby + 1), 1.0)}
    tongue = {d for d, (axis, plane, sgn) in borders.items()
              if any(sgn * (v[0][axis] - plane) <= 1.0
                     for p in parts if p in LAND_PARTS
                     for tri in donor_by_part[p] for v in tri)}
    if strips == "auto":
        gathered, windowed = set(strip_specs), tongue
    elif strips == "all":
        gathered = windowed = set(strip_specs)
    elif strips in ("none", None):
        gathered = windowed = set()
    else:
        gathered = windowed = {str(d).upper() for d in strips}
        if not gathered <= set(strip_specs):
            raise ValueError(f"strips must be 'auto', 'all', 'none' or a set of E/W/N/S -- got {strips!r}")
    raw: dict = {}
    donor_has_part: dict = {}
    strips_with_data: set = set()
    for p in parts:
        donor_tris = donor_by_part[p]
        donor_has_part[p] = bool(donor_tris)
        srcs = [(None, donor_tris, None)]
        for dname, ((nx2, ny2), axis, plane, below) in strip_specs.items():
            if dname in gathered and 0 <= nx2 < GRID_X and 0 <= ny2 < GRID_Y:
                srcs.append((dname, world_tris(nx2, ny2, p, disc=disc, lod=lod, game=game),
                             (axis, plane, below)))
        polys = []
        for (dname, tris, clip) in srcs:
            for tri in tris:
                poly = list(tri)
                if clip is not None:
                    poly = clip_poly(poly, *clip)
                    if len(poly) < 3:
                        continue
                    strips_with_data.add(dname)
                for tw in tweaks:
                    poly = tw.apply(p, poly)
                    if poly is None:
                        break
                if poly is None:
                    continue
                polys.append((dname, poly))
        for tw in tweaks:
            if tw.part == p:
                polys.extend((None, e) for e in tw.emit())
        raw[p] = polys
    if not any(donor_has_part.values()):
        raise ValueError(f"donor ({dbx},{dby}) has no block mesh data -- open ocean renders from the "
                         f"shared SeaBlockPrefab; pick a real coastal donor (world-coast --list)")

    # 2) ROTATE about the donor-local cell centre; LAND normals rotate (real slopes), sea normals
    #    keep the uniform byte constant every real tile shares regardless of tile rotation.
    #    The auto-shift land bbox counts the donor's OWN land + its tongue strips only -- a
    #    foreign (non-tongue) strip's land must not steer the centring or the land-fit.
    lb = [math.inf, -math.inf, math.inf, -math.inf]          # rotated UNIT-land bbox (pre-shift)
    rot_polys: dict = {}
    for p in parts:
        land = p in LAND_PARTS
        rp = []
        for (dname, poly) in raw[p]:
            unit_land = land and (dname is None or dname in windowed)
            tp = []
            for (wpos, nrm, uvv, tan) in poly:
                rx, rz = _rot_xz(wpos[0] - 64.0 * dbx, wpos[2] + 64.0 * dby, nrot)
                if land:
                    rnx, rnz = _rot_dir(nrm[0], nrm[2], nrot)
                    nrm = (rnx, nrm[1], rnz)
                if unit_land:
                    lb[0] = min(lb[0], rx); lb[1] = max(lb[1], rx)
                    lb[2] = min(lb[2], rz); lb[3] = max(lb[3], rz)
                tp.append(((rx, wpos[1], rz), nrm, uvv, tan))
            rp.append(tp)
        rot_polys[p] = rp

    # 3) SHIFT within the coverage-feasible window: shifting vacates a frame edge, and the only
    #    refill data beyond the donor frame is a WINDOWED (tongue) strip whose ROTATED image sits
    #    at that edge -- so each edge allows up to `extra` units iff its strip actually has data.
    avail = {_DIR_OF[(round(rdx), round(rdz))]
             for (rdx, rdz) in (_rot_dir(*_DIRS[d], nrot)
                                for d in (strips_with_data & windowed))}
    win_x = ((-extra if "E" in avail else 0.0), (extra if "W" in avail else 0.0))
    win_z = ((-extra if "N" in avail else 0.0), (extra if "S" in avail else 0.0))
    if shift in (None, "auto"):
        if math.isinf(lb[0]):
            sh_x = sh_z = 0.0                                # no land -- nothing to centre
        else:
            sh_x = max(win_x[0], min(win_x[1], 4.0 * round((32.0 - (lb[0] + lb[1]) / 2.0) / 4.0)))
            sh_z = max(win_z[0], min(win_z[1], 4.0 * round((-32.0 - (lb[2] + lb[3]) / 2.0) / 4.0)))
    else:
        sh_x, sh_z = float(shift[0]), float(shift[1])
        if sh_x % 4.0 or sh_z % 4.0:
            raise ValueError(f"shift ({sh_x:+g},{sh_z:+g}) must be multiples of 4 -- 0-mod-4 keeps "
                             f"every 4u lattice tile (the Wang ocean included) fully verbatim")
        if not (win_x[0] - 1e-9 <= sh_x <= win_x[1] + 1e-9
                and win_z[0] - 1e-9 <= sh_z <= win_z[1] + 1e-9):
            raise ValueError(f"shift ({sh_x:+g},{sh_z:+g}) outside the coverage-feasible window "
                             f"x[{win_x[0]:g},{win_x[1]:g}] z[{win_z[0]:g},{win_z[1]:g}] -- the "
                             f"only refill data beyond the donor frame is its neighbours' "
                             f"{extra:g}u edge strips (with data: {sorted(avail) or 'none'})")

    # 4) SHIFT + CLIP at the four frame planes + fan-triangulate (degenerate slivers skipped).
    bb = [math.inf, -math.inf, math.inf, -math.inf]
    lbc = [math.inf, -math.inf, math.inf, -math.inf]         # POST-clip land bbox (the gate's)
    carried: dict = {}
    clipped_out: dict = {}
    part_tris: dict = {}
    dropped_area2 = 0.0
    for p in parts:
        land = p in LAND_PARTS
        tris = []
        n_clip = 0
        for poly0 in rot_polys[p]:
            poly = [((v[0][0] + sh_x, v[0][1], v[0][2] + sh_z), v[1], v[2], v[3]) for v in poly0]
            for (axis, plane, below) in ((0, 0.0, False), (0, 64.0, True),
                                         (2, -64.0, False), (2, 0.0, True)):
                poly = clip_poly(poly, axis, plane, below)
                if len(poly) < 3:
                    break
            if len(poly) < 3:
                n_clip += 1
                continue
            for j in range(1, len(poly) - 1):
                t3 = [poly[0], poly[j], poly[j + 1]]
                a2 = _tri_area2_3d(t3)
                if a2 > MIN_TRI_AREA2:
                    for v in t3:
                        bb[0] = min(bb[0], v[0][0]); bb[1] = max(bb[1], v[0][0])
                        bb[2] = min(bb[2], v[0][2]); bb[3] = max(bb[3], v[0][2])
                        if land:
                            lbc[0] = min(lbc[0], v[0][0]); lbc[1] = max(lbc[1], v[0][0])
                            lbc[2] = min(lbc[2], v[0][2]); lbc[3] = max(lbc[3], v[0][2])
                    tris.append(t3)
                else:
                    dropped_area2 += a2
        part_tris[p] = tris
        carried[p] = len(tris)
        clipped_out[p] = n_clip

    # 5) BlockMeshes -- a donor part whose tris all clipped away must be BLANKED (else the donor
    #    prefab's ORIGINAL sub-mesh renders unrotated/unshifted underneath the transplant).
    from . import mesh as M
    meshes = []
    blanked = []
    for p in parts:
        nm = f"Block[{bx}][{by}] {part_name(p)}"
        if part_tris[p]:
            bm = _soup_block_mesh(nm, (bx, by), part_tris[p], disc=disc, lod=lod)
        elif donor_has_part[p]:
            bm = M.hidden_block_mesh(name=nm, disc=disc, x=bx, y=by, lod=lod)
            blanked.append(p)
        else:
            continue
        meshes.append((part_name(p), bm))

    # 6) GATES -- all must pass; I cannot see the game, these substitute for eyes.
    gates = []
    gates.append({"gate": "bounds", "x": [bb[0], bb[1]], "z": [bb[2], bb[3]],
                  "ok": (-FRAME_EPS <= bb[0] and bb[1] <= 64.0 + FRAME_EPS
                         and -64.0 - FRAME_EPS <= bb[2] and bb[3] <= FRAME_EPS)})
    lb_c = None if math.isinf(lbc[0]) else list(lbc)
    gates.append({"gate": "land-fit", "bbox": lb_c, "margin": land_margin,
                  "ok": lb_c is None or (lb_c[0] >= land_margin and lb_c[1] <= 64.0 - land_margin
                                         and lb_c[2] >= -64.0 + land_margin
                                         and lb_c[3] <= -land_margin)})
    if obj_tris:
        ox = [v[0][0] for t in obj_tris for v in t]
        oz = [v[0][2] for t in obj_tris for v in t]
        moved = (nrot != 0 or sh_x != 0.0 or sh_z != 0.0
                 or any(isinstance(tw, RowInsert) and tw.line < max(ox) - 1e-6
                        for tw in tweaks)
                 or any(isinstance(tw, RowInsertZ) and tw.line > min(oz) + 1e-6
                        for tw in tweaks))
        gates.append({"gate": "object-anchor", "x": [min(ox), max(ox)],
                      "z": [min(oz), max(oz)], "moved": moved,
                      "ok": (not moved) or allow_object_misalign})
    for tw in tweaks:
        gates.append(tw.gate())
    weld_in, weld_fr = _split_frame_pairs(M.weld_audit(meshes), (0.0, 64.0), (0.0, -64.0))
    gates.append({"gate": "weld-audit", "pairs": len(weld_in), "frame_pairs": len(weld_fr),
                  "ok": not weld_in})
    # THE CLIP-DROP gate (the hairline law's root accounting, 2026-07-09): the sliver
    # filter may only discard TRUE degenerates (collinear clip products, ~1e-9 each) --
    # any real dropped area is a coverage hole in the making (the (0,4) z-slide's 0.001u-
    # deep border seam was invisible to every probe grid but plain in this ledger).
    gates.append({"gate": "clip-drop", "area2": dropped_area2, "ok": dropped_area2 < 1e-3})
    from . import placement as P
    cen = P.census(meshes, samples=census_samples)
    # a real donor may MISS in situ (e.g. under a cliff headland's wall shadow -- no up-facing
    # ground there in the real game either). The transplant law: no INTRODUCED misses -- every
    # miss must map back (inverse shift+rot) to a point where the DONOR ITSELF misses.
    introduced = []
    inherited = 0
    if cen["miss"]:
        donor_meshes = []
        for p in parts:
            if not donor_by_part[p]:
                continue
            loc = [[((v[0][0] - 64.0 * dbx, v[0][1], v[0][2] + 64.0 * dby), v[1], v[2], v[3])
                    for v in t] for t in donor_by_part[p]]
            donor_meshes.append((part_name(p), _soup_block_mesh(f"donor {p}", (dbx, dby), loc,
                                                                disc=disc, lod=lod)))
        tinv = _tweak_inverse_x(tweaks)
        tinv_z = _tweak_inverse_z(tweaks)
        for (mx, mz) in cen["miss"]:
            ux, uz = mx - sh_x, mz - sh_z
            dlx, dlz = _rot_xz(ux, uz, (4 - nrot) % 4)
            dlx = tinv(dlx + 64.0 * dbx) - 64.0 * dbx      # undo RowInsert cuts (donor world x)
            dlz = tinv_z(dlz - 64.0 * dby) + 64.0 * dby    # undo RowInsertZ cuts (donor world z)
            if not (-FRAME_EPS <= dlx <= 64.0 + FRAME_EPS
                    and -64.0 - FRAME_EPS <= dlz <= FRAME_EPS):
                introduced.append((mx, mz))            # maps outside the donor frame: a strip hole
            elif P.place(donor_meshes, dlx, dlz)[1] == "MISS":
                inherited += 1
            else:
                introduced.append((mx, mz))
    gates.append({"gate": "census", "miss": len(cen["miss"]), "inherited": inherited,
                  "introduced": len(introduced), "samples": census_samples * census_samples,
                  "ok": not introduced})
    clean = all(g["ok"] for g in gates)

    summary = {"op": "transplant", "donor": [dbx, dby], "cell": [bx, by], "rot": rot,
               "shift": [sh_x, sh_z], "window": {"x": list(win_x), "z": list(win_z)},
               "strips": sorted(strips_with_data & windowed),
               "coverage_strips": sorted(strips_with_data - windowed), "carried": carried,
               "clipped_out": clipped_out, "blanked": blanked, "gates": gates,
               "clean": clean, "dry_run": dry_run, "deployed": []}
    if dry_run or not clean:
        return summary
    for (pn, bm) in meshes:
        summary["deployed"].append(str(M.deploy_override(bm, mod_folder=mod_folder, game=game,
                                                         lod=lod, part=pn)))
    summary["deployed"].append(str(M.deploy_donor_sidecar(dbx, dby, mod_folder=mod_folder,
                                                          disc=disc, x=bx, y=by, lod=lod,
                                                          game=game)))
    return summary


def transplant_region(mod_folder: str, *, cell, donor, size=(1, 1), rot: int = 0, shift="auto",
                      parts=PARTS, tweaks=(), strips="auto", extra: float = 8.0,
                      land_margin: float = 2.0, disc: int = 1, lod: str = "0_1", game=None,
                      census_samples: int = 24, allow_real_target: bool = False,
                      allow_object_misalign: bool = False, dry_run: bool = False) -> dict:
    """MULTI-CELL verbatim transplant: carry a CONNECTED RECT of ``size = (nx, ny)`` real donor
    blocks (anchor ``donor`` = the rect's min-x/min-y cell) to the target rect anchored at ocean
    ``cell``, as ONE rigid assembly -- rotated by ``rot`` about the REGION centre (a 90/270
    rotation swaps the target rect to ny x nx) and shifted by ``shift`` (0-mod-4). This is the
    unlock past the single-donor growth ceiling: a real 2-block landmass (191 adjacent pairs have
    land crossing a shared border) carries as a unit instead of one block + 8u tongue strips.

    The pipeline generalizes :func:`transplant` (which stays byte-identical for ``size=(1,1)`` --
    tested): GATHER every donor cell whole + ``extra``-unit strips along the REGION's outer
    borders only (interior borders are complete by construction -- both sides are carried);
    tweaks apply in donor WORLD coords (protocol unchanged); ROTATE about the region centre;
    SHIFT within the coverage-feasible window (the island-tongue law, per region border); then
    RE-PARTITION at the target rect's 64u block borders (the :func:`clip_poly` cut ``t`` is
    bit-identical on both sides of a shared border, so cross-border seams are watertight by
    construction -- the ``_split_at_borders`` law).

    PER-CELL DEPLOY (the s34 contract): each data-bearing target cell gets its own sub-mesh
    overrides + a ``Donor.txt`` sidecar naming a donor-rect block whose PREFAB hosts them. The
    sidecar donor must carry a SUPERSET of the cell's parts (RegisterBlockComponent binds by
    transform name -- a part the prefab lacks silently doesn't render: the ``prefab-parts``
    gate), any prefab part NOT carried is blanked, and a Terrain override always deploys
    (``HasLandOverride`` keys the divert on it). An OBJECT-bearing donor cell is never used as
    the sidecar for a foreign target cell (its prefab Object would ghost there); at identity
    transform its own target cell legitimately renders it. A target cell with no tris at all is
    skipped whole -- it stays true SeaBlockPrefab ocean.

    GATES (region-aware; all must pass or the deploy is refused): frame bounds; land fit within
    ``land_margin`` of the REGION's outer frame (interior borders exempt -- a real 2-block
    landmass crosses them); object-anchor per donor cell; each tweak's exact scope; the weld
    audit over the whole region IN REGION FRAME (cross-border cracks live between cells);
    prefab-parts; and the placement census -- engine-faithful (each probe consults only its
    CONTAINING cell's meshes, like the engine's per-block raycast), misses backmapped through
    the inverse transform to the donor's per-cell meshes (no INTRODUCED misses; a backmap into
    a data-less donor cell is introduced -- in situ that point was sailable SeaBlockPrefab
    ocean, on a deployed cell it would be a void + vehicle wall)."""
    (bx, by) = cell
    (dbx, dby) = donor
    (nx, ny) = (int(size[0]), int(size[1]))
    if nx < 1 or ny < 1:
        raise ValueError(f"size must be at least 1x1 -- got {nx}x{ny}")
    if rot not in (0, 90, 180, 270):
        raise ValueError("rot must be 0, 90, 180 or 270 -- 90-degree multiples keep the 4u tile "
                         "lattice (and the Wang ocean) fully verbatim; free angles do not")
    nrot = rot // 90
    (tw, th) = (nx, ny) if nrot % 2 == 0 else (ny, nx)
    if not (0 <= dbx and dbx + nx <= GRID_X and 0 <= dby and dby + ny <= GRID_Y):
        raise ValueError(f"donor rect ({dbx},{dby})+{nx}x{ny} out of the {GRID_X}x{GRID_Y} "
                         f"overworld grid")
    if not (0 <= bx and bx + tw <= GRID_X and 0 <= by and by + th <= GRID_Y):
        raise ValueError(f"target rect ({bx},{by})+{tw}x{th} (rot {rot}) out of the "
                         f"{GRID_X}x{GRID_Y} overworld grid")
    tweaks = list(tweaks)
    parts = tuple(parts)
    ext = (64.0 * nx, 64.0 * ny)                     # donor-region extent
    ext_r = (64.0 * tw, 64.0 * th)                   # rotated/target-region extent
    dcells = [(i, j) for j in range(ny) for i in range(nx)]
    tcells = [(i, j) for j in range(th) for i in range(tw)]

    if not allow_real_target:
        for (i, j) in tcells:
            occupied = {p: len(world_tris(bx + i, by + j, p, disc=disc, lod=lod, game=game))
                        for p in parts}
            occupied = {p: n for p, n in occupied.items() if n}
            if occupied:
                raise ValueError(f"target cell ({bx + i},{by + j}) is a REAL world block "
                                 f"({occupied}) -- transplanting onto it would replace real game "
                                 f"geometry. Pick empty open-ocean cells, or pass "
                                 f"allow_real_target=True if you really mean it")

    donor_cell_part = {(i, j): {p: world_tris(dbx + i, dby + j, p, disc=disc, lod=lod, game=game)
                                for p in parts} for (i, j) in dcells}
    donor_cell_has = {c: {p for p in parts if donor_cell_part[c][p]} for c in dcells}
    if not any(donor_cell_has[c] for c in dcells):
        raise ValueError(f"donor rect ({dbx},{dby})+{nx}x{ny} has no block mesh data -- open "
                         f"ocean renders from the shared SeaBlockPrefab; pick a rect containing "
                         f"a real landmass (world-coast --list browses coastal donors)")
    obj_by_cell = {c: world_tris(dbx + c[0], dby + c[1], "object", disc=disc, lod=lod, game=game)
                   for c in dcells}

    # 1) GATHER (donor WORLD coords): every donor cell whole + an `extra`-wide strip along each
    #    OUTER region border from the blocks beyond it (interior borders are complete -- both
    #    sides are carried whole). The island-tongue law is tested against the REGION border.
    strip_specs = {
        "E": [((dbx + nx, dby + j), 0, 64.0 * (dbx + nx) + extra, True) for j in range(ny)],
        "W": [((dbx - 1, dby + j), 0, 64.0 * dbx - extra, False) for j in range(ny)],
        "N": [((dbx + i, dby - 1), 2, -64.0 * dby + extra, True) for i in range(nx)],
        "S": [((dbx + i, dby + ny), 2, -64.0 * (dby + ny) - extra, False) for i in range(nx)]}
    borders = {"E": (0, 64.0 * (dbx + nx), -1.0), "W": (0, 64.0 * dbx, 1.0),
               "N": (2, -64.0 * dby, -1.0), "S": (2, -64.0 * (dby + ny), 1.0)}
    tongue = {d for d, (axis, plane, sgn) in borders.items()
              if any(sgn * (v[0][axis] - plane) <= 1.0
                     for c in dcells for p in parts if p in LAND_PARTS
                     for tri in donor_cell_part[c][p] for v in tri)}
    if strips == "auto":
        gathered, windowed = set(strip_specs), tongue
    elif strips == "all":
        gathered = windowed = set(strip_specs)
    elif strips in ("none", None):
        gathered = windowed = set()
    else:
        gathered = windowed = {str(d).upper() for d in strips}
        if not gathered <= set(strip_specs):
            raise ValueError(f"strips must be 'auto', 'all', 'none' or a set of E/W/N/S -- got {strips!r}")
    raw: dict = {}
    strips_with_data: set = set()
    for p in parts:
        srcs = [(None, donor_cell_part[c][p], None) for c in dcells]
        for dname, specs in strip_specs.items():
            if dname not in gathered:
                continue
            for ((nx2, ny2), axis, plane, below) in specs:
                if 0 <= nx2 < GRID_X and 0 <= ny2 < GRID_Y:
                    srcs.append((dname, world_tris(nx2, ny2, p, disc=disc, lod=lod, game=game),
                                 (axis, plane, below)))
        polys = []
        for (dname, tris, clip) in srcs:
            for tri in tris:
                poly = list(tri)
                if clip is not None:
                    poly = clip_poly(poly, *clip)
                    if len(poly) < 3:
                        continue
                    strips_with_data.add(dname)
                for tw_ in tweaks:
                    poly = tw_.apply(p, poly)
                    if poly is None:
                        break
                if poly is None:
                    continue
                polys.append((dname, poly))
        for tw_ in tweaks:
            if tw_.part == p:
                polys.extend((None, e) for e in tw_.emit())
        raw[p] = polys

    # 2) ROTATE about the donor REGION centre; LAND normals rotate, sea normals keep the shared
    #    byte constant. The unit-land bbox (auto-shift + land-fit) counts the donors' own land +
    #    windowed tongue strips only, in the ROTATED (target-region) frame.
    lb = [math.inf, -math.inf, math.inf, -math.inf]
    rot_polys: dict = {}
    for p in parts:
        land = p in LAND_PARTS
        rp = []
        for (dname, poly) in raw[p]:
            unit_land = land and (dname is None or dname in windowed)
            tp = []
            for (wpos, nrm, uvv, tan) in poly:
                rx, rz = _rot_region_xz(wpos[0] - 64.0 * dbx, wpos[2] + 64.0 * dby, nrot,
                                        ext, ext_r)
                if land:
                    rnx, rnz = _rot_dir(nrm[0], nrm[2], nrot)
                    nrm = (rnx, nrm[1], rnz)
                if unit_land:
                    lb[0] = min(lb[0], rx); lb[1] = max(lb[1], rx)
                    lb[2] = min(lb[2], rz); lb[3] = max(lb[3], rz)
                tp.append(((rx, wpos[1], rz), nrm, uvv, tan))
            rp.append(tp)
        rot_polys[p] = rp

    # 3) SHIFT within the coverage-feasible window (per REGION border, same law as transplant).
    avail = {_DIR_OF[(round(rdx), round(rdz))]
             for (rdx, rdz) in (_rot_dir(*_DIRS[d], nrot)
                                for d in (strips_with_data & windowed))}
    win_x = ((-extra if "E" in avail else 0.0), (extra if "W" in avail else 0.0))
    win_z = ((-extra if "N" in avail else 0.0), (extra if "S" in avail else 0.0))
    if shift in (None, "auto"):
        if math.isinf(lb[0]):
            sh_x = sh_z = 0.0
        else:
            sh_x = max(win_x[0], min(win_x[1],
                                     4.0 * round((ext_r[0] / 2.0 - (lb[0] + lb[1]) / 2.0) / 4.0)))
            sh_z = max(win_z[0], min(win_z[1],
                                     4.0 * round((-ext_r[1] / 2.0 - (lb[2] + lb[3]) / 2.0) / 4.0)))
    else:
        sh_x, sh_z = float(shift[0]), float(shift[1])
        if sh_x % 4.0 or sh_z % 4.0:
            raise ValueError(f"shift ({sh_x:+g},{sh_z:+g}) must be multiples of 4 -- 0-mod-4 keeps "
                             f"every 4u lattice tile (the Wang ocean included) fully verbatim")
        if not (win_x[0] - 1e-9 <= sh_x <= win_x[1] + 1e-9
                and win_z[0] - 1e-9 <= sh_z <= win_z[1] + 1e-9):
            raise ValueError(f"shift ({sh_x:+g},{sh_z:+g}) outside the coverage-feasible window "
                             f"x[{win_x[0]:g},{win_x[1]:g}] z[{win_z[0]:g},{win_z[1]:g}] -- the "
                             f"only refill data beyond the region frame is its neighbours' "
                             f"{extra:g}u edge strips (with data: {sorted(avail) or 'none'})")

    # 4) SHIFT + RE-PARTITION at the target rect's block borders. Both halves of a border-
    #    straddling tri share bit-identical cut points (the clip `t` is the same expression on
    #    either side), so the border weld is exact by construction. Everything is kept in the
    #    REGION frame here -- the weld audit + census must see cross-border geometry in ONE
    #    frame; translation to block-local happens only at BlockMesh construction.
    bb = [math.inf, -math.inf, math.inf, -math.inf]
    lbc = [math.inf, -math.inf, math.inf, -math.inf]
    cell_tris = {c: {p: [] for p in parts} for c in tcells}
    carried: dict = {}
    clipped_out: dict = {}
    dropped_area2 = 0.0
    for p in parts:
        land = p in LAND_PARTS
        n_clip = 0
        n_kept = 0
        for poly0 in rot_polys[p]:
            poly = [((v[0][0] + sh_x, v[0][1], v[0][2] + sh_z), v[1], v[2], v[3]) for v in poly0]
            xs = [v[0][0] for v in poly]
            zs = [v[0][2] for v in poly]
            i0 = max(0, math.floor((min(xs) + 1e-9) / 64.0))
            i1 = min(tw - 1, math.floor((max(xs) - 1e-9) / 64.0))
            j0 = max(0, math.floor((-max(zs) + 1e-9) / 64.0))
            j1 = min(th - 1, math.floor((-min(zs) - 1e-9) / 64.0))
            survived = False
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    q = poly
                    for (axis, plane, below) in ((0, 64.0 * i, False), (0, 64.0 * (i + 1), True),
                                                 (2, -64.0 * (j + 1), False), (2, -64.0 * j, True)):
                        q = clip_poly(q, axis, plane, below)
                        if len(q) < 3:
                            break
                    if len(q) < 3:
                        continue
                    for k in range(1, len(q) - 1):
                        t3 = [q[0], q[k], q[k + 1]]
                        a2 = _tri_area2_3d(t3)
                        if a2 <= MIN_TRI_AREA2:
                            dropped_area2 += a2
                        else:
                            survived = True
                            for v in t3:
                                bb[0] = min(bb[0], v[0][0]); bb[1] = max(bb[1], v[0][0])
                                bb[2] = min(bb[2], v[0][2]); bb[3] = max(bb[3], v[0][2])
                                if land:
                                    lbc[0] = min(lbc[0], v[0][0]); lbc[1] = max(lbc[1], v[0][0])
                                    lbc[2] = min(lbc[2], v[0][2]); lbc[3] = max(lbc[3], v[0][2])
                            cell_tris[(i, j)][p].append(t3)
                            n_kept += 1
            if not survived:
                n_clip += 1
        carried[p] = n_kept
        clipped_out[p] = n_clip

    # 5) PER-CELL sidecar donors + blanking + region-frame audit/census mesh lists.
    #    The natural sidecar = the donor cell the target cell maps back to (its prefab hosted
    #    exactly this geometry in situ); a fallback donor must carry a SUPERSET of the cell's
    #    parts and must NOT bear an Object (a foreign cell would ghost-render its prefab Object).
    from . import mesh as M
    inv_rot = (4 - nrot) % 4
    cell_meta: dict = {}
    prefab_bad: list = []
    deploy_meshes: dict = {}                  # (i, j) -> [(part_name, block-local BlockMesh)]
    audit_meshes: list = []                   # region-frame soups, all cells (the weld gate's)
    census_meshes: dict = {}                  # (i, j) -> [(part_name, region-frame BlockMesh)]
    for (i, j) in tcells:
        need = [p for p in parts if cell_tris[(i, j)][p]]
        if not need:
            continue                          # stays true SeaBlockPrefab ocean -- nothing deploys
        ccx, ccz = 64.0 * i + 32.0, -64.0 * j - 32.0
        dlx, dlz = _rot_region_xz(ccx - sh_x, ccz - sh_z, inv_rot, ext_r, ext)
        nat = (min(nx - 1, max(0, math.floor(dlx / 64.0))),
               min(ny - 1, max(0, math.floor(-dlz / 64.0))))
        pick = None
        if set(need) <= donor_cell_has[nat]:
            pick = nat
        else:
            for c in dcells:
                if c != nat and not obj_by_cell[c] and set(need) <= donor_cell_has[c]:
                    pick = c
                    break
        if pick is None:
            prefab_bad.append({"cell": [bx + i, by + j], "need": need,
                               "natural": [dbx + nat[0], dby + nat[1]]})
            continue
        blanked = sorted(donor_cell_has[pick] - set(need), key=parts.index)
        meshes = []
        for p in parts:
            nm = f"Block[{bx + i}][{by + j}] {part_name(p)}"
            if cell_tris[(i, j)][p]:
                loc = [[((v[0][0] - 64.0 * i, v[0][1], v[0][2] + 64.0 * j), v[1], v[2], v[3])
                        for v in t] for t in cell_tris[(i, j)][p]]
                bm = _soup_block_mesh(nm, (bx + i, by + j), loc, disc=disc, lod=lod)
                reg = _soup_block_mesh(nm, (bx + i, by + j), cell_tris[(i, j)][p],
                                       disc=disc, lod=lod)
            elif p in donor_cell_has[pick]:
                bm = M.hidden_block_mesh(name=nm, disc=disc, x=bx + i, y=by + j, lod=lod)
                reg = bm
            else:
                continue
            meshes.append((part_name(p), bm))
            audit_meshes.append((part_name(p), reg))
            census_meshes.setdefault((i, j), []).append((part_name(p), reg))
        deploy_meshes[(i, j)] = meshes
        cell_meta[(i, j)] = {"cell": [bx + i, by + j], "donor": [dbx + pick[0], dby + pick[1]],
                             "carried": {p: len(cell_tris[(i, j)][p]) for p in need},
                             "blanked": blanked}

    # 6) GATES -- all must pass; I cannot see the game, these substitute for eyes.
    gates = []
    gates.append({"gate": "bounds", "x": [bb[0], bb[1]], "z": [bb[2], bb[3]],
                  "ok": (-FRAME_EPS <= bb[0] and bb[1] <= ext_r[0] + FRAME_EPS
                         and -ext_r[1] - FRAME_EPS <= bb[2] and bb[3] <= FRAME_EPS)})
    lb_c = None if math.isinf(lbc[0]) else list(lbc)
    gates.append({"gate": "land-fit", "bbox": lb_c, "margin": land_margin,
                  "ok": lb_c is None or (lb_c[0] >= land_margin
                                         and lb_c[1] <= ext_r[0] - land_margin
                                         and lb_c[2] >= -ext_r[1] + land_margin
                                         and lb_c[3] <= -land_margin)})
    for c in dcells:
        if not obj_by_cell[c]:
            continue
        ox = [v[0][0] for t in obj_by_cell[c] for v in t]
        oz = [v[0][2] for t in obj_by_cell[c] for v in t]
        moved = (nrot != 0 or sh_x != 0.0 or sh_z != 0.0
                 or any(isinstance(tw_, RowInsert) and tw_.line < max(ox) - 1e-6
                        for tw_ in tweaks)
                 or any(isinstance(tw_, RowInsertZ) and tw_.line > min(oz) + 1e-6
                        for tw_ in tweaks))
        gates.append({"gate": f"object-anchor[{dbx + c[0]},{dby + c[1]}]",
                      "x": [min(ox), max(ox)], "z": [min(oz), max(oz)], "moved": moved,
                      "ok": (not moved) or allow_object_misalign})
    for tw_ in tweaks:
        gates.append(tw_.gate())
    gates.append({"gate": "prefab-parts", "bad": prefab_bad, "ok": not prefab_bad})
    weld_in, weld_fr = _split_frame_pairs(M.weld_audit(audit_meshes),
                                          (0.0, ext_r[0]), (0.0, -ext_r[1]))
    weld_in, weld_bt = _split_border_pairs(weld_in, tuple(64.0 * i for i in range(1, tw)),
                                           tuple(-64.0 * j for j in range(1, th)))
    gates.append({"gate": "weld-audit", "pairs": len(weld_in), "frame_pairs": len(weld_fr),
                  "border_t_pairs": len(weld_bt), "ok": not weld_in})
    # THE CLIP-DROP gate (the hairline law's root accounting -- see transplant()): real
    # dropped area = a hole in the making, at ANY thinness a probe grid could step over.
    gates.append({"gate": "clip-drop", "area2": dropped_area2, "ok": dropped_area2 < 1e-3})

    # region census, engine-faithful: each probe consults only its CONTAINING cell's meshes
    # (the engine raycasts the containing block); a probe over an undeployed cell is skipped
    # (true SeaBlockPrefab ocean in-game). Misses backmap to the donor's per-cell meshes.
    from . import placement as P
    donor_meshes: dict = {}
    for c in dcells:
        dml = []
        for p in parts:
            if not donor_cell_part[c][p]:
                continue
            loc = [[((v[0][0] - 64.0 * dbx, v[0][1], v[0][2] + 64.0 * dby), v[1], v[2], v[3])
                    for v in t] for t in donor_cell_part[c][p]]
            dml.append((part_name(p), _soup_block_mesh(f"donor {p}", c, loc, disc=disc, lod=lod)))
        donor_meshes[c] = dml
    sx_n, sz_n = census_samples * tw, census_samples * th
    probed = 0
    misses = []
    for a in range(sx_n):
        for b_ in range(sz_n):
            px = 2.0 + (ext_r[0] - 4.0) * a / (sx_n - 1)
            pz = -ext_r[1] + 2.0 + (ext_r[1] - 4.0) * b_ / (sz_n - 1)
            tc = (min(tw - 1, max(0, math.floor(px / 64.0))),
                  min(th - 1, max(0, math.floor(-pz / 64.0))))
            ml = census_meshes.get(tc)
            if ml is None:
                continue
            probed += 1
            if P.place(ml, px, pz)[1] == "MISS":
                misses.append((px, pz))
    introduced = []
    inherited = 0
    tinv = _tweak_inverse_x(tweaks)
    tinv_z = _tweak_inverse_z(tweaks)
    for (mx, mz) in misses:
        dlx, dlz = _rot_region_xz(mx - sh_x, mz - sh_z, inv_rot, ext_r, ext)
        dlx = tinv(dlx + 64.0 * dbx) - 64.0 * dbx          # undo RowInsert cuts (donor world x)
        dlz = tinv_z(dlz - 64.0 * dby) + 64.0 * dby        # undo RowInsertZ cuts (donor world z)
        if not (-FRAME_EPS <= dlx <= ext[0] + FRAME_EPS
                and -ext[1] - FRAME_EPS <= dlz <= FRAME_EPS):
            introduced.append((mx, mz))               # maps outside the region: a strip hole
            continue
        dc = (min(nx - 1, max(0, math.floor(dlx / 64.0))),
              min(ny - 1, max(0, math.floor(-dlz / 64.0))))
        if donor_meshes[dc] and P.place(donor_meshes[dc], dlx, dlz)[1] == "MISS":
            inherited += 1                            # the donor misses there in situ too
        else:
            introduced.append((mx, mz))
    gates.append({"gate": "census", "miss": len(misses), "inherited": inherited,
                  "introduced": len(introduced), "samples": probed, "ok": not introduced})

    # BORDER MICRO-CENSUS (the hairline law's eyes, 2026-07-09): the coarse census grid
    # cannot see a hairline gap at a re-partition plane (the (0,4) z-slide's 0.8u x 0.004u
    # dropped-sliver hole read in-game as "a seam in the cliff"). Probe pairs straddling
    # every interior border at 0.5u steps: ANY missing side that does not backmap to a
    # donor miss is a border HOLE (the proven hole missed on BOTH sides -- each cell had
    # lost its own hairline fragment, so a one-sided-only parity test stays blind). A
    # side over an undeployed cell is the prefab boundary -- skipped (the sea prefab
    # renders there). The inset must be NARROWER than the gaps it hunts -- the proven
    # hole was only ~0.001u deep, so 0.0005; but ANY finite inset can be stepped over,
    # which is why the clip-drop ledger above is the root gate for the dropped-sliver
    # class and this probe net covers the others (a missing fill, a shifted band).
    def _donor_misses_at(px, pz):
        dlx, dlz = _rot_region_xz(px - sh_x, pz - sh_z, inv_rot, ext_r, ext)
        dlx = tinv(dlx + 64.0 * dbx) - 64.0 * dbx
        dlz = tinv_z(dlz - 64.0 * dby) + 64.0 * dby
        if not (-FRAME_EPS <= dlx <= ext[0] + FRAME_EPS
                and -ext[1] - FRAME_EPS <= dlz <= FRAME_EPS):
            return False
        dc = (min(nx - 1, max(0, math.floor(dlx / 64.0))),
              min(ny - 1, max(0, math.floor(-dlz / 64.0))))
        return bool(donor_meshes[dc]) and P.place(donor_meshes[dc], dlx, dlz)[1] == "MISS"

    bd = 0.0005
    bholes = []
    bprobed = 0
    bplanes = ([(0, 64.0 * i) for i in range(1, tw)]
               + [(2, -64.0 * j) for j in range(1, th)])
    for (baxis, plane) in bplanes:
        span = ext_r[1] if baxis == 0 else ext_r[0]
        for k in range(int(span / 0.5)):
            t = 0.25 + 0.5 * k
            pa = (plane - bd, -t) if baxis == 0 else (t, plane + bd)
            pb = (plane + bd, -t) if baxis == 0 else (t, plane - bd)
            res = []
            for (px, pz) in (pa, pb):
                tc = (min(tw - 1, max(0, math.floor(px / 64.0))),
                      min(th - 1, max(0, math.floor(-pz / 64.0))))
                ml = census_meshes.get(tc)
                res.append(None if ml is None else P.place(ml, px, pz)[1])
            if None in res:
                continue                      # an undeployed side: the prefab boundary
            bprobed += 1
            for (r, (px, pz)) in zip(res, (pa, pb)):
                if r == "MISS" and not _donor_misses_at(px, pz):
                    bholes.append((px, pz))
    gates.append({"gate": "border-census", "holes": len(bholes), "probed": bprobed,
                  "ok": not bholes})
    clean = all(g["ok"] for g in gates)

    summary = {"op": "transplant-region", "donor": [dbx, dby], "size": [nx, ny],
               "cell": [bx, by], "tsize": [tw, th], "rot": rot, "shift": [sh_x, sh_z],
               "window": {"x": list(win_x), "z": list(win_z)},
               "strips": sorted(strips_with_data & windowed),
               "coverage_strips": sorted(strips_with_data - windowed), "carried": carried,
               "clipped_out": clipped_out,
               "cells": {f"{bx + i},{by + j}": cell_meta[(i, j)] for (i, j) in tcells
                         if (i, j) in cell_meta},
               "gates": gates, "clean": clean, "dry_run": dry_run, "deployed": []}
    if dry_run or not clean:
        return summary
    for (i, j) in tcells:
        if (i, j) not in deploy_meshes:
            continue
        for (pn, bm) in deploy_meshes[(i, j)]:
            summary["deployed"].append(str(M.deploy_override(bm, mod_folder=mod_folder,
                                                             game=game, lod=lod, part=pn)))
        (sdx, sdy) = cell_meta[(i, j)]["donor"]
        summary["deployed"].append(str(M.deploy_donor_sidecar(sdx, sdy, mod_folder=mod_folder,
                                                              disc=disc, x=bx + i, y=by + j,
                                                              lod=lod, game=game)))
    return summary
