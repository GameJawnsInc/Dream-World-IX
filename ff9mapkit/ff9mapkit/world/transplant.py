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
MIN_TRI_AREA2 = 0.02                 # post-clip degenerate-sliver filter (2x the xz area)
PROVEN_DONOR = (7, 17)               # the in-game-proven beach island (E tongue in (8,17))

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
               dry_run: bool = False) -> dict:
    """Carry the complete real ``donor`` block to ocean ``cell``, rotated by ``rot`` (0/90/180/270
    about the cell centre) and rigid-shifted by ``shift`` (0-mod-4 units; ``"auto"`` centres the
    LAND within the coverage-feasible window), with optional component ``tweaks``. All sub-mesh
    ``parts`` come along verbatim: the donor's own tris plus an ``extra``-unit edge strip from the
    neighbour blocks selected by ``strips`` (the proven (8,17) island tongue, generalized),
    Sutherland-Hodgman clipped at the cell frame so shore-conforming tiles keep their inside part
    exactly.

    ``strips="auto"`` carries a neighbour strip ONLY where the donor's own LAND reaches that
    border -- the island's tongue continues there, so the strip is part of the island UNIT.
    Neighbour blocks are real world-map blocks with their own content (a FOREIGN landmass' edge,
    someone else's coast): carrying them silently pollutes the transplant, so they never come
    along unless asked -- pass an explicit direction set (e.g. ``("E", "N")``), ``"all"``, or
    ``"none"``. The shift window follows the carried strips: shifting may only vacate an edge a
    carried strip refills, by at most ``extra`` units.

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
    if rot not in (0, 90, 180, 270):
        raise ValueError("rot must be 0, 90, 180 or 270 -- 90-degree multiples keep the 4u tile "
                         "lattice (and the Wang ocean) fully verbatim; free angles do not")
    nrot = rot // 90
    tweaks = list(tweaks)
    parts = tuple(parts)

    # 1) GATHER (donor WORLD coords): the donor block + an `extra`-wide edge strip from the
    #    selected neighbours, tweaks applied per poly, emissions appended after their part.
    strip_specs = {"E": ((dbx + 1, dby), 0, 64.0 * (dbx + 1) + extra, True),
                   "W": ((dbx - 1, dby), 0, 64.0 * dbx - extra, False),
                   "N": ((dbx, dby - 1), 2, -64.0 * dby + extra, True),
                   "S": ((dbx, dby + 1), 2, -64.0 * (dby + 1) - extra, False)}
    donor_by_part = {p: world_tris(dbx, dby, p, disc=disc, lod=lod, game=game) for p in parts}
    if strips == "auto":
        # a strip is part of the island UNIT iff the donor's own land reaches that border
        borders = {"E": (0, 64.0 * (dbx + 1), -1.0), "W": (0, 64.0 * dbx, 1.0),
                   "N": (2, -64.0 * dby, -1.0), "S": (2, -64.0 * (dby + 1), 1.0)}
        selected = {d for d, (axis, plane, sgn) in borders.items()
                    if any(sgn * (v[0][axis] - plane) <= 1.0
                           for p in parts if p in LAND_PARTS
                           for tri in donor_by_part[p] for v in tri)}
    elif strips == "all":
        selected = set(strip_specs)
    elif strips in ("none", None):
        selected = set()
    else:
        selected = {str(d).upper() for d in strips}
        if not selected <= set(strip_specs):
            raise ValueError(f"strips must be 'auto', 'all', 'none' or a set of E/W/N/S -- got {strips!r}")
    raw: dict = {}
    donor_has_part: dict = {}
    strips_with_data: set = set()
    for p in parts:
        donor_tris = donor_by_part[p]
        donor_has_part[p] = bool(donor_tris)
        srcs = [(None, donor_tris, None)]
        for dname, ((nx2, ny2), axis, plane, below) in strip_specs.items():
            if dname in selected and 0 <= nx2 < GRID_X and 0 <= ny2 < GRID_Y:
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
                polys.append(poly)
        for tw in tweaks:
            if tw.part == p:
                polys.extend(tw.emit())
        raw[p] = polys
    if not any(donor_has_part.values()):
        raise ValueError(f"donor ({dbx},{dby}) has no block mesh data -- open ocean renders from the "
                         f"shared SeaBlockPrefab; pick a real coastal donor (world-coast --list)")

    # 2) ROTATE about the donor-local cell centre; LAND normals rotate (real slopes), sea normals
    #    keep the uniform byte constant every real tile shares regardless of tile rotation.
    lb = [math.inf, -math.inf, math.inf, -math.inf]          # rotated LAND bbox (pre-shift)
    rot_polys: dict = {}
    for p in parts:
        land = p in LAND_PARTS
        rp = []
        for poly in raw[p]:
            tp = []
            for (wpos, nrm, uvv, tan) in poly:
                rx, rz = _rot_xz(wpos[0] - 64.0 * dbx, wpos[2] + 64.0 * dby, nrot)
                if land:
                    rnx, rnz = _rot_dir(nrm[0], nrm[2], nrot)
                    nrm = (rnx, nrm[1], rnz)
                    lb[0] = min(lb[0], rx); lb[1] = max(lb[1], rx)
                    lb[2] = min(lb[2], rz); lb[3] = max(lb[3], rz)
                tp.append(((rx, wpos[1], rz), nrm, uvv, tan))
            rp.append(tp)
        rot_polys[p] = rp

    # 3) SHIFT within the coverage-feasible window: shifting vacates a frame edge, and the only
    #    refill data beyond the donor frame is a neighbour strip whose ROTATED image sits at that
    #    edge -- so each edge allows up to `extra` units iff its strip actually has data.
    avail = {_DIR_OF[(round(rdx), round(rdz))]
             for (rdx, rdz) in (_rot_dir(*_DIRS[d], nrot) for d in strips_with_data)}
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
    carried: dict = {}
    clipped_out: dict = {}
    part_tris: dict = {}
    for p in parts:
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
                area2 = abs((t3[1][0][0] - t3[0][0][0]) * (t3[2][0][2] - t3[0][0][2])
                            - (t3[2][0][0] - t3[0][0][0]) * (t3[1][0][2] - t3[0][0][2]))
                if area2 > MIN_TRI_AREA2:
                    for v in t3:
                        bb[0] = min(bb[0], v[0][0]); bb[1] = max(bb[1], v[0][0])
                        bb[2] = min(bb[2], v[0][2]); bb[3] = max(bb[3], v[0][2])
                    tris.append(t3)
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
    lb_s = None if math.isinf(lb[0]) else [lb[0] + sh_x, lb[1] + sh_x, lb[2] + sh_z, lb[3] + sh_z]
    gates.append({"gate": "bounds", "x": [bb[0], bb[1]], "z": [bb[2], bb[3]],
                  "ok": (-FRAME_EPS <= bb[0] and bb[1] <= 64.0 + FRAME_EPS
                         and -64.0 - FRAME_EPS <= bb[2] and bb[3] <= FRAME_EPS)})
    gates.append({"gate": "land-fit", "bbox": lb_s, "margin": land_margin,
                  "ok": lb_s is None or (lb_s[0] >= land_margin and lb_s[1] <= 64.0 - land_margin
                                         and lb_s[2] >= -64.0 + land_margin
                                         and lb_s[3] <= -land_margin)})
    for tw in tweaks:
        gates.append(tw.gate())
    weld = M.weld_audit(meshes)
    gates.append({"gate": "weld-audit", "pairs": len(weld), "ok": not weld})
    from . import placement as P
    cen = P.census(meshes, samples=census_samples)
    gates.append({"gate": "census", "miss": len(cen["miss"]),
                  "samples": census_samples * census_samples, "ok": not cen["miss"]})
    clean = all(g["ok"] for g in gates)

    summary = {"op": "transplant", "donor": [dbx, dby], "cell": [bx, by], "rot": rot,
               "shift": [sh_x, sh_z], "window": {"x": list(win_x), "z": list(win_z)},
               "strips": sorted(strips_with_data), "carried": carried,
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
