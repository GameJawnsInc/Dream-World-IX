"""The REAL overworld GRASS tile language -- byte-measured (2026-07-07) and in-game proven on the synth islands.

FF9 grass is the OCEAN-MAINS grammar on land. Measured across the grass-richest disc-1 blocks
((15,15)/(16,14)/(14,15)/... and Uaho (0,0)):

* **Mains**: one 2x2 QUADRANT tile-set at ``u[0.00391,0.12695] x v[0.76855,0.83008]`` (each quadrant
  ~62x31px, with a real 1-2px bleed gutter at the internal split). ONE full quadrant fills ONE 4u lattice
  cell (96%% of clean cells); the UV is EXACTLY linear in world XZ (fit residual med 0.00px); 4 rotations,
  ONE handedness (ori0 ``u=+15.5px/u*x, v=-7.75*z``); constant density 0.01087 uv/u.
* **Neighbour policy**: adjacent cells avoid the same quadrant (real same-quadrant 12%%) and mildly cluster
  rotation (real same-rotation 49%%) -- the ocean's stochastic checkerboard.
* **Bleed rule**: conforming boundary tris extrapolate slightly PAST their quadrant -- but only INWARD
  (across the internal split into the sibling quadrant), NEVER outside the 2x2 region: outside lies
  Moguri's transparent atlas gutters, which render WHITE.
* **Meadow patches**: a 2nd meadow quadrant set (D) + 4 transition v-strips (B) -- but a rule-based Wang
  synthesizer reads SQUARE in-game (~40%% of a real ring is MIXED cells whose boundary cuts through cell
  interiors). The faithful path is verbatim LAYOUT STAMPS: each real D-core's neighbourhood captured as
  per-cell per-TRIANGLE geometry+UVs and replayed exactly. Stamps are DERIVED FROM THE INSTALL's bytes ->
  cached next to StreamingAssets (like the palette), never shipped.
* **Relief**: real grass is NEVER flat (0 dead-flat cells; Y std 0.66-1.25, 4u-neighbour |dY| med ~0.2
  p90 ~0.5-0.7; desert topo-17 is rougher still, y std 2.44). The mint deliberately does NOT reproduce
  this: an ambient ``relief_field``/``relief_at`` pair shipped with the first world-island but a
  coordinate-frame mismatch kept it at 0.0 everywhere in practice, and flat interiors were repeatedly
  in-game APPROVED (up to an r52 pure-plain desert island, 2026-07-15) -- so it was RETIRED rather than
  fixed (THE DEAD-RELIEF DISCOVERY). Explicit height comes from the studied verbs (world-hill /
  world-forest / world-mountain). If a continent-scale plain ever reads too flat, resurrect relief as a
  measured per-ground rung (stats above; frame fix = island-local or lattice-wrapped anchoring) --
  the record lives in studies/overworld-topography/README.md (THE DESERT TILE FIDELITY CHECK).

Full teardown: project memory ``project-ff9-overworld-coast-mosaic``; the placement rules the meshes must
obey live in :mod:`ff9mapkit.world.placement`.
"""
from __future__ import annotations

import collections
import json
import math
import random

# ---- the byte-probed tile constants (5dp; the u/v splits carry the real 1-2px bleed gutter) -----------------------
GRASS_U_HALF = [(0.00391, 0.06445), (0.06641, 0.12695)]     # main grass 2x2 quadrant u-halves
GRASS_V_HALF = [(0.76855, 0.79883), (0.7998, 0.83008)]      # v-halves (shared by the meadow set)
MEADOW_U_HALF = [(0.13379, 0.19434), (0.19629, 0.25684)]    # the meadow (D) quadrant set
STRIP_U = (0.39355, 0.4541)                                 # the transition (B) strip column
STRIPS_V = [(0.36914, 0.39844), (0.40039, 0.43066), (0.43164, 0.46191), (0.46289, 0.49316)]
ORIS = (0, 90, 180, 270)
GRASS_DENSITY = 0.01087                                     # uv per world unit (geometric mean)

#: per-family STRICT UV bounds -- a corner outside its family region samples a transparent gutter (white)
FAM_REGION = {
    "main": (GRASS_U_HALF[0][0], GRASS_V_HALF[0][0], GRASS_U_HALF[1][1], GRASS_V_HALF[1][1]),
    "D": (MEADOW_U_HALF[0][0], GRASS_V_HALF[0][0], MEADOW_U_HALF[1][1], GRASS_V_HALF[1][1]),
    "B": (STRIP_U[0], STRIPS_V[0][0], STRIP_U[1], STRIPS_V[3][1]),
    "?": (0.0, 0.0, 1.0, 1.0),
}

#: GROUND FAMILIES -- byte-measured TRANSLATION LAWS (2026-07-15, the desert study +
#: the ground-families census, ``studies/overworld-topography/ground_families_anatomy.py``):
#: THE TRANSLATION LAW is UNIVERSAL -- every stock walkable ground family is the grass
#: language TRANSLATED in the atlas: the mains 2x2 rects (same widths 0.06054/0.03028,
#: same gutters 0.00196/0.00097) and the coastal cliff-wall band (same 0.248-wide
#: strip, one row) each sit at their own spot,
#: outer-bound byte-exact at 5dp (the grass control recovers delta (0,0) with ZERO
#: spread; dirt gameplay variants 19/20 recover the desert constants exactly).
#: ``topo`` is the family's walkable topograph (in-family ids are gameplay variants);
#: the ``wall_*`` deltas shift the mint's ROCK_U/ROCK_V band. Walls: brush fringes
#: the DESERT wall in stock (byte-exact adjacency, measured); snow + canyon carry
#: their own measured bands; scrub and dunes never touch topo-58 in stock, so they
#: BORROW the desert wall -- an authoring choice, not a measurement. Real ground ALSO
#: slides free fractional windows over its (painted-over) internal gutter -- the
#: locked grass-form window is a common real form and the safe generative choice, so
#: minting reuses :func:`mains_uv`.
#:
#: ``cls`` = the family's STOCK ROLE (the ground-sampler playtest, 2026-07-15): only
#: ``"island"`` families are whole-landmass fills with a coast that reads native.
#: ``"transition"`` (scrub) = a SEAM vocabulary -- stock lays it only as narrow strips
#: between solid grass and dirt fields, free grass-style placement (the macro-tile
#: parity hypothesis measured FALSE, 31% ~= chance), so a filled field of it reads as
#: a tiling mismatch. ``"slope"`` (brush) = stock paints it on ~30-deg-median
#: hillsides (the Black-Mage-Village brush); flat fills read as canopy, and the rim
#: lip does not line up. ``"interior"`` (dunes) = the ground fill reads fine but the
#: family has no native coast band -- use away from shorelines.
GROUNDS = {
    "grass": dict(topo=0, mains_du=0.0, mains_dv=0.0, wall_du=0.0, wall_dv=0.0,
                  cls="island", wall_coastal=True, relief_scale=1.0),  # opt-in relief base amp
    "desert": dict(topo=17, mains_du=0.65332, mains_dv=-0.09863,
                   wall_du=-0.27127, wall_dv=-0.02066, cls="island",
                   wall_coastal=True, relief_scale=1.6),             # desert lowland ~1.5-2x rougher
    #                                  (topo-17 detrended std ~1.0 vs grass ~0.5; calib_relief.py)
    #                                  map-wide 19/20 faces coastal, to
    #                                  6.57u (2026-07-19 map-wide re-measure; the old "12/13 to 5.03u"
    #                                  was a specimen-slice reading, retired -- same defect class as the
    #                                  canyon/snow figures corrected 2026-07-18).
    "scrub": dict(topo=4, mains_du=0.25977, mains_dv=-0.06738,      # grass<->dirt ecotone
                  wall_du=-0.27127, wall_dv=-0.02066,               # borrowed desert wall -- and the
    #                                  BORROW IS BYTE-TRUE where it occurs (5dp-exact, zero delta).
                  cls="transition", wall_coastal=False),            # ★ MEASURED 2026-07-19
    #                                  (wall_coastal_unmeasured.py): scrub touches topo-58 exactly ONCE
    #                                  map-wide -- 1 welded face / 3 tris at ~(17,1), out of 41
    #                                  scrub-bearing blocks and 1877 scrub ground tris. That single face
    #                                  IS open-sea with no gorge counterexample, but n=1 cannot certify a
    #                                  systematic coastal usage. REFUSE (revises the older "scrub never
    #                                  touches topo-58" framing: it touches once, too thin to build on).
    "brush": dict(topo=38, mains_du=0.45703, mains_dv=-0.20215,  # bare-brush hillside
                     wall_du=-0.27127, wall_dv=-0.02066,            # its REAL stock wall (5dp-exact on
    #                                  6 of 7 adjacent faces -- the borrow claim is byte-verified)
                     cls="slope", wall_coastal=False),              # ★ SETTLED 2026-07-19 round 2
    #                                  (wall_coastal_crossblock.py). Round 1 left this UNSET (fail-closed)
    #                                  because its lone open-sea face, against 5 interior/gorge faces, was
    #                                  WEAKER evidence than the scrub face it had just refused --
    #                                  certifying it would have applied a backwards bar. The open question
    #                                  was the shared blind spot: every wall-adjacency figure in this arc
    #                                  only saw adjacency WITHIN a block's own tri list, never a
    #                                  world-space-coincident edge ACROSS a block boundary. That scan now
    #                                  exists and is map-wide: it adds ZERO new evidence for brush, scrub
    #                                  OR dunes, while proving itself non-null on the desert control
    #                                  (+9/1838 tris recovered). So brush and scrub TIE at exactly one
    #                                  open-sea face each, and under the same bar that disqualified canyon
    #                                  (open-sea faces support; gorge faces do not) both fail. REFUSE.
    "snow": dict(topo=27, mains_du=0.0, mains_dv=-0.33691,          # Lost-Continent field
                 wall_du=-0.44021, wall_dv=0.05161,                 # icy band, measured
                 cls="island", wall_coastal=True),                  # ★ map-wide 1019 tris/10 faces, ALL
    #                                  coastal, to 6.35u (2026-07-18 map-wide re-census; the old "733/733"
    #                                  matched neither the map-wide nor the specimen-slice reading and is
    #                                  retired -- the specimen slice reads 272 tris/8 faces, all coastal,
    #                                  max 5.73u).
    "canyon": dict(topo=45, mains_du=0.7793, mains_dv=-0.31641,     # Forgotten red tiers
                   wall_du=-0.69509, wall_dv=-0.49722,              # red-rock band, measured
                   cls="island", wall_coastal=False),               # ★ ground verbatim-compared; ⚠ THE
    #                                  WALL-CONTEXT LAW: ZERO open-sea coastal canyon walls (the
    #                                  Forgotten's sea cliffs are topo-49 MURALS), so a canyon SEA cliff
    #                                  is off-language. Canyon = interior ground behind a lawful coast.
    #                                  ⚠ THE TALLY HAS BEEN WRONG TWICE -- the DIRECTION never moved.
    #                                  "748 tris map-wide, 0 coastal" was a top-8-specimen-slice
    #                                  artifact presented as map-wide (caught 2026-07-18). Its
    #                                  replacement "655 tris / 48 faces" is ALSO wrong (caught
    #                                  2026-07-19, canyon_wall_courses.py): it counted the red-band UV
    #                                  RECT topo-agnostically, and 594 of those 655 tris are topo-49
    #                                  MURAL + 1 is topo-59. The true red WALL population is 60 tris /
    #                                  8 faces (topo-58 strict), or 43 tris / 7 faces by ground
    #                                  adjacency -- still zero open-sea, so the refusal stands.
    #                                  LAW: cite a wall figure ONLY from a topo-58-FILTERED count; a
    #                                  UV-rect count is a mural count.
    #                                  Note: canyon stays cls="island" for
    #                                  the UV-TRANSLATION grouping only -- wall_coastal=False means a
    #                                  coastal canyon LANDMASS is refused by the shipped guard
    #                                  (build_landmass / GroundRetile.for_donor).
    "dunes": dict(topo=41, mains_du=0.38964, mains_dv=-0.13477,     # pale sandy event dunes
                  wall_du=-0.27127, wall_dv=-0.02066,               # borrowed desert wall -- a TRUE
    #                                  borrow: there is nothing to measure it against (below)
                  cls="interior", wall_coastal=False),              # ★ MEASURED 2026-07-19
    #                                  (wall_coastal_unmeasured.py): an exhaustive map-wide scan of all
    #                                  9 dunes-bearing blocks finds ZERO topo-58 tris sharing an edge
    #                                  with any dunes tri anywhere. The wall band is unmeasurable from
    #                                  direct evidence -- "borrow" is the honest word. REFUSE.
}


#: THE ECOTONE-STRIP TABLE (``ecotone_strip_decode.py``, 2026-07-19) -- DATA ONLY, not yet an
#: authoring surface. A family boundary is never plain|plain: some pairs wear a dedicated
#: one-tile strip COLUMN, and where they do, that column is the grass B-strip
#: (``FAM_REGION["B"]``) TRANSLATED -- the same law the mains obey. Both entries below are
#: proven-5dp map-wide (zero outer-bound spread, exact 0.03125 row pitch, all 4 rows).
#:
#: ⚠ WHAT THIS IS NOT: a placement policy. These are the rects; NOBODY has measured which of
#: the 4 rows goes in which cell (the mains 2x2's avoid-repeat neighbour policy has no strip
#: analogue yet). An emitter needs that before it can stamp a seam -- so this table unblocks
#: the *vocabulary* half of the dunes-patch carry, not the carry itself.
#:
#: THE UNION METHOD (why the old earmark was wrong): an outer-bounds fit on ONE side of the
#: boundary can TIE between row-alignment hypotheses, because B's row0 is exactly 1 texel
#: (1/1024) shorter than rows 1-3, so different k-consecutive-row windows span numerically
#: identical v-extents. UNIONING both sides recovers all 4 rows and forces the alignment
#: unique. That is what caught the desert|dunes earmark's dv being off by EXACTLY one row
#: pitch (-0.06738 -> the proven -0.09863).
#:
#: Only these two pairs are translated B-columns. The other three real adjacencies are
#: structurally different art and must NOT be forced through this path:
#:   desert|scrub -- no strip at all; the blend is literal texture substitution (59% of the
#:                   desert-side boundary tris simply wear SCRUB's own mains).
#:   desert|brush -- desert side plain (98% own-mains); brush wears its own edge column at
#:                   u[0.72070,0.78125] v[0.53516,0.59668], but REFUTED as a lattice
#:                   translation (515/517 cells fail the per-cell exact-linear UV test) --
#:                   it is scattered independently-UV'd triangles, needing its own decode.
#:   grass|scrub  -- a THIRD, previously-uncatalogued shared atlas asset at
#:                   u[0.34082,0.40332] v[0.83594,0.86621], width 0.0625 (matching neither
#:                   B's 0.06055 nor the mains quadrant); both sides land on the identical
#:                   rect. Not visually inspected -- do not carry it blind.
STRIPS = {
    ("grass", "desert"): dict(du=0.52442, dv=-0.04687, rows=4),
    ("desert", "dunes"): dict(du=-0.13476, dv=-0.09863, rows=4),
}

#: A SECOND desert ground rect (``secondary_mains_rect_decode.py``, 2026-07-19) -- DATA ONLY,
#: nothing consumes it yet. A minority of desert specimen blocks fit their mains at
#: ``du=0.85058, dv=-0.11425`` rather than the primary ``GROUNDS["desert"]`` translation;
#: proven-5dp on a 5-block cluster (11,4) (11,5) (12,4) (12,5) (12,6). It matched none of the
#: 21 catalogued atlas regions, and it is NOT the generic desert edge decal it was first
#: suspected to be (a >0.2 v-gap separates them, despite near-identical u-origins 0.85058 vs
#: 0.85059 -- that near-collision is a coincidence and cost a round to rule out).
#:
#: HOW IT SURFACED, and the lesson: as an apparent DEFECT. The control lane re-deriving the
#: shipped constants printed nonzero cross-specimen spread for desert (0.19726) and brush, and
#: its own harness banner read ">=1 required control FAILED" -- while that lane's headline
#: claimed every control passed. The "failure" was a real second region, not noise. Read a
#: control failure before you explain it away.
#:
#: The aggregate/majority fit that produced GROUNDS["desert"] remains correct -- the primary
#: rect is what most blocks wear. Do NOT treat this as a family: the two rects INTERLEAVE
#: geographically (block (13,4) fits the PRIMARY exactly and directly borders the secondary
#: cluster at (12,4)), so there is no clean territory to key an authoring decision on.
DESERT_MAINS_SECONDARY = dict(du=0.85058, dv=-0.11425,
                              blocks=((11, 4), (11, 5), (12, 4), (12, 5), (12, 6)))


#: TOPO -> ground FAMILY, scoped to the families :data:`STRIPS` actually keys off (grass/desert/
#: dunes today; ``studies/overworld-topography/dunes_grazing_eye.py``'s own ``TOPO_FAM`` table,
#: reproduced here as shipped vocabulary rather than study-only). Variant/gameplay topo ids within
#: a family share its plain-mains language (the ground-families census): grass's 9 walkable
#: variants, desert's 4 (16 = the STRIPS decal's own dedicated fringe topo; 17 = plain mains; 19/20
#: = dirt gameplay variants that recover the desert constants exactly), dunes' 1. A family with no
#: STRIPS pair has no entry here -- nothing consumes it (an orphan-decal census only needs "which
#: family does THIS tri's own topo wear", never a full topo->family census of every ground type).
TOPO_FAMILY = {}
for _t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    TOPO_FAMILY[_t] = "grass"
for _t in (16, 17, 19, 20):
    TOPO_FAMILY[_t] = "desert"
TOPO_FAMILY[41] = "dunes"
del _t

#: self-consistency: a colour band cannot classify a language it was never taught, and neither can
#: an incomplete family table -- if STRIPS ever grows a pair whose family has no TOPO_FAMILY
#: coverage, that pair would silently see zero tris and never flag anything. Fail loudly instead.
_strips_families = {f for pair in STRIPS for f in pair}
assert _strips_families <= set(TOPO_FAMILY.values()), (
    f"STRIPS references families with no TOPO_FAMILY coverage: "
    f"{sorted(_strips_families - set(TOPO_FAMILY.values()))}")
del _strips_families


def ground_uv(x: float, z: float, cell, quad, ori: int, ground: str = "grass"):
    """:func:`mains_uv` re-based to a ground family (THE TRANSLATION LAW). ``grass`` is
    the identity (bit-exact -- adding 0.0 changes no float)."""
    g = GROUNDS[ground]
    u, v = mains_uv(x, z, cell, quad, ori)
    return [u + g["mains_du"], v + g["mains_dv"]]


def ground_main_region(ground: str = "grass"):
    """The ground family's mains region bounds (the FAM_REGION['main'] analogue)."""
    g = GROUNDS[ground]
    lo_u, lo_v, hi_u, hi_v = FAM_REGION["main"]
    return (lo_u + g["mains_du"], lo_v + g["mains_dv"],
            hi_u + g["mains_du"], hi_v + g["mains_dv"])

_STAMP_CACHE = ".ff9stamps_grass"                           # cached next to StreamingAssets, per disc
_STAMP_BLOCKS = [(15, 15), (16, 14), (14, 15), (15, 16), (19, 12), (17, 15), (18, 15), (18, 12), (16, 15), (17, 14)]


def rot_ab(fx: float, fz: float, ori: int):
    """The 4 measured orientation maps, cell-normalized ``(fx, fz)`` -> quadrant-rect ``(a, b)`` -- one
    handedness (real: 100%%): ori0 ``u=+x,v=-z``; 90 ``u=+z,v=+x``; 180 ``u=-x,v=+z``; 270 ``u=-z,v=-x``."""
    if ori == 0:
        return fx, 1 - fz
    if ori == 90:
        return fz, fx
    if ori == 180:
        return 1 - fx, fz
    return 1 - fz, 1 - fx


def assign_mains(cells, seed: int = 0xF91):
    """Per-4u-cell ``(quadrant, orientation)`` under the real neighbour policy: never repeat a W/S
    neighbour's quadrant (real same-quadrant 12%%); copy a neighbour's rotation with p=0.32 (real
    same-rotation 49%%). Deterministic per ``seed``. Returns ``(cell_quad, cell_ori)`` dicts."""
    rng = random.Random(seed)
    cell_quad, cell_ori = {}, {}
    for (i, j) in sorted(cells):
        nb_q = [cell_quad[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_quad]
        choices = [(u, v) for u in (0, 1) for v in (0, 1)]
        if nb_q:
            avoid = nb_q[rng.randrange(len(nb_q))]
            choices = [q for q in choices if q != avoid]
        cell_quad[(i, j)] = choices[rng.randrange(len(choices))]
        nb_o = [cell_ori[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_ori]
        if nb_o and rng.random() < 0.32:
            cell_ori[(i, j)] = nb_o[rng.randrange(len(nb_o))]
        else:
            cell_ori[(i, j)] = ORIS[rng.randrange(4)]
    return cell_quad, cell_ori


def assign_mains_seeded(cells, pre_quad, pre_ori, seed: int = 0xF92):
    """:func:`assign_mains`' exact loop body extended to a CONSTRAINED boundary (the UV-arc
    repair, ``studies/overworld-topography/uvf_fix2.py``): ``pre_quad``/``pre_ori`` hold
    ground-truth cells (decoded from real bytes) consulted for the W/S anti-repeat and the
    p=0.32 rotation-copy but NEVER rewritten; only ``cells`` draw from the single stream, in
    ``sorted`` order. Every W=(i-1,j)/S=(i,j-1) sorts before (i,j), so each neighbour is
    already resolved (pre-seed or earlier cell) when a cell is drawn -- with an empty
    pre-seed the output is bit-identical to :func:`assign_mains`. THE DIVERSITY POLICY: an
    uncoupled per-cell uniform pick reads as a chevron quilt at region scale (same-rotation
    ~0.25 vs the real map's ~0.49). Returns ``(quad, ori)`` dicts for ``cells`` only."""
    rng = random.Random(seed)
    cell_quad, cell_ori = dict(pre_quad), dict(pre_ori)
    out_quad, out_ori = {}, {}
    for (i, j) in sorted(cells):
        nb_q = [cell_quad[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_quad]
        choices = [(u, v) for u in (0, 1) for v in (0, 1)]
        if nb_q:
            avoid = nb_q[rng.randrange(len(nb_q))]
            choices = [q for q in choices if q != avoid]
        q = choices[rng.randrange(len(choices))]
        cell_quad[(i, j)] = q
        out_quad[(i, j)] = q
        nb_o = [cell_ori[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_ori]
        if nb_o and rng.random() < 0.32:
            o = nb_o[rng.randrange(len(nb_o))]
        else:
            o = ORIS[rng.randrange(4)]
        cell_ori[(i, j)] = o
        out_ori[(i, j)] = o
    return out_quad, out_ori


def mains_uv(x: float, z: float, cell, quad, ori: int):
    """The mains map for one corner: linear-in-position into the cell's quadrant rect, with the
    DIRECTION-AWARE bleed clamp (inward/cross-split bleed like real conforming tris; never outside the
    region -- outside = transparent gutters = white)."""
    (i, j) = cell
    fx = (x - 4.0 * i) / 4.0
    fz = (z - 4.0 * j) / 4.0
    a, b = rot_ab(fx, fz, ori)
    uh, vh = quad
    a = max(0.0 if uh == 0 else -0.15, min(1.15 if uh == 0 else 1.0, a))
    b = max(0.0 if vh == 0 else -0.15, min(1.15 if vh == 0 else 1.0, b))
    u0, u1 = GRASS_U_HALF[uh]
    v0, v1 = GRASS_V_HALF[vh]
    return [u0 + a * (u1 - u0), v0 + b * (v1 - v0)]


# ---- meadow patch STAMPS (verbatim real layouts; derived from the install -> cached, never shipped) ----------------

def _fam_of_rect(r) -> str:
    main = (0.004, 0.769, 0.127, 0.830)
    if main[0] - 0.002 <= r[0] and r[2] <= main[2] + 0.002 and main[1] - 0.002 <= r[1] and r[3] <= main[3] + 0.002:
        return "main"
    if 0.39 <= r[0] <= 0.46:
        return "B"
    if 0.13 <= r[0] <= 0.27:
        return "D"
    return "?"


def extract_stamps(disc: int = 1, *, blocks=None, game=None, cache: bool = True) -> list:
    """The meadow-patch STAMP library from the install's real grass blocks. Each stamp = a connected
    meadow core's cell box (grown until the border carries only plain-main or strip0 tiles -- a
    meadow-strength tile cut at the box edge is the hard 90-degree corner), with EVERY cell's per-TRIANGLE
    local geometry + UV affine. ``trunc`` = residual strong border tris (0 = perfectly bounded; the
    smallest trunc-0 stamp is 5x5 cells). Cached as JSON next to StreamingAssets (install-derived data
    stays out of the repo, like the palette cache)."""
    from pathlib import Path
    from .. import config
    cache_path = None
    if cache and blocks is None:
        try:
            cache_path = Path(config.find_game_path(game)) / "StreamingAssets" / f"{_STAMP_CACHE}_disc{disc}.json"
            if cache_path.is_file():
                return json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, config.ConfigError):
            cache_path = None
    from . import extract as X
    stamps = []
    for (bx, by) in (blocks or _STAMP_BLOCKS):
        try:
            terr = X.read_block(bx, by, disc=disc, part="terrain", game=game)
        except (ValueError, FileNotFoundError):
            continue
        V, UV = terr.verts, terr.uvs
        NT = len(terr.flat_index) // 3
        cell_tris = collections.defaultdict(list)
        cell_all_grass = collections.defaultdict(lambda: True)
        for t in range(NT):
            idx = terr.flat_index[3 * t:3 * t + 3]
            cx = sum(V[i][0] for i in idx) / 3
            cz = sum(V[i][2] for i in idx) / 3
            c = (math.floor(cx / 4), math.floor(cz / 4))
            if X.decode_id(int(round(terr.tangents[idx[0]][0])))["topograph"] == 0:
                cell_tris[c].append(idx)
            else:
                cell_all_grass[c] = False

        def tri_rect(idx):
            us = [UV[i][0] for i in idx]
            vs = [UV[i][1] for i in idx]
            return (round(min(us), 3), round(min(vs), 3), round(max(us), 3), round(max(vs), 3))

        def tile_ok_on_border(idx):
            r = tri_rect(idx)
            f = _fam_of_rect(r)
            if f == "main":
                return True
            return f == "B" and abs(r[1] - 0.369) < 0.012    # strip0: near-grass, terminates invisibly

        d_cells = set()
        for c, ts in cell_tris.items():
            if any(_fam_of_rect(tri_rect(idx)) == "D" for idx in ts):
                d_cells.add(c)
        seen = set()
        for c0 in sorted(d_cells):
            if c0 in seen:
                continue
            comp = []
            stack = [c0]
            seen.add(c0)
            while stack:
                cc = stack.pop()
                comp.append(cc)
                for nb in ((cc[0]+1, cc[1]), (cc[0]-1, cc[1]), (cc[0], cc[1]+1), (cc[0], cc[1]-1)):
                    if nb in d_cells and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            xs = [c[0] for c in comp]
            zs = [c[1] for c in comp]
            x0, x1 = min(xs) - 1, max(xs) + 1
            z0, z1 = min(zs) - 1, max(zs) + 1

            def strong_border():
                n = 0
                for i in range(x0, x1 + 1):
                    for j in range(z0, z1 + 1):
                        if i in (x0, x1) or j in (z0, z1):
                            n += sum(1 for idx in cell_tris.get((i, j), []) if not tile_ok_on_border(idx))
                return n

            for _grow in range(3):
                dirty = set()
                for i in range(x0, x1 + 1):
                    for j in (z0, z1):
                        if any(not tile_ok_on_border(idx) for idx in cell_tris.get((i, j), [])):
                            dirty.add("z0" if j == z0 else "z1")
                for j in range(z0, z1 + 1):
                    for i in (x0, x1):
                        if any(not tile_ok_on_border(idx) for idx in cell_tris.get((i, j), [])):
                            dirty.add("x0" if i == x0 else "x1")
                if not dirty:
                    break
                nx0 = x0 - ("x0" in dirty)
                nx1 = x1 + ("x1" in dirty)
                nz0 = z0 - ("z0" in dirty)
                nz1 = z1 + ("z1" in dirty)
                grown = [(i, j) for i in range(nx0, nx1 + 1) for j in range(nz0, nz1 + 1)]
                if not all(c in cell_tris and cell_all_grass[c] for c in grown):
                    break
                x0, x1, z0, z1 = nx0, nx1, nz0, nz1
            box = [(i, j) for i in range(x0, x1 + 1) for j in range(z0, z1 + 1)]
            if not all(c in cell_tris and cell_all_grass[c] and len(cell_tris[c]) >= 1 for c in box):
                continue
            cells_out = {}
            ok = True
            for (i, j) in box:
                recs = []
                for idx in cell_tris[(i, j)]:
                    pts = [(V[q][0], V[q][2]) for q in idx]
                    uvs = [UV[q] for q in idx]
                    (ax, az), (bx2, bz2), (cx2, cz2) = pts
                    e1 = (bx2 - ax, bz2 - az)
                    e2 = (cx2 - ax, cz2 - az)
                    det = e1[0] * e2[1] - e1[1] * e2[0]
                    if abs(det) < 1e-9:
                        ok = False
                        break
                    f1 = (uvs[1][0] - uvs[0][0], uvs[1][1] - uvs[0][1])
                    f2 = (uvs[2][0] - uvs[0][0], uvs[2][1] - uvs[0][1])
                    au = (f1[0] * e2[1] - f2[0] * e1[1]) / det
                    bu = (-f1[0] * e2[0] + f2[0] * e1[0]) / det
                    av = (f1[1] * e2[1] - f2[1] * e1[1]) / det
                    bv = (-f1[1] * e2[0] + f2[1] * e1[0]) / det
                    lx0 = ax - 4.0 * i
                    lz0 = az - 4.0 * j
                    recs.append({"poly": [[round(px - 4.0 * i, 4), round(pz - 4.0 * j, 4)] for (px, pz) in pts],
                                 "au": au, "bu": bu, "cu": uvs[0][0] - au * lx0 - bu * lz0,
                                 "av": av, "bv": bv, "cv": uvs[0][1] - av * lx0 - bv * lz0,
                                 "fam": _fam_of_rect(tri_rect(idx))})
                if not ok:
                    break
                cells_out[f"{i - x0},{j - z0}"] = recs
            if ok:
                stamps.append({"block": [bx, by], "core": len(comp), "w": x1 - x0 + 1, "h": z1 - z0 + 1,
                               "trunc": strong_border(), "cells": cells_out})
    if cache_path is not None and stamps:
        try:
            cache_path.write_text(json.dumps(stamps), encoding="utf-8")
        except OSError:
            pass
    return stamps


def stamp_fwd(placement, xs: float, zs: float):
    """Stamp-frame ``(xs, zs)`` -> world ``(x, z)`` for a placement ``(oi, oj, Wc, Hc, rot, stamp)``
    (cell-origin, rotated footprint, rotation, stamp). rot90 = the layout rotated 90 deg CCW."""
    oi, oj, Wc, Hc, rot, stamp = placement
    w4, h4 = 4.0 * stamp["w"], 4.0 * stamp["h"]
    if rot == 0:
        X_, Z_ = xs, zs
    elif rot == 90:
        X_, Z_ = h4 - zs, xs
    elif rot == 180:
        X_, Z_ = w4 - xs, h4 - zs
    else:
        X_, Z_ = zs, w4 - xs
    return 4.0 * oi + X_, 4.0 * oj + Z_


def place_stamps(cells, stamps, *, box_ok, seed: int = 0xF92, n_patches: int = 2, gap: int = 1):
    """Greedy stamp placement over grass ``cells``: least-truncated first (trunc asc), then largest core.
    ``box_ok(box)`` is the caller's geometry constraint (flat-lattice / weld-clearance / no-poke). Enforces
    isolation (``gap`` cells between boxes -- real patches never merge) and the border-lattice guard (a
    conforming mid-edge stamp vert would micro-crack against a neighbour's straight edge once Y varies).
    Returns ``(placements, stamped_cell)``."""
    rng = random.Random(seed)
    cells_set = set(cells)
    placed = []
    stamped_cell = {}
    uses = collections.Counter()                         # diversity: don't repeat a stamp/rotation while
    rot_uses = collections.Counter()                     # an equally-good alternative exists
    origins = sorted(cells_set, key=lambda c: rng.random())
    while len(placed) < n_patches:
        by_pref = sorted(range(len(stamps)),                 # quality first (trunc asc); variety among equals
                         key=lambda si: (stamps[si].get("trunc", 0), uses[si], -stamps[si]["core"]))
        rots = sorted(ORIS, key=lambda r: (rot_uses[r], rng.random()))
        placed_one = False
        for si, rot, oc in ((s, r, o) for s in by_pref for r in rots for o in origins):
            stamp = stamps[si]
            w_s, h_s = stamp["w"], stamp["h"]
            Wc, Hc = (w_s, h_s) if rot in (0, 180) else (h_s, w_s)
            box = [(oc[0] + di, oc[1] + dj) for di in range(Wc) for dj in range(Hc)]
            if not all(c in cells_set for c in box):
                continue
            if any((c[0] + gi, c[1] + gj) in stamped_cell
                   for c in box for gi in range(-gap, gap + 1) for gj in range(-gap, gap + 1)):
                continue
            if not box_ok(box):
                continue
            pl = (oc[0], oc[1], Wc, Hc, rot, stamp)
            x_lo, x_hi = 4.0 * oc[0], 4.0 * (oc[0] + Wc)
            z_lo, z_hi = 4.0 * oc[1], 4.0 * (oc[1] + Hc)
            border_ok = True
            for key, recs in stamp["cells"].items():
                ci, cj = map(int, key.split(","))
                for rec in recs:
                    for (lx, lz) in rec["poly"]:
                        x_, z_ = stamp_fwd(pl, 4.0 * ci + lx, 4.0 * cj + lz)
                        on_x = abs(x_ - x_lo) < 1e-3 or abs(x_ - x_hi) < 1e-3
                        on_z = abs(z_ - z_lo) < 1e-3 or abs(z_ - z_hi) < 1e-3
                        if (on_x and abs(z_ / 4.0 - round(z_ / 4.0)) > 2.5e-4) or \
                           (on_z and abs(x_ / 4.0 - round(x_ / 4.0)) > 2.5e-4):
                            border_ok = False
                            break
                    if not border_ok:
                        break
                if not border_ok:
                    break
            if not border_ok:
                continue
            idx_p = len(placed)
            placed.append(pl)
            for c in box:
                stamped_cell[c] = idx_p
            uses[si] += 1
            rot_uses[rot] += 1
            placed_one = True
            break
        if not placed_one:
            break
    return placed, stamped_cell


def stamp_geometry(placements) -> list:
    """Every placed stamp's triangles as ``([(x, z, u, v)] x3, family)`` -- VERBATIM geometry + exact
    corner UVs (real diagonals, real UV jumps, real edge contracts; zero resampling/clamping -- the affine
    field approach smeared in-game)."""
    out = []
    for pl in placements:
        stamp = pl[5]
        for key, recs in stamp["cells"].items():
            ci, cj = map(int, key.split(","))
            for rec in recs:
                corners = []
                for (lx, lz) in rec["poly"]:
                    x, z = stamp_fwd(pl, 4.0 * ci + lx, 4.0 * cj + lz)
                    u = rec["au"] * lx + rec["bu"] * lz + rec["cu"]
                    v = rec["av"] * lx + rec["bv"] * lz + rec["cv"]
                    corners.append((x, z, u, v))
                out.append((corners, rec["fam"]))
    return out


# ---- rolling relief (opt-in; a deterministic WORLD-XZ value-noise height field) ------------------------------------
#
# THE RESURRECTION (2026-07-21). Real grass/desert lowland is never dead-flat -- plane-DETRENDED
# undulation measures (this study's census.py + calib): grass topo-0 residual std ~0.46-1.07 (calm
# interior plains 0.46-0.49), 4u-neighbour |dY| med ~0.2 p90 ~0.5-0.7, per-tri slope p90 ~9-25 deg
# p99 ~15-33 (independently re-confirming the HILL-AT-SCALE p99 28.6), autocorrelation decorrelation
# ~9-12u (characteristic wavelength ~18-22u). Desert topo-17 is ~1.5-2x rougher.
#
# The FIRST relief shipped (grassland.relief_field/relief_at, 9e9be73) was DEAD: it keyed a real
# donor block's BLOCK-LOCAL lattice (i in [0,16], j in [-16,0]) while island.fill_y sampled it with
# WORLD coords, so field.get(...) -> 0.0 for every island away from block (0,0). It was RETIRED
# (3ba8462, THE DEAD-RELIEF DISCOVERY). This resurrection fixes the frame BY CONSTRUCTION: a pure
# function of WORLD (x, z). That (a) makes the same world location always yield the same height (the
# dead-relief bug cannot recur), and (b) is REQUIRED for cross-block seam welds -- a border vertex
# shared by two blocks has ONE world (x, z) -> ONE relief value on both sides (a block-local field
# would crack seams). Opt-in only (island.build_landmass(relief_amp=0.0) = flat = byte-identity).

#: (period_u, weight, salt) octave set -- calibrated (calib_relief.py): amp 1.3 measures std ~0.58,
#: slope p90 ~8 / p99 ~11 / max ~15 deg (a >2.4x margin under the walk envelope MAX_FLANK 28.6),
#: decorr ~15u -- squarely inside the calm-grass band, position-independent across seeds/offsets.
RELIEF_OCTAVES = ((20.0, 1.0, 0), (10.0, 0.45, 0x9E37))
RELIEF_DEFAULT_AMP = 1.3                                  # the grass default (GROUNDS[..]["relief_scale"] scales it)


def _relief_hash01(ix: int, iz: int, seed: int) -> float:
    """A deterministic integer hash of a lattice node -> a float in [0, 1). Pure; no RNG state."""
    h = (ix * 374761393 + iz * 668265263 + (seed & 0xFFFFFFFF) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return h / 4294967296.0


def _relief_octave(x: float, z: float, period: float, seed: int) -> float:
    """Smoothstep-interpolated bilinear value noise over a hash lattice of ``period`` -> [-1, 1]."""
    gx = x / period
    gz = z / period
    ix = math.floor(gx)
    iz = math.floor(gz)
    tx = gx - ix
    tz = gz - iz
    sx = tx * tx * (3.0 - 2.0 * tx)                       # smoothstep -> C1-continuous (no lattice creases)
    sz = tz * tz * (3.0 - 2.0 * tz)
    c00 = _relief_hash01(ix, iz, seed)
    c10 = _relief_hash01(ix + 1, iz, seed)
    c01 = _relief_hash01(ix, iz + 1, seed)
    c11 = _relief_hash01(ix + 1, iz + 1, seed)
    top = c00 * (1.0 - sx) + c10 * sx
    bot = c01 * (1.0 - sx) + c11 * sx
    return (top * (1.0 - sz) + bot * sz) * 2.0 - 1.0


def relief(x: float, z: float, *, seed: int = 0, amp: float = RELIEF_DEFAULT_AMP) -> float:
    """Deterministic ambient relief displacement (in units) at WORLD ``(x, z)`` -- the multi-octave
    value-noise sum (:data:`RELIEF_OCTAVES`) scaled by ``amp``. A PURE function of world coords: the
    same ``(x, z)`` always returns the same height, so coincident cross-block seam vertices weld
    exactly and the DEAD-RELIEF frame bug cannot recur. ``amp=0`` -> exactly 0.0 (the flat default)."""
    if amp == 0.0:
        return 0.0
    s = 0.0
    for (period, w, salt) in RELIEF_OCTAVES:
        s += w * _relief_octave(x, z, period, (int(seed) ^ salt) & 0xFFFFFFFF)
    return amp * s


def relief_fade(edge_dist: float, *, fade_lo: float = 2.0, fade_hi: float = 12.0) -> float:
    """Smoothstep rim fade weight in [0, 1]: 0 within ``fade_lo`` of the land edge/rim (the weld keeps
    its exact Y), ramping to 1 by ``fade_hi`` (~one wavelength inland). Stock relief does NOT taper at
    the coast (the land edge is where the cliff rises) -- this fade is a WELD-PRESERVATION requirement
    (keep the synthetic wall-top rim at exactly land_height), not stock mimicry."""
    if edge_dist <= fade_lo:
        return 0.0
    if edge_dist >= fade_hi:
        return 1.0
    t = (edge_dist - fade_lo) / (fade_hi - fade_lo)
    return t * t * (3.0 - 2.0 * t)


def smooth_normals(pos, tris, assign_vids):
    """Position-welded, area-weighted vertex normals over ``tris`` (geometric cross accumulation), written
    back for ``assign_vids`` only. Returns the normals list (parallel to ``pos``). Real grass normals are
    smoothed geometric -- never (0,1,0); the engine lights with them and the dapple masks tile borders."""
    nrm = [[0.0, 1.0, 0.0] for _ in pos]
    acc = collections.defaultdict(lambda: [0.0, 0.0, 0.0])

    def pk(p):
        return (round(p[0], 3), round(p[1], 3), round(p[2], 3))

    for tr in tris:
        a, b, c = pos[tr[0]], pos[tr[1]], pos[tr[2]]
        e1 = [b[i] - a[i] for i in range(3)]
        e2 = [c[i] - a[i] for i in range(3)]
        fn = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]]
        for vid in tr:
            A = acc[pk(pos[vid])]
            A[0] += fn[0]
            A[1] += fn[1]
            A[2] += fn[2]
    for vid in assign_vids:
        A = acc[pk(pos[vid])]
        L = math.sqrt(A[0]*A[0] + A[1]*A[1] + A[2]*A[2]) or 1.0
        v = [A[0]/L, A[1]/L, A[2]/L]
        nrm[vid] = v if v[1] > 0 else [0.0, 1.0, 0.0]
    return nrm
