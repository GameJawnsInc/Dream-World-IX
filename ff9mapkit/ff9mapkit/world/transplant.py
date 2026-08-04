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
import warnings

from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, decode_id, encode_id
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

#: prioritized sidecar-donor candidates for the map-wide prefab fallback (the
#: proven beach donors carry the fullest part sets); the full block scan follows
_PREFAB_CANDIDATES = ((7, 17), (13, 8), (9, 17), (3, 13), (10, 17), (16, 5))
_prefab_fallback_cache: dict = {}


def _prefab_fallback(need, *, disc, lod, game):
    """A map-wide sidecar donor whose prefab hosts a SUPERSET of ``need`` and
    bears no Object -- the multi-cell-carry fallback with the search widened
    past the region: a SYNTHESIZED part set (e.g. a minted beach on a
    beach-less donor) has no in-region host by construction. Returns
    ``((bx, by), parts)`` or ``(None, None)``."""
    key = (frozenset(need), disc, lod)
    if key in _prefab_fallback_cache:
        return _prefab_fallback_cache[key]
    from .extract import list_blocks

    def probe(b):
        if world_tris(b[0], b[1], "object", disc=disc, lod=lod, game=game):
            return None
        have = {p for p in ("terrain", "beach1", "sea2", "sea1", "sea3",
                            "sea5", "sea4")
                if world_tris(b[0], b[1], p, disc=disc, lod=lod, game=game)}
        return have if set(need) <= have else None

    for b in _PREFAB_CANDIDATES:
        have = probe(b)
        if have is not None:
            _prefab_fallback_cache[key] = (tuple(b), have)
            return _prefab_fallback_cache[key]
    for b in sorted(list_blocks(disc=disc, lod=lod)):
        b = (b[0], b[1])
        if b in _PREFAB_CANDIDATES:
            continue
        have = probe(b)
        if have is not None:
            _prefab_fallback_cache[key] = (b, have)
            return _prefab_fallback_cache[key]
    _prefab_fallback_cache[key] = (None, None)
    return _prefab_fallback_cache[key]


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


#: MEASURED layout support per retile pair -- the share of the SOURCE family's mains tris
#: whose position WITHIN its own rect also occurs in the destination family. Every family's
#: mains rect is the same size (0.1230 x 0.0615), so the retile is a pure rigid shift; what
#: this table measures is whether the two families actually TILE that rect the same way.
#:
#: THE HEADLINE: grass<->desert (0.708/0.762) is the only strong pair, and it is exactly the
#: pair that was measured and proven in-game (the desert bench). The retile's in-game success
#: is therefore evidence about ONE PAIR, not about the operator. A low-support target still
#: samples the right family's texture -- the uv lands inside its rect -- but uses sub-tile
#: arrangements stock essentially never uses for that family.
#:
#: Regenerate: py studies/coast-shape-language/ground_translation_census.py --disc 1
#: Full table + reading guide: studies/coast-shape-language/GROUND-TRANSLATION-CENSUS.md
LAYOUT_SUPPORT = {
    'brush': {'canyon': 0.0089, 'desert': 0.0095, 'dunes': 0.2979, 'grass': 0.0116,
              'scrub': 0.0, 'snow': 0.0},
    'canyon': {'brush': 0.0215, 'desert': 0.0039, 'dunes': 0.0, 'grass': 0.0033,
               'scrub': 0.0072, 'snow': 0.0},
    'desert': {'brush': 0.0045, 'canyon': 0.0009, 'dunes': 0.0016, 'grass': 0.7621,
               'scrub': 0.0015, 'snow': 0.2441},
    'dunes': {'brush': 0.3319, 'canyon': 0.0, 'desert': 0.0043, 'grass': 0.0087,
              'scrub': 0.0, 'snow': 0.0},
    'grass': {'brush': 0.011, 'canyon': 0.0012, 'desert': 0.7083, 'dunes': 0.004,
              'scrub': 0.007, 'snow': 0.2995},
    'scrub': {'brush': 0.0, 'canyon': 0.0033, 'desert': 0.0028, 'dunes': 0.0,
              'grass': 0.0028, 'snow': 0.0},
    'snow': {'brush': 0.0, 'canyon': 0.0, 'desert': 0.2024, 'dunes': 0.0,
             'grass': 0.2186, 'scrub': 0.0},
}
#: below this, the pair is off the measured path -- WARN, do not refuse. No rendering
#: evidence was gathered, so a refusal would be stronger than the measurement supports.
LAYOUT_SUPPORT_WARN = 0.50

#: THE LOOK-FAMILY TOPOGRAPH SETS (the interior census, ``studies/overworld-topography/
#: README.md``: "~37 in-use topograph ids collapse into ~9 tile families"). Ids inside a
#: family are GAMEPLAY variants -- encounter regions and event triggers -- not looks, so
#: they all wear the family's mains tiles.
#:
#: This is the FAMILY GATE for :class:`GroundRetile`'s mains branch, not its classifier:
#: a tri is mains only when its topo is in its source family's set AND its uv sits inside
#: that family's (source-derived) mains rect. The rect does the discriminating; the set
#: only says "this id belongs to the family whose rect we are about to test".
#:
#: ⚠ ``grass`` is EXACTLY the historic ``GRASS_TOPOS`` and must stay so -- the grass->desert
#: retile is in-game proven on (7,17)/(8,17)/(10,17) and every carried triangle of it is
#: frozen by the byte-identity oracles. The census's grass LOOK family also lists 59;
#: 59 is NOT added here, because adding it would move a proven path.
#:
#: ⚠ ``dunes`` (41) is kept OUT of ``desert`` even though the census groups the dirt-desert
#: LOOK family as 16-23/41: the translation table calls 41 a "family-model EXCEPTION -- its
#: own pale-sand set, NOT desert's", i.e. it has a different mains rect. Folding it into
#: desert would let a topo-41 tri fail desert's rect and then get SYNTHESIZED by the
#: path-strip recover. Left out, it refuses loudly instead. Fail closed.
FAMILY_TOPOS = {
    "grass": frozenset({0, 1, 2, 3, 10, 11, 12, 13, 42}),
    "desert": frozenset({16, 17, 18, 19, 20, 21, 22, 23}),
    "scrub": frozenset({4, 5, 6}),
    "brush": frozenset({38}),
    "snow": frozenset({27, 28}),
    "canyon": frozenset({45, 46}),
    "dunes": frozenset({41}),
}


class GroundRetile:
    """Tweak class -- THE GROUND-FAMILY RETILE (the translation law over a whole carried
    block; built for the (7,17)->desert beach island, 2026-07-15).

    Rewrites the carried donor's texture classes from one ground family to another.
    Geometry, heights and normals stay VERBATIM -- only uvs and the ``tangent.x``
    topograph change, each class by its own byte-measured translation law (nothing is
    synthesized; ``studies/overworld-topography/island717_retile_census.py``):

    * ground MAINS (uv in the SOURCE family's mains rect, and a topo in that family's
      :data:`FAMILY_TOPOS` row) -> the ``grassland.GROUNDS`` mains delta, topo -> the
      target family topo  [in-game proven: the full desert bench, grass->desert]
    * the coastal ROCK band (uv in the wall strip, any topo) -> the ``GROUNDS`` wall
      delta, topo unchanged  [in-game proven: the desert bench walls]
    * the SAND band (the source family's sand topo) -> ``coastmorph.SAND_BANDS``:
      u + the family du, v remapped over the donor's own OBSERVED pins onto the
      target's pins (classified verts land EXACTLY on the target pin; conforming
      verts lerp within their tier)  [offline-proven on all 15 real desert blocks]
    * THE DEGENERATE-SAND GUARD (the (8,17)->desert carry, in-game 2026-07-20): a
      sand tri whose verts straddle two SOURCE sub-variant pins (``SAND_V_CAP_LAND``
      alone lists 6) that collapse onto the target's ONE discrete row keeps real
      world-space area but a ~0-area mapped UV -- the renderer stretches one atlas
      texel-row across it (bold diagonal banding). Not a mapping to fix: an
      unmeasurable-for-this-triangle granularity mismatch, diverted to the SAME
      PATH-STRIP RECOVER treatment below (position-evaluated target mains) and
      counted separately (``sand_degenerate_recovered``, frozen by the prescan).
      Fires ONLY when the remap strictly reduces the distinct-uv count -- a triple
      already degenerate at the source (a zero-area strip-clip residue, e.g. the
      (10,17) donor's W-strip beach fragments) is not an artifact and stays
      verbatim sand.
    * beach1 FOAM -> topo relabel only (30 <-> 34; the foam texture is universal
      per the beach translation law)
    * water topos and the sea parts -> byte-verbatim.
    * PATH-STRIP RECOVER (budgeted): a walkable tri in NO measured class (the (7,17)
      2-cell dirt path down to the beach) re-uvs as position-evaluated TARGET mains
      (the mint's ``assign_mains`` policy) -- stock desert has no path analogue, its
      sand back-welds DIRECTLY onto desert mains (86/111 census welds). Budgeted by
      the factory's prescan; anything beyond refuses.

    Every other tri REFUSES via the gate (part/topo/uv-bbox in the report): a donor
    class the translation census has not measured must be studied, not guessed.
    Build instances with :meth:`for_donor` (byte-reads the donor)."""

    #: the grass gameplay-variant topographs (the families census: same look, gameplay ids).
    #: Kept as the historic name -- ``island717_retile_acceptance.py`` reads it -- but it is
    #: now just the grass row of the module-level :data:`FAMILY_TOPOS`.
    GRASS_TOPOS = FAMILY_TOPOS["grass"]
    _WATER = frozenset({53, 54, 55, 56, 57})
    _EPS = 0.006                                             # uv region-membership slack

    def __init__(self, *, dst: str, src: str = "grass", sand_anchors=(),
                 recover_cells=None, recover_budget: int = 0, expected=None):
        from . import grassland as G
        from . import island as I                            # lazy on the module (import cycle)
        from . import coastmorph as CM
        from . import islandbeach as IB
        if dst not in G.GROUNDS:
            raise ValueError(f"unknown ground family {dst!r} (families: {sorted(G.GROUNDS)})")
        if src not in FAMILY_TOPOS:
            raise ValueError(f"no measured topograph set for source family {src!r} "
                             f"(FAMILY_TOPOS: {sorted(FAMILY_TOPOS)}) -- the mains branch "
                             f"cannot tell which of this donor's ids wear its mains tiles")
        self.part = "terrain"                                # emission host (nothing emitted)
        self.src, self.dst = src, dst
        #: the SOURCE family's gameplay-variant ids -- the mains branch's family gate
        self.src_topos = FAMILY_TOPOS[src]
        gs, gd = G.GROUNDS[src], G.GROUNDS[dst]
        self.mains_d = (gd["mains_du"] - gs["mains_du"], gd["mains_dv"] - gs["mains_dv"])
        self.wall_d = (gd["wall_du"] - gs["wall_du"], gd["wall_dv"] - gs["wall_dv"])
        self.dst_topo = gd["topo"]
        m = G.FAM_REGION["main"]
        self.mains_rect = (m[0] + gs["mains_du"], m[1] + gs["mains_dv"],
                           m[2] + gs["mains_du"], m[3] + gs["mains_dv"])
        self.wall_rect = (min(I.ROCK_U) + gs["wall_du"], min(I.ROCK_V) + gs["wall_dv"],
                          max(I.ROCK_U) + gs["wall_du"], max(I.ROCK_V) + gs["wall_dv"])
        self.sand_src = CM.SAND_BANDS.get(src)
        self.sand_dst = CM.SAND_BANDS.get(dst)
        self.sand_du = (self.sand_dst["du"] - self.sand_src["du"]) \
            if (self.sand_src and self.sand_dst) else None
        self.sand_eps = self.sand_src["eps_v"] if self.sand_src else 0.0
        self.sand_anchors = tuple(sorted(sand_anchors))
        self.foam_src = IB.FOAM_TOPO.get(src)
        self.foam_dst = IB.FOAM_TOPO.get(dst)
        self.recover_cells = dict(recover_cells or {})
        self.recover_budget = int(recover_budget)
        self._degenerate_cache: dict = {}                    # degenerate-sand per-cell mains
        self.expected = dict(expected or {})
        self.n = collections.Counter()
        self.unclassified: list = []

    # -- helpers ---------------------------------------------------------------------
    def _retag(self, tan, topo):
        d = decode_id(int(round(tan[0])))
        return (float(encode_id(d["event"], d["area"], topo, d["flags"])),) + tuple(tan[1:])

    def _in(self, uv, rect):
        return (rect[0] - self._EPS <= uv[0] <= rect[2] + self._EPS
                and rect[1] - self._EPS <= uv[1] <= rect[3] + self._EPS)

    def _sand_v(self, v):
        """The donor-pins -> target-pins monotone remap: exact on pins, per-tier lerp
        between them, unit-slope beyond the ends."""
        A = self.sand_anchors
        for (s, d) in A:
            if abs(v - s) <= self.sand_eps:
                return d
        if v <= A[0][0]:
            return A[0][1] + (v - A[0][0])
        if v >= A[-1][0]:
            return A[-1][1] + (v - A[-1][0])
        for k in range(len(A) - 1):
            (s0, d0), (s1, d1) = A[k], A[k + 1]
            if s0 <= v <= s1:
                return d0 + (v - s0) * (d1 - d0) / (s1 - s0)
        return v                                             # unreachable (A is sorted)

    def _refuse(self, part, topo, poly, cell):
        us = [v[2][0] for v in poly]
        vs = [v[2][1] for v in poly]
        self.unclassified.append(dict(part=part, topo=topo, cell=cell,
                                      uv=[round(min(us), 4), round(min(vs), 4),
                                          round(max(us), 4), round(max(vs), 4)]))

    # -- the tweak protocol ----------------------------------------------------------
    def apply(self, part, poly):
        if part == "beach1":
            if self.foam_src is not None and \
                    decode_id(int(round(poly[0][3][0])))["topograph"] == self.foam_src:
                if self.foam_dst is None:                    # gated in for_donor; belt here
                    self._refuse(part, self.foam_src, poly, None)
                    return poly
                self.n["foam"] += 1
                return [(p, nr, uvv, self._retag(tan, self.foam_dst))
                        for (p, nr, uvv, tan) in poly]
            # THE SILENT BRANCH, CLOSED. This used to `return poly` for ANY non-foam
            # beach1 tri -- correct for water by the verbatim policy, but it could not
            # tell water from a class nobody has measured, so an unmeasured one shipped
            # silently while the identical class in `terrain` refused. Census of every
            # beach1 topograph in disc 1: {30: 443, 34: 280, 53: 4, 55: 10} -- foam and
            # water only, nothing else, so refusing the remainder cannot fire on stock
            # data and costs no shipped donor.
            btopo = decode_id(int(round(poly[0][3][0])))["topograph"]
            if btopo in self._WATER:
                self.n["beach1_water"] += 1
                return poly
            self._refuse(part, btopo, poly, None)
            return poly
        if part != "terrain":
            return poly
        topo = decode_id(int(round(poly[0][3][0])))["topograph"]
        if topo in self._WATER:
            return poly
        if self.sand_src is not None and topo == self.sand_src["topo"]:
            if not self.sand_anchors or self.sand_du is None:
                self._refuse(part, topo, poly, None)         # sand with no readable pins
                return poly
            # THE DEGENERATE-SAND GUARD (see the class docstring): fires only when the
            # remap STRICTLY REDUCES the distinct (u,v) count -- i.e. the mapping itself
            # collapsed source-distinct verts onto one target point (the ~0-area-UV
            # banding artifact). A triple already degenerate at the SOURCE (a zero-area
            # clip residue, e.g. the (10,17) W-strip beach fragments) stays verbatim
            # sand: it renders as nothing and diverting it would drift deployed bytes.
            # Diverted tris take the PATH-STRIP RECOVER treatment, keyed per-4u-cell so
            # neighbours share one mains assignment (recover_cells first, then the cache).
            src_pts = {(round(uvv[0], 6), round(uvv[1], 6)) for (_, _, uvv, _) in poly}
            pts = {(round(uvv[0] + self.sand_du, 6), round(self._sand_v(uvv[1]), 6))
                   for (_, _, uvv, _) in poly}
            if len(pts) < len(src_pts):
                from . import grassland as G
                cx = sum(v[0][0] for v in poly) / len(poly)
                cz = sum(v[0][2] for v in poly) / len(poly)
                cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
                qo = self.recover_cells.get(cell) or self._degenerate_cache.get(cell)
                if qo is None:
                    cq, co = G.assign_mains({cell}, seed=0xF93)
                    qo = (cq[cell], co[cell])
                    self._degenerate_cache[cell] = qo
                (quad, ori) = qo
                self.n["sand_degenerate_recovered"] += 1
                return [(p, nr, tuple(G.ground_uv(p[0], p[2], cell, quad, ori, self.dst)),
                         self._retag(tan, self.dst_topo))
                        for (p, nr, uvv, tan) in poly]
            self.n["sand"] += 1
            return [(p, nr, (uvv[0] + self.sand_du, self._sand_v(uvv[1])),
                     self._retag(tan, self.sand_dst["topo"]))
                    for (p, nr, uvv, tan) in poly]
        if all(self._in(uvv, self.wall_rect) for (_, _, uvv, _) in poly):
            self.n["wall"] += 1
            return [(p, nr, (uvv[0] + self.wall_d[0], uvv[1] + self.wall_d[1]), tan)
                    for (p, nr, uvv, tan) in poly]
        cx = sum(v[0][0] for v in poly) / len(poly)
        cz = sum(v[0][2] for v in poly) / len(poly)
        cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        if topo in self.src_topos:
            if all(self._in(uvv, self.mains_rect) for (_, _, uvv, _) in poly):
                self.n["mains"] += 1
                return [(p, nr, (uvv[0] + self.mains_d[0], uvv[1] + self.mains_d[1]),
                         self._retag(tan, self.dst_topo))
                        for (p, nr, uvv, tan) in poly]
            qo = self.recover_cells.get(cell)
            if qo is not None:
                from . import grassland as G
                (quad, ori) = qo
                self.n["recovered"] += 1
                return [(p, nr, tuple(G.ground_uv(p[0], p[2], cell, quad, ori, self.dst)),
                         self._retag(tan, self.dst_topo))
                        for (p, nr, uvv, tan) in poly]
        self._refuse(part, topo, poly, cell)
        return poly

    def emit(self) -> list:
        return []

    def gate(self) -> dict:
        # the detail is a 4-item SAMPLE; lead with the total and a topo histogram, or a
        # 395-tri refusal reads as a 4-tri one and the reader goes looking for a small
        # hole instead of the whole unmeasured class that is actually there.
        det = "; ".join(f"{u['part']}:t{u['topo']}@{u['cell']} uv{u['uv']}"
                        for u in self.unclassified[:4])
        if det:
            h = collections.Counter(u["topo"] for u in self.unclassified)
            det = (f"{len(self.unclassified)} tris, topo "
                   + ",".join(f"{t}x{n}" for t, n in sorted(h.items()))
                   + f" -- first 4: {det}")
        ok = (not self.unclassified
              and self.n["recovered"] <= self.recover_budget
              and all(self.n[k] == v for k, v in self.expected.items()))
        return {"gate": f"retile[{self.src}->{self.dst}]",
                **{k: self.n[k] for k in ("mains", "wall", "sand", "foam", "recovered",
                                          "sand_degenerate_recovered")},
                "budget": self.recover_budget,
                "unclassified": det if det else 0, "ok": ok}

    @staticmethod
    def _mains_family(tris, donor=None, *, margin: float = 2.0, floor: int = 12):
        """The donor's ground family, read from its MAINS uv region by dominance.

        Used when the donor has no sand band to name the family. Regions are not fully
        disjoint (a desert donor also lands 63 tris in brush's rect), so this takes the
        plurality and requires the winner to lead by ``margin`` -- a genuinely mixed
        landmass must REFUSE and be told to pass ``src`` explicitly, never be guessed at.
        """
        from . import grassland as G
        regions = {f: G.ground_main_region(f) for f in G.GROUNDS}
        counts: dict = {}
        for t3 in tris:
            us = [v[2][0] for v in t3]
            vs = [v[2][1] for v in t3]
            u_lo, u_hi, v_lo, v_hi = min(us), max(us), min(vs), max(vs)
            for f, (r_u0, r_v0, r_u1, r_v1) in regions.items():
                if (u_lo >= r_u0 - 1e-4 and u_hi <= r_u1 + 1e-4
                        and v_lo >= r_v0 - 1e-4 and v_hi <= r_v1 + 1e-4):
                    counts[f] = counts.get(f, 0) + 1
        if not counts:
            return "grass"                       # no mains at all: the historic default
        rank = sorted(counts.items(), key=lambda kv: -kv[1])
        top, n = rank[0]
        runner = rank[1][1] if len(rank) > 1 else 0
        # A UNANIMOUS READ IS NOT AMBIGUOUS. The floor exists to stop a handful of stray
        # tris naming a family when another family is also present; with no competitor at
        # all there is nothing to be ambiguous BETWEEN. Donor (12,10) -- a real carryable
        # 1x1 island -- reads {'grass': 11} and was refused purely for being small, which
        # blocks a legitimate donor for no measurement reason.
        unanimous = runner == 0 and n >= 4
        dominant = runner > 0 and n >= margin * runner and n >= floor
        if not (unanimous or dominant):
            raise ValueError(
                f"donor {donor or ''} has no dominant ground family in its mains "
                f"({dict(rank)}) -- pass src= explicitly rather than let it be guessed")
        return top

    @classmethod
    def for_donor(cls, donor, dst, *, size=(1, 1), src=None, strips="auto",
                  extra: float = 8.0, disc: int = 1, lod: str = "0_1", game=None):
        """Build the retile from the donor's own bytes: auto-detect the source family
        (the sand topo is PURE per block -- the census law), byte-read the donor's sand
        pins as the v-remap anchors, prescan the exact content :func:`transplant` /
        :func:`transplant_region` will gather (every donor rect cell whole + the
        REGION's outer-border ``extra`` edge bands per ``strips``, same clip planes)
        to pre-assign the recover cells and freeze the per-class EXPECTED counts.
        ``strips`` must MATCH the transplant call's -- the expected counts are exact."""
        from . import coastmorph as CM
        from . import grassland as G
        (dbx, dby) = donor
        (nx, ny) = (int(size[0]), int(size[1]))
        polys = {"terrain": [], "beach1": []}
        for p in polys:
            for j in range(ny):
                for i in range(nx):
                    polys[p] += [list(t) for t in world_tris(dbx + i, dby + j, p,
                                                             disc=disc, lod=lod, game=game)]
        all_specs = {
            "E": [((dbx + nx, dby + j), 0, 64.0 * (dbx + nx) + extra, True) for j in range(ny)],
            "W": [((dbx - 1, dby + j), 0, 64.0 * dbx - extra, False) for j in range(ny)],
            "N": [((dbx + i, dby - 1), 2, -64.0 * dby + extra, True) for i in range(nx)],
            "S": [((dbx + i, dby + ny), 2, -64.0 * (dby + ny) - extra, False) for i in range(nx)]}
        if strips in ("auto", "all"):
            gathered = set(all_specs)
        elif strips in ("none", None):
            gathered = set()
        else:
            gathered = {str(d).upper() for d in strips}
            if not gathered <= set(all_specs):
                raise ValueError(f"strips must be 'auto', 'all', 'none' or a set of "
                                 f"E/W/N/S -- got {strips!r}")
        strip_specs = [spec for d in sorted(gathered) for spec in all_specs[d]]
        for ((nx2, ny2), axis, plane, below) in strip_specs:
            if not (0 <= nx2 < GRID_X and 0 <= ny2 < GRID_Y):
                continue
            for p in polys:
                for tri in world_tris(nx2, ny2, p, disc=disc, lod=lod, game=game):
                    cp = clip_poly(list(tri), axis, plane, below)
                    if len(cp) >= 3:
                        polys[p].append(cp)
        sand_fam = CM._sand_band_family(polys["terrain"], what=f"donor {donor}")
        if src is None:
            # THE SAND BAND IS AUTHORITATIVE WHEN PRESENT (it is pure per block -- the
            # census law), but it is not the only evidence. This used to fall back to
            # `"grass"` for ANY donor without a beach, which silently mislabelled every
            # beachless non-grass landmass: the comma island (9,5) has 355 desert mains,
            # zero grass mains, and topo 17 x355, yet detected as grass -- so the grass
            # mains rect matched nothing, the retile classified 0 tris of 917, and the
            # only tris it flagged were desert mains falling outside every *grass* class.
            # The mains carry the family; read them.
            src = sand_fam["name"] if sand_fam else cls._mains_family(polys["terrain"],
                                                                     donor)
        if src == dst:
            raise ValueError(f"--ground {dst}: donor ({dbx},{dby}) is already {src} -- "
                             f"nothing to retile")
        # THE SOURCE GATE. The mains branch now keys on the SOURCE family's topograph set
        # (FAMILY_TOPOS), so any family whose ids are censused can classify its own mains.
        # What is NOT free is the DIRECTION: grass->X has an in-game-proven instance
        # (grass->desert) and keeps the historic WARN below, but a source we have never
        # shipped is only as good as the translation census says it is, so a
        # newly-reachable pair must CLEAR the support bar, not merely warn about it.
        # desert->grass is 0.762 -- the strongest pair in the table, above the proven
        # grass->desert 0.708 -- and is the only non-grass direction that clears it.
        # (an unknown ``src`` needs no check here: it can only come from a GROUNDS key or
        # the caller, FAMILY_TOPOS covers GROUNDS one-for-one -- asserted in the tests --
        # and __init__ raises on the caller's typo. A second copy would be unreachable.)
        if src != "grass":
            sup = LAYOUT_SUPPORT.get(src, {}).get(dst)
            if sup is None or sup < LAYOUT_SUPPORT_WARN:
                ok = sorted(d for d, s in LAYOUT_SUPPORT.get(src, {}).items()
                            if s >= LAYOUT_SUPPORT_WARN)
                raise ValueError(
                    f"--ground {dst}: donor ({dbx},{dby}) is {src}, and {src}->{dst} has "
                    f"layout support "
                    + (f"{sup:.3f}" if sup is not None else "no census entry")
                    + f" (bar {LAYOUT_SUPPORT_WARN:.2f}). Only grass sources may retile "
                      f"below the bar on a WARNING -- grass->desert is in-game proven, so "
                      f"the mechanism is exercised in that direction; from {src} nothing "
                      f"has ever been shipped, so a weak pair must be measured before it "
                      f"is offered. Supported targets from {src}: "
                    + (", ".join(ok) if ok else "none")
                    + ". Table: LAYOUT_SUPPORT / "
                      "studies/coast-shape-language/GROUND-TRANSLATION-CENSUS.md")
        if sand_fam and dst not in CM.SAND_BANDS:
            raise ValueError(f"donor ({dbx},{dby}) carries a sand band and {dst!r} has no "
                             f"measured sand family (SAND_BANDS: {sorted(CM.SAND_BANDS)}) "
                             f"-- only those targets can retile a beach donor")
        from . import islandbeach as IB
        if polys["beach1"] and dst not in IB.FOAM_TOPO:
            raise ValueError(f"donor ({dbx},{dby}) carries a beach1 foam part and {dst!r} "
                             f"has no measured foam topo (FOAM_TOPO: {sorted(IB.FOAM_TOPO)})")
        # THE LAYOUT-SUPPORT WARNING. grass->desert is the only currently-reachable target
        # whose tiling was measured to match; grass->snow/canyon/scrub are permitted but sit
        # at 0.30/0.001/0.007, i.e. they use sub-tile arrangements stock never uses for that
        # family. Warn rather than refuse: the census measures ARRANGEMENT, not rendering,
        # so a refusal would claim more than the evidence supports.
        support = LAYOUT_SUPPORT.get(src, {}).get(dst)
        if support is not None and support < LAYOUT_SUPPORT_WARN:
            best = max(LAYOUT_SUPPORT.get(src, {}).items(), key=lambda kv: kv[1],
                       default=(None, 0.0))
            warnings.warn(
                f"--ground {src}->{dst}: layout support {support:.3f} -- this pair is OFF "
                f"THE MEASURED PATH. Both families' mains rects are the same size so the "
                f"retile lands on {dst}'s texture, but {1 - support:.0%} of the translated "
                f"tris use sub-tile arrangements stock does not use for {dst}. The proven "
                f"pair is grass->desert (0.708)"
                + (f"; from {src} the best-supported target is {best[0]} ({best[1]:.3f})"
                   if best[0] else "")
                + ". Review in-game. Table: LAYOUT_SUPPORT / "
                "studies/coast-shape-language/GROUND-TRANSLATION-CENSUS.md",
                stacklevel=2)
        anchors = []
        if sand_fam:
            sfam, dfam = CM.SAND_BANDS[src], CM.SAND_BANDS[dst]
            pin_of = {"run_land": "v_land", "run_seam": "v_seam",
                      "cap_land": "v_cap_land", "cap_seam": "v_cap_seam"}
            obs: dict = {}
            for t3 in polys["terrain"]:
                if decode_id(int(round(t3[0][3][0])))["topograph"] != sfam["topo"]:
                    continue
                for (_, _, uvv, _) in t3:
                    c = CM._sand_vclass(uvv[1], sfam)
                    if c:
                        obs.setdefault(c, set()).add(round(uvv[1], 5))
            anchors = sorted((v, dfam[pin_of[c]][0]) for c, vals in obs.items() for v in vals)
            for k in range(len(anchors) - 1):
                if anchors[k + 1][1] < anchors[k][1]:
                    raise ValueError(f"donor sand pin remap is not monotone -- off-language "
                                     f"pins: {anchors}")
        # prescan: classify exactly what transplant() will pass through apply()
        pre = cls(dst=dst, src=src, sand_anchors=anchors)
        for p, pl in polys.items():
            for poly in pl:
                pre.apply(p, poly)
        # THE WALL-CONTEXT LAW (family_wall_envelope.py, 2026-07-15): wall bands are
        # CONTEXT-keyed, not just atlas-keyed. A donor whose walls reach the waterline
        # (sea cliffs) can only retile to a family whose band is MEASURED coastal
        # (grass/desert/snow); canyon's red band is interior-only in stock (0/748
        # coastal faces -- the Forgotten's sea cliffs are topo-49 murals).
        coastal_walls = sum(
            1 for t3 in polys["terrain"]
            if all(pre._in(v[2], pre.wall_rect) for v in t3)
            and min(v[0][1] for v in t3) < 0.05)
        if coastal_walls and G.GROUNDS[dst].get("wall_coastal") is not True:
            why = ("is INTERIOR-ONLY in stock (0 coastal faces map-wide)"
                   if G.GROUNDS[dst].get("wall_coastal") is False
                   else "has no MEASURED coastal usage")
            raise ValueError(f"--ground {dst}: THE WALL-CONTEXT LAW -- donor "
                             f"({dbx},{dby}) has {coastal_walls} sea-cliff wall tris, "
                             f"and the {dst} wall band {why}; a {dst} sea cliff is "
                             f"off-language. Coastal-wall targets: "
                             f"{sorted(n for n, g in G.GROUNDS.items() if g.get('wall_coastal'))}")
        rec = sorted({u["cell"] for u in pre.unclassified
                      if u["part"] == "terrain" and u["topo"] in FAMILY_TOPOS[src]})
        cq, co = G.assign_mains(set(rec), seed=0xF93)
        # COUNT ONLY WHAT CAN ACTUALLY RECOVER. `rec` is the set of CELLS holding at least
        # one source-family refusal, but budgeting every refusal in those cells counts
        # foreign classes that the recover path will never take -- so expected["recovered"]
        # became unreachable and the gate could only fail. The predicate here is the same
        # one that selects `rec`, counted per TRI instead of per cell.
        budget = sum(1 for u in pre.unclassified
                     if u["cell"] in set(rec) and u["part"] == "terrain"
                     and u["topo"] in FAMILY_TOPOS[src])
        expected = {k: pre.n[k] for k in ("mains", "wall", "sand", "foam",
                                          "sand_degenerate_recovered")}
        expected["recovered"] = budget
        return cls(dst=dst, src=src, sand_anchors=anchors,
                   recover_cells={c: (cq[c], co[c]) for c in rec},
                   recover_budget=budget, expected=expected)


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

    def census_inverse(self, x: float, z: float):
        """Approximate donor pre-image of a DISPLACED-region point (donor world XZ) -- the
        census backmap hook: a pre-existing donor hole near a moved shore TRANSLATES with
        the displacement and would otherwise shift out from under the identity backmap and
        misread as introduced (the RowInsert-inverse phenomenon, displacement flavour).
        Nearest-moved-vert field: exact at the verts, adequate between them at bow scale."""
        best, bd = None, 1e18
        for (kx, ky, kz), d in self.moves.items():
            d2 = (x - (kx + d[0])) ** 2 + (z - (kz + d[2])) ** 2
            if d2 < bd:
                best, bd = d, d2
        if best is None or bd > (6.0 + max(abs(best[0]), abs(best[2]))) ** 2:
            return x, z
        return x - best[0], z - best[2]

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


#: THE LEARNED WANG TABLE (byte-learned 2026-07-09, the band-crossing re-Wang study): a real
#: Wang transition tile's (v-strip index, dihedral orientation) <-> its DEEP-EDGE-SET, in the
#: KIT'S OWN tile-decode frame (fx = 0 at min-x, fz = 0 at min-z of the 4u cell; orientation
#: names = water.py's OMAPS rotations composed with an optional rect-u flip "+f"). Learned by
#: constraint intersection over 221 real sea5/sea1 tiles across 10 blocks: ZERO contradictions,
#: every sea5 key pins to EXACTLY ONE edge-set, and sea1's observations all match sea5's values
#: (sea1 = the same language one rung down, confirming the island_morph v2 finding). This is
#: the empirical mapping -- shipped in the decode frame rather than derived through water.py's
#: synthesis conventions, because a frame-convention mismatch is exactly what a derivation
#: would silently get wrong (the study's pass-1 lesson). The determinism (a strip tile is a
#: PURE FUNCTION of which neighbours sit on the deeper band, no hidden state) is the soundness
#: license for RE-DERIVING tiles after a structural edit instead of copying them.
STRIP_EDGESET = {
    (0, "r0+f"): frozenset("W"), (0, "r90+f"): frozenset("S"),
    (0, "r180+f"): frozenset("E"), (0, "r270+f"): frozenset("N"),
    (1, "r0+f"): frozenset("NW"), (1, "r90+f"): frozenset("SW"),
    (1, "r180+f"): frozenset("ES"), (1, "r270+f"): frozenset("EN"),
    (2, "r0+f"): frozenset("NSW"), (2, "r90+f"): frozenset("ESW"),
    (2, "r180+f"): frozenset("ENS"), (2, "r270+f"): frozenset("ENW"),
    (3, "r0+f"): frozenset("SW"), (3, "r90+f"): frozenset("ES"),
    (3, "r180+f"): frozenset("EN"), (3, "r270+f"): frozenset("NW"),
}
#: deep-edge-set -> [(strip, orientation), ...] (corner sets have the two byte-observed
#: seam-variants, matching DEEPSET2TILE's variant structure).
EDGESET2STRIP: dict = {}
for _k, _es in STRIP_EDGESET.items():
    EDGESET2STRIP.setdefault(_es, []).append(_k)


def _dih_maps():
    """The kit-frame dihedral-8 orientation maps ``(fx, fz) -> (a, b)`` (rect position):
    water.py's 4 rotations + each composed with a rect-u flip (``+f``)."""
    from .water import OMAPS
    maps = dict(OMAPS)
    for rname, m in list(OMAPS.items()):
        maps[rname + "+f"] = (lambda mm: (lambda fx, fz:
                              ((lambda ab: (1 - ab[0], ab[1]))(mm(fx, fz)))))(m)
    return maps


def strip_edge_set(poly, *, eps: float = 0.04):
    """Decode a lattice Wang-strip tile's DEEP-EDGE-SET from its corner UVs (the
    :data:`STRIP_EDGESET` inverse decode): match the tile's ``(fx, fz) -> uv`` mapping
    against the 8 dihedral placements of each of the 4 v-strips and look the winner up in
    the learned table. Returns the ``frozenset`` of deep edges, or ``None`` for a
    non-strip / non-lattice / unmatched tile."""
    from .water import UFULL, VSTRIP
    n = len(poly)
    cx = 4.0 * math.floor(sum(v[0][0] for v in poly) / n / 4.0)
    cz = 4.0 * math.floor(sum(v[0][2] for v in poly) / n / 4.0)
    uvf = _affine_uv(poly)
    corners = {}
    for fx in (0, 1):
        for fz in (0, 1):
            corners[(fx, fz)] = uvf(cx + 4.0 * fx, cz + 4.0 * fz)
    best = None
    for k in range(4):
        (u0, u1), (v0, v1) = UFULL, VSTRIP[k]
        for oname, om in _dih_maps().items():
            err = 0.0
            for (fx, fz), (u, v) in corners.items():
                a, b = om(fx, fz)
                err = max(err, abs(u0 + a * (u1 - u0) - u), abs(v0 + b * (v1 - v0) - v))
            if best is None or err < best[2]:
                best = (k, oname, err)
    if best is None or best[2] > eps:
        return None
    return STRIP_EDGESET.get((best[0], best[1]))


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


class SpillClip:
    """Tweak class 5 -- the ``spills-into-empty`` kill (2026-07-09, the (10,17) unlock; the
    sibling of the multi-boundary extrusion's ``gap-vacation`` kill). A REGION cut's shift is
    global: an EMPTY donor cell whose WEST neighbour has data receives the neighbour's east
    columns across their shared border -- deploying the empty cell as a nearly-empty override
    over what was TRUE sailable SeaBlockPrefab ocean (a 60u hole in the sea). This clips the
    SHIFTED assembly at the empty cell's fixed border plane (donor-frame ``x = plane``) inside
    the empty cell's row z-window ``[z0, z1]``: the spilled columns are DROPPED, so the empty
    cell stays genuine prefab ocean and deploys nothing.

    Why dropping is FAITHFUL: the census (``cut_census`` ``spill_clips``) certifies a column
    BUDGET first -- the dropped columns and the column that becomes the new border must be
    consecutive open-water columns with an IDENTICAL per-row part profile (all on-lattice, no
    straddlers), so after the clip the prefab-facing border speaks bit-for-bit the same
    language class it did in situ (the new border column is the donor's own next water
    column; rigid translation preserves every internal Wang adjacency, and prefab sea does
    not vertex-couple across the border -- the donor's own data/prefab seam is the existing
    in-game-proven precedent). Pure clipping of real bytes: no UV synthesis, no new geometry.

    Order in the tweak list: AFTER every RowInsert (it must see the shifted content);
    :func:`chain_row_inserts` ``spill_clips=`` appends + validates this (cut count within the
    budget; no fill band east of the plane -- emissions bypass later tweaks, so a fill that
    crossed the plane would dodge this clip). One instance per PART per window; the gate
    fails if anything dropped was NOT open water (apply-time re-certification) or if a poly
    straddled the z-window while crossing the plane (never silently mangle geometry)."""

    def __init__(self, part: str, *, plane: float, z0: float, z1: float, eps: float = 1e-4):
        self.part = part
        self.plane = float(plane)
        self.x_hi = self.plane + 64.0        # the empty CELL's east border: the clip zone is the
        #                                      cell's own footprint -- foreign refill strips beyond
        #                                      it (a west shift's slack) pass through untouched
        self.z0, self.z1 = min(float(z0), float(z1)), max(float(z0), float(z1))
        self.eps = float(eps)
        self.dropped = 0
        self.dropped_area2 = 0.0
        self.clipped = 0
        self.z_straddle = 0

    def apply(self, part: str, poly):
        if part != self.part:
            return poly
        xs = [v[0][0] for v in poly]
        if max(xs) <= self.plane + self.eps or min(xs) >= self.x_hi - self.eps:
            return poly                      # fully west of the border / beyond the cell: untouched
        zs = [v[0][2] for v in poly]
        zm = sum(zs) / len(zs)
        if not (self.z0 - self.eps <= zm <= self.z1 + self.eps):
            return poly                      # a data row (outside the empty cell's window)
        if min(zs) < self.z0 - self.eps or max(zs) > self.z1 + self.eps:
            self.z_straddle += 1             # crossing the window row while crossing the plane:
            return poly                      # keep it intact and FAIL the gate (donor tiles never
        #                                      straddle block borders -- this would be new geometry)
        area = sum(_tri_area2_3d([poly[0], poly[k], poly[k + 1]])
                   for k in range(1, len(poly) - 1))
        if min(xs) >= self.plane - self.eps:
            self.dropped += 1                # wholly across the border: the certified water column
            self.dropped_area2 += area
            return None
        kept = clip_poly(poly, 0, self.plane, True)   # defensive: census-clean columns have no
        self.clipped += 1                             # straddlers, but a clip here stays exact
        if len(kept) < 3:
            self.dropped += 1
            self.dropped_area2 += area
            return None
        self.dropped_area2 += max(0.0, area - sum(_tri_area2_3d([kept[0], kept[k], kept[k + 1]])
                                                  for k in range(1, len(kept) - 1)))
        return kept

    def emit(self) -> list:
        return []

    def inverse_x(self, x: float) -> float:
        return x                             # nothing west of the plane moves; east has no probes

    def gate(self) -> dict:
        ok = (self.z_straddle == 0
              and (self.part in OPEN_WATER_PARTS
                   or (self.dropped == 0 and self.clipped == 0)))
        return {"gate": f"spillclip[{self.part}]@{self.plane:g}", "dropped": self.dropped,
                "clipped": self.clipped, "area2": self.dropped_area2,
                "z_straddle": self.z_straddle, "ok": ok}


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


def _spill_clip_budget(polys, plane, z0, z1, *, max_cols: int = 8, eps: float = 1e-4) -> int:
    """The certified :class:`SpillClip` column budget at an empty cell's west border: how
    many 4u columns west of ``plane`` (inside the z-window) a chain of cuts may push across
    the border and DROP. Column m (m=1 at the border) is valid iff every tile inside it is
    OPEN WATER on the 4u lattice with no straddlers at its planes; the budget is the longest
    run of columns whose per-row part PROFILE is identical to the border column's, minus one
    (the last such column must remain, as the new prefab-facing border -- profile identity
    means the border speaks bit-for-bit the same language after every certified drop, and
    every internal adjacency is a rigid translation of real bytes). An EMPTY profile counts
    (nothing to spill there is trivially safe)."""
    profiles = []
    for m in range(1, max_cols + 2):
        x_hi = plane - 4.0 * (m - 1)
        x_lo = plane - 4.0 * m
        prof = {}
        ok = True
        for (p, poly) in polys:
            xs = [v[0][0] for v in poly]
            if max(xs) <= x_lo + eps or min(xs) >= x_hi - eps:
                continue
            zs = [v[0][2] for v in poly]
            zm = sum(zs) / len(zs)
            if not (z0 - eps <= zm <= z1 + eps):
                continue
            if min(xs) < x_lo - eps or max(xs) > x_hi + eps:
                ok = False                   # straddles a column plane (shore-conforming)
                break
            if p not in OPEN_WATER_PARTS:
                ok = False
                break
            if any(abs(v[0][0] / 4.0 - round(v[0][0] / 4.0)) > 2.5e-4
                   or abs(v[0][2] / 4.0 - round(v[0][2] / 4.0)) > 2.5e-4 for v in poly):
                ok = False                   # off-lattice verts (the lattice-seam law's kin)
                break
            row = math.floor(zm / 4.0)
            if prof.setdefault(row, p) != p:
                ok = False                   # two parts claim one row-cell
                break
        if not ok:
            break
        profiles.append(prof)
    budget = 0
    for m in range(1, len(profiles)):
        if profiles[m] != profiles[0]:
            break
        budget = m
    return budget


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
      ocean) is likewise flagged ONLY when the border is UNCLIPPABLE: a border whose
      adjacent donor columns are consecutive open-water columns with an identical per-row
      part profile (on-lattice, no straddlers) is instead reported in ``spill_clips`` as
      ``(plane, z0, z1, budget)`` -- feed the triples to :func:`chain_row_inserts`
      ``spill_clips=`` and a :class:`SpillClip` drops the spilled columns at the border so
      the empty cell stays TRUE prefab ocean (``budget`` = how many cuts the certified
      water run can absorb). Any other language at the border keeps the risk.

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
    # the WEST-border spill certification (SpillClip's): an empty cell whose west in-rect
    # neighbour has data gets a certified water-column BUDGET at their shared border
    spill_info: dict = {}
    for (ci, cj), has in cell_has_data.items():
        if has or not cell_has_data.get((ci - 1, cj)):
            continue
        plane = 64.0 * (dbx + ci)
        z0, z1 = -64.0 * (dby + cj + 1), -64.0 * (dby + cj)
        spill_info[(ci, cj)] = {"plane": plane, "z": (z0, z1),
                                "budget": _spill_clip_budget(polys, plane, z0, z1)}
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
        # THE STRIP-ACROSS-LINE law (the learned Wang table's census dividend, 2026-07-09):
        # a Wang strip OWNING the west seam whose deep edge points E/W has its transition
        # band running PARALLEL to the cut -- the translate-clone fill duplicates the
        # transition column (a 2-wide blend band real data never shows; previously
        # allowed-but-wrong). A strip whose deep edges are pure N/S extends ALONG its run
        # instead (the in-game-proven clone). Corner sets touch E/W -> conservative-flag.
        if any(p in OPEN_WATER_PARTS
               and sum(1 for v in poly if abs(v[0][0] - line) <= 1e-4) >= 2
               and sum(v[0][0] for v in poly) / len(poly) < line
               and (es := strip_edge_set(poly)) is not None
               and (es & {"E", "W"})
               for (p, poly) in polys):
            risks.append("strip-across-line")
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
        sclips = []
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
            sp = spill_info.get((ci, cj))
            if sp is not None and line <= sp["plane"] + 1e-6:
                if sp["budget"] >= 1:
                    t = [sp["plane"], sp["z"][0], sp["z"][1], sp["budget"]]
                    if t not in sclips:
                        sclips.append(t)
                elif "spills-into-empty" not in risks:
                    risks.append("spills-into-empty")
        out.append({"line": line, "straddlers": strad, "grows_land": grows, "risks": risks,
                    "boundary_fills": sorted(bfills), "spill_clips": sorted(sclips),
                    "clean": strad == 0 and not risks,
                    "ok": strad == 0 and grows and not risks})
    for c in out:
        c["axis"] = axis
        if axis == "z":                # map the rotated frame back to world z / x-windows
            c["line"] = -c["line"]
            c["boundary_fills"] = sorted([-b, w0 + _ZC, w1 + _ZC]
                                         for (b, w0, w1) in c["boundary_fills"])
            c["spill_clips"] = sorted([-pl, w0 + _ZC, w1 + _ZC, bud]
                                      for (pl, w0, w1, bud) in c["spill_clips"])
    return out


def _dedupe_spill_windows(spill_clips):
    """Normalize census ``spill_clips`` rows to unique ``(plane, z0, z1, budget)`` windows."""
    out = []
    for t in spill_clips:
        pl, z0, z1 = float(t[0]), float(t[1]), float(t[2])
        budget = float(t[3]) if len(t) > 3 else math.inf
        key = (pl, min(z0, z1), max(z0, z1))
        if key not in [(s[0], s[1], s[2]) for s in out]:
            out.append((key[0], key[1], key[2], budget))
    return out


def chain_row_inserts(lines, *, parts=PARTS, delta: float = 4.0, relief: float = 0.4,
                      seed: int = 0xF95, eps: float = 1e-4, boundaries=(),
                      spill_clips=()) -> list:
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

    ``spill_clips`` are the census's ``(plane, z0, z1, budget)`` rows (an empty cell's WEST
    border + its row z-window): one :class:`SpillClip` per part per window is appended AFTER
    every cut (it must see the shifted content), after validating the chain against the
    certified budget -- the number of cuts at-or-west of a plane may not exceed it, and no
    cut may sit so close to the border that its fill band lands east of the plane (RowInsert
    emissions bypass later tweaks, so such a fill would dodge the clip).

    A line given twice composes correctly (the second lands one column east) but yields
    two adjacent flat fill bands off one seam profile -- prefer spread-out lines.
    """
    bnds = [(float(b), float(z0), float(z1)) for (b, z0, z1) in boundaries]
    out = []
    slines = sorted(float(l) for l in lines)
    for i, ln in enumerate(slines):
        cut_b = [(b + i * delta, z0, z1) for (b, z0, z1) in bnds if ln <= b + 1e-6]
        for p in parts:
            out.append(RowInsert(p, line=ln + i * delta, delta=delta, relief=relief,
                                 seed=seed + 0x9E37 * i, eps=eps, boundaries=cut_b))
    for (pl, z0, z1, budget) in _dedupe_spill_windows(spill_clips):
        owed = [ln for ln in slines if ln <= pl + 1e-6]
        if len(owed) > budget:
            raise ValueError(f"{len(owed)} cuts at-or-west of spill plane {pl:g} exceed its "
                             f"certified water-column budget {budget:g} (cut_census "
                             f"spill_clips) -- the drop would consume uncertified columns")
        for i, ln in enumerate(owed):
            if ln + (i + 1) * delta > pl + 1e-6:
                raise ValueError(f"cut line {ln:g} sits too close to spill plane {pl:g} for "
                                 f"a chain this deep -- its fill band would land east of the "
                                 f"plane and bypass the SpillClip (fills skip later tweaks)")
        for p in parts:
            out.append(SpillClip(p, plane=pl, z0=z0, z1=z1, eps=eps))
    return out


def build_grow_tweaks(donor, size, *, grow_cut=(), grow_cut_z=(), disc: int = 1,
                      lod: str = "0_1", game=None):
    """Build the census-validated tweak list for region grow cuts on both axes, with
    boundary fills + spill clips AUTO-WIRED from the census -- the shared core of the
    ``world-transplant --grow-cut`` and ``world-fuse`` layout paths. Region lines
    (``size != (1,1)``) must be census-clean; single-cell lines pass through raw (the
    byte-proven single-cell path has no region census). Returns ``(tweaks, notes)``
    where ``notes`` are printable info lines; raises ``ValueError`` for a line that is
    not an interior lattice line or not census-clean."""
    (snx, sny) = (int(size[0]), int(size[1]))
    (dx, dy) = donor
    tweaks = []
    notes = []
    for axis, arg, chain in (("x", grow_cut, chain_row_inserts),
                             ("z", grow_cut_z, chain_row_inserts_z)):
        if not arg:
            continue
        flag = "--grow-cut-z" if axis == "z" else "--grow-cut"
        lines = [float(v) for v in arg]
        boundaries = ()
        spill_clips = ()
        if (snx, sny) != (1, 1):
            cen = {c["line"]: c for c in cut_census((dx, dy), size=(snx, sny),
                                                    disc=disc, lod=lod, game=game,
                                                    axis=axis)}
            for ln in lines:
                if ln not in cen:
                    raise ValueError(f"{flag} {ln:g}: not an interior 4u {axis} lattice "
                                     f"line of the donor rect ({dx},{dy})+{snx}x{sny}")
                if not cen[ln]["clean"]:
                    why = ", ".join(cen[ln]["risks"]) or \
                        f"straddlers={cen[ln]['straddlers']}"
                    raise ValueError(f"{flag} {ln:g}: not census-clean ({why}) -- "
                                     f"a cut may not cross a coast component")
            wl = "z" if axis == "x" else "x"
            boundaries = sorted({tuple(t) for ln in lines
                                 for t in cen[ln]["boundary_fills"]})
            if boundaries:
                notes.append("empty-cell boundary fills (census-certified open water): "
                             + "  ".join(f"{axis}={b:g} {wl}[{a0:g},{a1:g}]"
                                         for (b, a0, a1) in boundaries))
            spill_clips = sorted({tuple(t) for ln in lines
                                  for t in cen[ln]["spill_clips"]})
            if spill_clips:
                notes.append("empty-cell spill clips (census-certified water-column "
                             "budget): "
                             + "  ".join(f"{axis}={p:g} {wl}[{a0:g},{a1:g}] budget {b:g}"
                                         for (p, a0, a1, b) in spill_clips))
        tweaks.extend(chain(lines, boundaries=boundaries, spill_clips=spill_clips))
    return tweaks, notes


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


class SpillClipZ:
    """z-axis :class:`SpillClip`: clip the shifted assembly at an empty donor cell's NORTH
    border plane (donor-frame ``z = plane``; a z-cut shifts content SOUTHWARD, so it spills
    into an empty cell across the empty cell's north border when the empty cell's NORTH
    neighbour has data), inside the empty cell's column x-window ``[x0, x1]``. Implemented as
    the exact-rotation adapter over :class:`SpillClip` -- same certification laws, take the
    tuples from :func:`cut_census` ``axis="z"`` ``spill_clips``."""

    def __init__(self, part: str, *, plane: float, x0: float, x1: float, eps: float = 1e-4):
        self.part = part
        self.plane = float(plane)
        self._sc = SpillClip(part, plane=-self.plane, z0=float(x0) - _ZC,
                             z1=float(x1) - _ZC, eps=eps)

    def apply(self, part: str, poly):
        if part != self.part:
            return poly
        rp = self._sc.apply(part, _z_in_poly(poly))
        return None if rp is None else _z_out_poly(rp)

    def emit(self) -> list:
        return []

    def gate(self) -> dict:
        d = self._sc.gate()
        d["gate"] = f"spillclipz[{self.part}]@{self.plane:g}"
        return d


def chain_row_inserts_z(lines, *, parts=PARTS, delta: float = 4.0, relief: float = 0.4,
                        seed: int = 0xF95, eps: float = 1e-4, boundaries=(),
                        spill_clips=()) -> list:
    """z-axis :func:`chain_row_inserts`: ``lines`` are DONOR-frame z cut planes, sorted
    NORTH-to-SOUTH; content shifts southward, so a later (more southern) cut's donor line
    rides ``- i*delta`` (the mirror of the x chain's ``+ i*delta``), and each boundary
    plane a cut owes (its line at-or-north of it) rides the same correction.
    ``spill_clips`` are the ``axis="z"`` census's ``(plane_z, x0, x1, budget)`` rows (an
    empty cell's NORTH border + its column x-window): validated + appended as
    :class:`SpillClipZ`, the mirror of the x chain's laws (a cut owes a plane when its line
    is at-or-north of it; the fill band must stay north of the plane)."""
    bnds = [(float(b), float(x0), float(x1)) for (b, x0, x1) in boundaries]
    out = []
    slines = sorted((float(l) for l in lines), reverse=True)
    for i, ln in enumerate(slines):
        cut_b = [(b - i * delta, x0, x1) for (b, x0, x1) in bnds if ln >= b - 1e-6]
        for p in parts:
            out.append(RowInsertZ(p, line=ln - i * delta, delta=delta, relief=relief,
                                  seed=seed + 0x9E37 * i, eps=eps, boundaries=cut_b))
    for (pl, x0, x1, budget) in _dedupe_spill_windows(spill_clips):
        owed = [ln for ln in slines if ln >= pl - 1e-6]
        if len(owed) > budget:
            raise ValueError(f"{len(owed)} cuts at-or-north of spill plane {pl:g} exceed its "
                             f"certified water-column budget {budget:g} (cut_census "
                             f"spill_clips) -- the drop would consume uncertified columns")
        for i, ln in enumerate(owed):
            if ln - (i + 1) * delta < pl - 1e-6:
                raise ValueError(f"cut line {ln:g} sits too close to spill plane {pl:g} for "
                                 f"a chain this deep -- its fill band would land south of "
                                 f"the plane and bypass the SpillClipZ (fills skip later "
                                 f"tweaks)")
        for p in parts:
            out.append(SpillClipZ(p, plane=pl, x0=x0, x1=x1, eps=eps))
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


class DropTris:
    """Tweak class 6 -- drop an EXACT set of donor tris (matched by their rounded vertex-key
    sets, read from the mesh, never hand-typed). The scope gate requires every listed tri to
    have been seen and dropped. The generic half of a drop-and-refill edit (the coast-morph
    pillar's DROP-DON'T-DRAG law: a surviving tri whose vert drags far smears its texture --
    drop it and re-fill natively instead)."""

    def __init__(self, part: str, tris, key_decimals: int = 4):
        self.part = part
        self.kd = int(key_decimals)
        self.keys = {self._key_set(t) for t in tris}
        self.expected = len(tris)
        self.dropped = 0

    def _key_set(self, poly):
        return frozenset((round(v[0][0], self.kd), round(v[0][1], self.kd),
                          round(v[0][2], self.kd)) for v in poly)

    def apply(self, part: str, poly):
        if part == self.part and len(poly) == 3 and self._key_set(poly) in self.keys:
            self.dropped += 1
            return None
        return poly

    def emit(self) -> list:
        return []

    def gate(self) -> dict:
        return {"gate": f"drop[{self.part}]", "applied": self.dropped,
                "expected": self.expected, "ok": self.dropped == self.expected}


class EmitTris:
    """Tweak class 7 -- emit a precomputed list of (pos, normal, uv, tangent) triangles into
    one part (donor world frame; the transplant transform carries them like donor tris). The
    generic refill half of a drop-and-refill edit; emissions bypass other tweaks' apply."""

    def __init__(self, part: str, tris):
        self.part = part
        self.tris = [list(t) for t in tris]

    def apply(self, part: str, poly):
        return poly

    def emit(self) -> list:
        return [list(t) for t in self.tris]

    def gate(self) -> dict:
        return {"gate": f"emit[{self.part}]", "applied": len(self.tris),
                "expected": len(self.tris), "ok": True}


class SeaBump:
    """Tweak class 8 -- the WATER displace (in-game proven 2026-07-09, the coast-morph bump):
    move keyed water verts like :class:`VertexDisplace` but RE-EVALUATE each moved vert's UV
    through the tile's OWN (original) affine, so the caustic texture stays pinned in world
    space and the waterline simply cuts it at a new place. Dragged water UVs compress the
    pattern over the shrunken tile (stretched/smushed in-game); land drags fine at the same
    amplitude, water does not. Neighbours share the same map, so re-evaluation introduces
    zero seams by construction. The fold gate matches VertexDisplace's."""

    def __init__(self, *, moves: dict, expected: int, part: str = "sea4",
                 key_decimals: int = 4):
        self.part = part
        self.kd = int(key_decimals)
        self.moves = {self._key(k): tuple(v) for k, v in dict(moves).items()}
        self.expected = int(expected)
        self.applied = 0
        self.folds = 0

    def _key(self, p):
        return (round(p[0], self.kd), round(p[1], self.kd), round(p[2], self.kd))

    def apply(self, part: str, poly):
        if part != self.part or not any(self._key(v[0]) in self.moves for v in poly):
            return poly
        uvf = _affine_uv(poly)                         # the ORIGINAL tile map
        us = [v[2][0] for v in poly]
        vs = [v[2][1] for v in poly]
        out = []
        for (pos, nrm, uv, tan) in poly:
            d = self.moves.get(self._key(pos))
            if d is not None:
                pos = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2])
                nu, nv = uvf(pos[0], pos[2])
                uv = (min(max(nu, min(us) - 0.02), max(us) + 0.02),
                      min(max(nv, min(vs) - 0.02), max(vs) + 0.02))
                self.applied += 1
            out.append((pos, nrm, uv, tan))
        a0 = VertexDisplace._area2(poly)
        a1 = VertexDisplace._area2(out)
        if abs(a0) > 0.02 and (a0 * a1 <= 0.0 or abs(a1) < 0.02):
            self.folds += 1
        return out

    def emit(self) -> list:
        return []

    def gate(self) -> dict:
        return {"gate": f"seabump[{self.part}]", "applied": self.applied,
                "expected": self.expected, "folds": self.folds,
                "ok": self.applied == self.expected and self.folds == 0}


def _mod_overwrite_gate(mod_folder, cell_donors, *, disc, lod="0_1", game=None,
                        allow=False):
    """THE MOD-OVERWRITE GATE (2026-07-15, the dunes-islet incident): the real-target
    gate reads STOCK data only, so a target cell already holding a PRIOR MOD DEPLOY (a
    minted islet, an older transplant) sailed straight through and was silently
    overwritten. Every DATA cell is checked for existing override files in the deploy
    tree; existing files REFUSE unless the cell's ``Donor.txt`` names this deploy's OWN
    sidecar donor (= a re-deploy/iteration of the same transplant -- the proven loop).
    ``cell_donors`` maps world cell ``(bx, by)`` -> the sidecar donor to be written.
    ``allow`` (the --allow-mod-overwrite flag) waives the gate deliberately."""
    from .. import config
    hits = []
    redeploys = 0
    try:
        root = config.find_game_path(game) / mod_folder
    except Exception:
        root = None                              # no install resolvable: nothing to hit
    if root is not None:
        for (cx, cy), (sdx, sdy) in sorted(cell_donors.items()):
            rdir = root / f"FF9_Data/WorldMap/Disc{disc}/{lod}/r{cy}"
            prefix = f"Block[{cx}][{cy}] "
            existing = sorted(p.name for p in rdir.iterdir()
                              if p.name.startswith(prefix)) if rdir.is_dir() else []
            if not existing:
                continue
            dt = rdir / f"{prefix}Donor.txt"
            if dt.is_file() and dt.read_text(encoding="utf-8").strip() == f"{sdx},{sdy}":
                redeploys += 1                   # the same transplant, iterated in place
            else:
                have = dt.read_text(encoding="utf-8").strip() if dt.is_file() else "?"
                hits.append(f"({cx},{cy}) {len(existing)} files donor={have}")
    return {"gate": "mod-overwrite", "cells": len(cell_donors), "redeploys": redeploys,
            "existing": "; ".join(hits) if hits else 0, "ok": allow or not hits}


# --------------------------------------------------------------------------------------------------
# THE EFFECTIVE-PREFAB GATE + AUTO-ARM, and THE WANG-CARRY GATE -- the two productized water-carry
# gates (from the (11,19) water-only-cell arc + THE WANG-CARRY LAW; coast memory
# ``project-ff9-overworld-coast-mosaic``).  The engine binds a cell's overrides PER the effective
# prefab's transform set (armed divert donor vs the generic SeaBlockPrefab), and a carry that crops a
# Wang'd ocean breaks the puzzle at the cut edges -- both invisible to the coverage census.
_CELL, _G = 4.0, 16

#: THE LAWFUL SEA-SHADE ADJACENCY TABLE (byte-derived from STOCK 2026-07-20, the coastal-shade extension
#: of THE WANG-CARRY LAW; census: ``studies/overworld-topography/s12_stock_map_census_opus.py`` +
#: ``wang_seam_census.py``).  The ocean's DEPTH RING, shallow -> deep:
#:   land < beach1 < sea2 < sea1 < sea3 < sea5 < sea4
#: A carry that crops a Wang region can leave a tile facing a DEEPER ring than any it lawfully abuts.  Which
#: pairs are LAWFUL is NOT the ladder's adjacent rungs -- it is what stock AUTHORS, measured directed-edge,
#: land-aware, interior + cross-block, over the whole shipping map (counts cited per pair below).  The
#: OFF-LANGUAGE pairs each have ZERO systematic stock instances (a lone donor-verbatim interior tile is not
#: a coastline): ``sea1|sea4`` 0, ``sea2|sea4`` 0, ``sea2|sea5`` 0 -- so a sea1 tile's DEEPEST lawful
#: neighbour is sea5 and a sea2 tile's is sea3; NEITHER ever faces the deep sea4 ring directly (the deep
#: system's own invariant, ``sea3|sea4`` 0, is enforced separately by the sea5-orientation logic).  Encoded
#: as the UNORDERED lawful set; same-shade is always lawful and implicit (:func:`sea_adjacent_lawful`).
SEA_ADJ_LAWFUL = frozenset({
    frozenset({"sea2", "sea1"}),      # 488/517 -- the shallowest pair
    frozenset({"sea1", "sea3"}),      # 588
    frozenset({"sea1", "sea5"}),      #  78 -- sea1's DEEPEST lawful neighbour (the {sea1,sea5} ladder)
    frozenset({"sea2", "sea3"}),      #   9 -- sea2's DEEPEST lawful neighbour
    frozenset({"sea1", "beach1"}),    #  78 -- shore contact
    frozenset({"sea2", "beach1"}),    # 465 -- shore contact
    frozenset({"sea1", "land"}),      # 121 -- shore contact (terrain-shaded coast cell)
    frozenset({"sea2", "land"}),      # 238 -- shore contact
})


def sea_adjacent_lawful(a: str, b: str) -> bool:
    """Does stock FF9 author sea-shade ``a`` directly abutting ``b`` (either order)?  Same-shade is always
    lawful; every other lawful COASTAL pair is in :data:`SEA_ADJ_LAWFUL` (byte-derived, never invented).
    The off-language pairs a CROP can introduce -- ``sea1|sea4``, ``sea2|sea4``, ``sea2|sea5`` (and the deep
    system's ``sea3|sea4``) -- return False: each has 0 systematic stock instances.  (The sea5 transition
    tip terminates INTO the deep ring lawfully, but that is ORIENTATION-gated, not pairwise -- handled by
    the gate's sea5 deep-set logic, not this table.)"""
    return a == b or frozenset({a, b}) in SEA_ADJ_LAWFUL


def effective_prefab_arm(meshes, *, cell, sidecar_parts, disc: int = 1, lod: str = "0_1"):
    """THE EFFECTIVE-PREFAB GATE + AUTO-ARM (the (11,19) water-only-cell fix; THE DIVERT-ARM /
    EFFECTIVE-PREFAB laws, in-game proven 2026-07-20).

    The engine binds a cell's sub-mesh overrides ONLY for the transforms its EFFECTIVE prefab exposes,
    looked up by ``transform.name``:
      * a cell WITH a ``Terrain.ff9mesh`` override (real, blanked, or a stub) has ``HasLandOverride`` =
        true -> the s34 divert fires -> the effective prefab is the ``Donor.txt`` DONOR prefab, whose
        transform set = ``sidecar_parts``;
      * a cell WITHOUT any Terrain override loads the generic ``SeaBlockPrefab``, whose ONLY transform is
        ``Sea4`` -> every OTHER emitted sea layer (Sea3/Sea5/Beach1/...) is SILENTLY DROPPED (holes +
        a pale/black void -- the (11,19) bug).

    So a WATER-ONLY carry (donor + sidecar both Terrain-less) that emits >1 sea layer must AUTO-ARM: emit
    a degenerate :func:`ff9mapkit.world.mesh.stub_terrain_mesh` (never bound as geometry -- a water-only
    donor prefab has no ``TerrainForm1``) so the divert loads the sidecar prefab and each layer binds its
    OWN material.  ``meshes`` = the ``(part_name, BlockMesh)`` list about to deploy for ``cell``;
    ``sidecar_parts`` = the lowercase part names the cell's ``Donor.txt`` prefab exposes.  Returns
    ``(arm_mesh_or_None, gate_dict)``; the arm mesh (if any) is deploy-only (excluded from the weld/
    coverage census -- it is skip-flagged and below the world).  IDEMPOTENT: a cell that already ships a
    Terrain override needs no arm -> ``arm_mesh`` is ``None`` and the bytes are unchanged."""
    from . import mesh as M
    names = {pn for pn, _ in meshes}
    (bx, by) = cell
    has_terrain = "Terrain" in names
    non_sea4 = {pn for pn in names if pn not in ("Terrain", "Sea4")}
    arm = None
    armed = False
    if not has_terrain and non_sea4:                          # SeaBlockPrefab would bind ONLY Sea4
        arm = M.stub_terrain_mesh(disc=disc, x=bx, y=by, lod=lod)
        armed = True
        has_terrain = True
    if has_terrain:
        bound = {p.lower() for p in (sidecar_parts if sidecar_parts is not None
                                     else {pn.lower() for pn in names})}
    else:
        bound = {"sea4"}                                       # generic SeaBlockPrefab
    emitted = {pn.lower() for pn in names}
    unbindable = sorted(p for p in emitted if p != "terrain" and p not in bound)
    gate = {"gate": f"effective-prefab[{bx},{by}]", "armed": armed, "bound": sorted(bound),
            "unbindable": unbindable, "ok": not unbindable}
    return arm, gate


def _sea_shade_grid(sea_by_name):
    """16x16 shade grid ('sea3'/'sea4'/'sea5', empty->'sea4') from a ``{lower_part: BlockMesh}`` map --
    the deployed-byte counterpart of :func:`ff9mapkit.world.water.read_shade_grid`."""
    seen = [[None] * _G for _ in range(_G)]
    for part in ("sea3", "sea4", "sea5"):
        bm = sea_by_name.get(part)
        if bm is None:
            continue
        for tri in bm.tris:
            i = int((sum(bm.verts[q][0] for q in tri) / 3) // _CELL)
            j = int((-sum(bm.verts[q][2] for q in tri) / 3) // _CELL)
            if 0 <= i < _G and 0 <= j < _G:
                seen[i][j] = part
    return [[seen[i][j] or "sea4" for j in range(_G)] for i in range(_G)]


def _sea_water_grid(sea_by_name):
    """16x16 has-water bool grid (any Sea3/Sea4/Sea5 triangle binned to the cell) -- for LAND-AWARENESS
    (a 'sea4' shade with NO water triangle is a coast/land cell, not deep water)."""
    hw = [[False] * _G for _ in range(_G)]
    for part in ("sea3", "sea4", "sea5"):
        bm = sea_by_name.get(part)
        if bm is None:
            continue
        for tri in bm.tris:
            i = int((sum(bm.verts[q][0] for q in tri) / 3) // _CELL)
            j = int((-sum(bm.verts[q][2] for q in tri) / 3) // _CELL)
            if 0 <= i < _G and 0 <= j < _G:
                hw[i][j] = True
    return hw


def _sea_shallow_grid(sea_by_name):
    """16x16 COASTAL-shade grid ('sea1'/'sea2'/None) -- the shallow-alphabet counterpart of
    :func:`_sea_shade_grid`, which bins only the DEEP sea3/4/5 alphabet (so a Sea1/Sea2 frame tile read as
    deep and was never flagged -- the (12,18) sand-spit corner the {sea1,sea5} ladder had to fix by hand).
    Shallowest wins per THE RING LADDER (sea2 is shallower than sea1); a cell with neither reads None."""
    seen = [[None] * _G for _ in range(_G)]
    for part in ("sea1", "sea2"):                       # sea2 iterated last -> shallowest wins the label
        bm = sea_by_name.get(part)
        if bm is None:
            continue
        for tri in bm.tris:
            i = int((sum(bm.verts[q][0] for q in tri) / 3) // _CELL)
            j = int((-sum(bm.verts[q][2] for q in tri) / 3) // _CELL)
            if 0 <= i < _G and 0 <= j < _G:
                seen[i][j] = part
    return seen


def _sea5_deepsets(sea5_bm):
    """{(i,j): deepset} for a Sea5 BlockMesh, fitting cells with >=3 corner UVs (so a 1-triangle shore
    sliver classifies too), via :func:`ff9mapkit.world.water._fit_tile` + the DEEPSET2TILE inverse."""
    from . import water as W
    if sea5_bm is None:
        return {}
    inv = {sr: ds for ds, variants in W.DEEPSET2TILE.items() for sr in variants}
    corners = collections.defaultdict(dict)
    for tri in sea5_bm.tris:
        i = int((sum(sea5_bm.verts[q][0] for q in tri) / 3) // _CELL)
        j = int((-sum(sea5_bm.verts[q][2] for q in tri) / 3) // _CELL)
        for k in tri:
            v = sea5_bm.verts[k]
            corners[(i, j)][(round((v[0] - i * _CELL) / _CELL), round((-v[2] - j * _CELL) / _CELL))] = sea5_bm.uvs[k]
    out = {}
    for (i, j), d in corners.items():
        if len(d) >= 3:
            us = [uv[0] for uv in d.values()]
            vs = [uv[1] for uv in d.values()]
            if max(us) - min(us) > 1e-6 and max(vs) - min(vs) > 1e-6:
                fit = W._fit_tile(d)
                if fit is not None:
                    ds = inv.get((W._strip_of(fit[2]), fit[4]))
                    if ds is not None:
                        out[(i, j)] = ds
    return out


def wang_carry_gate(sea_by_cell, region_cells, *, enforce=False, allow=False):
    """THE WANG-CARRY GATE (THE WANG-CARRY LAW, user-authored 2026-07-20; productizes the (11,19)
    study's land-aware ``frame_edge_verdicts`` census).

    Water tiles are a cross-block WANG puzzle: neighbouring cells agree by construction (a Sea3 shallow
    never abuts a Sea4 deep without a Sea5 transition bridge), and that holds ACROSS block seams too.  A
    carry that CROPS a Wang region breaks the puzzle at the CUT edges -- the carried region's OUTER FRAME,
    where a tile that was interior (facing more island water) now faces the open-ocean deep with no
    transition ring = a hard shallow|deep seam (the 17 cropped-Wang rim seams on the (8,17)+2x2 island,
    fixed by ``studies/overworld-topography/wang_rim_retile.py``).

    This gate CENSUSES the carried cells' OUTER-FRAME sea tiles (land-aware: an edge whose region-
    neighbour carries no water triangle is a coast, not deep, and is skipped -- without this the census
    over-flags real coastlines).  It runs TWO parallel systems whose counts are reported separately:

    * THE DEEP SYSTEM (unchanged): a ``sea3`` / mis-oriented-``sea5`` frame tile facing the open-ocean deep
      ring is ``incoherent`` (surfaced in ``incoherent_deep``).
    * THE COASTAL SYSTEM (the shade-alphabet extension, 2026-07-20): :func:`_sea_shade_grid` bins only the
      DEEP sea3/4/5 alphabet, so a **Sea1/Sea2** frame tile read as deep and was NEVER flagged -- the exact
      class the {sea1,sea5} ladder had to close by hand on the deployed island (2 sea1|sea4 sand-spit corner
      tiles).  A sea1/sea2 frame tile is now binned by :func:`_sea_shallow_grid` and flagged
      (``incoherent_shallow``) because stock authors ``sea1|sea4`` and ``sea2|sea4`` ZERO times map-wide
      (``s12_stock_map_census_opus.py`` -- land-aware, interior + cross-block): a sea1 tile's DEEPEST lawful
      neighbour is sea5, a sea2 tile's is sea3, so neither ever faces the deep ring (:data:`SEA_ADJ_LAWFUL`).
      The interior donor-verbatim ``sea2|sea4`` tile at (12,19) is an INTERIOR edge the frame census never
      sees, so it never false-positives.

    ``incoherent`` = ``incoherent_deep + incoherent_shallow``; the two systems are mutually exclusive per
    edge (a deep-flagged cell is not re-counted as coastal), so the DEEP count is byte-identical to the
    pre-extension gate -- the coastal count is purely ADDITIVE.  Every flagged edge is in ``detail``.

    ``enforce`` controls whether an incoherent frame edge FAILS the build.  It defaults **OFF** -- report-
    only with a ``warn`` flag, ``ok`` stays True -- and this is NOT because the predicate is unreliable.
    The opposite: a map-wide census of shipping FF9 finds **ZERO** sea3-directly-abuts-sea4 edges across
    ANY block border (all 194 shallow->deep transitions are sea5-mediated;
    ``studies/overworld-topography/wang_seam_census.py``), so a flagged sea3-abuts-deep frame edge IS a
    real seam.  The default does not REFUSE because carrying ANY coastal island standalone necessarily
    crops the neighbour blocks that hosted its sea5 transition rings -- so a real coastal donor (e.g.
    (7,17) alone shows 16 flagged frame edges) legitimately PRODUCES frame seams, fixed by a post-carry
    RE-TILE (the ``studies/overworld-topography/wang_rim_retile.py`` pattern), a human-reviewed step (the
    shallow-rim look at the exact carry is the user's visual call, Hard-Constraint S2).  So the gate WARNS
    by default and refuses only on demand.

    NOTE (why there is no safe hard-fail-by-default): a DONOR-BASELINE subtraction (census the donor's own
    frame and subtract the "pre-existing" seams) does not help -- since shipping FF9 has no sea3-abuts-deep
    edge ANYWHERE, there is no pre-existing such edge to subtract; every flagged sea3 frame edge is
    crop-introduced, so the subtraction collapses to the raw count and would refuse every coastal carry
    (empirically the donor-outward-deep baseline calls 15/16 of the proven (7,17) carry "introduced").
    ``enforce=True`` hard-fails on any incoherent frame edge (a fresh mint onto known-deep open ocean, or
    a post-retile CI check); ``allow`` waives even then.

    ``sea_by_cell`` = ``{(bx,by): {lower_part: BlockMesh}}`` for the carried WATER cells (sea1/sea2 keys are
    now consumed by the coastal system; the deep grids ignore them, so passing them is byte-neutral there);
    ``region_cells`` = the set of ``(bx,by)`` in the carried region (an edge to a NON-region block faces the
    deep ring)."""
    dirs = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
    region = {tuple(c) for c in region_cells}
    shade = {c: _sea_shade_grid(p) for c, p in sea_by_cell.items()}
    water = {c: _sea_water_grid(p) for c, p in sea_by_cell.items()}
    shallow = {c: _sea_shallow_grid(p) for c, p in sea_by_cell.items()}
    ds5 = {c: _sea5_deepsets(p.get("sea5")) for c, p in sea_by_cell.items()}
    deep_bad, shallow_bad = [], []
    for (bx, by), _p in sea_by_cell.items():
        g, w, sg, d5 = shade[(bx, by)], water[(bx, by)], shallow[(bx, by)], ds5[(bx, by)]
        for i in range(_G):
            for j in range(_G):
                if not (w[i][j] or sg[i][j] is not None):     # deep water OR a coastal (sea1/sea2) tile
                    continue
                for d in "NESW":
                    di, dj = dirs[d]
                    off = not (0 <= i + di < _G and 0 <= j + dj < _G)
                    to_block = (bx + (1 if i + di >= _G else -1 if i + di < 0 else 0),
                                by + (1 if j + dj >= _G else -1 if j + dj < 0 else 0))
                    if not (off and to_block not in region):   # only OUTER-FRAME edges (facing the deep ring)
                        continue
                    # DEEP system -- byte-identical verdicts to the pre-extension gate; runs only where the
                    # deep sea3/4/5 alphabet is binned.  A deep-flagged edge is NOT re-counted as coastal.
                    if w[i][j]:
                        sh = g[i][j]
                        if sh == "sea3":
                            deep_bad.append(((bx, by), (i, j), d, "sea3 abuts deep, no transition ring"))
                            continue
                        if sh != "sea4":                       # sea5: coherent iff its tip points OUT
                            ds = d5.get((i, j))
                            if ds is None or d not in ds:
                                deep_bad.append(((bx, by), (i, j), d,
                                                 f"sea5 deepset {sorted(ds) if ds else None} !point {d}"))
                            continue                           # sea5 resolved (coherent or flagged)
                        # sh == "sea4": deep meets deep -> coherent; fall through in case a Sea1/Sea2 tile
                        # ALSO occupies this cell (a mixed shallow+deep cell still faces the deep ring shallow)
                    # COASTAL system (the shade-alphabet extension): a Sea1/Sea2 frame tile facing the deep
                    # ring is off-language -- stock authors sea1|sea4 / sea2|sea4 ZERO times (SEA_ADJ_LAWFUL).
                    ssh = sg[i][j]
                    if ssh is not None and not sea_adjacent_lawful(ssh, "sea4"):
                        shallow_bad.append(((bx, by), (i, j), d, f"{ssh} abuts deep, no ladder ring"))
    incoherent = deep_bad + shallow_bad
    detail = "; ".join(f"({bxy[0]},{bxy[1]})@{ij}.{d}" for (bxy, ij, d, _r) in incoherent[:6])
    ok = allow or (not enforce) or not incoherent
    # WARN by default (report-only, ok True) when the carry produced real cropped-Wang frame seams --
    # the count is surfaced but the build is not refused (a coastal carry is expected to be re-tiled or
    # accepted by the human).  Suppressed once enforced (then it FAILS) or explicitly allowed.
    warn = bool(incoherent) and not enforce and not allow
    return {"gate": "wang-carry", "incoherent": len(incoherent),
            "incoherent_deep": len(deep_bad), "incoherent_shallow": len(shallow_bad),
            "enforced": bool(enforce), "warn": warn, "detail": detail or 0, "ok": ok}


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
               allow_mod_overwrite: bool = False, allow_wang_seams: bool = False,
               enforce_wang_carry: bool = False, allow_orphan_decals: bool = False,
               enforce_orphan_decals: bool = False, redress_orphans: bool = False,
               enforce_texture_gates: bool = False, allow_texture_gates: bool = False,
               dry_run: bool = False, skip_mirror: bool = False,
               target_disc: int | None = None, all_sea_target: bool = False) -> dict:
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
    and the engine-placement census (``miss == 0`` -- full walk/sail coverage). Two more WARN-by-
    default (report-only) census gates ride alongside: :func:`wang_carry_gate` and
    :func:`~ff9mapkit.world.orphangate.orphan_decal_gate` (a STRIPS transition-vocabulary decal --
    e.g. a grass|desert fringe tile -- carried without the neighbourhood context that justifies it;
    checked against a 1-block Moore RING of real deployed-or-stock terrain around the target, read-
    only, matching the study's own ``--census3``; ``enforce_orphan_decals``/``allow_orphan_decals``
    match the wang-carry knobs; ``redress_orphans`` auto-fixes every non-``AMBIGUOUS`` finding to the
    wearing side's plain mains IN MEMORY before any write). ``dry_run``
    builds and gates without writing. A donor part whose tris all clip away is BLANKED (a hidden
    override) so the donor prefab's original sub-mesh cannot render unrotated underneath.

    Returns a summary dict (``clean``, ``gates``, ``carried``, ``shift``, ``deployed`` paths). A real deploy
    auto-mirrors the written overrides to Disc4 (THE DISC-4 GAP; ``skip_mirror=True`` opts out)."""
    (bx, by) = cell
    (dbx, dby) = donor
    if not (0 <= bx < GRID_X and 0 <= by < GRID_Y):
        raise ValueError(f"cell ({bx},{by}) out of the {GRID_X}x{GRID_Y} overworld grid")
    if not (0 <= dbx < GRID_X and 0 <= dby < GRID_Y):
        raise ValueError(f"donor ({dbx},{dby}) out of the {GRID_X}x{GRID_Y} overworld grid")
    rtarget = disc if target_disc is None else int(target_disc)   # THE READ/WRITE DISC SPLIT:
    # `disc` stays the STOCK read disc (the donor bytes); `rtarget` is where the overrides land.
    # THE TARGET must be OPEN OCEAN (no per-block mesh assets -- it renders from the shared
    # SeaBlockPrefab). A cell with real data is part of the game's world: overriding it replaces
    # real continent/coast geometry and shreds the whole area (proven the hard way, 2026-07-08).
    # ``all_sea_target`` opts out -- the island.py law verbatim: the gate is a PROXY probing the
    # REAL disc's assets, broken in both directions on a Path D world in s75 BLANK mode, yet
    # DELIBERATELY NOT keyed on ``target_disc != disc`` because in s75 CLONE mode the synthetic
    # grid's IsSea flags ARE the stock flags this probe measures -- folding the skip into the
    # retarget would fail-OPEN on precisely the mode that needs it.
    if not allow_real_target and not all_sea_target:
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

    # THE EFFECTIVE-PREFAB GATE + AUTO-ARM: a water-only carry (no Terrain override) would load the
    # generic SeaBlockPrefab and bind ONLY Sea4 -- so arm the divert with a stub Terrain (deploy-only;
    # excluded from the weld/coverage census below since it is skip-flagged + below the world).
    arm_mesh, effective_gate = effective_prefab_arm(
        meshes, cell=(bx, by), sidecar_parts={p for p in parts if donor_has_part[p]}, disc=disc, lod=lod)

    # 6) GATES -- all must pass; I cannot see the game, these substitute for eyes.
    from . import orphangate as OG
    gates = []
    gates.append(effective_gate)
    gates.append(wang_carry_gate(
        {(bx, by): {pn.lower(): bm for pn, bm in meshes
                    if pn.lower() in ("sea1", "sea2", "sea3", "sea4", "sea5")}},
        {(bx, by)}, enforce=enforce_wang_carry, allow=allow_wang_seams))
    gates.append(OG.orphan_decal_gate(
        {(bx, by): meshes}, {(bx, by)}, enforce=enforce_orphan_decals,
        allow=allow_orphan_decals, redress=redress_orphans,
        mod_folder=mod_folder, disc=disc, lod=lod, game=game))
    # THE TEXTURE + SEA GATES (the Rung-F UV/relief fold-back, 2026-07-25) -- same WARN-default
    # shape as the two gates above, purely read-only, zero output-byte change.  Runs AFTER the
    # orphan gate so a --redress-orphans mutation is judged in its POST state.  ``quad_ori`` is
    # deliberately not supplied: a carry (GroundRetile included) TRANSLATES the donor's own free
    # fractional windows rather than minting on the 2x2 quadrant lattice, so the ONE-WINDOW law is
    # undefined here and its gate reports ``skipped`` -- see texgates' calibration docstring.
    from . import texgates as TG
    gates.extend(TG.texture_sea_gates({(bx, by): meshes}, {(bx, by)},
                                      enforce=enforce_texture_gates, allow=allow_texture_gates))
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
            for tw_ in tweaks:                             # undo displacement fields (bows)
                inv = getattr(tw_, "census_inverse", None)
                if inv is not None:
                    wx, wz = inv(dlx + 64.0 * dbx, dlz - 64.0 * dby)
                    dlx, dlz = wx - 64.0 * dbx, wz + 64.0 * dby
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
    gates.append(_mod_overwrite_gate(mod_folder, {(bx, by): (dbx, dby)}, disc=rtarget,
                                     lod=lod, game=game, allow=allow_mod_overwrite))
    clean = all(g["ok"] for g in gates)

    summary = {"op": "transplant", "donor": [dbx, dby], "cell": [bx, by], "rot": rot,
               "disc": disc, "target_disc": rtarget,
               "shift": [sh_x, sh_z], "window": {"x": list(win_x), "z": list(win_z)},
               "strips": sorted(strips_with_data & windowed),
               "coverage_strips": sorted(strips_with_data - windowed), "carried": carried,
               "clipped_out": clipped_out, "blanked": blanked, "gates": gates,
               "clean": clean, "dry_run": dry_run, "deployed": []}
    if dry_run or not clean:
        return summary
    for (pn, bm) in meshes:
        summary["deployed"].append(str(M.deploy_override(bm, mod_folder=mod_folder, game=game,
                                                         lod=lod, part=pn, disc=rtarget)))
    if arm_mesh is not None:                                   # the divert-arm stub Terrain (water-only cell)
        summary["deployed"].append(str(M.deploy_override(arm_mesh, mod_folder=mod_folder, game=game,
                                                         lod=lod, part="Terrain", disc=rtarget)))
    summary["deployed"].append(str(M.deploy_donor_sidecar(dbx, dby, mod_folder=mod_folder,
                                                          disc=rtarget, x=bx, y=by, lod=lod,
                                                          game=game)))
    from . import discmirror as DM
    DM.auto_mirror(summary["deployed"], mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary


def morph_in_place(mod_folder: str, *, cell, tweaks, parts=PARTS, disc: int = 1,
                   lod: str = "0_1", game=None, dry_run: bool = False,
                   skip_mirror: bool = False) -> dict:
    """Apply tweak objects to a REAL world cell IN PLACE -- the coast-morph demonstrator
    path for shores no single-cell transplant can carry (a nose beach's landmass is always
    a coastline fragment; only (7,17)'s pocket is fully in-block). Reads the cell's own
    parts, runs the tweak pipeline, and deploys loose overrides for the TOUCHED parts
    only, keyed to the SAME cell: the s34 per-part override loads for any streamed block
    (``transform.name``-keyed -- real land cells included; ``world-terrain`` is the
    Terrain-only precedent). No Donor.txt, no placement census, no land-fit: the cell
    keeps its real neighbours, so tweaks must be frame-safe by construction (the
    coastmorph fields pin block-frame verts). Reversible: delete the deployed files. A real
    deploy auto-mirrors the written overrides to Disc4 (``skip_mirror=True`` opts out)."""
    from . import mesh as M
    bx, by = cell
    raw, originals = {}, {}
    for p in parts:
        tris = world_tris(bx, by, p, disc=disc, lod=lod, game=game)
        if not tris:
            # a part the cell does not carry: the prefab has NO transform for it, so
            # a loose override could never bind (the (6,17) lesson) -- a tweak that
            # EMITS into it must refuse, not silently drop its tris (the (18,3)
            # desert-beach incident: foam/wash/sea1 vanished while gates read clean)
            eaten = sum(len(tw.emit() or ()) for tw in tweaks
                        if getattr(tw, "part", None) == p)
            if eaten:
                raise ValueError(
                    f"cell {cell} carries no '{p}' part -- its prefab has no such "
                    f"transform, so the {eaten} emitted tris could never render. "
                    f"An in-place morph can only emit into parts the REAL cell "
                    f"already has; pick a window on a block that carries them")
            continue
        polys, touched = [], False
        for tri in tris:
            poly = list(tri)
            for tw in tweaks:
                p2 = tw.apply(p, poly)
                if p2 is not poly:
                    touched = True
                poly = p2
                if poly is None:
                    break
            if poly is not None:
                polys.append(poly)
        for tw in tweaks:
            if getattr(tw, "part", None) == p:
                em = tw.emit()
                if em:
                    touched = True
                    polys.extend(list(e) for e in em)
        if touched:
            raw[p] = polys
            originals[p] = tris
    gates = [tw.gate() for tw in tweaks]

    # IN-PLACE-specific gates: the cell keeps its REAL neighbours, so (a) every vert on
    # the block frame welds to a neighbour block's coincident vert -- the frame vert SET
    # must be byte-unchanged; (b) nothing may spill past the cell (the transplant's bounds
    # gate, in-place flavour: an emitted structural outline must stay in the block).
    def _frame_set(polys):
        out = set()
        for poly in polys:
            for v in poly:
                lx, lz = v[0][0] - 64.0 * bx, v[0][2] + 64.0 * by
                if min(abs(lx), abs(lx - 64.0), abs(lz), abs(lz + 64.0)) < 0.01:
                    out.add((round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)))
        return out
    for p in sorted(raw):
        fw_ok = _frame_set(raw[p]) == _frame_set(originals[p])
        oob = sum(1 for poly in raw[p] for v in poly
                  if not (-0.01 <= v[0][0] - 64.0 * bx <= 64.01
                          and -64.01 <= v[0][2] + 64.0 * by <= 0.01))
        gates.append({"gate": f"in-place-frame[{p}]", "welds": "unchanged" if fw_ok
                      else "CHANGED", "out_of_cell": oob, "ok": fw_ok and oob == 0})
    clean = all(g.get("ok", True) for g in gates)
    summary = {"op": "morph-in-place", "cell": [bx, by], "touched": sorted(raw),
               "gates": gates, "clean": clean, "dry_run": dry_run, "deployed": []}
    if not raw:
        raise ValueError("no tweak touched this cell -- nothing to morph in place")
    if dry_run or not clean:
        return summary
    for p in sorted(raw):
        loc = [[((v[0][0] - 64.0 * bx, v[0][1], v[0][2] + 64.0 * by), v[1], v[2], v[3])
                for v in poly] for poly in raw[p]]
        nm = f"Block[{bx}][{by}] {part_name(p)}"
        bm = _soup_block_mesh(nm, (bx, by), loc, disc=disc, lod=lod)
        summary["deployed"].append(str(M.deploy_override(
            bm, mod_folder=mod_folder, game=game, lod=lod, part=part_name(p))))
    from . import discmirror as DM
    DM.auto_mirror(summary["deployed"], mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary


def transplant_region(mod_folder: str, *, cell, donor, size=(1, 1), rot: int = 0, shift="auto",
                      parts=PARTS, tweaks=(), strips="auto", extra: float = 8.0,
                      land_margin: float = 2.0, disc: int = 1, lod: str = "0_1", game=None,
                      census_samples: int = 24, allow_real_target: bool = False,
                      allow_object_misalign: bool = False, allow_mod_overwrite: bool = False,
                      allow_wang_seams: bool = False, enforce_wang_carry: bool = False,
                      allow_orphan_decals: bool = False, enforce_orphan_decals: bool = False,
                      redress_orphans: bool = False,
                      enforce_texture_gates: bool = False, allow_texture_gates: bool = False,
                      dry_run: bool = False, skip_mirror: bool = False,
                      target_disc: int | None = None, all_sea_target: bool = False) -> dict:
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
    ocean, on a deployed cell it would be a void + vehicle wall). Two more WARN-by-default
    (report-only) census gates ride over the whole region: :func:`wang_carry_gate` and
    :func:`~ff9mapkit.world.orphangate.orphan_decal_gate` (``enforce_orphan_decals``/
    ``allow_orphan_decals``/``redress_orphans`` -- see :func:`transplant`).

    A real deploy auto-mirrors the written overrides to Disc4 (THE DISC-4 GAP; ``skip_mirror=True``
    opts out -- :func:`~ff9mapkit.world.fuse.fuse_layout` uses this to defer to its own single
    end-of-layout mirror instead of one per placement)."""
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

    rtarget = disc if target_disc is None else int(target_disc)   # THE READ/WRITE DISC SPLIT
    # ``all_sea_target`` skips the stock-occupancy proxy exactly as in :func:`transplant` /
    # island.landmass -- deliberately NOT keyed on ``target_disc != disc`` (s75 CLONE mode).
    if not allow_real_target and not all_sea_target:
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
    cell_sidecar: dict = {}                   # (i, j) -> the cell's Donor.txt prefab part set (bind set)
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
        pick = pick_parts = None
        if set(need) <= donor_cell_has[nat]:
            pick = (dbx + nat[0], dby + nat[1])
            pick_parts = donor_cell_has[nat]
        else:
            for c in dcells:
                if c != nat and not obj_by_cell[c] and set(need) <= donor_cell_has[c]:
                    pick = (dbx + c[0], dby + c[1])
                    pick_parts = donor_cell_has[c]
                    break
        if pick is None:
            # a synthesized part set (a minted beach on a beach-less donor) has
            # no in-region host by construction -- widen the sidecar search
            # map-wide (superset of parts, no Object; the same law)
            pick, pick_parts = _prefab_fallback(need, disc=disc, lod=lod,
                                                game=game)
        if pick is None:
            prefab_bad.append({"cell": [bx + i, by + j], "need": need,
                               "natural": [dbx + nat[0], dby + nat[1]]})
            continue
        blanked = sorted(pick_parts - set(need), key=parts.index)
        meshes = []
        for p in parts:
            nm = f"Block[{bx + i}][{by + j}] {part_name(p)}"
            if cell_tris[(i, j)][p]:
                loc = [[((v[0][0] - 64.0 * i, v[0][1], v[0][2] + 64.0 * j), v[1], v[2], v[3])
                        for v in t] for t in cell_tris[(i, j)][p]]
                bm = _soup_block_mesh(nm, (bx + i, by + j), loc, disc=disc, lod=lod)
                reg = _soup_block_mesh(nm, (bx + i, by + j), cell_tris[(i, j)][p],
                                       disc=disc, lod=lod)
            elif p in pick_parts:
                bm = M.hidden_block_mesh(name=nm, disc=disc, x=bx + i, y=by + j, lod=lod)
                reg = bm
            else:
                continue
            meshes.append((part_name(p), bm))
            audit_meshes.append((part_name(p), reg))
            census_meshes.setdefault((i, j), []).append((part_name(p), reg))
        deploy_meshes[(i, j)] = meshes
        cell_sidecar[(i, j)] = set(pick_parts)
        cell_meta[(i, j)] = {"cell": [bx + i, by + j], "donor": [pick[0], pick[1]],
                             "carried": {p: len(cell_tris[(i, j)][p]) for p in need},
                             "blanked": blanked}

    # THE EFFECTIVE-PREFAB GATE + AUTO-ARM (per cell): a water-only cell whose sidecar prefab is also
    # Terrain-less binds ONLY Sea4 -- arm the divert with a stub Terrain so each carried sea layer binds
    # (deploy-only; excluded from weld/census).  See effective_prefab_arm.
    arm_meshes: dict = {}

    # 6) GATES -- all must pass; I cannot see the game, these substitute for eyes.
    gates = []
    for (i, j), mlist in deploy_meshes.items():
        arm, epg = effective_prefab_arm(mlist, cell=(bx + i, by + j), sidecar_parts=cell_sidecar[(i, j)],
                                        disc=disc, lod=lod)
        gates.append(epg)
        if arm is not None:
            arm_meshes[(i, j)] = arm
    gates.append(wang_carry_gate(
        {(bx + i, by + j): {pn.lower(): bm for pn, bm in mlist
                            if pn.lower() in ("sea1", "sea2", "sea3", "sea4", "sea5")}
         for (i, j), mlist in deploy_meshes.items()},
        {tuple(cell_meta[(i, j)]["cell"]) for (i, j) in deploy_meshes},
        enforce=enforce_wang_carry, allow=allow_wang_seams))
    from . import orphangate as OG
    orphan_region = {tuple(cell_meta[(i, j)]["cell"]) for (i, j) in deploy_meshes}
    gates.append(OG.orphan_decal_gate(
        {tuple(cell_meta[(i, j)]["cell"]): mlist for (i, j), mlist in deploy_meshes.items()},
        orphan_region, enforce=enforce_orphan_decals, allow=allow_orphan_decals,
        redress=redress_orphans, mod_folder=mod_folder, disc=disc, lod=lod, game=game))
    # THE TEXTURE + SEA GATES -- see the note at transplant()'s own call site (same shape, same
    # WARN default, read-only; region-wide so sea predicate B actually has adjacent-block pairs).
    from . import texgates as TG
    gates.extend(TG.texture_sea_gates(
        {tuple(cell_meta[(i, j)]["cell"]): mlist for (i, j), mlist in deploy_meshes.items()},
        orphan_region, enforce=enforce_texture_gates, allow=allow_texture_gates))
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
        for tw_ in tweaks:                                 # undo displacement fields (bows)
            inv = getattr(tw_, "census_inverse", None)
            if inv is not None:
                wx, wz = inv(dlx + 64.0 * dbx, dlz - 64.0 * dby)
                dlx, dlz = wx - 64.0 * dbx, wz + 64.0 * dby
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
    gates.append(_mod_overwrite_gate(
        mod_folder,
        {(bx + i, by + j): tuple(cell_meta[(i, j)]["donor"]) for (i, j) in deploy_meshes},
        disc=rtarget, lod=lod, game=game, allow=allow_mod_overwrite))
    clean = all(g["ok"] for g in gates)

    # FRAME BORDER PROFILES (the cross-donor FUSE law's input, 2026-07-09): per frame edge,
    # per 4u row along it, the parts with a tri EDGE on the plane (>=2 on-plane verts; an
    # edge spanning several rows contributes to each) + an on-lattice flag, plus which
    # border cells deploy at all. `fuse_census` reads two placements' facing profiles to
    # certify their shared border (see world/fuse.py) -- rows are REGION-frame indices
    # (`floor(region_coord / 4)`); world rows = region rows offset by the rect anchor.
    frame_profile: dict = {}
    for (ename, faxis, fplane, ecells) in (
            ("W", 0, 0.0, [(0, j) for j in range(th)]),
            ("E", 0, float(ext_r[0]), [(tw - 1, j) for j in range(th)]),
            ("N", 2, 0.0, [(i, 0) for i in range(tw)]),
            ("S", 2, -float(ext_r[1]), [(i, th - 1) for i in range(tw)])):
        rows: dict = {}
        lat_bad: set = set()
        edep = []
        along = 2 if faxis == 0 else 0
        for (i, j) in ecells:
            if (i, j) not in deploy_meshes:
                continue                      # stays prefab: no profile rows to speak of
            edep.append(j if faxis == 0 else i)
            for p in parts:
                for t in cell_tris[(i, j)][p]:
                    onp = [v for v in t if abs(v[0][faxis] - fplane) <= 1e-4]
                    if len(onp) < 2:
                        continue
                    lo = min(v[0][along] for v in onp)
                    hi = max(v[0][along] for v in onp)
                    for r in range(math.floor(lo / 4.0 + 1e-9),
                                   max(math.floor(lo / 4.0 + 1e-9) + 1,
                                       math.ceil(hi / 4.0 - 1e-9))):
                        rows.setdefault(r, set()).add(p)
                        if any(abs(v[0][along] / 4.0 - round(v[0][along] / 4.0)) > 2.5e-4
                               for v in onp):
                            lat_bad.add(r)
        frame_profile[ename] = {"plane": fplane, "deployed": sorted(edep),
                                "rows": {str(r): {"parts": sorted(rows[r]),
                                                  "lattice": r not in lat_bad}
                                         for r in sorted(rows)}}

    summary = {"op": "transplant-region", "donor": [dbx, dby], "size": [nx, ny],
               "cell": [bx, by], "tsize": [tw, th], "rot": rot, "shift": [sh_x, sh_z],
               "disc": disc, "target_disc": rtarget,
               "window": {"x": list(win_x), "z": list(win_z)},
               "strips": sorted(strips_with_data & windowed),
               "coverage_strips": sorted(strips_with_data - windowed), "carried": carried,
               "clipped_out": clipped_out,
               "cells": {f"{bx + i},{by + j}": cell_meta[(i, j)] for (i, j) in tcells
                         if (i, j) in cell_meta},
               "frame_profile": frame_profile,
               "gates": gates, "clean": clean, "dry_run": dry_run, "deployed": []}
    if dry_run or not clean:
        return summary
    for (i, j) in tcells:
        if (i, j) not in deploy_meshes:
            continue
        for (pn, bm) in deploy_meshes[(i, j)]:
            summary["deployed"].append(str(M.deploy_override(bm, mod_folder=mod_folder,
                                                             game=game, lod=lod, part=pn,
                                                             disc=rtarget)))
        if (i, j) in arm_meshes:                              # the divert-arm stub Terrain (water-only cell)
            summary["deployed"].append(str(M.deploy_override(arm_meshes[(i, j)], mod_folder=mod_folder,
                                                             game=game, lod=lod, part="Terrain",
                                                             disc=rtarget)))
        (sdx, sdy) = cell_meta[(i, j)]["donor"]
        summary["deployed"].append(str(M.deploy_donor_sidecar(sdx, sdy, mod_folder=mod_folder,
                                                              disc=rtarget, x=bx + i, y=by + j,
                                                              lod=lod, game=game)))
    from . import discmirror as DM
    DM.auto_mirror(summary["deployed"], mod_folder=mod_folder, skip_mirror=skip_mirror)
    return summary


# --------------------------------------------------------------------------- excise
#: sea4's measured UV quadrant vocabulary -- u breaks 0/0.5039/0.9921, v breaks
#: 0/0.5079/1.0. The quadrant is distributed UNIFORMLY across world-cell parities, i.e.
#: the anti-tiling choice is free: a patch cannot pick a "wrong" tile.
SEA4_QUADS = ((0.0, 0.0, 0.5039, 0.5079), (0.5039, 0.0, 0.9921, 0.5079),
              (0.0, 0.5079, 0.5039, 1.0), (0.5039, 0.5079, 0.9921, 1.0))
SEA4_IDALL = 228


def _plan_centroid(tri):
    return (sum(v[0][0] for v in tri) / 3.0, sum(v[0][2] for v in tri) / 3.0)


def _point_in_poly(p, poly) -> bool:
    x, z = p
    inside = False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        if (az > z) != (bz > z):
            t = (z - az) / (bz - az)
            if x < ax + t * (bx - ax):
                inside = not inside
    return inside


def excise_plan(donor, size=(1, 1), *, disc: int = 1, lod: str = "0_1", game=None,
                land_margin: float = 2.0, parts=PARTS, keep_largest: bool = True):
    """Plan the EXCISE of every landmass ASSEMBLY that crosses the donor rect frame.

    A multi-block carry is refused by the ``land-fit`` gate whenever a neighbouring mass
    crosses the rect frame: carrying it ships a mass cropped to a ruler-straight 64u
    slice of land ending in mid-air. Of 57 disc-1 landmasses only 7 are carryable, and
    the disqualifier is almost never the island we want -- it is the neighbour. This
    drops the neighbour and re-zips deep ocean over its footprint.

    Returns ``(tweaks, report)``; the tweaks go straight into
    :func:`transplant_region`'s ``tweaks=`` in donor WORLD coords.

    THE UNIT IS THE ASSEMBLY, NOT THE LANDMASS. An island owns a shallow water ladder
    (sea3/sea5, and beach1/sea1/sea2 where present) welded to its coast; dropping the
    terrain alone would strand that ladder as a ring of shallows around nothing. So the
    components are taken over every part EXCEPT sea4, which is exactly the deep sheet the
    fill lands in.

    THE FILL IS EXACT BY CONSTRUCTION, not by tolerance. The dropped assembly's own
    outer boundary IS the hole, and it was measured to consist entirely of waterline
    vertices (every one of which is already a sea4 vertex -- 11/11 and 8/8 on the two
    real cases) plus vertices lying on the rect frame. So the patch reuses those
    vertices verbatim and introduces no new boundary vertex. *A repair that is not exact
    is a hole* -- relaxing that last time cost 26 px of visible background.

    The patch lands on sea4 and nowhere else: no land, no land/sea junction, no wall, no
    walk surface, no height field. It is the one authoring job in this arc that cannot
    mint a walk trap, and it needs no tone gate because sea4's quadrant choice is free.
    """
    from . import meshedit as ME

    dx, dy = int(donor[0]), int(donor[1])
    nx, ny = int(size[0]), int(size[1])
    x0, x1 = 64.0 * dx, 64.0 * (dx + nx)
    z0, z1 = -64.0 * (dy + ny), -64.0 * dy            # z0 < z1

    tagged, sea4 = [], []
    for by in range(dy, dy + ny):
        for bx in range(dx, dx + nx):
            for p in parts:
                got = world_tris(bx, by, p, disc=disc, lod=lod, game=game)
                if p == "sea4":
                    sea4 += got
                else:
                    tagged += [(p, t) for t in got]

    comps = ME.vertex_components([t for _, t in tagged])
    owner = {}
    for ci, c in enumerate(comps):
        for t in c:
            owner[id(t)] = ci

    # CROSSING IS JUDGED ON LAND ONLY, because ``land-fit`` is judged on land only. An
    # island's shallow ladder (sea3/sea5) legitimately runs out to the rect frame while
    # its coast sits well inside; testing the whole assembly condemned the very island
    # being carried and refused a rect that is in fact clean.
    part_of = {}
    for p, t in tagged:
        part_of[id(t)] = p
    foreign = []
    for ci, c in enumerate(comps):
        land_tris = [t for t in c if part_of.get(id(t)) in LAND_PARTS]
        if not land_tris:
            continue                                  # a pure water body crosses nothing
        xs = [v[0][0] for t in land_tris for v in t]
        zs = [v[0][2] for t in land_tris for v in t]
        if (min(xs) <= x0 + land_margin or max(xs) >= x1 - land_margin
                or min(zs) <= z0 + land_margin or max(zs) >= z1 - land_margin):
            foreign.append(ci)
    # NO "keep the biggest assembly" exception. The first cut spared component 0 on the
    # assumption it is the island being carried -- but on a rect that clips a CONTINENT
    # (Daguerreo's (5,15)+3x2, the Forgotten margin at (4,13)+4x4) the biggest assembly
    # IS the frame-crosser, so the exception kept the continent and excised the island:
    # exactly backwards, and it left land-fit still failing on all three verified rects.
    # Whether a mass crosses the frame is the only criterion; what SURVIVES is then
    # checked below.
    kept_ids = [ci for ci in range(len(comps)) if ci not in foreign]
    if not kept_ids:
        report = dict(assemblies=[len(c) for c in comps], foreign=list(foreign),
                      dropped={}, fill_tris=0, rings=0, weld_exact=True,
                      weld_checked=0, weld_missing=[],
                      refused="every assembly crosses the frame -- nothing to carry")
        return [], report

    report = dict(assemblies=[len(c) for c in comps], foreign=list(foreign),
                  dropped={}, fill_tris=0, rings=0,
                  weld_exact=True, weld_checked=0, weld_missing=[])
    if not foreign:
        return [], report

    sea4_keys = {(round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))
                 for t in sea4 for v in t}
    _fx0, _fx1 = 64.0 * dx, 64.0 * (dx + nx)
    _fz1, _fz0 = -64.0 * dy, -64.0 * (dy + ny)

    def _on_frame(v, eps: float = 1e-3):
        """Is this vertex on the donor RECT's outer frame? (see THE EXACTNESS GATE)"""
        return (abs(v[0] - _fx0) < eps or abs(v[0] - _fx1) < eps
                or abs(v[2] - _fz0) < eps or abs(v[2] - _fz1) < eps)
    # Take the sheet's OWN normal and winding rather than inventing them. Sea normals are
    # a shared byte constant that is not (0,1,0), and stock sea4 winds negative -- a fill
    # wound the other way renders but is back-facing to the ground raycast (73 introduced
    # census misses, measured).
    sea4_normal = tuple(sea4[0][0][1]) if sea4 else (0.0, 1.0, 0.0)
    sea4_wind = -1.0
    if sea4:
        a, b, c = [v[0] for v in sea4[0]]
        sea4_wind = -1.0 if ((b[0] - a[0]) * (c[2] - a[2])
                             - (c[0] - a[0]) * (b[2] - a[2])) < 0 else 1.0

    by_part: dict = {}
    for p, t in tagged:
        if owner.get(id(t)) in foreign:
            by_part.setdefault(p, []).append(t)
    tweaks = []
    for p, tris in by_part.items():
        tweaks.append(DropTris(p, tris))
        report["dropped"][p] = len(tris)

    emitted = []
    for ci in foreign:
        rings = ME.boundary_cycles(comps[ci])
        if not rings:
            continue
        # ONLY the outer ring: an interior ring is a hole in the assembly, and filling it
        # would double-cover. And the ring must be reduced to its PLAN outline first --
        # a cropped coastal mass's 3D boundary climbs the cliff at the frame slice, so
        # several boundary verts share one plan position. Projecting all of them
        # produced a self-overlapping polygon whose ear-clip left 73 introduced census
        # misses and 13 weld pairs. Collapsing consecutive plan-duplicates turns the
        # slice back into the straight frame chord it actually is.
        ring = rings[0]
        plan, last = [], None
        for v in ring:
            key = (round(v[0], 4), round(v[2], 4))
            if key == last:
                continue
            last = key
            plan.append(v)

        # COLLAPSE THE CROP PROFILE. Where the mass is sliced by the rect frame its
        # boundary climbs the cliff, and those verts carry cliff-profile x positions at
        # land height. Flattening them to the waterline drops them a few tenths of a unit
        # from real sea verts -- near-miss pairs, which IS the hairline-crack gate's whole
        # subject (13 of them, measured). They are collinear along the frame, so collapse
        # every run of them to its endpoints. A vertex the sea sheet actually shares is
        # NEVER collapsed: that one is load-bearing for the exact weld.
        def _shared(v):
            return (round(v[0], 4), round(v[1], 4), round(v[2], 4)) in sea4_keys

        keep, n = [], len(plan)
        for i, v in enumerate(plan):
            if _shared(v) or abs(v[1]) < 1e-6:
                keep.append(v)
                continue
            a, b = plan[(i - 1) % n], plan[(i + 1) % n]
            cross = ((v[0] - a[0]) * (b[2] - a[2]) - (v[2] - a[2]) * (b[0] - a[0]))
            if abs(cross) > 1e-3:                     # a real corner, not a profile step
                keep.append(v)
        plan = keep
        if len(plan) < 3:
            continue
        for v in plan:                                # THE EXACTNESS GATE
            if abs(v[1]) < 1e-6:
                report["weld_checked"] += 1
                if (round(v[0], 4), round(v[1], 4), round(v[2], 4)) in sea4_keys:
                    continue
                # A WATERLINE VERTEX ON THE RECT FRAME NEEDS NO SEA4 PARTNER INSIDE THE
                # RECT. v1 counted these as weld failures and refused with "the mass owns
                # a shallow-water ladder, which excise v1 does not re-zip" -- but that
                # diagnosis was wrong. Measured on the two rects it was blocking
                # (Daguerreo (5,15)+3x2 and the sinuous island (3,11)+2x4): 39/39 and
                # 41/41 of the weld-missing vertices lie EXACTLY on the rect frame, none
                # is an interior hole in the sheet, and none is welded to a kept assembly.
                # The excised mass's ladder simply runs out to the frame, so sea4 has no
                # vertex there to weld to -- and it should not: beyond the frame is the
                # neighbouring cell's ocean, which the region's own border re-partition
                # and the prefab handle. Filling out to the frame is the correct result.
                if _on_frame(v):
                    report["frame_waterline"] = report.get("frame_waterline", 0) + 1
                    continue
                report["weld_exact"] = False
                report["weld_missing"].append(v)
        try:
            emitted += ME.flat_patch(plan, y=0.0, uv_quads=SEA4_QUADS,
                                     idall=SEA4_IDALL, normal=sea4_normal,
                                     winding=sea4_wind)
            report["rings"] += 1
        except ValueError as e:
            report.setdefault("skipped_rings", []).append(str(e))
    report["fill_tris"] = len(emitted)

    # THE CAPABILITY BOUNDARY, ENFORCED RATHER THAN DOCUMENTED. Measured over a
    # gate-verified sample: excise is clean when the excised mass is a bare land crumb
    # (terrain only, no ladder of its own) and fails when the mass owns a shallow-water
    # ladder -- then the vacated region does not abut sea4 all the way round, the fill
    # cannot weld exactly, and the hairline-crack gate refuses downstream. Refuse HERE
    # with the reason instead of handing back a fill that will fail later: a caller that
    # gets tweaks is entitled to assume they are sound.
    if not report["weld_exact"]:
        report["refused"] = (
            f"{len(report['weld_missing'])} waterline vertex/vertices of the excised "
            "assembly do not lie on the deep sheet -- the mass owns a shallow-water "
            "ladder, which excise v1 does not re-zip. Choose a rect whose frame-crossing "
            "mass is a bare land crumb, or extend the fill to rebuild the ladder.")
        return [], report
    if emitted:
        tweaks.append(EmitTris("sea4", emitted))
    return tweaks, report
