"""INTERIOR topography on a DEPLOYED kit island: ``world-forest`` (carry a real canopy
blob), ``world-hill`` (a raised-cosine grass hill) and ``world-mountain`` (carry a real
rock massif whole) -- the productized forms of the in-game-proven island-E / Uaho-bench
studies (2026-07-12/13: the forest re-home "walked the whole rim aggressively, no more
sticking"; the hill "looks natural, walkable from all sides"; the Uaho carry "the cliff
is great -- walkable, seams against the grass great").

All three verbs RESHAPE the deployed override bytes (never a real map block -- reshaping
stock land is ``world-terrain``'s job) and refuse when the working footprint leaves the
deployed blocks. Everything below is a faithful port of ``studies/overworld-topography/
forest_rehome.py`` + ``hill_at_scale.py`` + ``massif_carry.py`` -- the laws it encodes
(full statements in memory ``project-ff9-overworld-interior-topography``):

* THE CANOPY CARRY LAW -- canopy texture is hand-authored; carry a real topo-37 blob
  WHOLE (verbatim verts/UVs/normals/idall), never synthesize it.
* THE COMPREHENSIVE CANOPY STEP LAW -- the engine's climb check is SURFACE-to-SURFACE
  across one foot step (~0.44u/frame); crossing the un-hittable vertical rim wall the
  candidate lands up to a step INSIDE, so every rim station lifts against the exact
  canopy surface one step in (``SAFE_RISE``), and THE PERIMETER WALK-IN GATE simulates
  the climb rule around the whole rim (ceiling 2.34375; descent is always legal --
  ``ff9.rayDistance`` is dead code).
* THE ROUND-AFTER-TRANSLATE WELD -- ring keys derive from the CARRIED floats.
* Zip-annulus mains UVs are DECODED per 4u cell from the kept tris' own bytes (16
  hypotheses, exact); fully-dropped cells resolve through ``assign_mains``' own seeded
  policy pre-seeded with the decoded ground truth (THE DIVERSITY POLICY, uvf_fix2:
  an uncoupled per-cell uniform pick reads as a chevron quilt).
* THE GRASS-HILL LANGUAGE -- lowland slope envelope p99 28.6 deg, pure-grass summits are
  real, prominence 3.5-5.2 over 20-26u, peaks <= the lowland band top (~8.6); the hill is
  a PURE-Y raised-cosine displacement (mains UVs are XZ-linear, so vertical motion keeps
  every tile lawful) with LOCAL normal re-smoothing.
* THE CARRY LAW (6th instance) -- rock texture organization is hand-authored; carry the
  real massif WHOLE (verbatim verts/UVs/normals/idall), synthesize only the seam.
* THE ROCK-RIGID LAW -- carried rock never deforms beyond the global affine (de-tilt +
  DY); ALL seating deformation goes to the GRASS (the donor-shaped pure-Y apron lift).
* THE WELD-SAFE LIFT -- worldmap meshes don't share vertex entries; every lift computes
  per POSITION and applies to every coincident entry, or the weld splits (sea slivers).
* THE FALLS-APERTURE LAW at mountain scale -- extra blob rims must be literal Object-mesh
  apertures; they carry as verbatim plugs wearing the rock collar's own UV chart.
"""
from __future__ import annotations

import dataclasses
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

from .extract import BLOCK_SIZE as _BS
from . import extract as X
from . import grassland as G
from . import mesh as M

BLOCK = float(_BS)

# ---- the proven constants (forest_rehome.py / hill_at_scale.py) --------------------------
FOREST_DONOR = (15, 15)          # the clean grass-bounded canopy blob
FOREST_SPREAD_MAX = 1.5          # --spread ceiling: the canopy's plan stretch, kept in game (terrain study X3:
#                                  "1.5x is starting to look stretched but still feels fine")
FOREST_ZIP_NY_FLOOR = 0.5        # a mapped canopy's zip routes round tris steeper than this (~60 deg)
FOREST_RIM_MIN = 8               # a canopy rim ring this short is still a blob: the (13,15) grove has 11
CURTAIN_HAIRLINE = 0.05          # a steep curtain corner pair closer than this in plan (donor units) is one
#                                  corner a hair off (the HAIRLINE CURTAIN, carve_forest)
CLEAR = 2.5                      # annulus clearance around the carried rim
SCAN_BAND = CLEAR + 4.0          # mains-only zone: dropped + hole-boundary tris
RING_BAND = CLEAR + 6.5          # hole-ring once-edge capture
MAX_RISE = 2.25                  # per-face ceiling (engine 2.34375)
SAFE_RISE = 2.10                 # pad-to-canopy bound per rim station
S_STEP = 0.65                    # engine foot step ~0.44/frame + margin
GATE_CLIMB = 2.30                # single-step crossing ceiling
RIM_MARGIN = 5.0                 # footprint clearance from the coast rim

HILL_H, HILL_R = 4.2, 18.0       # in-language prominence / radius
MAX_FLANK = 28.6                 # the measured lowland-grass slope p99 (deg)
PEAK_CAP = 8.6                   # the lowland band top
FOREST_CLEAR = 12.0              # hill footprint clearance from topo-37
STAMP_CLEAR = 4.0
RIM_CLEAR = 6.0

# ---- the proven mountain constants (massif_carry.py, the Uaho carry) ----------------------
MOUNTAIN_DONOR = (0, 0)          # Uaho island -- the only donor with a full anatomy study
#: Massif rock (NOT the coastal-lip topo 58). Narrowed from {49, 7, 62} on 2026-07-19
#: (``mural_partition_settle.py``): 7 and 62 were only ever LUMPED IN with 49 by assumption,
#: and the bytes refute it -- topo 7 is FLAT WALKABLE ground (snow-adjacent, 430 tris over 11
#: blocks at bx 4-9) and topo 62 is a STEEP STREAM-BANK paired with topo-51 (480 tris over 10
#: blocks at bx 16-20). Neither is rock, and neither appears even once in ANY of the four
#: qualified --donor rects (Uaho (0,0) / crag (10,5-6) / horseshoe (5-6,15-16) / comp20
#: (12,16-17) -- all verified 0), so this narrowing is a proven no-op on every shipped donor.
#: It is not merely inert though: leaving them in meant a FUTURE donor near those regions
#: would silently pull walkable ground and stream-bank into its "rock" component.
MOUNTAIN_ROCK_TOPOS = frozenset({49})
# Uaho's alcove floor: ((x0, x1), (z0, z1), y_min) in the donor block's world frame -- the
# notch's flat cave-floor pocket is mountain-attached terrain; without it the blob rim
# oscillates 1.5<->6.3 inside the notch and no smooth apron can meet it. Donor-specific
# (hand-measured); a new donor needs its own box (or none) -- see carve_mountain(alcove=).
UAHO_ALCOVE = ((31.0, 40.5), (-38.5, -30.5), 4.5)
MTN_CLEAR = 2.5                  # annulus clearance around the carried rim
MTN_GBLEND = 12.0                # ground-apron blend reach (the proven hill-at-scale value)
MTN_TJ_TOL = 0.05                # T-junction colinearity tolerance (covers kk3/split lerp
#                                  exactness AND the few-cm off-line slop of real lattices --
#                                  the R4 slivers passed the 29.5deg slope gate, so their
#                                  T-verts sat a few cm off the host line)
MTN_MAX_EDGE = 9.0               # max new-tri edge length
MTN_ZIP_RISE = 2.34              # zip-tri vertical span ceiling (engine step 2.34375)
MTN_ZIP_NY_MIN = 0.83            # the zip winding ENVELOPE (~34 deg -- admits the Uaho
#                                  alcove-mouth bank); a real donor rim may force a FEW
#                                  steeper banks (the horseshoe's falls outlet: 2/137)
MTN_ZIP_NY_FLOOR = 0.5           # the hard per-tri floor (~60 deg) for those banks
MTN_ZIP_BANK_MAX = 2             # max zip tris allowed between FLOOR and ENVELOPE
ZIP_STEEP_PENALTY = 1.0e6        # _zip_dp's extra cost for a candidate tri below its ny_floor (a sliver)
MTN_FC_CLEAR = 0.75              # window hole clearance: the contact hugs the rim so the
#                                  toe CONTINUES the face (THE PROFILE LAW, R4 take 8)
MTN_FC_MIN_RISE = 2.5            # a rock foot course exists only where the CARRIED massif
#                                  rises this far above the lawn within 6u -- else the
#                                  mountain has ended there and the contact is grass
MTN_FC_RIM_ABOVE = 0.25          # ...AND only where the NEAREST carried rim node stands this
#                                  far above the lawn (R4 take 9, the owner-filed NW sliver: a
#                                  low slab's rim under the plateau, 6u from a rising face,
#                                  minted fringe rock lying on a free-base dip -- "should be
#                                  ground")
MTN_FC_SLOPE_MIN = 25.0         # a foot tri shallower than this is GROUND, not a wall: stock's
#                                  rock-grass contact tris, p01 (stock_fringe census, R4 take 11)
MTN_FC_TILE_W = 4.6              # course LENGTH one fringe tile spans along the contact (the
#                                  foot course's own ~4.6u chaining since take 5); u is a per-
#                                  vertex function of arc length, mirror-repeated (R4 take 11)
MTN_FC_TILE_H = 3.0              # the course height ONE full fringe tile spans: v is a per-
#                                  VERTEX function of height over the lawn line, capped at
#                                  1/3 tile-height per unit -- stock's own short-contact
#                                  density (stock_fringe_census: 1130 disc-1 rock-grass
#                                  contacts, short ones p50 0.33; all p50 0.25 / p90 0.34).
#                                  A shorter course shows a PARTIAL tile from the fringe edge,
#                                  as stock does; a taller one the full tile, as before
MTN_FOOT_NY_FLOOR = 0.25         # foot-course tris are DELIBERATELY steep rock (blocked
#                                  topo 49, exempt from the grass zip envelope); below
#                                  ~75 deg they are slivers, refuse
MTN_ROCK_RIGID = 0.035           # THE ROCK-RIGID GATE: max carried-edge length drift
#                                  (against the DECLARED shape: the donor, or its --rock-height /
#                                  --spread map)
MTN_SPREAD_MAX = 1.5             # --spread ceiling: the owner passed Uaho widened x1.5, alone and scaled
#                                  whole, in game (terrain study round 20, mountainspread/)
MTN_ROCK_HEIGHT_MAX = 2.0        # --rock-height ceiling: the owner passed the Uaho rock stretched
#                                  x2.0 in game ("2x honestly doesn't look bad", terrain study X1,
#                                  RESULTS section 30); past it is untested
STOCK_TERRAIN_MAX_Y = 42.68      # the tallest stock terrain vertex (terrain study vertical census);
#                                  the airship flies at 42.1875, so taller rock holds it inside
MTN_APRON_SLOPE = 29.5           # the grass apron's slope envelope (deg)
MTN_STOCK_DOWN_NY = 0.02         # a VERBATIM donor tri that faced down at home by at most this (ny >= -0.02, about
#                                  1.15 deg past vertical) is stock wall, not a flip -- the down gate keeps it
#                                  (mountaindonors/STEP.md round 2; disc 1 ships 55 such tris, downface_census.py)
# The terrain atlas's rock-band UV phase (u, v) -- measured by daguerreo_massif_anatomy.py
# (its out/daguerreo_massif.json "phase"); the aperture-plug chart gate quantizes against
# it (cols 5-10, rows 6-12 = the painted rock band).
ROCK_CHART_PHASE = (0.015625, 0.01953125)
ATLAS_GUTTER_WHITE = 250         # the Moguri terrain atlas's gutter lines are pure white; no stock Terrain tri
#                                  samples a texel this white (snowmassif/gutter_census.py) -- _atlas_gate_mountain
PLUG_CHART_BAND = ((5, 10), (6, 12))  # that band, (cols, rows): GRASS-world rock (Daguerreo); see _plug_chart_ok
LAWN_LINE_TOL = 0.05             # THE LAWN-LINE SNAP (UAHO-LAWN-LINE-BENCH.md): a carried fringe
#                                  contact-edge end further than this (tiles) off the painted lawn
#                                  line snaps onto it -- stock disc 1 seats 2,081 of 2,088 ends ON
#                                  it (v = phase + 11 rows), p99.5 0.031
FRINGE_SEAM_TOL = 0.25           # THE FRINGE-SEAM UNIFY (UAHO-SEAM-BENCH.md): a v spread above this
#                                  (tiles) among the fringe corners at a contact tri's corner is a
#                                  seam -- stock disc 1 has 6 in 2,536 shared fringe positions, every
#                                  one on a contact tri (stock_fringe_continuity.py)
# THE ENSEMBLE CARRY's auxiliary part universe (canonical override spellings): a big
# massif's aperture is a river/falls MOUTH whose ring is owned by the UNION of these
# parts (the horseshoe: object 22 + falls 12 + river 15 + riverjoint 4 of 43 ring pts) --
# the parts carry under the same rigid map and cover the hole in-game exactly as stock.
ENSEMBLE_PARTS = ("Object", "Falls", "River", "RiverJoint")

kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))  # noqa: E731


class CarveRefused(ValueError):
    """A carve gate refused, and says WHERE (editor rung B1, the forest's gates first): ``gate`` names the gate,
    ``where`` lists world ``(x, z)`` points where it fails, so the editor can draw the refusal on the map. The
    message is the gate's own text, unchanged -- the CLI prints ``str(e)`` and stays byte-identical
    (``river.RiverRefused`` puts its points into its text; this one carries them beside it)."""

    def __init__(self, gate: str, msg: str, where=(), *, detail: str = ""):
        super().__init__(msg)
        self.gate, self.detail = gate, detail
        self.where = [(round(float(x), 2), round(float(z), 2)) for x, z in where]


def _weld_point(key, exact: dict):
    """THE EXACT-WELD LAW's one seam: the float a zip's hole-ring KEY is emitted as -- the kept grass's own
    position, bit for bit (a key is rounded to 1e-3; emitted as-is it sat up to 5e-4u off the grass it welds to,
    a pinhole on screen). The July identity net swaps this for the key itself to reproduce the in-game-approved
    July bytes, which carried that defect."""
    return exact[key]


# ---- the island soup ----------------------------------------------------------------------
def soup_from_blocks(blocks: dict) -> dict:
    """Build the WORLD-frame island soup from ``{(bx, by): BlockMesh}`` (freshly built or
    deployed-and-read-back -- one code path). Fams classify from the BYTES (the hill
    study's proven derivation): topo 37 = forest, 58 = rock, other nonzero = topoN,
    topo 0 = ``main`` when every corner u sits in the mains atlas region else ``stamp``.
    ``coast`` = the (x, z) of every topo-58 vert (the rim-clearance proxy).

    ``tan`` = every vertex's SOURCE tangent, all four floats: a kept tri re-emits it verbatim
    (:func:`_assemble`), so a block the carve never touched writes back byte-identical and the
    deploy's byte-compare skips it. The kit writes ``[idall, 0, 0, 1]``, but a carried stock part
    need not -- the world-river island's Terrain stores tangent.w = 0 -- and rebuilding it made
    every relief carve rewrite (and take ledger ownership of) its whole read window."""
    order = sorted(blocks)
    pos, nrm, tan, tris, meta, coast = [], [], [], [], [], []
    lo, hi = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
    for blk in order:
        bm = blocks[blk]
        bx, by = blk
        base = len(pos)
        ps = bm.chan_arrays[X.CH_POS]
        ns = bm.chan_arrays[X.CH_NRM]
        us = bm.chan_arrays[X.CH_UV]
        ts = bm.chan_arrays[X.CH_TAN]
        for k in range(bm.vcount):
            v = ps[k]
            pos.append([v[0] + BLOCK * bx, v[1], v[2] - BLOCK * (by + 1) + BLOCK])
            nrm.append(list(ns[k]))
            tan.append(list(ts[k]))
        for tri in bm.tris:
            idall = float(ts[tri[0]][0])
            topo = X.decode_id(int(round(idall)))["topograph"]
            if topo == 37:
                fam = "forest"
            elif topo == 58:
                fam = "rock"
                for i in tri:
                    w = pos[base + i]
                    coast.append((w[0], w[2]))
            elif topo != 0:
                fam = f"topo{topo}"
            else:
                fam = "main" if all(lo - 0.02 <= us[i][0] <= hi + 0.02 for i in tri) else "stamp"
            tris.append([tri[0] + base, tri[1] + base, tri[2] + base])
            meta.append((blk, idall, fam, [(us[i][0], us[i][1]) for i in tri]))
    return {"pos": pos, "nrm": nrm, "tan": tan, "tris": tris, "meta": meta,
            "blocks": dict(blocks), "coast": coast}


def read_deployed_blocks(mod_folder: str, *, near, reach: float, disc: int = 1,
                         lod: str = "0_1", game=None, target_disc: int | None = None) -> dict:
    """Read every deployed ``Block[x][y] Terrain.ff9mesh`` override whose block rect
    intersects the ``near +- reach`` window. Blocks without an override are OCEAN and
    load nothing (the safety is downstream: the footprint-lawful gates, the rim-clearance
    margins, the carve leak assert, and the crack gate all refuse work that would leave
    the deployed island). Refuses only when NO override exists in the window -- these
    verbs reshape DEPLOYED kit islands only (reshaping a real block is ``world-terrain``'s
    job).

    THE READ/WRITE DISC SPLIT. Like ``terrain.reshape`` -- and unlike the borrow verbs -- the
    interior verbs work ON the deployed island, so with ``target_disc`` set the READ moves to that
    namespace too: a synthetic world's island exists ONLY as its deployed overrides, and a Disc1
    read here would hand the carve real disc-1 land while the caller believes it is on a synthetic
    world. ``disc`` stays the STOCK read disc for the donor/census paths (``carve_*``,
    ``census_gate``), which is why it is a separate parameter.

    THE SEAM WRAP -- the world-island mint lane's shape (island.py, 2026-08-27), reused, not
    re-invented. The window's columns are UNWRAPPED, anchored at ``near``: each one reads its
    WRAPPED label's file (:func:`mesh.wrap_block_col` -- a ``Block[-1]``/``Block[24]`` file can
    never exist, so the old linear probe read a seam-straddling island back PARTIAL), and the
    returned key AND BlockMesh identity stay unwrapped. :func:`soup_from_blocks` therefore
    rebuilds ONE contiguous world frame across x = 0/1536 and every carve/gate downstream runs
    in it unchanged; the label wraps back exactly once, at the write seam (:func:`_wrap_label`
    in :func:`deploy_changed` / :func:`deploy_mountain_parts` / :func:`census_gate`). A window
    inside [0, 1536) has unwrapped == wrapped, so its read is byte-identical to before. A window
    wider than the whole 24-column world would read one file under two keys (the same land
    twice, 1536u apart) and refuses -- the island lane's wraps-onto-itself invariant."""
    from .. import config
    rtarget = disc if target_disc is None else int(target_disc)
    gp = Path(config.find_game_path(game))
    root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{rtarget}" / lod
    wx, wz = near
    bx0, bx1 = int(math.floor((wx - reach) / BLOCK)), int(math.floor((wx + reach) / BLOCK))
    by0, by1 = int(math.floor(-(wz + reach) / BLOCK)), int(math.floor(-(wz - reach) / BLOCK))
    if bx1 - bx0 + 1 > M.GRID_COLS:
        raise ValueError(
            f"the read window near ({wx:.0f},{wz:.0f}) reach {reach:.0f} spans "
            f"{bx1 - bx0 + 1} block columns -- more than the whole {M.GRID_COLS}-column world, "
            f"so one wrapped file would read twice (the same land 1536u apart). Narrow --reach.")
    out = {}
    for bx in range(bx0, bx1 + 1):
        wbx = M.wrap_block_col(bx)                       # the file the engine knows; the key stays bx
        for by in range(by0, by1 + 1):
            p = root / f"r{by}" / f"Block[{wbx}][{by}] Terrain.ff9mesh"
            if p.exists():
                out[(bx, by)] = M.blockmesh_from_ff9mesh(p, disc=rtarget, x=bx, y=by,
                                                         lod=lod, part="terrain")
    if not out:
        raise ValueError(f"no deployed Terrain overrides near world ({wx:.0f},{wz:.0f}) "
                         f"in {mod_folder} -- these verbs reshape DEPLOYED kit islands only")
    return out


def _wrap_label(bm, part: str):
    """THE SEAM WRAP POINT for the interior writers: ``island.landmass``'s deploy-stage relabel,
    verbatim. An unwrapped column (a seam-side key from :func:`read_deployed_blocks`) takes its
    wrapped label; the bytes are untouched (a ``.ff9mesh`` carries no identity, and 24*64 = the
    world width, so the block-local frame is the same). A column already in [0, 24) is returned
    as-is -- every window off the seam deploys exactly what it did before."""
    wbx = M.wrap_block_col(bm.x)
    if wbx == bm.x:
        return bm
    return dataclasses.replace(bm, x=wbx, name=f"Block[{wbx}][{bm.y}] {part}")


def _require_one_label_per_cell(keys, what: str) -> None:
    """Exactly ONE mesh per wrapped cell (the engine invariant the island lane's wraps-onto-
    itself gate guards): two unwrapped columns 24 apart would write one file twice."""
    owner = {}
    for bx, by in sorted(keys):
        lab = (M.wrap_block_col(bx), by)
        prev = owner.setdefault(lab, (bx, by))
        if prev != (bx, by):
            raise ValueError(f"{what}: unwrapped columns {prev[0]} and {bx} both land on wrapped "
                             f"cell {lab} -- one Terrain mesh per cell is an engine invariant")


# ---- shared geometry helpers ---------------------------------------------------------------
def chain_ring(edges, what: str, *, min_len: int = 12):
    """Chain once-edges into one simple cycle (raises on degeneracy: a repeat, or fewer than ``min_len`` points)."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    bad = [p for p, l in adj.items() if len(l) != 2]
    if bad:
        raise ValueError(f"{what} ring not a simple cycle ({len(bad)} odd-degree points)")
    start = edges[0][0]
    ring = [start]
    prev = None
    while True:
        nxts = [p for p in adj[ring[-1]] if p != prev]
        if not nxts:
            break
        prev = ring[-1]
        ring.append(nxts[0])
        if ring[-1] == start:
            ring.pop()
            break
    if len(ring) != len({*ring}) or len(ring) < min_len:
        raise ValueError(f"{what} ring degenerate")
    return ring


def chain_rings(edges, what: str):
    """All simple cycles in a degree-2 once-edge set (the multi-ring form of
    :func:`chain_ring` -- a massif blob legally owns several rings: the outer rim plus
    Object-mesh apertures)."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    bad = [p for p, l in adj.items() if len(l) != 2]
    if bad:
        raise ValueError(f"{what} ring set not degree-2 ({len(bad)} odd points)")
    unused = set(map(tuple, (tuple(sorted(e)) for e in edges)))
    rings = []
    while unused:
        e0 = next(iter(unused))
        ring = [e0[0]]
        prev = None
        while True:
            # pick the neighbor whose edge is still unused
            nxt = None
            for p in adj[ring[-1]]:
                if p != prev and tuple(sorted((ring[-1], p))) in unused:
                    nxt = p
                    break
            if nxt is None:
                break
            unused.discard(tuple(sorted((ring[-1], nxt))))
            prev = ring[-1]
            ring.append(nxt)
            if ring[-1] == ring[0]:
                ring.pop()
                break
        if len(ring) != len({*ring}) or len(ring) < 3:
            raise ValueError(f"{what} ring degenerate")
        rings.append(ring)
    return rings


def signed_area(ring):
    s = 0.0
    for i in range(len(ring)):
        x1, z1 = ring[i][0], ring[i][2]
        x2, z2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][2]
        s += x1 * z2 - x2 * z1
    return s / 2


def pip(px, pz, poly):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > pz) != (zj > pz) and px < (xj - xi) * (pz - zi) / (zj - zi + 1e-12) + xi:
            c = not c
        j = i
    return c


def near_poly(px, pz, poly, d):
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        ex, ez = x2 - x1, z2 - z1
        L2 = ex * ex + ez * ez + 1e-12
        t01 = max(0.0, min(1.0, ((px - x1) * ex + (pz - z1) * ez) / L2))
        ddx, ddz = px - (x1 + t01 * ex), pz - (z1 + t01 * ez)
        if ddx * ddx + ddz * ddz < d * d:
            return True
    return False


def split_borders8(parents):
    """Split world-frame parent tris at 64u block borders, generic-lerping every corner
    channel (x,y,z,u,v,nx,ny,nz). Degeneracy = TRUE 3D area (THE WALL LAW: canopy rim
    walls are vertical curtains -- plan-degenerate but real surface)."""
    def clip(poly, axis, val, keep_ge):
        out = []
        for ii in range(len(poly)):
            a, b = poly[ii], poly[(ii + 1) % len(poly)]
            da = (a[axis] - val) if keep_ge else (val - a[axis])
            db = (b[axis] - val) if keep_ge else (val - b[axis])
            if da >= 0:
                out.append(a)
            if (da >= 0) != (db >= 0):
                t = da / (da - db)
                out.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(len(a))))
        return out
    out = defaultdict(list)
    for corners, idall, fam in parents:
        xs = [c[0] for c in corners]
        zs = [c[2] for c in corners]
        bx0, bx1 = int(math.floor(min(xs) / BLOCK)), int(math.floor((max(xs) - 1e-9) / BLOCK))
        bz0, bz1 = int(math.floor(min(zs) / BLOCK)), int(math.floor((max(zs) - 1e-9) / BLOCK))
        for bx in range(bx0, bx1 + 1):
            for bz in range(bz0, bz1 + 1):
                p = [tuple(c) for c in corners]
                if bx1 > bx0:
                    p = clip(p, 0, bx * BLOCK, True)
                    if len(p) >= 3:
                        p = clip(p, 0, (bx + 1) * BLOCK, False)
                if bz1 > bz0 and len(p) >= 3:
                    p = clip(p, 2, bz * BLOCK, True)
                    if len(p) >= 3:
                        p = clip(p, 2, (bz + 1) * BLOCK, False)
                if len(p) < 3:
                    continue
                for k in range(1, len(p) - 1):
                    tri = (p[0], p[k], p[k + 1])
                    e1 = [tri[1][q] - tri[0][q] for q in range(3)]
                    e2 = [tri[2][q] - tri[0][q] for q in range(3)]
                    cx_ = e1[1] * e2[2] - e1[2] * e2[1]
                    cy_ = e1[2] * e2[0] - e1[0] * e2[2]
                    cz_ = e1[0] * e2[1] - e1[1] * e2[0]
                    if cx_ * cx_ + cy_ * cy_ + cz_ * cz_ < 1e-12:
                        continue
                    out[(bx, -bz - 1)].append((tri, idall, fam))
    return out


def raised_cosine(d: float, height: float, radius: float) -> float:
    return 0.0 if d >= radius else height / 2.0 * (1.0 + math.cos(math.pi * d / radius))


def decode_cell_pick(cell, decoded: dict):
    """Deterministic in-language (quad, ori) for ONE isolated mains cell -- avoid the
    W/S neighbours' quads. RETIRED from the carve path (the UV arc's DIVERSITY POLICY:
    its uncoupled uniform orientation reads as a chevron quilt over any multi-cell
    region -- use :func:`grassland.assign_mains_seeded` there); kept for single-cell
    decode/forensic use (the uvf_fix* studies reconstruct round-1 fields with it)."""
    import random as _r
    QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
    i, j = cell
    rng = _r.Random((i * 73856093) ^ (j * 19349663) ^ 0xF91)
    avoid = {q for n in ((i - 1, j), (i, j - 1))
             for q in ([decoded[n][0]] if n in decoded else [])}
    choices = [q for q in QUADS if q not in avoid] or QUADS
    return (choices[rng.randrange(len(choices))], (0, 90, 180, 270)[rng.randrange(4)])


def _tri_centroids(soup):
    out = []
    pos = soup["pos"]
    for tri in soup["tris"]:
        a, b, c = (pos[i] for i in tri)
        out.append(((a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3))
    return out


def _coast_d2(soup, px, pz):
    return min(((px - x) ** 2 + (pz - z) ** 2 for (x, z) in soup["coast"]), default=1e18)


def ground_words(fam: str, topo: int) -> str:
    """A soup tri's ground in words, for a refusal that says what the footprint reached."""
    return {"main": "plain grass", "stamp": "a stamped grass tile", "forest": "forest (topograph 37)",
            "rock": "coast rock (topograph 58)"}.get(fam, f"topograph {topo}")


def massif_ground_words(topo: int, ground: str) -> str:
    """A bench tri the massif footprint may not reach, in words: a ``ground`` tile off the mains (a stamp), another
    ground family, forest, coast rock, or a bare topograph."""
    if topo == G.GROUNDS[ground]["topo"]:
        return f"a stamped {ground} tile"
    if topo in (37, 58):
        return ground_words("forest" if topo == 37 else "rock", topo)
    name = next((n for n, g in G.GROUNDS.items() if g["topo"] == topo), None)
    return f"{name} ground (topograph {topo})" if name else f"topograph {topo}"


def _block_mid(b):
    """The world ``(x, z)`` at the middle of block ``b``: where a refusal about a whole block is drawn."""
    return (BLOCK * b[0] + BLOCK / 2, -(BLOCK * b[1] + BLOCK / 2))


def forest_footprint_lawful(soup, tri_c, poly, why=None):
    """THE FOREST FOOTPRINT LAW (``carve_forest``'s placement test): every island tri in or within
    :data:`SCAN_BAND` of the rim polygon ``poly`` is plain-grass mains with no corner within :data:`RIM_MARGIN`
    of the coast. Returns how many tris it judged, or None at the first that fails (appending ``((x, z),
    what)`` to ``why``). ``world.forestedit.footprint_preview`` is this, vectorised (and fenced against it)."""
    gpos, gtris, gmeta = soup["pos"], soup["tris"], soup["meta"]
    seen = 0
    for tidx, tri in enumerate(gtris):
        cx, cz = tri_c[tidx]
        hit = pip(cx, cz, poly) or near_poly(cx, cz, poly, SCAN_BAND)
        if not hit:
            hit = any(pip(gpos[i][0], gpos[i][2], poly) or
                      near_poly(gpos[i][0], gpos[i][2], poly, SCAN_BAND) for i in tri)
        if not hit:
            continue
        seen += 1
        _, idall, fam, _ = gmeta[tidx]
        topo = X.decode_id(int(round(idall)))["topograph"]
        if fam != "main" or topo != 0:
            if why is not None:
                why.append(((cx, cz), ground_words(fam, topo)))
            return None
        for i in tri:
            if _coast_d2(soup, gpos[i][0], gpos[i][2]) < RIM_MARGIN ** 2:
                if why is not None:
                    why.append(((gpos[i][0], gpos[i][2]), "the coast rim"))
                return None
    return seen


# ---- THE FOREST CARVE -----------------------------------------------------------------------
def _zip_dp(hole_ord, rim_base, rimw, h_float, *, ny_floor=None):
    """THE ZIP ANNULUS by a minimal-total-chord DP strip between the hole ring and the carried rim (same
    orientation), started at their closest pair: a greedy walk stalls on concavity into long chords and slivers
    at any rotation; the DP strip is optimal and concavity-immune. With ``ny_floor`` a candidate tri steeper than
    it costs :data:`ZIP_STEEP_PENALTY` more, so the strip routes round a sliver (a rim node on the line of a hole
    edge) wherever another way exists (the forest's; the mountain passes none -- its foot course is deliberately
    steep). ``rimw`` maps a rim key to its carried float; the hole side takes the kept grass's exact floats (THE
    EXACT-WELD LAW). Returns ``(H, R, zip_tris)``: the aligned hole points, the aligned rim keys, the strip's
    tris."""
    def d2(p, q):
        return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

    def steep(p, q, r):
        if ny_floor is None:
            return 0.0
        ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        return ZIP_STEEP_PENALTY if ln < 1e-12 or abs(ny) / ln < ny_floor else 0.0

    i0, j0 = min(((i, j) for i in range(len(hole_ord)) for j in range(len(rim_base))),
                 key=lambda ij: d2(hole_ord[ij[0]], rimw(rim_base[ij[1]])))
    H = [_weld_point(p, h_float) for p in hole_ord[i0:] + hole_ord[:i0]]   # exact floats, not the ring's keys
    R = rim_base[j0:] + rim_base[:j0]
    NH, NR = len(H), len(R)
    Rw = [rimw(p) for p in R]
    INF = 1e18
    cost = [[INF] * (NR + 1) for _ in range(NH + 1)]
    back = [[None] * (NR + 1) for _ in range(NH + 1)]
    cost[0][0] = 0.0
    for i in range(NH + 1):
        for j in range(NR + 1):
            c0 = cost[i][j]
            if c0 >= INF:
                continue
            if i < NH:
                nc = c0 + math.sqrt(d2(H[(i + 1) % NH], Rw[j % NR]))
                nc += steep(H[i % NH], H[(i + 1) % NH], Rw[j % NR])
                if nc < cost[i + 1][j]:
                    cost[i + 1][j] = nc
                    back[i + 1][j] = "h"
            if j < NR:
                nc = c0 + math.sqrt(d2(H[i % NH], Rw[(j + 1) % NR]))
                nc += steep(H[i % NH], Rw[j % NR], Rw[(j + 1) % NR])
                if nc < cost[i][j + 1]:
                    cost[i][j + 1] = nc
                    back[i][j + 1] = "r"
    zip_tris = []
    i, j = NH, NR
    while i > 0 or j > 0:
        if back[i][j] == "h":
            zip_tris.append((H[(i - 1) % NH], H[i % NH], Rw[j % NR]))
            i -= 1
        else:
            zip_tris.append((H[i % NH], Rw[j % NR], Rw[(j - 1) % NR]))
            j -= 1
    return H, R, zip_tris


def _forest_plan(dv_w, dnrm, c, *, spread: float, rot_deg):
    """THE CANOPY PLAN MAP (terrain study X3): the donor blob scaled ``spread`` in plan and
    turned ``rot_deg`` about ``c``, heights kept -- every curtain stays vertical (its top and
    base share a plan point, and the map moves both alike). Normals take the inverse
    transpose, (nx/s, ny, nz/s) turned the same way, at their original length. Same angle
    convention as :func:`carve_mountain`: a whole number of quarter turns is the exact
    coordinate swap, any other angle cos/sin; positive turns east -> south."""
    import numpy as np
    k = 0
    if rot_deg is not None:
        d = float(rot_deg) % 360.0
        k = int(d // 90) if d % 90.0 == 0.0 else d / 90.0

    def turn(x, z):
        if isinstance(k, int):
            for _ in range(k):
                x, z = z, -x
            return x, z
        c_, s_ = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
        return c_ * x + s_ * z, -s_ * x + c_ * z

    out = np.array(dv_w, dtype=np.float64)
    for i in range(len(out)):
        x, z = turn(out[i][0] - c[0], out[i][2] - c[1])
        out[i][0], out[i][2] = c[0] + spread * x, c[1] + spread * z
    nrm = []
    for n in dnrm:
        nx, nz = turn(n[0] / spread, n[2] / spread)
        L0 = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        L1 = math.sqrt(nx * nx + n[1] * n[1] + nz * nz) or 1.0
        nrm.append([nx * L0 / L1, n[1] * L0 / L1, nz * L0 / L1])
    return out, nrm


def _forest_donor(donor, *, disc: int = 1, game=None):
    """THE DONOR CANOPY: the largest topo-37 blob with tris in block ``donor`` whose rim meets only grass,
    gathered whole from the 3x3 blocks round it (a stock blob may cross a block border; forest donor census,
    studies/terrain-malleability/forestdonors). The named block is read first, so a one-block blob keeps its tris in
    the block's own order. A rim edge across which lies rock or any other ground refuses: a forest that meets rock
    (the rock stands on its canopy) carried alone would leave an open, unwalled edge. Returns world-frame
    ``(verts, uvs, normals, tangents, tris, blob, blob_blocks)``."""
    import numpy as np
    from . import mesh as M_
    bx0, by0 = donor
    V, UV, NRM, TAN, TRIS, SRC = [], [], [], [], [], []
    order = [(bx0, by0)] + [(bx0 + dx, by0 + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
    for bx, by in order:
        if not M_.block_in_grid(bx, by):
            continue
        try:
            bm = X.read_block(bx, by, disc=disc, game=game)
        except (ValueError, FileNotFoundError):
            if (bx, by) == (bx0, by0):
                raise
            continue
        base = len(V)
        V.extend((float(v[0]) + BLOCK * bx, float(v[1]), float(v[2]) - BLOCK * by) for v in bm.verts)
        UV.extend(bm.uvs)
        NRM.extend(bm.normals)
        TAN.extend(bm.tangents)
        for t in bm.tris:
            TRIS.append([base + t[0], base + t[1], base + t[2]])
            SRC.append((bx, by))
    topo = [X.decode_id(int(TAN[t[0]][0]))["topograph"] for t in TRIS]
    edge_tris = defaultdict(list)
    for t, tri in enumerate(TRIS):
        k = [kk3(V[i]) for i in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((k[a], k[b])))].append(t)
    adj = defaultdict(set)
    for ts in edge_tris.values():
        f = [t for t in ts if topo[t] == 37]
        for x in f:
            adj[x].update(y for y in f if y != x)
    seen, comps = set(), []
    for t in range(len(TRIS)):
        if topo[t] != 37 or t in seen or SRC[t] != (bx0, by0):
            continue
        comp, st = {t}, [t]
        while st:
            u = st.pop()
            for w in adj[u]:
                if w not in comp:
                    comp.add(w)
                    st.append(w)
        seen |= comp
        comps.append(sorted(comp))
    if not comps:
        raise ValueError(f"donor block {tuple(donor)} has no topo-37 canopy")
    refused = []
    for comp in sorted(comps, key=len, reverse=True):
        cset, eu = set(comp), Counter()
        for t in comp:
            k = [kk3(V[i]) for i in TRIS[t]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu[tuple(sorted((k[a], k[b])))] += 1
        meets = Counter()
        for e, n in eu.items():
            if n == 1:
                for t in edge_tris[e]:
                    if t not in cset and topo[t] != 0:
                        meets[topo[t]] += 1
        if meets:
            refused.append((len(comp), dict(meets)))
            continue
        return (np.asarray(V, dtype=np.float64), np.asarray(UV, dtype=np.float64), NRM, TAN, TRIS, comp,
                sorted({SRC[t] for t in comp}))
    raise ValueError(f"donor block {tuple(donor)} has no canopy blob bounded by grass alone: "
                     + "; ".join(f"{n} tris meeting topographs {m} (rim edges)" for n, m in refused)
                     + " -- a forest that meets rock or other ground cannot be carried alone")


def carve_forest(soup, *, center=None, near=None, donor=FOREST_DONOR, disc: int = 1,
                 game=None, spread: float = 1.0, rot_deg=None, log=print) -> dict:
    """Carry the donor block's topo-37 canopy blob onto the island at ``center`` (exact
    blob centre) or the best lawful placement near ``near``. Returns ``{"changed",
    "center", "report"}``; raises ``ValueError`` on any gate.

    ``spread`` (1.0..:data:`FOREST_SPREAD_MAX`) scales the blob in plan and ``rot_deg`` turns
    it to any angle, both about the donor blob's centre (:func:`_forest_plan`); its heights,
    UVs and topographs stay the donor's. ``spread=1`` with no ``rot_deg`` (or 0) is the
    verbatim carry, byte for byte."""
    import numpy as np
    gpos, gtris, gmeta, gnrm = soup["pos"], soup["tris"], soup["meta"], soup["nrm"]
    spread = float(spread)
    if not (math.isfinite(spread) and 1.0 <= spread <= FOREST_SPREAD_MAX):
        raise ValueError(f"spread x{spread:g} is outside 1.0..{FOREST_SPREAD_MAX:g} (the canopy's "
                         f"in-game-judged range)")
    if rot_deg is not None and not math.isfinite(float(rot_deg)):
        raise ValueError(f"rot_deg must be a finite angle, got {rot_deg!r}")

    # donor blob, verbatim, world frame
    dv_w, duv, dnrm, dtan, dtris, blob, blob_blocks = _forest_donor(donor, disc=disc, game=game)
    if blob_blocks != [tuple(donor)]:
        log(f"donor blob spans blocks {blob_blocks}")
    bpts = np.array([dv_w[i] for t in blob for i in dtris[t]])
    c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2, (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
    planned = spread != 1.0 or (rot_deg is not None and float(rot_deg) % 360.0 != 0.0)
    if planned:
        dv_w, dnrm = _forest_plan(dv_w, dnrm, c_local, spread=spread, rot_deg=rot_deg)
    edge_use = Counter()
    for t in blob:
        tri = dtris[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_use[tuple(sorted((kk3(dv_w[tri[a]]), kk3(dv_w[tri[b]]))))] += 1
    rim = chain_ring([e for e, n in edge_use.items() if n == 1], "donor rim", min_len=FOREST_RIM_MIN)
    rim_set = set(rim)
    rim_poly_local = [(p[0], p[2]) for p in rim]
    log(f"donor blob: {len(blob)} tris, rim ring {len(rim)} positions")
    hairlines = 0
    if planned:
        # THE HAIRLINE CURTAIN: 2 of the (15,15) blob's 48 curtain tris stand too steep for the engine's ground
        # query (ny <= 0.1) yet keep a plan footprint 0.010-0.015u wide: both share one top corner set 0.0195u off
        # the base corner below it, a strip no down-ray grounds on (the census MISSes it when a sample lands in
        # it). The plan map widens it by s; close it by setting that top corner on its base corner in plan.
        for t in blob:
            P3 = [dv_w[i] for i in dtris[t]]
            n = np.cross(P3[1] - P3[0], P3[2] - P3[0])
            ln = float(np.linalg.norm(n))
            if ln < 1e-12 or abs(n[1]) / ln > 0.1:
                continue
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ka, kb = kk3(P3[a]), kk3(P3[b])
                dpl = math.hypot(P3[a][0] - P3[b][0], P3[a][2] - P3[b][2])
                if not 0.0 < dpl <= CURTAIN_HAIRLINE * spread or (ka in rim_set) == (kb in rim_set):
                    continue
                base, top = (P3[a], kb) if ka in rim_set else (P3[b], ka)
                bx_, bz_ = float(base[0]), float(base[2])
                for i in range(len(dv_w)):
                    if kk3(dv_w[i]) == top:
                        dv_w[i][0], dv_w[i][2] = bx_, bz_
                hairlines += 1
    rim_splits = 0
    if planned and spread > 1.0:
        # THE RIM GRAIN: a spread rim edge is s times its donor length, and the zip bridging it grows with it (x1.5:
        # 9.1u chords against the 9u grain gate). Split each rim edge longer than the donor's longest into equal
        # pieces by splitting its curtain tri -- a planar split, UV and normal lerped along the edge, renders the
        # same -- so the carried rim is never coarser than the donor's.
        once = {e for e, k in edge_use.items() if k == 1}
        elen = {e: math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2]) for e in once}
        L0 = max(elen.values()) / spread
        dtan = [list(t4) for t4 in dtan]
        dnrm = [list(n3) for n3 in dnrm]
        add_v, add_uv = [], []
        for _ in range(3):                          # a corner tri wears two rim edges: its piece is split next pass
            for t in list(blob):
                tri = dtris[t]
                for a in range(3):
                    b, c = (a + 1) % 3, (a + 2) % 3
                    pa = dv_w[tri[a]] if tri[a] < len(dv_w) else add_v[tri[a] - len(dv_w)]
                    pb = dv_w[tri[b]] if tri[b] < len(dv_w) else add_v[tri[b] - len(dv_w)]
                    e = tuple(sorted((kk3(pa), kk3(pb))))
                    if e not in once or elen[e] <= L0 + 1e-9:
                        continue
                    k_n = math.ceil(elen[e] / L0 - 1e-9)
                    ua = duv[tri[a]] if tri[a] < len(duv) else add_uv[tri[a] - len(duv)]
                    ub = duv[tri[b]] if tri[b] < len(duv) else add_uv[tri[b] - len(duv)]
                    chain = [tri[a]]
                    for k in range(1, k_n):
                        f = k / k_n
                        add_v.append(np.asarray(pa, dtype=np.float64) + f * (np.asarray(pb) - np.asarray(pa)))
                        add_uv.append(np.asarray(ua, dtype=np.float64) + f * (np.asarray(ub) - np.asarray(ua)))
                        na, nb = np.asarray(dnrm[tri[a]]), np.asarray(dnrm[tri[b]])
                        nm = na + f * (nb - na)
                        dnrm.append(list(nm * (float(np.linalg.norm(na)) / (float(np.linalg.norm(nm)) or 1.0))))
                        dtan.append(list(dtan[tri[a]]))
                        chain.append(len(dv_w) + len(add_v) - 1)
                    chain.append(tri[b])
                    pieces = [[chain[k], chain[k + 1], tri[c]] for k in range(k_n)]
                    dtris[t] = pieces[0]
                    for pc in pieces[1:]:
                        dtris.append(pc)
                        blob.append(len(dtris) - 1)
                    once.discard(e)
                    rim_splits += 1
                    break
        if add_v:
            dv_w = np.vstack([dv_w, np.array(add_v)])
            duv = np.vstack([duv, np.array(add_uv)])
            edge_use = Counter()
            for t in blob:
                tri = dtris[t]
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    edge_use[tuple(sorted((kk3(dv_w[tri[a]]), kk3(dv_w[tri[b]]))))] += 1
            rim = chain_ring([e for e, k in edge_use.items() if k == 1], "split rim", min_len=FOREST_RIM_MIN)
            rim_set = set(rim)
            rim_poly_local = [(p[0], p[2]) for p in rim]
    if planned:
        log(f"canopy plan map: spread x{spread:g}, rot {0 if rot_deg is None else float(rot_deg) % 360.0:g} deg; "
            f"{hairlines} hairline curtain corner(s) closed, {rim_splits} rim edge(s) split to the donor's grain "
            f"(rim ring {len(rim)})")

    tri_c = _tri_centroids(soup)

    def poly_at(dx, dz):
        return [(x + dx, z + dz) for (x, z) in rim_poly_local]

    def footprint_lawful(poly, why=None):
        return forest_footprint_lawful(soup, tri_c, poly, why)

    if center is not None:
        TX, TZ = center
        poly = poly_at(TX - c_local[0], TZ - c_local[1])
        why = []
        seen = footprint_lawful(poly, why)
        if seen is None or seen < 40:
            raise CarveRefused("footprint", f"footprint at ({TX},{TZ}) is not lawful plain-grass mains "
                               f"clear of the rim (seen={seen})",
                               [p for p, _ in why] or [(x, z) for x, z in poly],
                               detail=f"it reaches {why[0][1]}" if why else "too little plain grass under it")
    else:
        if near is None:
            raise ValueError("give center= (exact) or near= (scan)")
        gx0 = 4 * round((near[0] - 40) / 4)
        gz0 = 4 * round((near[1] - 40) / 4)
        cands = []
        for gx in range(gx0, gx0 + 84, 4):
            for gz in range(gz0, gz0 + 84, 4):
                poly = poly_at(gx - c_local[0], gz - c_local[1])
                seen = footprint_lawful(poly)
                if seen is not None and seen >= 40:
                    d_rim = min(_coast_d2(soup, x, z) for (x, z) in poly) ** 0.5
                    cands.append((round(d_rim, 1), -gx, gx, gz))
        if not cands:
            raise CarveRefused("footprint", "no lawful placement -- the island has no plain-grass pocket "
                               "for this blob near the given point", [near])
        cands.sort(reverse=True)
        d_rim, _, TX, TZ = cands[0]
        log(f"placement: blob centre -> world ({TX},{TZ}) (rim clearance {d_rim}u, "
            f"{len(cands)} lawful candidates)")
    DX, DZ = TX - c_local[0], TZ - c_local[1]
    poly = poly_at(DX, DZ)

    # carve the hole
    drop = set()
    for tidx, tri in enumerate(gtris):
        for i in tri:
            if pip(gpos[i][0], gpos[i][2], poly) or near_poly(gpos[i][0], gpos[i][2], poly, CLEAR):
                drop.add(tidx)
                break
    dropped_fams = Counter(gmeta[t][2] for t in drop)
    if not set(dropped_fams) <= {"main"}:
        raise CarveRefused("hole", f"hole reaches non-mains island tris (fams {dict(dropped_fams)})",
                           [tri_c[t] for t in sorted(drop) if gmeta[t][2] != "main"])
    edge_use2 = Counter()
    for tidx, tri in enumerate(gtris):
        if tidx in drop:
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_use2[tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]]))))] += 1
    hole_edges = [e for e, n in edge_use2.items() if n == 1
                  and near_poly(e[0][0], e[0][2], poly, RING_BAND)
                  and near_poly(e[1][0], e[1][2], poly, RING_BAND)]
    hole = chain_ring(hole_edges, "hole")
    log(f"hole: dropped {len(drop)} tris, ring {len(hole)} positions")

    pos_nrm = {}
    for tidx, tri in enumerate(gtris):
        if tidx in drop:
            continue
        for i in tri:
            pos_nrm.setdefault(kk3(gpos[i]), list(gnrm[i]))

    # vertical anchor + THE COMPREHENSIVE CANOPY STEP LAW
    ground_med = float(np.median([p[1] for p in hole]))
    rim_med = float(np.median([p[1] for p in rim]))
    DY = ground_med - rim_med

    def nearest_ring_y(px, pz):
        return min(hole, key=lambda h: (h[0] - px) ** 2 + (h[2] - pz) ** 2)[1]

    rim_y = {p: nearest_ring_y(p[0] + DX, p[2] + DZ) for p in rim_set}
    for t in blob:                                          # per-face floor
        tri = dtris[t]
        ks = [kk3(dv_w[i]) for i in tri]
        tops = [dv_w[i][1] + DY for i, k in zip(tri, ks) if k not in rim_set]
        if not tops or not any(k in rim_set for k in ks):
            continue
        need = max(tops) - MAX_RISE
        for k in ks:
            if k in rim_set and need > rim_y[k]:
                rim_y[k] = need

    def canopy_y_at(px, pz):
        for t in blob:
            tri = dtris[t]
            a, b, c = (dv_w[i] for i in tri)
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / d
            w1 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / d
            w2 = 1 - w0 - w1
            if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                continue
            return w0 * a[1] + w1 * b[1] + w2 * c[1] + DY
        return None

    nrim = len(rim)
    for e0 in range(nrim):                                  # per-STATION rim lift
        p, q = rim[e0], rim[(e0 + 1) % nrim]
        ex, ez = q[0] - p[0], q[2] - p[2]
        el = (ex * ex + ez * ez) ** 0.5
        if el < 1e-6:
            continue
        nxi, nzi = -ez / el, ex / el
        mx, mz = p[0] + ex * 0.5, p[2] + ez * 0.5
        if canopy_y_at(mx + nxi * 0.4, mz + nzi * 0.4) is None:
            nxi, nzi = -nxi, -nzi
        nst = max(1, int(el / 0.4))
        for s in range(nst + 1):
            t01 = s / nst
            sx, sz = p[0] + ex * t01, p[2] + ez * t01
            tops = []
            for dd in (0.15, 0.3, 0.45, 0.6, 0.75):
                cy = canopy_y_at(sx + nxi * dd, sz + nzi * dd)
                if cy is not None:
                    tops.append(cy)
            if not tops:
                continue
            need = max(tops) - SAFE_RISE
            for k in (p, q):
                if need > rim_y[k]:
                    rim_y[k] = need

    def carry_vert(i):
        k = kk3(dv_w[i])
        p = dv_w[i]
        y = rim_y[k] if k in rim_set else p[1] + DY
        return [p[0] + DX, y, p[2] + DZ]

    carried = {t: [carry_vert(i) for i in dtris[t]] for t in blob}
    c_edge_use = Counter()
    c_float = {}
    for t in blob:
        ps = carried[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = kk3(ps[a]), kk3(ps[b])
            c_float.setdefault(ka, ps[a])
            c_float.setdefault(kb, ps[b])
            c_edge_use[tuple(sorted((ka, kb)))] += 1
    crim = chain_ring([e for e, n in c_edge_use.items() if n == 1], "carried rim", min_len=FOREST_RIM_MIN)
    rim_nrm = {}
    for t in blob:
        tri = dtris[t]
        for k in range(3):
            key = kk3(carried[t][k])
            if key in c_float:
                rim_nrm.setdefault(key, list(dnrm[tri[k]]))

    def signed_area(ring):
        s = 0.0
        for k in range(len(ring)):
            x1, z1 = ring[k][0], ring[k][2]
            x2, z2 = ring[(k + 1) % len(ring)][0], ring[(k + 1) % len(ring)][2]
            s += x1 * z2 - x2 * z1
        return s / 2

    # THE EXACT-WELD LAW (see carve_mountain): the ring holds kk3 KEYS; the zip's grass corners take the kept
    # grass's own float position, or on ground whose heights are not round they sit off it by up to 5e-4u
    h_float = {}
    for tidx, tri in enumerate(gtris):
        if tidx not in drop:
            for i in tri:
                h_float.setdefault(kk3(gpos[i]), tuple(gpos[i]))
    hole_ord = [_weld_point(p, h_float) for p in hole]
    rim_ord = list(crim)
    if signed_area(hole_ord) * signed_area(rim_ord) < 0:
        rim_ord.reverse()
    h0 = hole_ord[0]
    k0 = min(range(len(rim_ord)),
             key=lambda k: (rim_ord[k][0] - h0[0]) ** 2 + (rim_ord[k][2] - h0[2]) ** 2)
    rim_ord = rim_ord[k0:] + rim_ord[:k0]

    def rimw(p):
        return tuple(c_float[p])

    def d2(p, q):
        return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

    NH, NR = len(hole_ord), len(rim_ord)
    zip_tris = []
    i = j = 0
    if planned:     # a turned or spread canopy takes the mountain's DP strip: the greedy walk slivers at odd angles
        hole_ord, rim_ord, zip_tris = _zip_dp(list(hole), rim_ord, rimw, h_float, ny_floor=FOREST_ZIP_NY_FLOOR)
        i, j = NH, NR
    while i < NH or j < NR:
        h_cur = hole_ord[i % NH]
        r_cur = rimw(rim_ord[j % NR])
        can_h, can_r = i < NH, j < NR
        if can_h and can_r:
            adv_h = d2(hole_ord[(i + 1) % NH], r_cur) <= d2(h_cur, rimw(rim_ord[(j + 1) % NR]))
        else:
            adv_h = can_h
        if adv_h:
            zip_tris.append((h_cur, hole_ord[(i + 1) % NH], r_cur))
            i += 1
        else:
            zip_tris.append((h_cur, rimw(rim_ord[(j + 1) % NR]), r_cur))
            j += 1

    # zip UVs: decode each cell's mains from the kept bytes
    cell_of = lambda x, z: (int(np.floor(x / 4.0)), int(np.floor(z / 4.0)))  # noqa: E731
    kept_main_by_cell = defaultdict(list)
    for tidx, tri in enumerate(gtris):
        if tidx in drop or gmeta[tidx][2] != "main":
            continue
        cx, cz = tri_c[tidx]
        kept_main_by_cell[cell_of(cx, cz)].append(tidx)
    QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
    ORIS = (0, 90, 180, 270)

    def decode_cell_bytes(cell):
        # method (a): exact 16-hypothesis decode from the cell's own kept bytes
        for tidx in kept_main_by_cell.get(cell, []):
            tri = gtris[tidx]
            uvv = gmeta[tidx][3]
            for quad in QUADS:
                for ori in ORIS:
                    err = 0.0
                    for i, (u, v) in zip(tri, uvv):
                        mu, mv = G.mains_uv(gpos[i][0], gpos[i][2], cell, quad, ori)
                        err = max(err, abs(mu - u), abs(mv - v))
                    if err < 1e-4:
                        return (quad, ori)
        return None

    # resolve every zip cell UP FRONT: decoded ground truth where the kept bytes allow,
    # else the seeded assign_mains policy over the whole fallback set (THE DIVERSITY
    # POLICY -- the uncoupled per-cell pick this replaces read as a chevron ring)
    zcells = {cell_of((t[0][0] + t[1][0] + t[2][0]) / 3,
                      (t[0][2] + t[1][2] + t[2][2]) / 3) for t in zip_tris}
    decoded = {c: got for c in zcells if (got := decode_cell_bytes(c)) is not None}
    dropped = sorted(c for c in zcells if c not in decoded)
    pre = dict(decoded)
    for (ci, cj) in dropped:                # ground-truth W/S boundary where bytes exist
        for n in ((ci - 1, cj), (ci, cj - 1)):
            if n not in pre and n not in zcells and \
                    (got := decode_cell_bytes(n)) is not None:
                pre[n] = got
    dq, do = G.assign_mains_seeded(dropped, {c: qo[0] for c, qo in pre.items()},
                                   {c: qo[1] for c, qo in pre.items()})
    cell_qo = dict(decoded)
    cell_qo.update({c: (dq[c], do[c]) for c in dropped})
    log(f"zip mains: {len(decoded)} cells decoded from kept bytes, "
        f"{len(dropped)} resolved via the assign_mains policy")

    GRASS_ID = float(X.encode_id(topograph=0))
    new_parents = []
    for t in blob:                                          # the canopy, verbatim channels
        tri = dtris[t]
        idall = float(dtan[tri[0]][0])
        corners = tuple((*carried[t][k], duv[tri[k]][0], duv[tri[k]][1], *dnrm[tri[k]])
                        for k in range(3))
        new_parents.append((corners, idall, "forest"))
    worst_zip_rise = 0.0
    zip_ny_min = 1.0
    for tri3 in zip_tris:                                   # the grass annulus
        a, b, c = (np.asarray(p, dtype=np.float64) for p in tri3)
        n = np.cross(b - a, c - a)
        order = (a, b, c) if n[1] > 0 else (a, c, b)
        nl = float(np.linalg.norm(n)) or 1.0
        zip_ny_min = min(zip_ny_min, abs(float(n[1])) / nl)
        worst_zip_rise = max(worst_zip_rise,
                             float(max(p[1] for p in tri3) - min(p[1] for p in tri3)))
        ccx = float(a[0] + b[0] + c[0]) / 3
        ccz = float(a[2] + b[2] + c[2]) / 3
        cell = cell_of(ccx, ccz)
        quad, ori = cell_qo[cell]
        corners = []
        for pnt in order:
            key = kk3(pnt)
            nrm3 = pos_nrm.get(key) or rim_nrm[key]
            u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, quad, ori)
            corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]), u, v, *nrm3))
        new_parents.append((tuple(corners), GRASS_ID, "zip"))
    new_by_block = split_borders8(new_parents)
    if not set(new_by_block) <= set(soup["blocks"]):
        leak = sorted(set(new_by_block) - set(soup["blocks"]))
        raise CarveRefused("leak", f"carve leaks outside the deployed blocks: {leak}",
                           [(BLOCK * (bx + 0.5), -BLOCK * (by + 0.5)) for bx, by in leak])

    changed = _assemble(soup, drop, new_by_block)

    # gates (the study's section 9)
    worst_wall, wall_at = 0.0, None
    crim_keys = {kk3(c_float[r]) for r in crim}
    for t in blob:
        ps = carried[t]
        if any(kk3(p) in crim_keys for p in ps):
            rise = max(p[1] for p in ps) - min(p[1] for p in ps)
            if rise > worst_wall:
                worst_wall, wall_at = rise, (sum(p[0] for p in ps) / 3, sum(p[2] for p in ps) / 3)
    va = np.array([[c[0], c[1], c[2]] for corners, _, _ in new_parents for c in corners])
    fams = [fam for _, _, fam in new_parents]
    maxe = 0.0
    down = 0
    geo_at = []                                          # where the geometry gate fails (the editor draws it)
    for kdx in range(0, len(va), 3):
        a, b, c = va[kdx], va[kdx + 1], va[kdx + 2]
        n = np.cross(b - a, c - a)
        if n[1] < -1e-6 * float(np.linalg.norm(n)):     # a split curtain piece is vertical to float noise
            down += 1                                    # (~1e-13), not a down face
            geo_at.append(((a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3))
        for pq in ((a, b), (b, c), (c, a)):    # a spread canopy edge is gated against its declared length
            el = float(np.linalg.norm(pq[0] - pq[1]))
            el = el / spread if fams[kdx // 3] == "forest" else el
            maxe = max(maxe, el)
            if el >= 9.0:
                geo_at.append(((pq[0][0] + pq[1][0]) / 2, (pq[0][2] + pq[1][2]) / 2))
    ring_pts = np.array([list(p) for p in hole_ord] + [list(rimw(p)) for p in rim_ord])
    nm = 0
    for a_ in range(len(ring_pts)):
        dd = np.sum((ring_pts - ring_pts[a_]) ** 2, axis=1)
        close = int(((dd > 1e-9) & (dd < 0.0025)).sum())
        nm += close
        if close:
            geo_at.append((ring_pts[a_][0], ring_pts[a_][2]))
    # the annulus-crack gate = BASELINE-SUBTRACTED against the PRISTINE island, as carve_mountain's
    # once-edge gate is: an edge the island already holds open is its own, not a crack the carve
    # opened (the river island's grass crest over its carried stock bank, RUNG5.md "The forest after
    # the seam rung"). The carve must not ADD one; the same count over the same blocks before it.
    once0 = {e for e, n in _world_edge_use(soup["blocks"]).items() if n == 1}
    inner_once = [e for e, n in _world_edge_use(changed).items() if n == 1 and e not in once0
                  and near_poly((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2,
                                poly, RING_BAND + 2.0)]
    log(f"gates: down={down} maxEdge={maxe:.1f} nearMiss={nm // 2} "
        f"annulusOnce={len(inner_once)} wallRise={worst_wall:.2f} "
        f"zipRise={worst_zip_rise:.2f} zipNyMin={zip_ny_min:.2f}")
    if down or nm or inner_once or maxe >= 9.0:
        geo_at += [((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2) for e in inner_once]
        raise CarveRefused("geometry", "forest geometry gate failed (down/near-miss/annulus-crack/edge)", geo_at)
    if worst_wall > 2.34 or worst_zip_rise > 2.34 or zip_ny_min <= 0.1:
        step_at = [wall_at] if worst_wall > 2.34 and wall_at is not None else []
        for tri3 in zip_tris:
            a, b, c = (np.asarray(p, dtype=np.float64) for p in tri3)
            n = np.cross(b - a, c - a)
            rise = float(max(p[1] for p in tri3) - min(p[1] for p in tri3))
            if rise > 2.34 or abs(float(n[1])) / (float(np.linalg.norm(n)) or 1.0) <= 0.1:
                step_at.append((float(a[0] + b[0] + c[0]) / 3, float(a[2] + b[2] + c[2]) / 3))
        raise CarveRefused("step", "THE CANOPY STEP LAW gate failed (wall/zip rise or zip winding)", step_at)

    _perimeter_walk_in_gate(changed, [rimw(p) for p in rim_ord], poly, log=log)

    return {"changed": changed, "center": (TX, TZ), "drop": drop,
            "zip_cells": cell_qo, "zip_fallback": dropped,
            "report": {"blob_tris": len(blob), "dropped": len(drop),
                       "zip_tris": len(zip_tris), "zip_fallback_cells": len(dropped),
                       "wall_rise": round(worst_wall, 2),
                       "zip_rise": round(worst_zip_rise, 2),
                       "spread": spread,
                       "rot_deg": 0 if rot_deg is None else round(float(rot_deg) % 360.0, 6),
                       "hairlines": hairlines, "rim_splits": rim_splits}}


def _world_edge_use(blocks) -> Counter:
    """Edge use over ``{(bx, by): BlockMesh}`` in the world frame, keyed by :data:`kk3` -- an
    internal block border counts 2, one tri from each side's mesh. One count for a carve's gate
    and for the pristine baseline it subtracts, so the two can only differ where the carve did."""
    eu = Counter()
    for blk, bm in blocks.items():
        v_ = bm.chan_arrays[X.CH_POS]
        bx, by = blk
        for tri in bm.tris:
            w = [(v_[i][0] + BLOCK * bx, v_[i][1], v_[i][2] - BLOCK * (by + 1) + BLOCK)
                 for i in tri]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
    return eu


def _assemble(soup, drop, new_by_block):
    """Re-emit per-block meshes: kept tris byte-exact from the soup (position, uv, normal AND the
    source tangent -- :func:`soup_from_blocks`), new tris appended with the kit's
    ``[idall, 0, 0, 1]``."""
    gpos, gtris, gmeta, gnrm = soup["pos"], soup["tris"], soup["meta"], soup["nrm"]
    gtan = soup["tan"]
    changed = {}
    for blk in sorted(soup["blocks"]):
        bx, by = blk
        pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []

        def emit(p, u_, n_, t4):
            pos.append(list(p))
            nrm.append(list(n_))
            uv.append(list(u_))
            tan.append(list(t4))
            flat.append(len(pos) - 1)

        for tidx, tri in enumerate(gtris):
            tblk, idall, fam, uvv = gmeta[tidx]
            if tblk != blk or tidx in drop:
                continue
            for vid, (u, v) in zip(tri, uvv):
                w = gpos[vid]
                emit([w[0] - BLOCK * bx, w[1], w[2] + BLOCK * (by + 1) - BLOCK],
                     (u, v), gnrm[vid], gtan[vid])
            tris.append([flat[-3], flat[-2], flat[-1]])
        for corners, idall, fam in new_by_block.get(blk, []):
            for c in corners:
                emit([c[0] - BLOCK * bx, c[1], c[2] + BLOCK * (by + 1) - BLOCK],
                     (c[3], c[4]), [c[5], c[6], c[7]], [idall, 0.0, 0.0, 1.0])
            tris.append([flat[-3], flat[-2], flat[-1]])
        bm0 = soup["blocks"][blk]
        changed[blk] = X.BlockMesh(
            name=bm0.name, disc=bm0.disc, x=bx, y=by, lod=bm0.lod, vcount=len(pos),
            stride=48,
            channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2),
                      X.CH_TAN: (32, 4)},
            chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
            flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True,
            submeshes=[])
    return changed


def _perimeter_walk_in_gate(changed, rim_pts, poly, *, log=print):
    """Simulate the engine climb rule around the WHOLE rim on the assembled meshes: a
    single foot step crossing anywhere must climb <= GATE_CLIMB (descent always legal)."""
    from . import placement as P2
    _wv, _wt, _wf = [], [], []
    for blk, bm in sorted(changed.items()):
        bx, by = blk
        base = len(_wv)
        for k in range(bm.vcount):
            v_ = bm.chan_arrays[X.CH_POS][k]
            _wv.append((v_[0] + BLOCK * bx, v_[1], v_[2] - BLOCK * (by + 1) + BLOCK))
            _wt.append(bm.chan_arrays[X.CH_TAN][k])
        _wf.extend(i + base for i in bm.flat_index)

    class _W:
        pass

    _w = _W()
    _w.verts, _w.tangents, _w.flat_index = _wv, _wt, _wf
    _w.tris = [_wf[i:i + 3] for i in range(0, len(_wf), 3)]
    _wml = [("Terrain", _w)]
    # ~49 samples per 0.5u rim station: the grid index (a pure accelerator, same first hit)
    # turns each from a scan of every assembled tri into a scan of one bucket
    _idx = P2.build_meshlist_index(_wml)
    RES = 0.05
    SPAN = 1.2
    NSAMP = int(2 * SPAN / RES) + 1
    WIN = int(S_STEP / RES)
    worst = (0.0, None)
    for e0 in range(len(rim_pts)):
        a = rim_pts[e0]
        b = rim_pts[(e0 + 1) % len(rim_pts)]
        ex, ez = b[0] - a[0], b[2] - a[2]
        el = (ex * ex + ez * ez) ** 0.5
        if el < 1e-6:
            continue
        nxo, nzo = ez / el, -ex / el
        nst = max(1, int(el / 0.5))
        for s in range(nst + 1):
            t01 = s / nst
            sx, sz = a[0] + ex * t01, a[2] + ez * t01
            if pip(sx + nxo * 0.8, sz + nzo * 0.8, poly):
                nxo, nzo = -nxo, -nzo
            prof = []
            for k in range(NSAMP):
                d = SPAN - k * RES
                hy, nm_, _, _tp = P2.place(_wml, sx + nxo * d, sz + nzo * d, sky=True,
                                           index=_idx)
                prof.append(hy if nm_ != "MISS" else None)
            for i0 in range(NSAMP):
                if prof[i0] is None:
                    continue
                for j0 in range(i0 + 1, min(i0 + WIN + 1, NSAMP)):
                    if prof[j0] is None:
                        continue
                    climb = prof[j0] - prof[i0]
                    if climb > worst[0]:
                        worst = (climb, (round(sx, 1), round(sz, 1)))
    log(f"perimeter walk-in gate: worst single-step climb {worst[0]:.2f} at {worst[1]} "
        f"(ceiling {GATE_CLIMB})")
    if worst[0] > GATE_CLIMB:
        raise CarveRefused("walk-in", f"a rim segment climbs {worst[0]:.2f} > {GATE_CLIMB} at {worst[1]}",
                           [worst[1]])


# ---- THE HILL -------------------------------------------------------------------------------
def build_hill(soup, *, center=None, near=None, height: float = HILL_H,
               radius: float = HILL_R, log=print) -> dict:
    """Raise a raised-cosine grass hill at ``center`` (exact) or the best lawful pure-mains
    placement near ``near``. Pure-Y displacement of the soup's deployed bytes; LOCAL
    normal re-smooth; the grass-language gates. Returns ``{"changed", "center",
    "report"}``."""
    import numpy as np
    gpos, gtris, gmeta, gnrm = soup["pos"], soup["tris"], soup["meta"], soup["nrm"]
    tri_c = _tri_centroids(soup)
    tri_cx = np.array([c[0] for c in tri_c])
    tri_cz = np.array([c[1] for c in tri_c])
    tri_cy = np.array([(gpos[t[0]][1] + gpos[t[1]][1] + gpos[t[2]][1]) / 3 for t in gtris])
    fam_arr = np.array([m[2] for m in gmeta])
    pts = {f: np.array([(tri_cx[i], tri_cz[i]) for i in range(len(gtris))
                        if fam_arr[i] == f]) for f in ("forest", "stamp", "rock")}

    def mind(f, x, z):
        p = pts[f]
        if len(p) == 0:
            return 1e9
        return float(np.sqrt(((p[:, 0] - x) ** 2 + (p[:, 1] - z) ** 2).min()))

    FOOT = radius + 2.0

    def lawful(gx, gz):
        sel = (tri_cx - gx) ** 2 + (tri_cz - gz) ** 2 < FOOT ** 2
        if sel.sum() < 60 or not all(fam_arr[sel] == "main"):
            return None
        # the footprint must sit in the ROLLING-RELIEF envelope, not on prior displacement
        # (an existing hill's footprint is still pure mains -- stacking would bust the
        # slope envelope; a plain mint is flat, and stamp/zip variation spans well under this)
        if float(tri_cy[sel].max() - tri_cy[sel].min()) > 2.4:
            return None
        d_f = mind("forest", gx, gz) - FOOT
        d_s = mind("stamp", gx, gz) - FOOT
        d_r = mind("rock", gx, gz) - FOOT
        if d_f < FOREST_CLEAR or d_s < STAMP_CLEAR or d_r < RIM_CLEAR:
            return None
        return min(d_f, d_s, d_r)

    if center is not None:
        CX, CZ = center
        if lawful(CX, CZ) is None:
            raise ValueError(f"hill footprint at ({CX},{CZ}) is not lawful (pure mains "
                             f"disc r{FOOT:.0f} + clearances forest {FOREST_CLEAR}/"
                             f"stamp {STAMP_CLEAR}/rim {RIM_CLEAR})")
    else:
        if near is None:
            raise ValueError("give center= (exact) or near= (scan)")
        cands = []
        gx0 = 4 * round((near[0] - 56) / 4)
        gz0 = 4 * round((near[1] - 56) / 4)
        for gx in range(gx0, gx0 + 116, 4):
            for gz in range(gz0, gz0 + 116, 4):
                c = lawful(gx, gz)
                if c is not None:
                    cands.append((round(c, 1), gx, gz))
        if not cands:
            raise ValueError("no lawful hill placement near the given point")
        cands.sort(reverse=True)
        _, CX, CZ = cands[0]
        log(f"hill centre -> ({CX},{CZ}) (clearance {cands[0][0]}u, {len(cands)} candidates)")

    touched = set()
    for i, tri in enumerate(gtris):
        if any(raised_cosine(math.hypot(gpos[j][0] - CX, gpos[j][2] - CZ),
                             height, radius) > 1e-9 for j in tri):
            touched.add(i)
            if gmeta[i][2] != "main":
                raise ValueError(f"hill displaces a non-mains tri ({gmeta[i][2]})")
    new_y = {}
    for i in range(len(gpos)):
        lift = raised_cosine(math.hypot(gpos[i][0] - CX, gpos[i][2] - CZ), height, radius)
        if lift > 0.0:
            new_y[i] = gpos[i][1] + lift
    gpos2 = [([p[0], new_y[i], p[2]] if i in new_y else p) for i, p in enumerate(gpos)]

    recompute = {kk3(gpos2[j]) for i in touched for j in gtris[i]}
    acc = defaultdict(lambda: [0.0, 0.0, 0.0])
    for tri in gtris:
        a, b, c = (np.asarray(gpos2[j]) for j in tri)
        n = np.cross(b - a, c - a)
        for j in tri:
            k = kk3(gpos2[j])
            if k in recompute:
                v = acc[k]
                v[0] += n[0]
                v[1] += n[1]
                v[2] += n[2]
    new_nrm = {}
    for k, v in acc.items():
        L = math.sqrt(sum(q * q for q in v)) or 1.0
        new_nrm[k] = [v[0] / L, v[1] / L, v[2] / L]

    worst_slope = 0.0
    down = 0
    for i in touched:
        a, b, c = (np.asarray(gpos2[j]) for j in gtris[i])
        n = np.cross(b - a, c - a)
        L = float(np.linalg.norm(n)) or 1.0
        if n[1] <= 0:
            down += 1
        worst_slope = max(worst_slope, math.degrees(math.acos(min(1.0, abs(n[1]) / L))))
    peak_y = max(gpos2[j][1] for i in touched for j in gtris[i])
    log(f"gates: displaced tris={len(touched)} worstFlank={worst_slope:.1f}deg "
        f"(<= {MAX_FLANK}) down={down} peakY={peak_y:.2f}")
    if worst_slope > MAX_FLANK or down:
        raise ValueError(f"flank slope {worst_slope:.1f} > {MAX_FLANK} or down-facing tris "
                         f"-- lower --height or raise --radius")
    if peak_y > PEAK_CAP:
        raise ValueError(f"peak {peak_y:.2f} leaves the lowland band (cap {PEAK_CAP})")

    # the crack gate = BASELINE-SUBTRACTED against the PRISTINE island, as carve_forest's and
    # carve_mountain's once-edge gates are: an edge the island already holds open is its own, not a
    # crack the hill opened (the river island's grass crest over its carried stock bank, RUNG5.md
    # "The hill's crack gate"). The same count over the same tris on the positions BEFORE the lift,
    # matched by key: an open edge the lift MOVES gets a new key and is judged as the hill's (a
    # T-junction slit widens under a non-linear lift; an edge open only where the read stops tears
    # from the block it never saw). Before the lift, not after: after it, a weld the lift splits
    # would be its own baseline and the gate would go blind.
    in_reach = [i for i in range(len(gtris)) if math.hypot(tri_cx[i] - CX, tri_cz[i] - CZ) <= radius + 8]

    def once_edges(P):
        eu = Counter()
        for i in in_reach:
            tri = gtris[i]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu[tuple(sorted((kk3(P[tri[a]]), kk3(P[tri[b]]))))] += 1
        return [e for e, n in eu.items() if n == 1
                and math.hypot((e[0][0] + e[1][0]) / 2 - CX, (e[0][2] + e[1][2]) / 2 - CZ) < radius + 4]
    once0 = set(once_edges(gpos))
    once = once_edges(gpos2)
    inner_once = [e for e in once if e not in once0]
    inherited = len(once) - len(inner_once)
    if inherited:
        log(f"crack gate: {inherited} once-edge(s) within r+4 the island already holds open, untouched "
            f"by the lift: the island's own, not judged (e.g. at "
            + ", ".join(f"({(e[0][0] + e[1][0]) / 2:.2f},{(e[0][2] + e[1][2]) / 2:.2f})"
                        for e in sorted(e for e in once if e in once0)[:3]) + ")")
    if inner_once:
        raise ValueError(f"{len(inner_once)} once-edges inside the hill region (cracks)")

    # write back per block
    import dataclasses
    order = sorted(soup["blocks"])
    changed = {}
    base = 0
    for blk in order:
        bm = soup["blocks"][blk]
        pos = [list(v) for v in bm.chan_arrays[X.CH_POS]]
        nrm = [list(v) for v in bm.chan_arrays[X.CH_NRM]]
        dirty = False
        for k in range(bm.vcount):
            w = gpos2[base + k]
            if abs(w[1] - pos[k][1]) > 1e-9:
                pos[k][1] = w[1]
                dirty = True
            kkey = kk3(w)
            if kkey in new_nrm:
                nrm[k] = list(new_nrm[kkey])
                dirty = True
        if dirty:
            ca = dict(bm.chan_arrays)
            ca[X.CH_POS] = pos
            ca[X.CH_NRM] = nrm
            changed[blk] = dataclasses.replace(bm, chan_arrays=ca)
        base += bm.vcount
    return {"changed": changed, "center": (CX, CZ),
            "report": {"displaced_tris": len(touched), "worst_flank": round(worst_slope, 1),
                       "peak_y": round(peak_y, 2), "inherited_once": inherited}}


# ---- THE MOUNTAIN CARVE -----------------------------------------------------------------------
def _norm_donor_blocks(donor):
    """Normalize a donor spec -- one ``(bx, by)`` pair or an iterable of pairs -- to a
    list of block tuples (order preserved, duplicates dropped)."""
    if donor and isinstance(donor[0], (list, tuple)):
        out = []
        for b in donor:
            t = (int(b[0]), int(b[1]))
            if t not in out:
                out.append(t)
        return out
    return [(int(donor[0]), int(donor[1]))]


def _mountain_blob(donor_blocks, *, rock_topos, alcove_box, disc=1, game=None, log=print):
    """Build the donor massif blob (largest ``rock_topos`` component + enclosed raised
    tris + optional alcove floor + pocket fill + Object-aperture rings) from one or
    several donor blocks merged in the WORLD frame -- a real massif may straddle a block
    border (the crag spans two). Returns everything the carve needs donor-side; raises
    ``ValueError`` on structural refusals."""
    import numpy as np
    ROCK = frozenset(rock_topos)
    dV_rows, dU_rows, dN, dT, dtri = [], [], [], [], []
    read_blocks = []
    for (dbx, dby) in donor_blocks:
        try:
            don = X.read_block(dbx, dby, disc=disc, game=game)
        except ValueError:
            log(f"donor block ({dbx},{dby}) has no terrain mesh -- skipped")
            continue
        read_blocks.append((dbx, dby))
        base = len(dV_rows)
        doff_b = np.array([BLOCK * dbx, 0.0, -BLOCK * dby])
        for row in (np.asarray(don.verts, dtype=np.float64) + doff_b):
            dV_rows.append(row)
        for row in np.asarray(don.uvs, dtype=np.float64):
            dU_rows.append(row)
        dN.extend(list(n) for n in don.normals)
        dT.extend(list(t4) for t4 in don.tangents)
        nt = len(don.flat_index) // 3
        dtri.extend([don.flat_index[3 * t] + base, don.flat_index[3 * t + 1] + base,
                     don.flat_index[3 * t + 2] + base] for t in range(nt))
    if not read_blocks:
        raise ValueError(f"no donor terrain mesh in {list(donor_blocks)}")
    dV = np.asarray(dV_rows)
    dU = np.asarray(dU_rows)
    doff = np.array([BLOCK * read_blocks[0][0], 0.0, -BLOCK * read_blocks[0][1]])
    dtopo = [X.decode_id(int(round(dT[i[0]][0])))["topograph"] for i in dtri]

    d_edge = defaultdict(list)
    for t, idx in enumerate(dtri):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            d_edge[tuple(sorted((kk3(dV[idx[a]]), kk3(dV[idx[b]]))))].append(t)

    adjR = defaultdict(set)
    for e, ts in d_edge.items():
        r = [t for t in ts if dtopo[t] in ROCK]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adjR[r[i]].add(r[j]); adjR[r[j]].add(r[i])
    seen, comps = set(), []
    for s in range(len(dtri)):
        if dtopo[s] not in ROCK or s in seen:
            continue
        comp = {s}; st = [s]
        while st:
            t = st.pop()
            for t2 in adjR[t]:
                if t2 not in comp:
                    comp.add(t2); st.append(t2)
        seen |= comp
        comps.append(comp)
    if not comps:
        raise ValueError(f"donor block(s) {list(donor_blocks)} have no rock massif "
                         f"(topos {sorted(ROCK)})")
    comps.sort(key=len, reverse=True)
    blob = set(comps[0])
    log(f"donor rock component: {len(blob)} tris (next {[len(c) for c in comps[1:3]]})")

    def once_edges(tset):
        eu_ = Counter()
        for t in tset:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu_[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))] += 1
        return [e for e, n in eu_.items() if n == 1]

    rings0 = chain_rings(once_edges(blob), "donor blob")
    rings0.sort(key=lambda r: -abs(signed_area(r)))
    if len(rings0) > 1:                                    # inner rings enclose non-rock islands
        inner_pts = {p for r in rings0[1:] for p in r}
        seeds = []
        for e in once_edges(blob):
            if e[0] in inner_pts and e[1] in inner_pts:
                seeds += [t for t in d_edge[e] if t not in blob]
        st = list(seeds)
        added = 0
        while st:
            t = st.pop()
            if t in blob:
                continue
            blob.add(t); added += 1
            for a, b in ((0, 1), (1, 2), (2, 0)):
                for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
                    if t2 not in blob and dtopo[t2] not in ROCK:
                        st.append(t2)
        log(f"enclosed raised tris flooded in: {added}")
    # THE ALCOVE FLOOR CARRY (donor-conditional): a notch's flat floor is
    # mountain-attached terrain; without it the blob rim oscillates inside the notch and
    # no smooth ground apron can meet it. Carried verbatim; only the Object mesh itself
    # (a separate part) stays behind. The box reads in the FIRST donor block's local frame.
    # An optional fourth element names the floor's topographs (default grass, 0 -- Uaho's);
    # a snow massif's inlet floor is 27 (THE INLET FLOOR, mountaindonors/INLET.md); a desert crag's walled
    # scrub canopy is 38, carried whole with its walls so rock and canopy stand on one foot (THE CANOPY STEP, STEP.md).
    if alcove_box is not None:
        (nx0, nx1), (nz0, nz1), ny_min = alcove_box[:3]
        floor_topos = frozenset(alcove_box[3]) if len(alcove_box) > 3 else frozenset({0})
        NBOX = lambda c: nx0 < c[0] < nx1 and nz0 < c[2] < nz1  # noqa: E731
        seeds = []
        for e in once_edges(blob):
            for t in d_edge[e]:
                if t not in blob and dtopo[t] in floor_topos:   # floor tris only (canopy only when named: STEP.md)
                    c = (dV[dtri[t]] - doff).mean(axis=0)
                    if NBOX(c) and min(dV[i][1] for i in dtri[t]) > ny_min:
                        seeds.append(t)
        st = list(seeds)
        added = 0
        while st:
            t = st.pop()
            if t in blob:
                continue
            c = (dV[dtri[t]] - doff).mean(axis=0)
            if not (NBOX(c) and min(dV[i][1] for i in dtri[t]) > ny_min):
                continue
            blob.add(t)
            added += 1
            for a, b in ((0, 1), (1, 2), (2, 0)):
                for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
                    if t2 not in blob and dtopo[t2] in floor_topos:
                        st.append(t2)
        log(f"alcove floor carried: {added} tris (verbatim, incl. the cave-floor tiles)")

    oe = once_edges(blob)
    rings1 = chain_rings(oe, "blob rim")
    rings1.sort(key=lambda r: -abs(signed_area(r)))
    if len(rings1) > 1:                                    # fill enclosed pockets whole
        inner_pts = {p for r in rings1[1:] for p in r}
        st = [t for e in oe if e[0] in inner_pts and e[1] in inner_pts
              for t in d_edge[e] if t not in blob]
        filled = 0
        while st:
            t = st.pop()
            if t in blob:
                continue
            blob.add(t)
            filled += 1
            for a, b in ((0, 1), (1, 2), (2, 0)):
                for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
                    if t2 not in blob:
                        st.append(t2)
        if filled:
            log(f"enclosed pocket filled: {filled} tris (verbatim)")
        oe = once_edges(blob)
        rings1 = chain_rings(oe, "blob rim")
        rings1.sort(key=lambda r: -abs(signed_area(r)))
    # rings beyond the outer one must be OBJECT APERTURES -- the falls-aperture law at
    # mountain scale: literal holes in the terrain whose boundary is exactly the embedded
    # Object mesh's vertex set. Carried as verbatim PLUGS below.
    oV = oN = otris = None
    apertures = []
    ensemble_apertures = []
    if len(rings1) > 1:
        oV_rows, oN_l, otris = [], [], []
        for (dbx, dby) in read_blocks:
            try:
                om = X.read_block(dbx, dby, disc=disc, game=game, part="object")
            except Exception:
                continue
            base = len(oV_rows)
            doff_b = np.array([BLOCK * dbx, 0.0, -BLOCK * dby])
            for row in (np.asarray(om.verts, dtype=np.float64) + doff_b):
                oV_rows.append(row)
            oN_l.extend(list(n) for n in om.normals)
            nt = len(om.flat_index) // 3
            otris.extend([om.flat_index[3 * t] + base, om.flat_index[3 * t + 1] + base,
                          om.flat_index[3 * t + 2] + base] for t in range(nt))
        okeys = set()
        if oV_rows:
            oV = np.asarray(oV_rows)
            oN = oN_l
            okeys = {kk3(p) for p in oV}
        pending = []
        for r in rings1[1:]:
            if okeys and all(p in okeys for p in r):
                apertures.append(r)                        # Uaho-class: the PLUG path
            else:
                pending.append(r)
        if pending:
            # THE ENSEMBLE-APERTURE LAW (the horseshoe, 2026-07-15): a big massif's
            # aperture is the river/falls MOUTH -- its ring is owned by the UNION of
            # the donor's auxiliary parts, which carry under the same rigid map and
            # cover the hole in-game exactly as in stock. No plug is built.
            union = set(okeys)
            for part in ENSEMBLE_PARTS[1:]:                # object already read
                for (dbx, dby) in read_blocks:
                    try:
                        pm = X.read_block(dbx, dby, disc=disc, game=game,
                                          part=part.lower())
                    except Exception:
                        continue
                    doff_b = np.array([BLOCK * dbx, 0.0, -BLOCK * dby])
                    for p in (np.asarray(pm.verts, dtype=np.float64) + doff_b):
                        union.add(kk3(p))
            for r in pending:
                bad = [p for p in r if p not in union]
                if bad:
                    raise ValueError(f"extra blob ring is neither an OBJECT aperture "
                                     f"nor an ENSEMBLE aperture (points owned by no "
                                     f"auxiliary part, e.g. {bad[:2]})")
                ensemble_apertures.append(r)
    rim = rings1[0]
    if len(rim) != len(oe) - sum(len(r) for r in apertures) \
            - sum(len(r) for r in ensemble_apertures):
        raise ValueError("blob ring accounting failed (rim + apertures != once-edges)")
    if apertures:
        log(f"object apertures: {[len(r) for r in apertures]} pts "
            f"(plugged with the object's own tris)")
    if ensemble_apertures:
        log(f"ENSEMBLE apertures: {[len(r) for r in ensemble_apertures]} pts "
            f"(covered by the carried {'/'.join(ENSEMBLE_PARTS)} parts, no plugs)")
    rim_set = set(rim)
    bpts = np.array([dV[i] for t in blob for i in dtri[t]])
    c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2,
               (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
    r_rim = max(math.hypot(p[0] - c_local[0], p[2] - c_local[1]) for p in rim)
    # THE FOOTPRINT SWEEP (the horseshoe trap, 2026-07-15): every donor terrain tri
    # whose centroid lies plan-inside the rim rides along VERBATIM -- the mouth tunnel's
    # topo-58 lining, weld-isolated rock SHINGLES (the see-through quad), interior
    # canopy bits. They stay OUTSIDE the ring/rim accounting (a free shingle touching
    # the sheet at one vertex is legal stock structure that breaks manifold chaining);
    # their open edges are lawful stock boundaries, exempted at the crack gate.
    rim_poly_local = [(p[0], p[2]) for p in rim]
    sweep = []
    for t in range(len(dtri)):
        if t in blob:
            continue
        c = dV[dtri[t]].mean(axis=0)
        if pip(c[0], c[2], rim_poly_local):
            sweep.append(t)
    if sweep:
        log(f"footprint sweep: {len(sweep)} interior tris ride verbatim (topos "
            f"{dict(Counter(dtopo[t] for t in sweep))})")
    log(f"blob: {len(blob)} tris, extent {bpts[:, 0].max() - bpts[:, 0].min():.0f}x"
        f"{bpts[:, 2].max() - bpts[:, 2].min():.0f}u y[{bpts[:, 1].min():.1f},"
        f"{bpts[:, 1].max():.1f}]; rim {len(rim)} pts max plan radius {r_rim:.1f}u")

    # de-tilt: the donor mountain stands on sloped ground. Carried onto a flat bench, a
    # raw rim conform would shear the foot courses -- the exact stretch class the carry
    # exists to escape. Fit a least-squares plane over the RIM feet and subtract it from
    # the WHOLE blob (an affine shear); the rim conform then handles only the mesa-scale
    # residual. Normals get the shear's inverse-transpose.
    Amat = np.array([[p[0] - c_local[0], p[2] - c_local[1], 1.0] for p in rim])
    bvec = np.array([p[1] for p in rim])
    (ta, tb, tc), *_ = np.linalg.lstsq(Amat, bvec, rcond=None)
    res0 = bvec - Amat @ np.array([ta, tb, tc])
    log(f"de-tilt: rim plane slope {math.degrees(math.atan(math.hypot(ta, tb))):.1f}deg, "
        f"residual [{res0.min():+.2f},{res0.max():+.2f}]u")

    def detilt_p(p):
        return (p[0], p[1] - ta * (p[0] - c_local[0]) - tb * (p[2] - c_local[1]), p[2])

    def detilt_n(n):
        v3 = np.array([n[0] + ta * n[1], n[1], n[2] + tb * n[1]])
        return (v3 / (np.linalg.norm(v3) or 1.0)).tolist()

    dV2 = np.array([detilt_p(p) for p in dV])
    dN2 = [detilt_n(n) for n in dN]
    rim2 = [detilt_p(p) for p in rim]
    return dict(read_blocks=read_blocks, dV=dV, dU=dU, dN=dN, dT=dT, dtri=dtri,
                dtopo=dtopo, d_edge=d_edge, blob=blob, rim=rim, rim_set=rim_set,
                apertures=apertures, ensemble_apertures=ensemble_apertures,
                sweep=sweep, oV=oV, oN=oN, otris=otris, c_local=c_local,
                r_rim=r_rim, ta=ta, tb=tb, dV2=dV2, dN2=dN2, rim2=rim2)


def _plug_chart_ok(pcols, prows, own_cells=()) -> bool:
    """THE PLUG-CHART GATE: an aperture plug continues its collar's rock chart, so its chart columns and rows (at
    :data:`ROCK_CHART_PHASE`) must sit in painted rock -- the July band :data:`PLUG_CHART_BAND` (grass-world rock,
    measured on Daguerreo) OR the band the donor's OWN rock occupies, ``own_cells`` = its rock vertices' (col, row).
    Rock is painted per biome (grass rock cols 6-10 rows 7-11, desert 7-12 / 2-6, snow -1..3 / 1-5), so a snow
    massif's plug is lawful in snow rock and nowhere in the grass band (mountaindonors/INLET.md, round 2)."""
    (c0, c1), (r0, r1) = PLUG_CHART_BAND
    if min(pcols) >= c0 and max(pcols) <= c1 and min(prows) >= r0 and max(prows) <= r1:
        return True
    if not own_cells:
        return False
    oc = [c for c, _ in own_cells]
    orow = [r for _, r in own_cells]
    return min(pcols) >= min(oc) and max(pcols) <= max(oc) and min(prows) >= min(orow) and max(prows) <= max(orow)


def _tri_ny(p0, p1, p2) -> float:
    """The unit geometric normal's y of a tri (its winding, as the engine's ground query reads it); 0 when degenerate."""
    import numpy as np
    n = np.cross(np.asarray(p1, float) - np.asarray(p0, float), np.asarray(p2, float) - np.asarray(p0, float))
    L = float(np.linalg.norm(n))
    return float(n[1]) / L if L > 1e-12 else 0.0


def _stock_down_keys(donor_tris, dV, dtri, carried) -> dict:
    """THE STOCK NEAR-VERTICAL DOWN FACE (mountaindonors/STEP.md, round 2): the carried donor tris that ALREADY faced down
    at home (the raw stock winding, before de-tilt) and only by a hair, ``ny >= -MTN_STOCK_DOWN_NY``: near-vertical
    walls the shipping map holds 55 of on disc 1 (downface_census.py), comp10's two among them. Keyed by the carried
    corner positions, so a later pass that moves a corner drops the exemption. -> ``{key: home ny}``."""
    out = {}
    for t in donor_tris:
        ny = _tri_ny(*(dV[i] for i in dtri[t]))
        if -MTN_STOCK_DOWN_NY <= ny < 0:
            out[tuple(sorted(kk3(p) for p in carried[t]))] = ny
    return out


def _count_down(new_parents, stock_down, *, log=print):
    """The mountain gate's down-face count -> ``(down, exempted)``. A new tri facing down counts, unless it is a verbatim
    carried tri (``fam == "mountain"``) that faced down at home by a hair (``stock_down``) and still does so only by a
    hair as carried: stock geometry, not a flip the carve made. A tri the carry FLIPPED (up at home) is never in
    ``stock_down``, so it always counts; so does any steeper stock overhang."""
    down = exempt = 0
    for corners, _, fam in new_parents:
        ny = _tri_ny(*(p[:3] for p in corners))
        if ny >= 0:
            continue
        home = stock_down.get(tuple(sorted(kk3(p[:3]) for p in corners))) if fam == "mountain" else None
        if home is not None and ny >= -MTN_STOCK_DOWN_NY:
            exempt += 1
            log(f"  stock near-vertical down face kept: home ny {home:.4f}, carried ny {ny:.4f} at "
                f"({corners[0][0]:.1f},{corners[0][2]:.1f})")
            continue
        down += 1
    return down, exempt


def _strip_dispatch(idall_f) -> float:
    """THE DONOR-DISPATCH STRIP for one carried IDALL: keep the topograph and flags, drop the donor's event
    and area bits (entrance tiles, the camera place bucket -- meaningless and hazardous on a kit island).
    EXCEPT an IDALL the engine's ground query skips outright (``placement.IDALL_SKIP``: topo-62 stream
    banks at area 15 / 7, topo 59 at area 15): there the area IS the physics, and stripping it would turn
    a tri the engine never stands on into ground (THE BANK SKIP LAW). Those carry no event bits."""
    from .placement import ground_query_skips
    if ground_query_skips(idall_f):
        return float(int(round(float(idall_f))))
    d = X.decode_id(int(round(idall_f)))
    return float(X.encode_id(topograph=d["topograph"], flags=d["flags"]))


def _plan_spread(V, c, s: float):
    """THE DECLARED ``--spread`` SHAPE: positions ``V`` (N x 3) widened ``s`` times in plan about
    ``c = (x, z)``, heights kept -- what the rock-rigid gate measures a spread carry against."""
    import numpy as np
    out = np.array(V, dtype=np.float64)
    out[:, 0] = c[0] + s * (out[:, 0] - c[0])
    out[:, 2] = c[1] + s * (out[:, 2] - c[1])
    return out


def _mountain_rim_grain(B, s: float, *, log=print):
    """THE RIM GRAIN, for a widened massif (``world-mountain --spread``; the forest's own law,
    ``../canopyspread/NOTES.md``): a spread rim edge is ``s`` times its donor length, and the zip that
    bridges it grows with it (comp20 at x1.5: 10.2u chords against the 9u edge gate). Split every outer
    rim edge whose WIDENED plan length exceeds the donor's longest rim edge into equal pieces, by
    splitting the blob tri that owns it -- a planar fan from the opposite corner, position, UV and
    normal lerped along the edge, so it renders the same -- and the carried rim is never coarser than
    the donor's. Runs on the donor blob AFTER the de-tilt fit (the fit, and so the look, is unchanged);
    the new points join the rim ring, so ``--rock-height`` pins them like any rim position.

    An edge a footprint-sweep tri also touches is left whole (splitting it would T-junction the
    verbatim shingle); if it is too long the edge gate still refuses. Every per-vertex array -- the
    raw and de-tilted positions and normals, the UVs, and ``dVref`` when given (the rock-rigid gate's
    declared shape, which a ``--rock-height`` map has already set) -- extends by lerping its OWN two
    endpoint values, so a split adds nothing a map has not declared. Returns ``(B', splits)``."""
    import numpy as np
    dV, dV2, dU = B["dV"], B["dV2"], B["dU"]
    ref = B.get("dVref")
    dN, dN2, dT = list(B["dN"]), list(B["dN2"]), list(B["dT"])
    dtri, dtopo, blob = [list(t) for t in B["dtri"]], list(B["dtopo"]), set(B["blob"])
    rim = list(B["rim"])
    n0 = len(rim)
    elen = [math.hypot(rim[k][0] - rim[(k + 1) % n0][0], rim[k][2] - rim[(k + 1) % n0][2]) for k in range(n0)]
    L0 = max(elen)
    sweep_keys = [{kk3(dV[i]) for i in dtri[t]} for t in B["sweep"]]
    add_V, add_V2, add_U, add_R = [], [], [], []
    nV = len(dV)

    def pos(i):
        return dV[i] if i < nV else add_V[i - nV]

    def pos2(i):
        return dV2[i] if i < nV else add_V2[i - nV]

    def uv(i):
        return dU[i] if i < nV else add_U[i - nV]

    def rpos(i):
        return ref[i] if i < nV else add_R[i - nV]

    def lerp_n(n_a, n_b, f):                       # normals: lerped, at the first's length
        na, nb = np.asarray(n_a, dtype=np.float64), np.asarray(n_b, dtype=np.float64)
        nm = na + f * (nb - na)
        return (nm * (float(np.linalg.norm(na)) / (float(np.linalg.norm(nm)) or 1.0))).tolist()
    out_rim, splits, kept_long = [], 0, 0
    for k in range(n0):
        ka, kb = rim[k], rim[(k + 1) % n0]
        out_rim.append(ka)
        k_n = math.ceil(elen[k] * s / L0 - 1e-9)
        if k_n <= 1:
            continue
        if any(ka in sk and kb in sk for sk in sweep_keys):
            kept_long += 1
            continue
        owner = None
        for t in blob:
            tri = dtri[t]
            for a in range(3):
                b = (a + 1) % 3
                if {kk3(pos(tri[a])), kk3(pos(tri[b]))} == {ka, kb}:
                    owner = (t, a, b, 3 - a - b)
                    break
            if owner:
                break
        if owner is None:
            raise ValueError(f"rim grain: no blob tri owns the rim edge {ka} -- {kb}")
        t, a, b, c3 = owner
        tri = dtri[t]
        ia, ib, ic = tri[a], tri[b], tri[c3]
        pa, pb = np.asarray(pos(ia), dtype=np.float64), np.asarray(pos(ib), dtype=np.float64)
        qa, qb = np.asarray(pos2(ia), dtype=np.float64), np.asarray(pos2(ib), dtype=np.float64)
        ua, ub = np.asarray(uv(ia), dtype=np.float64), np.asarray(uv(ib), dtype=np.float64)
        chain = [ia]
        for j in range(1, k_n):
            f = j / k_n
            add_V.append(pa + f * (pb - pa))
            add_V2.append(qa + f * (qb - qa))
            add_U.append(ua + f * (ub - ua))
            if ref is not None:
                ra, rb = np.asarray(rpos(ia), dtype=np.float64), np.asarray(rpos(ib), dtype=np.float64)
                add_R.append(ra + f * (rb - ra))
            dN.append(lerp_n(dN[ia], dN[ib], f))
            dN2.append(lerp_n(dN2[ia], dN2[ib], f))
            dT.append(list(dT[ia]))
            chain.append(nV + len(add_V) - 1)
        chain.append(ib)
        pieces = [[chain[j], chain[j + 1], ic] for j in range(k_n)]      # a->b order keeps the winding
        dtri[t] = [None, None, None]
        for slot, v in ((a, pieces[0][0]), (b, pieces[0][1]), (c3, ic)):
            dtri[t][slot] = v
        for pc in pieces[1:]:
            tri2 = [None, None, None]
            tri2[a], tri2[b], tri2[c3] = pc
            dtri.append(tri2)
            dtopo.append(dtopo[t])
            blob.add(len(dtri) - 1)
        mids = [kk3(add_V[i - nV]) for i in chain[1:-1]]
        same_dir = kk3(pa) == ka
        out_rim.extend(mids if same_dir else mids[::-1])
        splits += 1
    if not splits:
        return B, 0
    dV_ = np.vstack([dV, np.array(add_V)])
    # rim2 stays the donor's: it only seats the massif (the median rim height), and a split must not move the seat
    B2 = dict(B, dV=dV_, dV2=np.vstack([dV2, np.array(add_V2)]), dU=np.vstack([dU, np.array(add_U)]),
              dN=dN, dN2=dN2, dT=dT, dtri=dtri, dtopo=dtopo, blob=blob, rim=out_rim, rim_set=set(out_rim))
    if ref is not None:
        B2["dVref"] = np.vstack([np.asarray(ref, dtype=np.float64), np.array(add_R)])
    d_edge = defaultdict(list)
    for t, idx in enumerate(dtri):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            d_edge[tuple(sorted((kk3(dV_[idx[a]]), kk3(dV_[idx[b]]))))].append(t)
    B2["d_edge"] = d_edge
    log(f"rim grain: {splits} rim edge(s) split to the donor's grain ({L0:.1f}u); rim ring {n0} -> "
        f"{len(out_rim)} positions" + (f"; {kept_long} long edge(s) left whole beside a sweep shingle"
                                         if kept_long else ""))
    return B2, splits


def _rock_height_map(B, s: float, *, rock_topos, log=print):
    """THE DECLARED ROCK HEIGHT (``world-mountain --rock-height``; terrain study X1, in-game
    passed to x2.0): stretch the carried rock pure-Y about its pinned rim, UV carried --
    ``y' = b(x,z) + s (y - b(x,z))`` on every FREE rock position, in the de-tilted donor frame.

    PINNED (never moves): the blob rim, every aperture ring, and every rock position the rock
    shares with non-rock carried geometry (an alcove floor, an enclosed ledge) or with the
    donor's Object. ``b`` is the least-squares plane through the pinned positions plus an
    inverse-distance blend of their residuals, so it equals the height at every pin: the rim,
    the plugs, the apron and the zip are untouched by construction (the Uaho build pins exactly
    the 30 positions the in-game round pinned). ``b`` is a function of plan position only, so
    coincident entries (one weld) map to one point. Normals take the map's inverse transpose.

    REFUSES a donor carrying geometry on its face that does not weld to the rock -- a
    footprint sweep (loose shingles, a mouth lining) or an ensemble aperture (falls / river
    riding the face, the horseshoe): neither would follow the stretch.

    Returns ``(dV2, dN2, dVref, report)``: the stretched de-tilted arrays, and the raw-frame
    REFERENCE shape the rock-rigid gate measures against, so a deformation the map does not
    declare still trips :data:`MTN_ROCK_RIGID`."""
    import numpy as np
    if not 1.0 <= s <= MTN_ROCK_HEIGHT_MAX:
        raise ValueError(f"--rock-height {s:g} is outside 1.0..{MTN_ROCK_HEIGHT_MAX:g}: x{MTN_ROCK_HEIGHT_MAX:g} "
                         f"is the tallest stretch seen in game (terrain study X1); lower is untested")
    if B["ensemble_apertures"] or B["sweep"]:
        raise ValueError(f"--rock-height refused: this massif carries geometry on its face that is not "
                         f"welded to the rock ({len(B['ensemble_apertures'])} falls/river mouth(s), "
                         f"{len(B['sweep'])} loose footprint tris); a height stretch would leave it behind. "
                         f"It is proven on rock-only massifs (Uaho; the crag and comp20 share its structure)")
    dV, dV2, dN2, dtri, dtopo = B["dV"], B["dV2"], B["dN2"], B["dtri"], B["dtopo"]
    ROCK = frozenset(rock_topos)
    rock = [t for t in B["blob"] if dtopo[t] in ROCK]
    rock_pos = {kk3(dV[i]) for t in rock for i in dtri[t]}
    other_pos = {kk3(dV[i]) for t in B["blob"] if dtopo[t] not in ROCK for i in dtri[t]}
    ring = set(B["rim"]) | {p for r in B["apertures"] for p in r}
    obj_pos = {kk3(p) for p in B["oV"]} if B["oV"] is not None else set()
    pinned = rock_pos & (other_pos | ring | obj_pos)
    if not pinned:
        raise ValueError("--rock-height: the rock has no pinned rim to stretch about")
    at = {}                                        # one de-tilted position per pinned key
    for t in B["blob"]:
        for i in dtri[t]:
            k = kk3(dV[i])
            if k in pinned and k not in at:
                at[k] = dV2[i]
    P = np.array([at[k] for k in sorted(at)])
    A = np.c_[P[:, 0], P[:, 2], np.ones(len(P))]
    coef, *_ = np.linalg.lstsq(A, P[:, 1], rcond=None)
    res = P[:, 1] - A @ coef

    def b(x, z):
        d2 = (P[:, 0] - x) ** 2 + (P[:, 2] - z) ** 2
        plane = coef[0] * x + coef[1] * z + coef[2]
        if d2.min() < 1e-12:
            return float(plane + res[int(d2.argmin())])
        w = 1.0 / d2
        return float(plane + (w * res).sum() / w.sum())

    h = 1e-3
    out_V, out_N, ref = dV2.copy(), [list(n) for n in dN2], dV.copy()
    moved = {}
    for t in rock:
        for i in dtri[t]:
            k = kk3(dV[i])
            if k in pinned:
                continue
            if k not in moved:
                x, y, z = dV2[i]
                bb = b(x, z)
                bx_ = (b(x + h, z) - b(x - h, z)) / (2 * h)
                bz_ = (b(x, z + h) - b(x, z - h)) / (2 * h)
                moved[k] = (y + (s - 1.0) * (y - bb), (1 - s) * bx_, (1 - s) * bz_, y)
            y_new, a_, c_, _ = moved[k]
            dy = y_new - dV2[i][1]
            out_V[i][1] = y_new
            ref[i][1] = dV[i][1] + dy                  # the raw frame's declared shape (de-tilt is a y shear)
            nx, ny, nz = dN2[i]                        # J = [[1,0,0],[a,s,c],[0,0,1]] -> n' ~ J^-T n
            m = np.array([nx - a_ * ny / s, ny / s, nz - c_ * ny / s])
            out_N[i] = (m * (math.sqrt(nx * nx + ny * ny + nz * nz) / (np.linalg.norm(m) or 1.0))).tolist()
    for t in rock:                                     # orientation: det J = s > 0, enforced anyway
        p0 = [dV2[i] for i in dtri[t]]
        p1 = [out_V[i] for i in dtri[t]]
        n0 = np.cross(p0[1] - p0[0], p0[2] - p0[0])
        n1 = np.cross(p1[1] - p1[0], p1[2] - p1[0])
        if np.sign(n0[1]) != np.sign(n1[1]) or np.linalg.norm(n1) < 2e-4:
            raise ValueError("--rock-height flipped or collapsed a rock tri (the rim pin sheared it)")
    report = {"scale": s, "pinned": len(pinned), "free": len(moved),
              "rise_max": round(max((v[0] - v[3] for v in moved.values()), default=0.0), 3)}
    log(f"rock height x{s:g}: {report['free']} rock positions stretched about {report['pinned']} pinned "
        f"(rim + welds + apertures; plane tilt {math.degrees(math.atan(math.hypot(coef[0], coef[1]))):.1f}deg), "
        f"tallest rise +{report['rise_max']:.2f}u")
    return out_V, out_N, ref, report


def carve_mountain(soup, *, center=None, near=None, donor=MOUNTAIN_DONOR,
                   rock_topos=MOUNTAIN_ROCK_TOPOS, alcove="auto", clear=MTN_CLEAR,
                   scan_band=None, gblend=MTN_GBLEND, search_radius=10, search_step=2,
                   scan_cutoff=60, ground: str = "grass", disc: int = 1, game=None,
                   max_apron_lift=None, foot_course_rects=None, rock_height: float = 1.0,
                   rot_deg=None, spread: float = 1.0, log=print) -> dict:
    """Carry a REAL rock massif (largest ``rock_topos`` component + enclosed raised tris
    + optional alcove floor + Object-aperture plugs) verbatim onto the island at
    ``center`` (exact placement, rotation 0) or the best lawful placement scanned around
    ``near`` (exact 90-deg rotations as fallbacks -- rotation keeps UVs verbatim, det +1
    keeps winding). A faithful port of ``studies/overworld-topography/massif_carry.py``
    (the in-game-approved Uaho carry, 2026-07-13): rock stays RIGID (de-tilt affine + DY
    only), the grass apron rises to meet the rigid rim over ``gblend``, hole carve +
    minimal-total-chord DP zip + apron normal re-smooth, then the study's full gate set.

    ``donor`` is one block ``(bx, by)`` or a list of blocks (a real massif may straddle
    a border -- the crag spans (10,5)+(10,6)); the blob builds on the merged world-frame
    bytes. The TARGET side sizes itself automatically: a blob that fits one block
    (``2*(r_rim + band) <= 64``) runs the proven single-block pipeline byte-identically;
    a bigger blob works over the minimal SPAN of deployed blocks covering its footprint
    (every span block must hold a deployed override), with new tris split at 64u borders
    (:func:`split_borders8`) and the apron taper applied at the span's OUTER borders
    only -- internal borders weld through the per-POSITION lift.

    Massif rock classifies from the donor's bytes by ``rock_topos`` (49/7/62) --
    deliberately distinct from the coastal topo-58 ``"rock"`` fam in
    :func:`soup_from_blocks`. ``alcove="auto"`` applies :data:`UAHO_ALCOVE` for the Uaho
    donor and nothing for any other; pass ``((x0, x1), (z0, z1), y_min)`` in the FIRST
    donor block's LOCAL frame to hand-tune a new donor (the aperture-plug path needs the
    donor's own anatomy pass first -- see the studies README). An optional fourth element
    names the floor's topographs, default ``(0,)`` (grass): a snow massif's inlet floor is
    ``(27,)`` (THE INLET FLOOR, ``studies/terrain-malleability/mountaindonors/INLET.md``).

    ``ground`` picks the bench's walkable ground family (:data:`grassland.GROUNDS` --
    the byte-measured TRANSLATION LAWS): the plain-ground classification, the zip
    annulus's mains UVs + topograph, and the outside-the-rim probe all speak that
    family. ``"grass"`` is the bit-frozen identity (the Uaho acceptance).

    ``rock_height`` (1.0..:data:`MTN_ROCK_HEIGHT_MAX`) stretches the carried rock pure-Y
    about its pinned rim before it is seated (:func:`_rock_height_map`, terrain study X1); the
    rock-rigid gate then measures the carry against that DECLARED shape. 1.0 = byte-identical.

    ``rot_deg`` turns the massif to ANY angle about its centre (degrees; positive is clockwise
    seen from above, east toward south, as the quarter-turn scan's +90): exact with ``center``, the only angle the ``near``
    scan tries. Rotation about Y keeps every UV verbatim and cannot leave the texture
    envelope (uvclass census); the grass stays on its lattice and the zip is minted fresh,
    so the gates judge the seam. A multiple of 90 takes the exact quarter-turn path, so
    ``rot_deg=0`` is byte-identical to the default ``center`` carry. ``None`` = the four
    quarter turns (scan) / 0 (exact), as before.

    ``spread`` (1.0..:data:`MTN_SPREAD_MAX`) scales the whole carry ``spread`` times wider in
    plan about the blob centre, heights kept: the massif twin of ``world-forest --spread``.
    It rides the one donor-to-world map (``rot_pt``: scale, then turn), so the rock, the rim,
    the plugs and any ensemble part move alike and every weld holds; normals take the
    inverse transpose (nx/s, ny, nz/s) at their original length; UVs and topographs stay the
    donor's. The rock-rigid gate measures against the plan-scaled donor (the declared
    shape). With ``rock_height`` equal to it, the massif scales uniformly. 1.0 = byte-identical.

    Returns ``{"changed", "center", "rot", "drop", "report"}``; raises ``ValueError`` on
    any gate."""
    import numpy as np

    gspec = G.GROUNDS[ground]
    g_topo = gspec["topo"]
    g_du, g_dv = gspec["mains_du"], gspec["mains_dv"]
    donor_blocks = _norm_donor_blocks(donor)
    if alcove == "auto":
        alcove_box = UAHO_ALCOVE if donor_blocks == [MOUNTAIN_DONOR] else None
    else:
        alcove_box = alcove
    SCAN_BAND = (clear + 4.0) if scan_band is None else scan_band
    ROCK = frozenset(rock_topos)
    SPREAD = float(spread)
    if not (math.isfinite(SPREAD) and 1.0 <= SPREAD <= MTN_SPREAD_MAX):
        raise ValueError(f"--spread {spread:g} is outside 1.0..{MTN_SPREAD_MAX:g} (x{MTN_SPREAD_MAX:g} is the "
                         f"widest massif seen in game: terrain study round 20)")

    # THE DONOR-DISPATCH STRIP: a carried IDALL keeps its topograph + flags but drops the
    # donor's event/area bits -- those are DISPATCH CONTEXT (area feeds the overworld
    # camera's place bucket via w_cameraArea2Place -- Uaho's baked area=63 is bucket 2 =
    # cameraDistance 6000, the alcove zoom-out quirk -- and event 1-3 marks a PLACE
    # ENTRANCE tile that fires the world .eb), meaningless and hazardous on a custom
    # island. The kit's own synthetic emitters default to area=0/event=0.
    def strip_dispatch(idall_f):
        return _strip_dispatch(idall_f)

    # ---- 1. the donor blob ----------------------------------------------------------------
    B = _mountain_blob(donor_blocks, rock_topos=ROCK, alcove_box=alcove_box,
                       disc=disc, game=game, log=log)
    dVref, rh = B["dV"], None                  # the rock-rigid gate's reference: the donor ...
    if rock_height != 1.0:                     # ... or its declared --rock-height stretch
        _V2, _N2, dVref, rh = _rock_height_map(B, float(rock_height), rock_topos=ROCK, log=log)
        B = dict(B, dV2=_V2, dN2=_N2)
    rim_splits = 0
    if SPREAD > 1.0:                           # THE RIM GRAIN: never a rim coarser than the donor's -- AFTER
        # the height map, so it pins the donor's own rim (X1's map, bit for bit); the new points sit between pins
        B, rim_splits = _mountain_rim_grain(dict(B, dVref=dVref), SPREAD, log=log)
        dVref = B["dVref"]
    dV, dU, dN, dT = B["dV"], B["dU"], B["dN"], B["dT"]
    dtri, dtopo, d_edge = B["dtri"], B["dtopo"], B["d_edge"]
    blob, rim, rim_set, apertures = B["blob"], B["rim"], B["rim_set"], B["apertures"]
    ensemble_apertures = B["ensemble_apertures"]
    sweep = B["sweep"]
    oV, oN, otris = B["oV"], B["oN"], B["otris"]
    c_local, r_rim, ta, tb = B["c_local"], B["r_rim"], B["ta"], B["tb"]
    dV2, dN2, rim2 = B["dV2"], B["dN2"], B["rim2"]
    if SPREAD != 1.0:                          # ... widened in plan by the declared --spread
        dVref = _plan_spread(dVref, c_local, SPREAD)
        log(f"spread x{SPREAD:g}: the carry is {SPREAD:g} times wider in plan about its centre "
            f"(radius {r_rim:.1f} -> {r_rim * SPREAD:.1f}u), heights kept")
    r_rim = r_rim * SPREAD                     # the PLACED footprint sizes the span (x1.0: unchanged)

    def detilt_p(p):
        return (p[0], p[1] - ta * (p[0] - c_local[0]) - tb * (p[2] - c_local[1]), p[2])

    def detilt_n(n):
        v3 = np.array([n[0] + ta * n[1], n[1], n[2] + tb * n[1]])
        return (v3 / (np.linalg.norm(v3) or 1.0)).tolist()

    # ---- 2. the target span + the bench arrays -------------------------------------------
    seed_pt = center if center is not None else near
    if seed_pt is None:
        raise ValueError("give center= (exact) or near= (scan)")
    CX, CZ = float(seed_pt[0]), float(seed_pt[1])
    seed_blk = (int(math.floor(CX / BLOCK)), int(math.floor(-CZ / BLOCK)))
    half = r_rim + SCAN_BAND + 2.0

    def rect(h):
        sx0 = int(math.floor((CX - h) / BLOCK))
        sx1 = int(math.floor((CX + h) / BLOCK))
        sy0 = int(math.floor(-(CZ + h) / BLOCK))
        sy1 = int(math.floor(-(CZ - h) / BLOCK))
        return [(sbx, sby) for sby in range(sy0, sy1 + 1)
                for sbx in range(sx0, sx1 + 1)]
    # THE CONTINENT ROUTE (west-seam R5, studies/overworld-topography/west-seam-continent/R5-UAHO-BENCH.md):
    # the single-block pipeline loads ONLY the seed block, so its borders must face open ocean (a small
    # kit island). On a continent they weld to DEPLOYED neighbours the span never loads, and an apron
    # lift reaching a border split the weld there (Uaho at the R4 slot: 8 new once-edges on x=1472).
    # A deployed neighbour inside the apron reach therefore routes a small donor to the multi-block
    # span -- which loads it and lifts per POSITION on both sides -- whenever that span's core rect is
    # fully covered. Otherwise (the Uaho identity bench: no neighbour in the soup) the single-block
    # pipeline runs byte-frozen as before.
    nb_deployed = sorted(b for b in rect(r_rim + gblend + 2.0)
                         if b != seed_blk and b in soup["blocks"])
    route = (2.0 * half <= BLOCK and bool(nb_deployed)
             and all(b in soup["blocks"] for b in rect(half)))
    if 2.0 * half <= BLOCK and not route:
        # the proven single-block pipeline (byte-frozen -- the Uaho identity acceptance)
        span = [seed_blk]
    else:
        if route:
            log(f"single-block-sized blob beside deployed neighbour block(s) {nb_deployed} inside "
                f"the apron reach: the MULTI-block span (welds per position across their borders)")
        # the CORE rect (rim + band) must be fully covered -- the hole/zip live there.
        # Around it, widen the span with every PRESENT block of the APRON rect (rim +
        # gblend): the lift taper only fires at borders facing non-span blocks, and a
        # rim within gblend of such a border starves the apron (the horseshoe's 0.59-ny
        # zip bank). Present neighbours weld through the per-POSITION lift; absent ones
        # (true ocean, no twin verts) keep the taper, which is then exactly right.
        core = rect(half)
        missing = [b for b in core if b not in soup["blocks"]]
        if missing:
            raise CarveRefused("blocks", f"the massif footprint around ({CX:.0f},{CZ:.0f}) needs "
                               f"deployed Terrain overrides on blocks {sorted(core)}, but "
                               f"{sorted(missing)} have none -- mint a bigger island first",
                               [_block_mid(b) for b in sorted(missing)],
                               detail=f"{len(missing)} block{'s' if len(missing) != 1 else ''} with no island")
        wide = rect(r_rim + gblend + 2.0)
        span = sorted(set(core) | {b for b in wide if b in soup["blocks"]})
        log(f"multi-block span {span}: the blob (radius {r_rim:.1f}u) needs "
            f"{2 * half:.0f}u of covered core ground")
        # the placement/bounds rect stays the fully-covered CORE
        span_rect = core
    if len(span) == 1:
        span_rect = span
    missing = [b for b in span if b not in soup["blocks"]]
    if missing:
        raise CarveRefused("blocks", f"the massif footprint around ({CX:.0f},{CZ:.0f}) needs deployed "
                           f"Terrain overrides on blocks {sorted(span)}, but "
                           f"{sorted(missing)} have none -- mint a bigger island first",
                           [_block_mid(b) for b in sorted(missing)],
                           detail=f"{len(missing)} block{'s' if len(missing) != 1 else ''} with no island")
    span = sorted(span)
    span_set = set(span)
    SPX0, SPX1 = (BLOCK * min(b[0] for b in span_rect),
                  BLOCK * (max(b[0] for b in span_rect) + 1))
    SPZ0, SPZ1 = (-BLOCK * (max(b[1] for b in span_rect) + 1),
                  -BLOCK * min(b[1] for b in span_rect))
    gpos, gtris, gnrm, guv, gtan, gblk = [], [], [], [], [], []
    for blk in span:
        bm0 = soup["blocks"][blk]
        sbx, sby = blk
        vbase = len(gpos)
        for v in bm0.verts:
            gpos.append([v[0] + BLOCK * sbx, v[1], v[2] - BLOCK * (sby + 1) + BLOCK])
        gnrm.extend(list(n) for n in bm0.chan_arrays[X.CH_NRM])
        guv.extend(list(u) for u in bm0.chan_arrays[X.CH_UV])
        gtan.extend(list(t) for t in bm0.chan_arrays[X.CH_TAN])
        for tri in bm0.tris:
            gtris.append([i + vbase for i in tri])
            gblk.append(blk)
    gtopo = [X.decode_id(int(round(gtan[t[0]][0])))["topograph"] for t in gtris]

    # ---- 2b. THE MINT-HOLE PATCH: detect every once-edge 3-cycle above sea level and
    # fill it with its neighbors' own language (uv = the centroid cell's own decoded
    # mains mapping at the corners; normal/id from a coincident entry). A mint from the
    # current kit ships hole-free (island.py's ring-conformity fix) so this is a genuine
    # no-op there -- it stays because the in-game-approved bench predates the fix, and
    # the identity acceptance replays that exact input.
    eu_h = Counter()
    for tri in gtris:
        w = [gpos[i] for i in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu_h[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
    oh = [e for e, n in eu_h.items() if n == 1
          and e[0][1] > 0.5 and e[1][1] > 0.5]
    adj_h = defaultdict(set)
    for a, b in oh:
        adj_h[a].add(b)
        adj_h[b].add(a)
    holes3 = set()
    for a in adj_h:
        for b in adj_h[a]:
            for c in adj_h[b]:
                if c != a and c in adj_h[a]:
                    holes3.add(tuple(sorted((a, b, c))))
    ent_at = defaultdict(list)                             # position -> vertex entries
    for tdx, tri in enumerate(gtris):
        for i in tri:
            ent_at[kk3(gpos[i])].append((tdx, i))
    cell4 = lambda x, z: (math.floor(x / 4.0), math.floor(z / 4.0))  # noqa: E731
    n_orig = len(gtris)

    def decode_cell_early(ccell):
        """The cell's (quad, ori) from any kept tri that exact-matches the mains language."""
        for tdx in range(n_orig):
            tri = gtris[tdx]
            tc = np.mean([gpos[j] for j in tri], axis=0)
            if cell4(tc[0], tc[2]) != ccell:
                continue
            for q in [(u2, v2) for u2 in (0, 1) for v2 in (0, 1)]:
                for o in (0, 90, 180, 270):
                    err = 0.0
                    for j in tri:
                        mu, mv = G.mains_uv(gpos[j][0], gpos[j][2], ccell, q, o)
                        err = max(err, abs(mu + g_du - guv[j][0]),
                                  abs(mv + g_dv - guv[j][1]))
                    if err < 1e-4:
                        return q, o
        return None

    patched_holes = 0
    for cyc in sorted(holes3):
        # a real hole has NO existing face spanning its three positions (a legally
        # detached tri's own edges also chain into a 3-cycle -- that is not a hole)
        t_sets = [set(t2 for t2, _ in ent_at[p]) for p in cyc]
        if t_sets[0] & t_sets[1] & t_sets[2]:
            continue
        cen = np.mean([list(p) for p in cyc], axis=0)
        ccell = cell4(cen[0], cen[2])
        # uv = the centroid cell's OWN decoded mapping evaluated at the corners -- the
        # mint's convention for cell-straddling tris (corner-copies from coincident
        # entries mix NEIGHBORING cells' mappings when the hole straddles a cell edge).
        qo = decode_cell_early(ccell)
        if not qo:
            raise ValueError(f"mint-hole cell {ccell} has no decodable mains tri")
        q, o = qo
        a3, b3, c3 = (np.array(p) for p in cyc)
        order = cyc if np.cross(b3 - a3, c3 - a3)[1] > 0 else (cyc[0], cyc[2], cyc[1])
        new_idx = []
        for p in order:
            pick = ent_at[p][0][1]                         # normal/id from any twin entry
            gpos.append(list(gpos[pick]))
            gnrm.append(list(gnrm[pick]))
            mu, mv = G.mains_uv(p[0], p[2], ccell, q, o)
            guv.append([mu + g_du, mv + g_dv])
            gtan.append(list(gtan[pick]))
            new_idx.append(len(gpos) - 1)
        gtris.append(new_idx)
        gblk.append((int(math.floor(cen[0] / BLOCK)), int(math.floor(-cen[2] / BLOCK))))
        gtopo.append(X.decode_id(int(round(gtan[new_idx[0]][0])))["topograph"])
        patched_holes += 1
        log(f"mint hole PATCHED at ({cen[0]:.1f},{cen[2]:.1f}) y {cen[1]:.1f} "
            f"(cell {ccell} quad {q} ori {o})")
    lo_u, hi_u = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
    plain = []
    for tdx, tri in enumerate(gtris):
        plain.append(gtopo[tdx] == g_topo and
                     all(lo_u - 0.02 <= guv[i][0] - g_du <= hi_u + 0.02 for i in tri))
    tri_c = [((gpos[tri[0]][0] + gpos[tri[1]][0] + gpos[tri[2]][0]) / 3,
              (gpos[tri[0]][2] + gpos[tri[1]][2] + gpos[tri[2]][2]) / 3)
             for tri in gtris]
    nonplain_c = np.array([tri_c[t] for t in range(len(gtris)) if not plain[t]])
    # THE INTERIOR SEAT (west-seam R5, studies/overworld-topography/west-seam-continent/R5-UAHO-BENCH.md):
    # a span with NO non-plain tri is the interior lawn of a larger kit landmass -- a small donor's
    # single-block span on a continent -- not a malformed bench. Clearance to the coast is unbounded
    # inside it, so the scan ranks candidates by distance to the requested seat instead (rot 0 keeps
    # the same 0.75u preference). A span with ANY non-plain tri runs the clearance ranking unchanged.
    interior = not len(nonplain_c)
    if interior:
        log(f"block span {span} has no non-plain tris: an INTERIOR seat -- clearance unbounded "
            f"within the span; candidates rank by distance to the requested seat")

    def clr(d):
        return "unbounded" if math.isinf(d) else f"{d:.1f}u"
    log(f"bench: {len(gtris)} tris ({sum(plain)} plain-grass mains)")
    # PRISTINE once-edge baseline, captured BEFORE any mutation: computed after the lift
    # it cancels self-consistent weld splits and the crack gate goes blind
    eu0 = Counter()
    for tri in gtris:
        w = [gpos[i] for i in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu0[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
    once0 = {e for e, n in eu0.items() if n == 1}

    # ROT counts quarter turns: an int takes the exact swap (the in-game-approved bytes); a
    # float is a free angle (``rot_deg``), the same rotation by cos/sin -- k = 1 gives (dz, -dx).
    # THE ONE DONOR-TO-WORLD MAP: every carried position (rock, rim, plugs, ensemble parts) and
    # every placement test goes through here, so ``spread`` scales them all alike -- scale, then
    # turn -- and x1.0 skips the multiply (the frozen bytes)
    def rot_pt(p, k):
        dx3, dz3 = p[0] - c_local[0], p[2] - c_local[1]
        if SPREAD != 1.0:
            dx3, dz3 = dx3 * SPREAD, dz3 * SPREAD
        if isinstance(k, int):
            for _ in range(k):
                dx3, dz3 = dz3, -dx3
        else:
            c_, s_ = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
            dx3, dz3 = c_ * dx3 + s_ * dz3, -s_ * dx3 + c_ * dz3
        return (c_local[0] + dx3, p[1], c_local[1] + dz3)

    def rot_n(n, k):
        nx, nz = n[0], n[2]
        if SPREAD != 1.0:                      # the inverse transpose of diag(s, 1, s), length kept
            L0 = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            mx, my, mz = nx / SPREAD, n[1], nz / SPREAD
            L1 = math.sqrt(mx * mx + my * my + mz * mz) or 1.0
            nx, nz, n = mx * L0 / L1, mz * L0 / L1, (n[0], my * L0 / L1, n[2])
        if isinstance(k, int):
            for _ in range(k):
                nx, nz = nz, -nx
        else:
            c_, s_ = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
            nx, nz = c_ * nx + s_ * nz, -s_ * nx + c_ * nz
        return [nx, n[1], nz]

    ROT0 = None                                # the fixed angle, in quarter turns
    if rot_deg is not None:
        _d = float(rot_deg)
        if not math.isfinite(_d):
            raise ValueError(f"rot_deg must be a finite angle, got {rot_deg!r}")
        _d %= 360.0
        ROT0 = int(_d // 90) if _d % 90.0 == 0.0 else _d / 90.0

    def in_span(ROT, gx, gz):
        """The hole band must stay inside the covered span (a mint can spill a few coast
        tris into a neighbor block the pipeline can't see)."""
        poly_pts = np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
        pp = poly_pts + np.array([gx - c_local[0], gz - c_local[1]])
        return not (pp[:, 0].min() < SPX0 + SCAN_BAND + 2 or pp[:, 0].max() > SPX1 - SCAN_BAND - 2
                    or pp[:, 1].min() < SPZ0 + SCAN_BAND + 2 or pp[:, 1].max() > SPZ1 - SCAN_BAND - 2)

    def band_offenders(ROT, gx, gz, limit=None):
        """Exact: the non-plain tris inside or near the placed rim polygon's band (their indices, at most
        ``limit``). ``world.mountainedit.footprint_preview`` is this, vectorised (and fenced against it)."""
        DXc, DZc = gx - c_local[0], gz - c_local[1]
        rp = [(p[0] + DXc, p[2] + DZc) for p in (rot_pt(q, ROT) for q in rim)]
        out = []
        for tdx, tri in enumerate(gtris):
            if plain[tdx]:
                continue
            cx2, cz2 = tri_c[tdx]
            if pip(cx2, cz2, rp) or near_poly(cx2, cz2, rp, SCAN_BAND) or any(
                    pip(gpos[i][0], gpos[i][2], rp) or
                    near_poly(gpos[i][0], gpos[i][2], rp, SCAN_BAND) for i in tri):
                out.append(tdx)
                if limit is not None and len(out) >= limit:
                    break
        return out

    def band_clean(ROT, gx, gz):
        return not band_offenders(ROT, gx, gz, limit=1)

    if center is not None:
        ROT, TX, TZ = (0 if ROT0 is None else ROT0), CX, CZ
        if not in_span(ROT, TX, TZ):
            m = SCAN_BAND + 2
            rp = [(p[0] + TX - c_local[0], p[2] + TZ - c_local[1]) for p in (rot_pt(q, ROT) for q in rim)]
            raise CarveRefused("span", f"massif at ({TX:.0f},{TZ:.0f}) leaves block span "
                               f"{span} (the working band must stay on covered ground)",
                               [(x, z) for x, z in rp if not (SPX0 + m <= x <= SPX1 - m and SPZ0 + m <= z <= SPZ1 - m)],
                               detail="its rim comes too near the edge of the deployed blocks")
        bad = band_offenders(ROT, TX, TZ, limit=12)
        if bad:
            raise CarveRefused("footprint", f"massif footprint at ({TX:.0f},{TZ:.0f}) is not clear "
                               f"plain-grass mains (band {SCAN_BAND}u)", [tri_c[t] for t in bad],
                               detail=f"it reaches {massif_ground_words(gtopo[bad[0]], ground)}")
        pp = (np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
              + np.array([TX - c_local[0], TZ - c_local[1]]))
        dmin = math.inf if interior else float(np.sqrt(((nonplain_c[:, None, :] - pp[None, :, :]) ** 2)
                                                       .sum(axis=2).min()))
        log(f"placement (exact): rot {ROT * 90:g}deg, blob centre -> ({TX},{TZ}) "
            f"(raw clearance {clr(dmin)})")
    else:
        cands = []                                         # (score, dmin, ROT, gx, gz)
        for ROT in ((0, 1, 2, 3) if ROT0 is None else (ROT0,)):
            poly_pts = np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
            for gx in range(int(CX) - search_radius, int(CX) + search_radius + 1, search_step):
                for gz in range(int(CZ) - search_radius, int(CZ) + search_radius + 1, search_step):
                    pp = poly_pts + np.array([gx - c_local[0], gz - c_local[1]])
                    if pp[:, 0].min() < SPX0 + SCAN_BAND + 2 or pp[:, 0].max() > SPX1 - SCAN_BAND - 2 \
                            or pp[:, 1].min() < SPZ0 + SCAN_BAND + 2 or pp[:, 1].max() > SPZ1 - SCAN_BAND - 2:
                        continue
                    if interior:                           # no coast: nearest the requested seat
                        cands.append((-math.hypot(gx - CX, gz - CZ) + (0.75 if ROT == 0 else 0.0),
                                      math.inf, ROT, gx, gz))
                        continue
                    # numpy prefilter: nearest non-plain centroid to any poly vertex
                    dmin = float(np.sqrt(
                        ((nonplain_c[:, None, :] - pp[None, :, :]) ** 2).sum(axis=2).min()))
                    cands.append((dmin + (0.75 if ROT == 0 else 0.0), dmin, ROT, gx, gz))
        if not cands:
            raise ValueError(f"no in-span candidate near ({CX:.0f},{CZ:.0f}) -- the blob "
                             f"(radius {r_rim:.1f}u + band {SCAN_BAND}u) does not fit "
                             f"the covered span {span}")
        cands.sort(reverse=True)
        log(f"scan: best raw clearance {clr(cands[0][1])} (rot {cands[0][2] * 90:g}deg) "
            f"of {len(cands)} in-bounds candidates")
        chosen = None
        for score, dmin, ROT, gx, gz in cands[:scan_cutoff]:
            if dmin < SCAN_BAND:
                break
            if band_clean(ROT, gx, gz):
                chosen = (ROT, gx, gz, dmin)
                break
        if not chosen:
            raise ValueError(f"no lawful placement -- best raw clearance "
                             f"{clr(cands[0][1])} vs the {SCAN_BAND}u band")
        ROT, TX, TZ, dmin = chosen
        log(f"placement: rot {ROT * 90:g}deg, blob centre -> ({TX},{TZ}) "
            f"(clearance {clr(dmin)})")
    DX, DZ = TX - c_local[0], TZ - c_local[1]
    rim_poly = [(p[0] + DX, p[2] + DZ) for p in (rot_pt(q, ROT) for q in rim)]

    # ---- 3. anchor + carry: ROCK RIGID, THE GROUND CONFORMS -----------------------------
    # THE ROCK-RIGID LAW: carried rock never deforms beyond the global affine (de-tilt +
    # DY); ALL seating deformation goes to the GRASS -- at the real donor the ground
    # RISES to meet the high foot, so the bench gets a donor-shaped apron lift (pure-Y
    # displacement of kept plain-grass verts, the proven hill-at-scale mechanism) rising
    # from bench ground to the rigid rim over gblend, tapered at block borders (a
    # displaced border vert would crack against the neighbor block's twin) AND near
    # non-plain tris (the coast band must not deform).
    rim_med = float(np.median([p[1] for p in rim2]))
    near_ys = [gpos[i][1] for tdx, tri in enumerate(gtris) if plain[tdx] for i in tri
               if not pip(gpos[i][0], gpos[i][2], rim_poly)
               and near_poly(gpos[i][0], gpos[i][2], rim_poly, clear + 3.0)]
    if not near_ys:
        raise CarveRefused("footprint", "no plain-grass ground around the rim to anchor against", [(TX, TZ)])
    ground_med = float(np.median(near_ys))
    DY = ground_med - rim_med

    # THE FOOT-COURSE WINDOW (2026-08-28, R4 takes 5-6): inside a window rect the
    # ground stays FLAT (its rim nodes leave the apron field; outside contributions
    # feather smoothly), the zip annulus emits as a synthetic ROCK FOOT COURSE (the
    # spur-graft class, massif_spur.py in-game proven), and an optional PULL steepens
    # the carried flank -- horizontal displacement toward the massif centre, full at
    # lawn height fading to zero at TOP. A donor face can be low-angle because its
    # HOME context hides it (forest at the base, rolling foothill); torn onto a flat
    # lawn it reads as walkable ground. The steepen is a DELIBERATE, gated, window-
    # scoped exception to THE ROCK-RIGID LAW, applied as a pure function of world
    # position at EVERY donor-to-world transform site (carried verts, rim nodes,
    # rim_poly, plugs, conform ring, ensemble aux) so welds and downstream geometry
    # (hole, zip, apron) stay consistent by construction. Spec per rect:
    # (x0,z0,x1,z1[,pull[,top]]). ``None`` = byte-identical legacy behavior.
    fc_rects = None
    fc_specs = []
    if foot_course_rects:
        fc_rects = []
        for _r in foot_course_rects:
            _rc = (min(_r[0], _r[2]), min(_r[1], _r[3]),
                   max(_r[0], _r[2]), max(_r[1], _r[3]))
            fc_rects.append(_rc)
            # feather only the INNER edges (the ones the massif centre lies beyond --
            # carried rock continues across them and must blend); an outer edge faces
            # open lawn where the rock terminates, and feathering it just starves the
            # pull (a ~25u window with 12u feather on all four edges has no core)
            _inner = (TX < _rc[0], TZ < _rc[1], TX > _rc[2], TZ > _rc[3] or TZ == _rc[3])
            fc_specs.append((_rc, float(_r[4]) if len(_r) > 4 else 0.0,
                             float(_r[5]) if len(_r) > 5 else ground_med + 12.0, _inner))

    def _in_fc(x, z):
        return fc_rects is not None and any(
            r[0] <= x <= r[2] and r[1] <= z <= r[3] for r in fc_rects)

    fc_steep_moved = set()

    def _fc_steep(w):
        best = 0.0
        for _rc, _pull, _top, _inner in fc_specs:
            if _pull <= 0.0 or w[1] >= _top or not (
                    _rc[0] <= w[0] <= _rc[2] and _rc[1] <= w[2] <= _rc[3]):
                continue
            # feather over 12u: the pull gradient must stay under ~0.7u per plan-u or
            # it exceeds shallow tris' own extent at the window ends and folds them
            _eds = [e for e, on in zip((w[0] - _rc[0], w[2] - _rc[1],
                                        _rc[2] - w[0], _rc[3] - w[2]), _inner) if on]
            _g = max(0.0, min(1.0, min(_eds) / 12.0)) if _eds else 1.0
            _f = max(0.0, min(1.0, (_top - w[1]) / max(1e-6, _top - ground_med)))
            best = max(best, _pull * _f * _g)
        if best <= 1e-9:
            return w
        _dx, _dz = TX - w[0], TZ - w[2]
        _L = math.hypot(_dx, _dz) or 1.0
        out = [w[0] + best * _dx / _L, w[1], w[2] + best * _dz / _L]
        fc_steep_moved.add((round(out[0], 3), round(out[2], 3)))
        return out

    def carry_vert(i):
        pr = rot_pt(dV2[i], ROT)
        return _fc_steep([pr[0] + DX, pr[1] + DY, pr[2] + DZ])

    if any(s[1] > 0 for s in fc_specs):
        # the footprint must match the steepened rim or the hole/zip span the OLD one
        rim_poly = [(_w2[0], _w2[2]) for _w2 in (
            _fc_steep([pr[0] + DX, pr[1] + DY, pr[2] + DZ])
            for pr in (rot_pt(detilt_p(q), ROT) for q in rim))]

    # NOTE: rim_nodes iterates rim_set (a set) -- CPython's set order is deterministic
    # for identical insertion sequences of identical (numeric-tuple) values, and the
    # ground_lift float accumulation below inherits that order. The in-game-approved
    # bytes were produced through this exact order; do NOT "clean this up" to sorted().
    rim_nodes = []                                         # (x, z, RIGID rim height)
    for p in rim_set:
        pr = rot_pt(detilt_p(p), ROT)
        _w2 = _fc_steep([pr[0] + DX, pr[1] + DY, pr[2] + DZ])
        rim_nodes.append((_w2[0], _w2[2], _w2[1]))
    log(f"rigid rim heights: [{min(n[2] for n in rim_nodes):.2f},"
        f"{max(n[2] for n in rim_nodes):.2f}] vs ground med {ground_med:.2f} "
        f"(the grass apron absorbs the difference over {gblend}u)")

    # THE PROFILE LAW predicate (R4 take 8): a rock foot course exists only where the
    # CARRIED massif actually rises -- the per-tri zip rise cannot tell a lawful toe
    # (tall face one course in, rim edge barely above lawn) from a CURB standing over
    # nothing (the taper arms), so the test is the carried heightfield itself: max
    # carried-vert height within 6u of the query, against lawn + MTN_FC_MIN_RISE.
    # Governs BOTH the tight hole cut and the rock-vs-grass zip emission, so the two
    # stay consistent by construction.
    _fc_rock_here = None
    if fc_rects:
        _fcg = defaultdict(list)
        for _t in blob:
            for _i in dtri[_t]:
                _w3 = carry_vert(_i)
                _fcg[(math.floor(_w3[0] / 6.0), math.floor(_w3[2] / 6.0))].append(
                    (_w3[0], _w3[1], _w3[2]))

        # THE RIM-ABOVE-LAWN test (R4 take 9): "the massif rises within 6u" also holds on a
        # taper tip whose OWN rim sits below the plateau -- a low slab beside a tall face --
        # and there take 8 minted fringe rock lying flat on the free-base dip (t673-t675,
        # the owner's "should be ground"). The nearest carried rim node must stand above
        # the lawn too; in the same predicate, so hole cut, apron hold and emission agree.
        _fcr = defaultdict(list)
        for _rn in rim_nodes:
            _fcr[(math.floor(_rn[0] / 6.0), math.floor(_rn[1] / 6.0))].append(_rn)

        def _fc_rim_above(x, z):
            _cx6, _cz6 = math.floor(x / 6.0), math.floor(z / 6.0)
            best = None
            for _gx in (_cx6 - 1, _cx6, _cx6 + 1):
                for _gz in (_cz6 - 1, _cz6, _cz6 + 1):
                    for _rn in _fcr.get((_gx, _gz), ()):
                        _d = (x - _rn[0]) ** 2 + (z - _rn[1]) ** 2
                        if best is None or _d < best[0]:
                            best = (_d, _rn[2])
            return best is None or best[1] > ground_med + MTN_FC_RIM_ABOVE

        def _fc_rises(x, z):
            _cx6, _cz6 = math.floor(x / 6.0), math.floor(z / 6.0)
            for _gx in (_cx6 - 1, _cx6, _cx6 + 1):
                for _gz in (_cz6 - 1, _cz6, _cz6 + 1):
                    for _w3 in _fcg.get((_gx, _gz), ()):
                        if (x - _w3[0]) ** 2 + (z - _w3[2]) ** 2 <= 36.0 \
                                and _w3[1] - ground_med >= MTN_FC_MIN_RISE:
                            return True
            return False

        def _fc_rock_here(x, z):
            # the hole cut + the apron hold: a POSITION's question, so the nearest rim decides
            return _fc_rim_above(x, z) and _fc_rises(x, z)
    # THE HIGH-FOOT CONFORM (2026-08-28, the R4 knoll): with ``max_apron_lift`` set, the
    # apron chases a high donor foot only this far; any outer-rim column still higher
    # CONFORMS DOWN to the capped grass instead -- the carried bottom wall row stretches
    # (uv untouched: THE WALL V CORNER-ROLE LAW -- V is a corner assignment, never f(y);
    # density varies freely), which is how the donor's own home reads there (level ground
    # meets the wall at the crease). Lifting instead minted a grass KNOLL pressed against
    # mid-wall with no transition (the owner-filed R4 defect on the (1418..1433,-469..-485)
    # arc, foot 4.3-5.1 over a 3.2 plateau). DOWN-ONLY: a LOW foot keeps its dip --
    # burying a base is stock-lawful (THE FREE-BASE LAW), and the owner passed those arcs.
    # Columns within 4u of an aperture/ensemble ring are EXEMPT (the falls-outlet weld
    # stays byte-coincident; the aux verts are ALSO adjusted through the same map, so the
    # exemption is belt and braces). ``None`` = byte-identical legacy behavior (the
    # frozen island-E/Uaho identity baselines).
    rim_adjust = {}
    adj_xz = set()
    _conform_ring_pts = []
    if max_apron_lift is not None:
        cap_y = ground_med + float(max_apron_lift)
        for _r in list(apertures or []) + list(ensemble_apertures or []):
            for _p in _r:
                _pr = rot_pt(detilt_p(_p), ROT)
                _conform_ring_pts.append(tuple(_fc_steep(
                    [_pr[0] + DX, _pr[1] + DY, _pr[2] + DZ])))
        rim_nodes = [(x, z, min(hy, cap_y)) for (x, z, hy) in rim_nodes]
    lift_nodes = rim_nodes
    if fc_rects:
        # held flat only where the massif truly rises (THE PROFILE LAW predicate):
        # a taper arm's low slab inside the window rejoins the apron field and gets
        # its lawful FREE-BASE burial (rolling ground over a low carried foot, the
        # owner-passed idiom) instead of poking bare out of a flat lawn
        lift_nodes = [n for n in rim_nodes
                      if not _in_fc(n[0], n[1]) or not _fc_rock_here(n[0], n[1])]
        log(f"foot-course window: {len(rim_nodes) - len(lift_nodes)} of "
            f"{len(rim_nodes)} rim nodes held flat (no apron)")
    # positions touched by ANY non-plain tri: the lift must be EXACTLY zero there --
    # worldmap meshes don't share vertex entries (welds = coincident positions), so a
    # lift applied to the grass-side entry but not the coast-side twin SPLITS the weld
    nonplain_xz = {(kk3(gpos[i])[0], kk3(gpos[i])[2])
                   for tdx, tri in enumerate(gtris) if not plain[tdx]
                   for i in tri}
    nonplain_pos = np.array(sorted(nonplain_xz))

    def ground_lift(px, pz, py, dnp):
        """Pure-Y apron field: 0 far away -> (rim height - ground) at the rim."""
        wsum = hsum = 0.0
        dmin2 = 1e18
        for (nx2, nz2, hy) in lift_nodes:
            dd2 = (px - nx2) ** 2 + (pz - nz2) ** 2
            dmin2 = min(dmin2, dd2)
            if dd2 > gblend * gblend:
                continue
            w = 1.0 / (dd2 + 0.04)
            wsum += w
            hsum += w * hy
        if wsum <= 0.0 or dmin2 >= gblend * gblend:
            return 0.0
        W = (1.0 - math.sqrt(dmin2) / gblend) ** 2
        # taper only at borders facing NON-SPAN blocks (an unloaded neighbor's twin
        # vert cannot receive the lift; a span neighbour's border is safe -- coincident
        # entries on both sides get the identical per-POSITION lift). For a one-block
        # span this reduces exactly to the block's four borders (the frozen baseline).
        pbx = int(math.floor(px / BLOCK))
        pby = int(math.floor(-pz / BLOCK))
        bd = 64.0
        if (pbx - 1, pby) not in span_set:
            bd = min(bd, px - BLOCK * pbx)
        if (pbx + 1, pby) not in span_set:
            bd = min(bd, BLOCK * (pbx + 1) - px)
        if (pbx, pby + 1) not in span_set:
            bd = min(bd, pz + BLOCK * (pby + 1))
        if (pbx, pby - 1) not in span_set:
            bd = min(bd, -BLOCK * pby - pz)
        bt = min(1.0, (bd - 0.5) / 3.0)
        pt = min(1.0, (dnp - 2.5) / 3.0)                   # die before the coast band
        return max(0.0, bt) * max(0.0, pt) * W * (hsum / wsum - py)

    # lift by POSITION (computed once per unique position, dnp = exact distance to the
    # nearest non-plain VERTEX position -- centroids under-measure at big coast tris),
    # then applied to EVERY coincident vertex entry so no weld can split
    cand = {}
    for tdx, tri in enumerate(gtris):
        if not plain[tdx]:
            continue
        for i in tri:
            k = kk3(gpos[i])
            if k in cand:
                continue
            dnp = math.inf if interior else float(np.sqrt(((nonplain_pos - np.array([k[0], k[2]])) ** 2)
                                                          .sum(axis=1).min()))
            cand[k] = ground_lift(k[0], k[2], gpos[i][1], dnp)  # interior: no coast band to taper before

    # THE T-JUNCTION LERP LAW (the R4 west-seam hairlines at --gblend 26): the bench
    # lattice holds T-verts -- a position lying colinear INSIDE a neighboring tri's edge
    # (split_borders8 border splits, mixed tessellation; the mint-hole patch seals the
    # 2-split kind with a degenerate sliver tri). The host edge's surface moves LINEARLY
    # between its endpoints' lifts while the T-vert's own IDW lift is nonlinear in
    # position, so at wide gblend the difference opens a sub-pixel slit and tips the
    # sliver toward vertical (the hairline-tear class, GROUND-JUNCTION SYNTHESIS).
    # Constrain each T-vert's lift to its host edge's own lerp so the vert stays ON the
    # deformed edge. Applied to the per-POSITION map, so every coincident entry still
    # moves together (the weld law); positions touched by non-plain tris keep their
    # exact-zero lift (the coast weld outranks the edge); a lattice with no T-verts in
    # reach writes nothing -- the frozen identity baselines replay byte-identical.
    tj_host = {}                                           # T-vert key -> (L2, ka, kb, t)
    if rim_nodes and cand:
        tj_pad = gblend + MTN_TJ_TOL
        tj_x0 = min(n[0] for n in rim_nodes) - tj_pad
        tj_x1 = max(n[0] for n in rim_nodes) + tj_pad
        tj_z0 = min(n[1] for n in rim_nodes) - tj_pad
        tj_z1 = max(n[1] for n in rim_nodes) + tj_pad
        tj_cell = 8.0
        tj_grid = defaultdict(list)
        for k in cand:
            if tj_x0 <= k[0] <= tj_x1 and tj_z0 <= k[2] <= tj_z1 \
                    and (k[0], k[2]) not in nonplain_xz:
                tj_grid[(math.floor(k[0] / tj_cell),
                         math.floor(k[2] / tj_cell))].append(k)
        tj_seen = set()
        for tdx, tri in enumerate(gtris):
            if not plain[tdx]:
                continue
            if max(gpos[i][0] for i in tri) < tj_x0 or \
                    min(gpos[i][0] for i in tri) > tj_x1 or \
                    max(gpos[i][2] for i in tri) < tj_z0 or \
                    min(gpos[i][2] for i in tri) > tj_z1:
                continue
            ks = [kk3(gpos[i]) for i in tri]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e = (ks[a], ks[b]) if ks[a] < ks[b] else (ks[b], ks[a])
                if e[0] == e[1] or e in tj_seen:
                    continue
                tj_seen.add(e)
                ka, kb = e
                ex, ey, ez = kb[0] - ka[0], kb[1] - ka[1], kb[2] - ka[2]
                L2 = ex * ex + ey * ey + ez * ez
                if L2 < 1e-9:
                    continue
                for gx in range(int(math.floor((min(ka[0], kb[0]) - MTN_TJ_TOL) / tj_cell)),
                                int(math.floor((max(ka[0], kb[0]) + MTN_TJ_TOL) / tj_cell)) + 1):
                    for gz in range(int(math.floor((min(ka[2], kb[2]) - MTN_TJ_TOL) / tj_cell)),
                                    int(math.floor((max(ka[2], kb[2]) + MTN_TJ_TOL) / tj_cell)) + 1):
                        for p in tj_grid.get((gx, gz), ()):
                            if p == ka or p == kb:
                                continue
                            t = ((p[0] - ka[0]) * ex + (p[1] - ka[1]) * ey
                                 + (p[2] - ka[2]) * ez) / L2
                            if t <= 0.0 or t >= 1.0:
                                continue
                            qx = ka[0] + t * ex - p[0]
                            qy = ka[1] + t * ey - p[1]
                            qz = ka[2] + t * ez - p[2]
                            if qx * qx + qy * qy + qz * qz > MTN_TJ_TOL * MTN_TJ_TOL:
                                continue
                            # a hair off a CORNER is a weld twin, not a T-vert
                            if min((p[0] - ka[0]) ** 2 + (p[1] - ka[1]) ** 2
                                   + (p[2] - ka[2]) ** 2,
                                   (p[0] - kb[0]) ** 2 + (p[1] - kb[1]) ** 2
                                   + (p[2] - kb[2]) ** 2) < 0.01:
                                continue
                            hit = (L2, ka, kb, t)
                            cur = tj_host.get(p)
                            if cur is None or hit[:3] < cur[:3]:  # tightest host wins
                                tj_host[p] = hit
    if tj_host:
        for _ in range(8):                                 # chained T-verts: fixpoint
            tj_delta = 0.0
            for p in sorted(tj_host):
                L2, ka, kb, t = tj_host[p]
                la, lb = cand[ka], cand[kb]
                nv = la + t * (lb - la)
                tj_delta = max(tj_delta, abs(nv - cand[p]))
                cand[p] = nv
            if tj_delta < 1e-12:
                break
        log(f"apron T-junction lerp: {len(tj_host)} T-vert position(s) pinned to "
            f"their host edge")
    lift_of = {}
    lift_max = 0.0
    for i in range(len(gpos)):
        lf = cand.get(kk3(gpos[i]), 0.0)
        if abs(lf) > 1e-6:
            gpos[i][1] += lf
            lift_of[i] = lf
            lift_max = max(lift_max, abs(lf))
    log(f"ground apron: {len(lift_of)} vertex entries lifted "
        f"({sum(1 for v in cand.values() if abs(v) > 1e-6)} positions, "
        f"max {lift_max:.2f}u)")

    # ---- 3b. hole carve (on the LIFTED bench; the drop test is plan-only) ---------------
    # THE PROFILE LAW (R4 take 8): inside a foot-course window, where the massif truly
    # rises, the hole hugs the rim -- stock's base course CONTINUES the face above it
    # down to the lawn (926 stock feet: first-8u climb p25-p75 = 42-53 deg, kink
    # centered +1.5), while the standard clear plus the 4u ground tessellation parks
    # the contact ~6.7u out and the toe reads as a 21-36 deg walkable skirt under a
    # 55-61 deg face (the owner-rejected shape, takes 0-7). Where the massif does NOT
    # rise (taper arms, shallow benches) the standard clear stays, so the grass zip
    # has room to ramp gently instead of minting a steep grass lip.
    drop = set()
    for tdx, tri in enumerate(gtris):
        for i in tri:
            _cl = MTN_FC_CLEAR if (
                _fc_rock_here is not None
                and _in_fc(gpos[i][0], gpos[i][2])
                and _fc_rock_here(gpos[i][0], gpos[i][2])) else clear
            if pip(gpos[i][0], gpos[i][2], rim_poly) or \
                    near_poly(gpos[i][0], gpos[i][2], rim_poly, _cl):
                drop.add(tdx)
                break
    fams = Counter(gtopo[t] for t in drop)
    log(f"bench tris dropped: {len(drop)} (topos {dict(fams)})")
    if set(fams) != {g_topo}:
        raise CarveRefused("hole", f"hole reaches non-ground island tris (topos {dict(fams)}, "
                           f"ground topo {g_topo})", [tri_c[t] for t in sorted(drop) if gtopo[t] != g_topo][:12])

    eu2 = Counter()
    for tdx, tri in enumerate(gtris):
        if tdx in drop:
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu2[tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]]))))] += 1
    dropped_edges = set()
    for tdx in drop:
        tri = gtris[tdx]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            dropped_edges.add(tuple(sorted((kk3(gpos[tri[a]]), kk3(gpos[tri[b]])))))
    hole_es = [e for e, n in eu2.items() if n == 1 and e in dropped_edges]
    holes = chain_rings(hole_es, "hole")
    if len(holes) != 1:
        raise ValueError(f"hole is {len(holes)} rings, want 1")
    hole = holes[0]
    # THE EXACT-WELD LAW (round 16, the owner's "1-pixel seams"): the ring's points are kk3 KEYS (rounded to
    # 1e-3), not positions. Emitted as zip corners they sat up to 5e-4u off the kept grass they weld to --
    # invisible to every key-based gate, a pinhole crack on screen all round the foot. The zip's grass side
    # takes the kept grass's own float position, bit for bit, as its rock side always took c_float.
    h_float = {}
    for tdx, tri in enumerate(gtris):
        if tdx in drop:
            continue
        for i in tri:
            k = kk3(gpos[i])
            if k in h_float and tuple(gpos[i]) != h_float[k]:
                raise ValueError(f"kept grass at {k} has two float positions {h_float[k]} / {tuple(gpos[i])} "
                                 f"-- a weld split before the zip; the zip cannot weld to both")
            h_float.setdefault(k, tuple(gpos[i]))
    log(f"hole ring: {len(hole)} positions")

    carried = {t: [carry_vert(i) for i in dtri[t]] for t in blob}
    for t in sweep:                                        # verbatim extras, outside the
        carried[t] = [carry_vert(i) for i in dtri[t]]      # ring accounting
    if max_apron_lift is not None:
        # THE HIGH-FOOT CONFORM's selection runs on the CARRIED floats themselves (a
        # rim_set-keyed first cut missed sweep-extra boundary verts AND risked float-path
        # divergence vs carry_vert): every vert on a ONCE-EDGE of the full carried set
        # (blob + sweep = the true rock-meets-grass boundary) sitting in (cap, cap+3]
        # pulls down to the cap, unless a real aperture/ensemble ring point sits within
        # 4u AND 3u vertically (the falls-outlet weld; its aux verts also ride the map).
        _once = Counter()
        for _t, _ps in carried.items():
            for _a, _b in ((0, 1), (1, 2), (2, 0)):
                _once[tuple(sorted((kk3(_ps[_a]), kk3(_ps[_b]))))] += 1
        _bound = {k for e, n in _once.items() if n == 1 for k in e}
        for _k in _bound:
            if cap_y + 1e-6 < _k[1] <= cap_y + 3.0 and not any(
                    (_k[0] - _a) ** 2 + (_k[2] - _c) ** 2 <= 16.0 and abs(_k[1] - _b) <= 3.0
                    for _a, _b, _c in _conform_ring_pts):
                rim_adjust[_k] = cap_y
                adj_xz.add((_k[0], _k[2]))
        if rim_adjust:
            log(f"high-foot conform: {len(rim_adjust)} boundary column(s) above cap "
                f"{cap_y:.2f} pull DOWN (max drop "
                f"{max(k[1] - cap_y for k in rim_adjust):.2f}u); apron lift capped at "
                f"{float(max_apron_lift):.2f}u")
        for _t, _ps in carried.items():
            for _v in _ps:
                _nk = kk3(_v)
                if _nk in rim_adjust:
                    _v[1] = rim_adjust[_nk]
    c_edge = Counter()
    c_float = {}
    for t in blob:
        ps = carried[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = kk3(ps[a]), kk3(ps[b])
            c_float.setdefault(ka, ps[a])
            c_float.setdefault(kb, ps[b])
            c_edge[tuple(sorted((ka, kb)))] += 1
    crims = chain_rings([e for e, n in c_edge.items() if n == 1], "carried rim")
    crims.sort(key=lambda r: -abs(signed_area(r)))
    if len(crims) != 1 + len(apertures) + len(ensemble_apertures):
        raise ValueError("carried ring count changed in transit")
    crim = crims[0]

    # THE APERTURE PLUGS: the Object mesh's own geometry, verbatim, carried as terrain
    # (winding up-facing). id = the adjacent rock's; normals de-tilted + rotated; verts
    # snap to the carried blob floats so the plug welds shut. The object's own uvs
    # target the OBJECT material (in the terrain atlas they'd sample grass); the plug
    # instead CONTINUES the surrounding rock chart -- fit the affine of the collar (the
    # rock tris touching the aperture, largest uv-continuous group) and evaluate it at
    # the plug verts: the panel's own flow extended across the hole, exactly how every
    # within-panel edge already flows (the gore-panel law).
    plug_parents = []
    plug_id = None
    if apertures:
        ap_pts = {p for r in apertures for p in r}
        ap_carried = {}
        for t in blob:
            tri = dtri[t]
            for k in range(3):
                k0 = kk3(dV[tri[k]])
                if k0 in ap_pts:
                    ap_carried[k0] = carried[t][k]
        for r in apertures:
            for i2 in range(len(r)):
                e = tuple(sorted((r[i2], r[(i2 + 1) % len(r)])))
                for t2 in d_edge.get(e, ()):
                    if dtopo[t2] in ROCK:
                        plug_id = strip_dispatch(float(dT[dtri[t2][0]][0]))
                        break
                if plug_id:
                    break
            if plug_id:
                break
        if plug_id is None:
            raise ValueError("aperture has no adjacent rock tri to take an id from")

        def carry_pt(p):
            pr = rot_pt(detilt_p(p), ROT)
            return _fc_steep([pr[0] + DX, pr[1] + DY, pr[2] + DZ])

        collar = [t for t in blob if dtopo[t] in ROCK
                  and any(kk3(dV[i]) in ap_pts for i in dtri[t])]
        cpar = {t: t for t in collar}

        def cfind(t):
            while cpar[t] != t:
                cpar[t] = cpar[cpar[t]]
                t = cpar[t]
            return t

        cuv = {(t, kk3(dV[i])): (dU[i][0], dU[i][1]) for t in collar for i in dtri[t]}
        for t1 in collar:
            for t2 in collar:
                if t2 <= t1:
                    continue
                shared = [kk3(dV[i]) for i in dtri[t1]
                          if kk3(dV[i]) in {kk3(dV[j]) for j in dtri[t2]}]
                if len(shared) < 2:
                    continue
                if all(abs(cuv[(t1, s)][0] - cuv[(t2, s)][0]) < 0.0015
                       and abs(cuv[(t1, s)][1] - cuv[(t2, s)][1]) < 0.0015 for s in shared):
                    r1, r2 = cfind(t1), cfind(t2)
                    if r1 != r2:
                        cpar[r1] = r2
        groups = defaultdict(list)
        for t in collar:
            groups[cfind(t)].append(t)
        cg = max(groups.values(), key=len)
        rows_, ru_, rv_ = [], [], []
        for t in cg:
            for i in dtri[t]:
                rows_.append([dV[i][0], dV[i][1], dV[i][2], 1.0])
                ru_.append(dU[i][0])
                rv_.append(dU[i][1])
        Am_ = np.array(rows_)
        cu_, *_ = np.linalg.lstsq(Am_, np.array(ru_), rcond=None)
        cv_, *_ = np.linalg.lstsq(Am_, np.array(rv_), rcond=None)
        res_u = float(np.percentile(np.abs(Am_ @ cu_ - ru_) * 2048, 90))
        res_v = float(np.percentile(np.abs(Am_ @ cv_ - rv_) * 4096, 90))
        log(f"plug chart: collar {len(collar)} tris, biggest continuous group {len(cg)}, "
            f"affine residual p90 u{res_u:.0f} v{res_v:.0f} px")

        # THE COLLAR-TILE CLAMP (snowmassif/NOTES.md, round 21): the affine chart extrapolates past the collar into
        # whatever the atlas paints next -- comp9's plug reached v 0.2038 while its collar stops at 0.1973, and the
        # atlas changes tile at v 0.200 (Moguri: a pure-white gutter line, a white sliver in game; vanilla: another
        # paint). The collar group is one painted patch, so a plug UV axis that leaves the collar's UV box by MORE
        # than the chart's own p90 fit residual on that axis is clamped into the box; an overshoot inside the fit's
        # noise is not an extrapolation and is kept (Uaho's: u 3.5 / v 8 px against residuals of 15 / 10 px, so its
        # in-game bytes do not move; comp9's v overshoot is 27 px against 9).
        cu_lo, cu_hi = min(ru_), max(ru_)
        cv_lo, cv_hi = min(rv_), max(rv_)
        tol_u, tol_v = res_u / 2048, res_v / 4096
        clamped = [0]
        raw_uv = []

        def plug_uv(p):
            v4 = np.array([p[0], p[1], p[2], 1.0])
            uu, vv = float(v4 @ cu_), float(v4 @ cv_)
            raw_uv.append((uu, vv))
            cu2 = min(max(uu, cu_lo), cu_hi) if not cu_lo - tol_u <= uu <= cu_hi + tol_u else uu
            cv2 = min(max(vv, cv_lo), cv_hi) if not cv_lo - tol_v <= vv <= cv_hi + tol_v else vv
            if (cu2, cv2) != (uu, vv):
                clamped[0] += 1
            return cu2, cv2

        for tri in otris:
            corners = []
            for i in tri:
                w = ap_carried.get(kk3(oV[i])) or carry_pt(oV[i])
                n3 = rot_n(detilt_n(oN[i]), ROT)
                uu, vv = plug_uv(oV[i])
                corners.append((*w, uu, vv, *n3))
            plug_parents.append((tuple(corners), plug_id, "plug"))
        puA, pvA = ROCK_CHART_PHASE
        pcols = sorted({math.floor((c[3] - puA) / 0.0625)
                        for cs, _, _ in plug_parents for c in cs})
        prows = sorted({math.floor((c[4] - pvA) / 0.03125)
                        for cs, _, _ in plug_parents for c in cs})
        log(f"aperture plugs: {len(plug_parents)} object tris carried as terrain "
            f"(id {plug_id:.0f}, chart cols {pcols} rows {prows})"
            + f"; raw plug uv u {min(u for u, _ in raw_uv):.4f}..{max(u for u, _ in raw_uv):.4f} "
              f"v {min(v for _, v in raw_uv):.4f}..{max(v for _, v in raw_uv):.4f} vs the collar box "
              f"u {cu_lo:.4f}..{cu_hi:.4f} v {cv_lo:.4f}..{cv_hi:.4f}"
            + (f"; {clamped[0]} plug uv corner(s) clamped into the collar's uv box" if clamped[0] else ""))
        own_cells = [(math.floor((dU[i][0] - puA) / 0.0625), math.floor((dU[i][1] - pvA) / 0.03125))
                     for t in blob if dtopo[t] in ROCK for i in dtri[t]]
        if not _plug_chart_ok(pcols, prows, own_cells):
            raise ValueError(f"plug chart left the rock band (plug cols {pcols} rows {prows}: outside the "
                             f"painted band and outside the donor's own rock)")
    rim_nrm = {}
    for t in blob:
        for k in range(3):
            key = kk3(carried[t][k])
            rim_nrm.setdefault(key, rot_n(dN2[dtri[t][k]], ROT))
    log(f"carried: peak y {max(p[1] for ps in carried.values() for p in ps):.1f}, "
        f"DY {DY:+.2f}")

    # ---- 5. zip annulus: minimal-total-chord DP (a greedy walk stalls on floor-mouth
    # CONCAVITY into long chords at any rotation; the DP strip between the two rings is
    # optimal and concavity-immune) -----------------------------------------------------
    hole_ord = list(hole)
    rim_base = list(crim)
    if signed_area(hole_ord) * signed_area(rim_base) < 0:
        rim_base.reverse()

    def rimw(p):
        return tuple(c_float[p])

    def d2(p, q):
        return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

    H, R, zip_tris = _zip_dp(hole_ord, rim_base, rimw, h_float)
    rim_ord = R
    zip_maxe = 0.0
    for tri3 in zip_tris:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            zip_maxe = max(zip_maxe, math.sqrt(d2(tri3[a], tri3[b])))
    log(f"zip annulus: {len(zip_tris)} tris (DP, max chord {zip_maxe:.1f}u)")

    # ---- 5b. apron + zip shading: re-smooth the CHANGED grass in place ------------------
    # the lift tilts the real surface but kept verts still wear the mint's flat-ground
    # normals, and the zip interpolated donor-rock normals across its whole band --
    # together = a visible seam ring. Re-smooth area-weighted over the FINAL geometry,
    # applied only where the ground actually moved (blended by lift magnitude -> exact
    # mint normals at the region edge, no new seam); rim verts keep the donor's
    # feet-weld normals.
    acc = defaultdict(lambda: np.zeros(3))

    def acc_tri(p3):
        a, b, c3 = (np.asarray(q, dtype=float) for q in p3)
        fn = np.cross(b - a, c3 - a)
        if fn[1] < 0:
            fn = -fn
        for q in p3:
            acc[kk3(q)] += fn

    for tdx, tri in enumerate(gtris):
        if tdx not in drop:
            acc_tri([gpos[i] for i in tri])
    for t in blob:
        acc_tri(carried[t])
    for tri3 in zip_tris:
        acc_tri(list(tri3))
    n_ns = 0
    for i, lf in lift_of.items():
        s = min(1.0, abs(lf) / 0.4)
        v3 = acc[kk3(gpos[i])]
        L = float(np.linalg.norm(v3))
        if s <= 0.0 or L < 1e-9:
            continue
        nb2 = np.asarray(gnrm[i], dtype=float) * (1 - s) + (v3 / L) * s
        nb2 /= (np.linalg.norm(nb2) or 1.0)
        gnrm[i] = nb2.tolist()
        n_ns += 1
    log(f"apron re-smooth: {n_ns} vert normals blended by lift")

    cell_of = lambda x, z: (int(np.floor(x / 4.0)), int(np.floor(z / 4.0)))  # noqa: E731
    kept_by_cell = defaultdict(list)
    for tdx, tri in enumerate(gtris):
        if tdx in drop or not plain[tdx]:
            continue
        kept_by_cell[cell_of(*tri_c[tdx])].append(tdx)
    QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
    ORIS = (0, 90, 180, 270)
    _dec = {}

    def decode_cell(cell):
        if cell in _dec:
            return _dec[cell]
        best2 = None
        for tdx in kept_by_cell.get(cell, []):
            tri = gtris[tdx]
            for q in QUADS:
                for o in ORIS:
                    err = 0.0
                    for i in tri:
                        mu, mv = G.mains_uv(gpos[i][0], gpos[i][2], cell, q, o)
                        err = max(err, abs(mu + g_du - guv[i][0]),
                                  abs(mv + g_dv - guv[i][1]))
                    if err < 1e-4:
                        best2 = (q, o)
                        break
                if best2:
                    break
            if best2:
                break
        if best2 is None:
            import random as _r
            i2, j2 = cell
            rr = _r.Random((i2 * 73856093) ^ (j2 * 19349663) ^ 0xF95)
            best2 = (QUADS[rr.randrange(4)], ORIS[rr.randrange(4)])
        _dec[cell] = best2
        return best2

    pos_nrm = {}
    for tdx, tri in enumerate(gtris):
        if tdx in drop:
            continue
        for i in tri:
            pos_nrm.setdefault(kk3(gpos[i]), list(gnrm[i]))

    ID0 = float(X.encode_id(topograph=g_topo))
    new_parents = []                                       # (corners8, idall, fam)
    skip_pairs = []                                        # (donor idall, carried idall) per carried tri
    for t in blob:                                         # the mountain, verbatim channels
        tri = dtri[t]
        idall = strip_dispatch(float(dT[tri[0]][0]))
        skip_pairs.append((float(dT[tri[0]][0]), idall))
        nr = [rot_n(dN2[tri[k]], ROT) for k in range(3)]
        corners = tuple((*carried[t][k], dU[tri[k]][0], dU[tri[k]][1], *nr[k])
                        for k in range(3))
        new_parents.append((corners, idall, "mountain"))
    for t in sweep:                                        # the footprint sweep, verbatim
        tri = dtri[t]
        idall = strip_dispatch(float(dT[tri[0]][0]))
        skip_pairs.append((float(dT[tri[0]][0]), idall))
        nr = [rot_n(dN2[tri[k]], ROT) for k in range(3)]
        corners = tuple((*carried[t][k], dU[tri[k]][0], dU[tri[k]][1], *nr[k])
                        for k in range(3))
        new_parents.append((corners, idall, "mountain"))
    from .placement import skip_parity_gate
    skip_gate = skip_parity_gate(skip_pairs, label="mountain")
    if not skip_gate["ok"]:
        raise ValueError(f"the carry changed the ground-query visibility of {skip_gate['flipped']} donor tri(s) "
                         f"(THE BANK SKIP LAW; e.g. donor/carried IDALL {skip_gate['sample'][:2]})")
    new_parents.extend(plug_parents)
    # THE FOOT COURSE (the spur-graft class, massif_spur.py in-game proven): inside a
    # window rect the zip emits as synthetic ROCK instead of grass. Harvest r10 exemplar
    # tiles from the donor's own foot course (edge-paired full-tile quads at chart row
    # 10, cols 6-9) and parameterize the hole chain by arc for the u sawtooth.
    fc_ex = {}
    fc_cols = []
    fc_SH = None
    fc_hole_keys = set()
    if fc_rects:
        puA, pvA = ROCK_CHART_PHASE
        _e2t = defaultdict(list)
        for t in blob:
            _ks = [kk3(carried[t][k]) for k in range(3)]
            for _a2, _b2 in ((0, 1), (1, 2), (2, 0)):
                _e = (_ks[_a2], _ks[_b2]) if _ks[_a2] < _ks[_b2] else (_ks[_b2], _ks[_a2])
                _e2t[_e].append(t)
        _seenq = set()
        for _e, _ts in _e2t.items():
            if len(_ts) != 2 or _ts[0] in _seenq or _ts[1] in _seenq:
                continue
            _vs4 = {kk3(v) for _t2 in _ts for v in carried[_t2]}
            if len(_vs4) != 4:
                continue
            _uvm = {}
            for _t2 in _ts:
                _tri = dtri[_t2]
                for k in range(3):
                    _uvm[kk3(carried[_t2][k])] = (dU[_tri[k]][0], dU[_tri[k]][1])
            _us = [u2[0] for u2 in _uvm.values()]
            _vs2 = [u2[1] for u2 in _uvm.values()]
            if not (0.05 < max(_us) - min(_us) <= 0.0625 + 1e-4
                    and 0.025 < max(_vs2) - min(_vs2) <= 0.03125 + 1e-4):
                continue
            _row = round((min(_vs2) - pvA) / 0.03125)
            _col = round((min(_us) - puA) / 0.0625)
            if _row != 10 or _col not in (6, 7, 8, 9) or _col in fc_ex:
                continue
            _p4 = sorted(_vs4, key=lambda p: p[1])
            fc_ex[_col] = (min(_us), max(_us),
                           (_uvm[_p4[0]][1] + _uvm[_p4[1]][1]) / 2,
                           (_uvm[_p4[2]][1] + _uvm[_p4[3]][1]) / 2)
            _seenq.update(_ts)
        if not fc_ex:
            raise ValueError("foot-course window set but the donor has no row-10 "
                             "exemplar quads (cols 6-9) to tile the course from")
        fc_cols = sorted(fc_ex)
        fc_SH = [0.0]
        for _i2 in range(1, len(H)):
            fc_SH.append(fc_SH[-1] + math.hypot(H[_i2][0] - H[_i2 - 1][0],
                                                H[_i2][2] - H[_i2 - 1][2]))
        fc_STOT = fc_SH[-1] + math.hypot(H[0][0] - H[-1][0], H[0][2] - H[-1][2])
        fc_hole_keys = {kk3(p) for p in H}
        # THE DONOR'S CUT TILE (R4 take 9): the donor's own lowest course already wears the
        # r10 fringe tile, and the carve cuts it MID-TILE at the rim (the window's high-foot
        # arc: v-frac 0.53-0.66 there). A foot course that restarts a fresh tile under it
        # seams at every shared rim vert; one that FINISHES the donor's tile -- fringe edge
        # at the lawn, the donor's own v at the rim -- is continuous there by construction,
        # and lands at stock density (~0.4-0.5 tile over the 1.1-1.6u course).
        fc_rim_v = {}
        for _t in blob:
            _tri = dtri[_t]
            _vc = sum(dU[i][1] for i in _tri) / 3
            _uc = sum(dU[i][0] for i in _tri) / 3
            if int((_vc - pvA) / 0.03125) != 10 or int((_uc - puA) / 0.0625) not in (6, 7, 8, 9):
                continue
            for _k in range(3):
                fc_rim_v.setdefault(kk3(carried[_t][_k]), dU[_tri[_k]][1])

        def fc_s_of(px2, pz2):
            """Continuous arc parameter: project onto the hole ring's SEGMENTS --
            nearest-VERTEX snap collapses a one-hole tri's whole u-extent to a
            single texel column (the measured take-5c smear class)."""
            best_d, best_s = 1e18, 0.0
            for _i3 in range(len(H)):
                _j3 = (_i3 + 1) % len(H)
                _ax, _az = H[_i3][0], H[_i3][2]
                _ex, _ez = H[_j3][0] - _ax, H[_j3][2] - _az
                _L2 = _ex * _ex + _ez * _ez
                _tt = 0.0 if _L2 < 1e-12 else max(0.0, min(1.0, (
                    (px2 - _ax) * _ex + (pz2 - _az) * _ez) / _L2))
                _dd = (px2 - _ax - _tt * _ex) ** 2 + (pz2 - _az - _tt * _ez) ** 2
                if _dd < best_d:
                    best_d = _dd
                    best_s = fc_SH[_i3] + _tt * math.sqrt(_L2)
            return best_s

        _fch = defaultdict(list)
        for _hp in H:
            _fch[(math.floor(_hp[0] / 6.0), math.floor(_hp[2] / 6.0))].append(_hp)

        def fc_lawn_y(px2, pz2):
            """The lawn line under a course vertex: the height of the NEAREST hole-ring
            position. A pure function of POSITION, so every tri sharing a vertex gives it the
            same v -- the per-tri (ylow, yspan) it replaces put one rim vert at v 0.03, 0.21,
            0.53 and 0.66 in four neighbours (take 8's SE corner: one tri's fringe meeting its
            neighbour's rock top along their shared edge; 10 of 32 window fringe positions
            seamed > 0.25 tile vs 6 of 2536 in stock -- stock_fringe_continuity)."""
            _cx6, _cz6 = math.floor(px2 / 6.0), math.floor(pz2 / 6.0)
            cand = [p for _gx in (_cx6 - 1, _cx6, _cx6 + 1) for _gz in (_cz6 - 1, _cz6, _cz6 + 1)
                    for p in _fch.get((_gx, _gz), ())] or H
            return min(cand, key=lambda p: (p[0] - px2) ** 2 + (p[2] - pz2) ** 2)[1]

        # THE STRIP (R4 take 11): the longest CONTIGUOUS run of exemplar cols (the donor's
        # r10 c6-c9 is one painted strip; a white gutter follows c9), its painted u extent,
        # and v constants every foot tri shares -- the innermost of the cols' own fringe/top
        # edges, so one vertex never takes two v from two columns
        _runs, _cur = [], [fc_cols[0]]
        for _c in fc_cols[1:]:
            if _c == _cur[-1] + 1:
                _cur.append(_c)
            else:
                _runs.append(_cur)
                _cur = [_c]
        _runs.append(_cur)
        fc_strip = max(_runs, key=len)
        fc_ulo, fc_uhi = fc_ex[fc_strip[0]][0], fc_ex[fc_strip[-1]][1]
        _vbs = [fc_ex[_c][2] for _c in fc_strip]
        _vts = [fc_ex[_c][3] for _c in fc_strip]
        if _vbs[0] > _vts[0]:
            fc_vb, fc_vt = min(_vbs), max(_vts)
        else:
            fc_vb, fc_vt = max(_vbs), min(_vts)
        # the s origin sits OUTSIDE the window (the ring vert farthest from the window
        # centre), so the ring's own s=0 cut never falls inside a foot course
        _wcx = sum((r[0] + r[2]) / 2 for r in fc_rects) / len(fc_rects)
        _wcz = sum((r[1] + r[3]) / 2 for r in fc_rects) / len(fc_rects)
        _iref = max(range(len(H)), key=lambda _i: (H[_i][0] - _wcx) ** 2 + (H[_i][2] - _wcz) ** 2)
        fc_sref = fc_SH[_iref]
        _ncol = len(fc_strip)

        def fc_u_of(px2, pz2):
            _U = ((fc_s_of(px2, pz2) - fc_sref) % fc_STOT) / MTN_FC_TILE_W
            _x = _U % (2 * _ncol)
            _t = _x if _x <= _ncol else 2 * _ncol - _x
            return fc_ulo + (_t / _ncol) * (fc_uhi - fc_ulo)

        log(f"foot course: exemplar cols {fc_cols} (strip {fc_strip}); window rects {fc_rects}")
    ID_FOOT = float(X.encode_id(topograph=49))
    fc_n = 0
    fc_ny_min = 1.0
    zip_rise = 0.0
    zip_rise_at = None                     # where the steepest grass zip tri is (a refusal draws it)
    zip_ny_min = 1.0
    zip_ny_low = 0
    for tri3 in zip_tris:
        a, b, c = (np.asarray(p, dtype=float) for p in tri3)
        nrm = np.cross(b - a, c - a)
        nl = float(np.linalg.norm(nrm)) or 1.0
        _cx0 = float(a[0] + b[0] + c[0]) / 3
        _cz0 = float(a[2] + b[2] + c[2]) / 3
        # THE PROFILE LAW relief gate: rock only where the carried massif rises (the
        # _fc_rock_here predicate, shared with the tight hole cut). Where it does not
        # -- taper arms, shallow benches -- a rock course is rock paint on flat
        # ground or a CURB standing over nothing (both owner-filed defect classes);
        # the contact retreats to grass there and the wider hole gives it room to
        # ramp gently.
        # ...asked of the TRI itself (R4 take 10): rock where the massif rises within 6u AND the
        # tri rises above the lawn -- never one lying wholly at or below it (the NW sliver,
        # t672/t673-t675, tops 2.62-3.05 on a 3.2 plateau). NOT the nearest-rim test the hole
        # cut uses: at the SE corner the nearest rim to a centroid was the donor's BURIED rim
        # (P, 2.45) while the tri itself climbs to M (4.58) -- take 9 painted that 52 deg face
        # grass, a regression the owner saw ("looks worse")
        is_foot = (_in_fc(_cx0, _cz0) and _fc_rises(_cx0, _cz0)
                   and max(float(p[1]) for p in tri3) > ground_med + MTN_FC_RIM_ABOVE
                   # ...and STEEP ENOUGH to be a wall (R4 take 11): stock's rock-grass contact
                   # tris are shallower than 25 deg in 1.1% of 1130 (p01; p05 31) -- the SE
                   # corner's 21 deg skirt (t630, the owner's "3") is ground, and seen from
                   # the lawn its fringe foreshortened into the streak takes 8-10 all showed
                   and abs(float(nrm[1])) / nl < math.cos(math.radians(MTN_FC_SLOPE_MIN))
                   # ...and never a FIN reaching down to a BURIED rim (R4 take 12): the donor's
                   # rim under the lawn is ground, part of its free-base burial. As rock, a fin
                   # put two verts on the fringe edge row and smeared it (the SE corner's t631,
                   # takes 10-11); as plain rock (owner option A, on the bench) it read as a grey
                   # shard lying on the lawn -- the NW one (t673) like the original sliver.
                   # As grass both blend: a steep bank at most (the zip's own bank budget)
                   and not any(kk3(p) not in fc_hole_keys
                               and float(p[1]) < ground_med - MTN_FC_RIM_ABOVE for p in tri3))
        if is_foot:
            fc_n += 1
            fc_ny_min = min(fc_ny_min, abs(float(nrm[1])) / nl)
        else:
            zip_ny_low += (abs(float(nrm[1])) / nl) < MTN_ZIP_NY_MIN
            zip_ny_min = min(zip_ny_min, abs(float(nrm[1])) / nl)
            # rise gated on the GRASS zip only: the engine-step ceiling protects
            # walkable grass; a foot-course toe deliberately spans the face's rise
            # in one course (its own fc_ny floor gates the winding)
            _rise = float(max(p[1] for p in tri3) - min(p[1] for p in tri3))
            if _rise > zip_rise:
                zip_rise, zip_rise_at = _rise, (sum(float(p[0]) for p in tri3) / 3, sum(float(p[2]) for p in tri3) / 3)
        order = tri3 if nrm[1] > 0 else (tri3[0], tri3[2], tri3[1])
        if is_foot:
            # r10 tile band -- fringe edge pinned at the hole (lawn) verts (the
            # foot-transition law: tile bottom edge ON the boundary), the FULL tile
            # spanning the course height (the spur's proven mapping -- a partial
            # window at natural density samples only the painted fringe zone and
            # smears green), u chained along the hole chain in ~4.6u windows, cols
            # cycling (the sawtooth; THE COL-FREEDOM LAW), one window per tri.
            # u PER VERTEX along the course (R4 take 11): the vertex's arc parameter s at
            # MTN_FC_TILE_W per tile, MIRROR-repeated across the contiguous exemplar strip
            # (fc_u_of). Take 5-10 stretched each tri's OWN s-extent over one full tile
            # width ("one tile per quad"): on the thin fan tris of a corner that squeezes or
            # stretches the tile sideways -- the owner's streaks at the SE corner (a tooth in
            # take 8, a smear in 9 and 10) -- and restarts u at every tri (window abs-u spread
            # p50 0.97 tile; stock p50 0.00). A mirror never jumps (c9's right edge is a
            # Moguri gutter, so a sawtooth could not wrap inside the strip) and never
            # clamps (the fixed-window grid's frozen-texel streaks, the reason the per-tri
            # stretch existed).
            _vb, _vt = fc_vb, fc_vt
            corners = []
            for pnt in order:
                key = kk3(pnt)
                n3 = pos_nrm.get(key) or rim_nrm.get(key, [0.0, 1.0, 0.0])
                _uu = fc_u_of(float(pnt[0]), float(pnt[2]))
                if key in fc_hole_keys:
                    _v = _vb
                elif key in fc_rim_v:
                    _v = fc_rim_v[key]                     # finish the donor's cut tile
                else:
                    # PER VERTEX, at stock density (R4 take 9): |deviation| from the lawn
                    # line under THIS vertex (an ascending course shades fringe->rock
                    # upward, a FREE-BASE dip downward the same way), one full tile per
                    # MTN_FC_TILE_H of it. Take 8 spread the full tile over each tri's own
                    # span: on the 1.6-1.9u high-foot courses that squashed the fringe to
                    # 0.45-0.56 tile-heights/u (stock p90 0.34) -- the owner's "stretched
                    # transition tile" -- and gave shared verts tri-dependent v.
                    _dev = abs(float(pnt[1]) - fc_lawn_y(float(pnt[0]), float(pnt[2])))
                    _v = _vb + min(1.0, _dev / MTN_FC_TILE_H) * (_vt - _vb)
                corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]),
                                _uu, _v, *n3))
            new_parents.append((tuple(corners), ID_FOOT, "foot"))
            continue
        cell = cell_of(float(a[0] + b[0] + c[0]) / 3, float(a[2] + b[2] + c[2]) / 3)
        q, o = decode_cell(cell)
        # plain positional mains, UNCLAMPED -- the mesa/forest-proven form
        corners = []
        for pnt in order:
            key = kk3(pnt)
            n3 = pos_nrm.get(key) or rim_nrm.get(key, [0.0, 1.0, 0.0])
            u, v = G.mains_uv(float(pnt[0]), float(pnt[2]), cell, q, o)
            corners.append((float(pnt[0]), float(pnt[1]), float(pnt[2]),
                            u + g_du, v + g_dv, *n3))
        new_parents.append((tuple(corners), ID0, "zip"))

    # ---- 5d. THE LAWN-LINE SNAP: the carried rock meets the zip on its painted lawn line ----
    new_parents, lawn_snap = _lawn_line_snap(new_parents, rock_topos=ROCK, log=log)
    new_parents, seam_unify = _fringe_seam_unify(new_parents, rock_topos=ROCK, log=log)

    # ---- 6. gates + assembly ------------------------------------------------------------
    for corners, idall, fam in new_parents:
        for p in corners:
            if not (SPX0 + 0.5 < p[0] < SPX1 - 0.5 and SPZ0 + 0.5 < p[2] < SPZ1 - 0.5):
                raise CarveRefused("span", f"{fam} leaves block span {span}: {p[:3]}", [(p[0], p[2])])
    down, stock_down = _count_down(new_parents, _stock_down_keys(list(blob) + list(sweep), dV, dtri, carried),
                                   log=log)
    maxe, maxe_at = 0.0, None
    for corners, _, fam in new_parents:
        a, b, c = (np.asarray(p[:3]) for p in corners)
        if fam not in ("zip", "foot"):
            continue                                       # verbatim rock/plug edges are stock-given
        for pq in ((a, b), (b, c), (c, a)):
            _e = float(np.linalg.norm(pq[0] - pq[1]))
            if _e > maxe:
                maxe, maxe_at = _e, (float(pq[0][0] + pq[1][0]) / 2, float(pq[0][2] + pq[1][2]) / 2)
    ring_pts = np.array([list(p) for p in hole_ord] + [list(rimw(p)) for p in rim_ord])
    nm = 0
    for a_ in range(len(ring_pts)):
        dd = np.sum((ring_pts - ring_pts[a_]) ** 2, axis=1)
        nm += int(((dd > 1e-9) & (dd < 0.0025)).sum())
    # per-block assembly: kept tris stay in their origin block, new tris split at the
    # 64u borders (real cross-block mountains ship border-split with identity welds --
    # split_borders8 cuts every parent at the same plane with the same lerp, so the
    # welds hold); every span block re-emits
    new_by_block = split_borders8(new_parents)
    if not set(new_by_block) <= set(span):
        raise CarveRefused("leak", f"carve leaks outside the span blocks: "
                           f"{sorted(set(new_by_block) - set(span))}",
                           [_block_mid(b) for b in sorted(set(new_by_block) - set(span))])
    changed = {}
    for blk in span:
        sbx, sby = blk
        bm0 = soup["blocks"][blk]
        pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []

        def emit(p3, u2, n3, t4):
            pos.append([p3[0] - BLOCK * sbx, p3[1], p3[2] + BLOCK * (sby + 1) - BLOCK])
            uv.append(list(u2)); nrm.append(list(n3)); tan.append(list(t4))
            flat.append(len(pos) - 1)

        for tdx, tri in enumerate(gtris):
            if gblk[tdx] != blk or tdx in drop:
                continue
            for i in tri:     # a KEPT tri re-emits its source tangent (soup_from_blocks); a patched mint hole is new
                emit(gpos[i], guv[i], gnrm[i],
                     gtan[i] if tdx < n_orig else [gtan[i][0], 0.0, 0.0, 1.0])
            tris.append([flat[-3], flat[-2], flat[-1]])
        for corners, idall, fam in new_by_block.get(blk, []):
            for p in corners:
                emit(p[:3], (p[3], p[4]), (p[5], p[6], p[7]), [idall, 0.0, 0.0, 1.0])
            tris.append([flat[-3], flat[-2], flat[-1]])
        changed[blk] = X.BlockMesh(
            name=bm0.name, disc=bm0.disc, x=sbx, y=sby, lod=bm0.lod, vcount=len(pos),
            stride=48,
            channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2),
                      X.CH_TAN: (32, 4)},
            chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
            flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True,
            submeshes=[])
    # once-edge gate = BASELINE-SUBTRACTED against the PRISTINE snapshot (captured before
    # the lift): the mint has its own legal once-edges; the build must not ADD any --
    # including lift-split welds ANYWHERE in the span (internal span borders count 2
    # here, one edge from each block's re-emit, exactly like the baseline)
    eu3 = Counter()
    for blk, bmB in changed.items():
        sbx, sby = blk
        v_ = bmB.chan_arrays[X.CH_POS]
        for tri in bmB.tris:
            w = [(v_[i][0] + BLOCK * sbx, v_[i][1], v_[i][2] - BLOCK * (sby + 1) + BLOCK)
                 for i in tri]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu3[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
    # the transit rings beyond the outer rim (crims[1:]) are LAWFUL open boundaries:
    # plug-class apertures get welded shut by their plugs (exemption = no-op, the Uaho
    # baseline), ensemble-class apertures ship OPEN exactly as stock does (the water
    # parts cover them). Their once-edges may be border-SPLIT halves of a ring edge, so
    # the test is segment PROXIMITY, not edge identity.
    open_segs = []
    for ring_o in crims[1:]:
        for i2 in range(len(ring_o)):
            open_segs.append((ring_o[i2], ring_o[(i2 + 1) % len(ring_o)]))
    for t in sweep:                                        # sweep-tri edges too -- a
        ps = carried[t]                                    # border SPLIT half is a
        for a, b in ((0, 1), (1, 2), (2, 0)):              # collinear sub-segment
            open_segs.append((tuple(ps[a]), tuple(ps[b])))

    def _on_open(pt):
        for a3, b3 in open_segs:
            ex, ey, ez = b3[0] - a3[0], b3[1] - a3[1], b3[2] - a3[2]
            L2 = ex * ex + ey * ey + ez * ez
            if L2 < 1e-12:
                continue
            t01 = ((pt[0] - a3[0]) * ex + (pt[1] - a3[1]) * ey + (pt[2] - a3[2]) * ez) / L2
            t01 = max(0.0, min(1.0, t01))
            dx3 = pt[0] - (a3[0] + t01 * ex)
            dy3 = pt[1] - (a3[1] + t01 * ey)
            dz3 = pt[2] - (a3[2] + t01 * ez)
            if dx3 * dx3 + dy3 * dy3 + dz3 * dz3 < 0.0009:  # 0.03u: kk3 + split lerp
                return True
        return False

    # footprint-sweep tris are verbatim stock shingles/lining: any open edge they
    # create existed in stock or borders uncarried stock -- lawful, not a crack
    sweep_edges = set()
    for t in sweep:
        ps = carried[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            sweep_edges.add(tuple(sorted((kk3(ps[a]), kk3(ps[b])))))
    inner_once = []
    for e, n in eu3.items():
        if n != 1 or e in once0:
            continue
        if e in sweep_edges:
            continue
        if open_segs and _on_open(e[0]) and _on_open(e[1]):
            continue
        inner_once.append(e)
    for e in inner_once[:6]:
        log(f"  NEW ONCE EDGE: {e[0]} -- {e[1]}")
    worst_rig = 0.0                                        # THE ROCK-RIGID GATE
    _rig_exempt = adj_xz | fc_steep_moved
    for t in list(blob) + list(sweep):
        tri = dtri[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if _rig_exempt and (
                    (round(carried[t][a][0], 3), round(carried[t][a][2], 3)) in _rig_exempt
                    or (round(carried[t][b][0], 3),
                        round(carried[t][b][2], 3)) in _rig_exempt):
                continue                         # the deliberate conform / face steepen
            d0 = float(np.linalg.norm(dVref[tri[a]] - dVref[tri[b]]))
            if d0 > 0.05:
                worst_rig = max(worst_rig,
                                abs(math.dist(carried[t][a], carried[t][b]) / d0 - 1.0))
    g_worst, g_worst_at = 0.0, None                        # the apron slope envelope
    for tdx, tri in enumerate(gtris):
        if tdx in drop or not plain[tdx]:
            continue
        a, b, c3 = (np.array(gpos[i]) for i in tri)
        fn = np.cross(b - a, c3 - a)
        L = float(np.linalg.norm(fn)) or 1.0
        _sl = math.degrees(math.acos(max(-1, min(1, abs(fn[1]) / L))))
        if _sl > g_worst:
            g_worst, g_worst_at = _sl, tri_c[tdx]
    log(f"gates: down={down}" + (f" (+{stock_down} stock near-vertical exempt)" if stock_down else "")
        + f" maxEdge={maxe:.1f} nearMiss={nm // 2} "
        f"annulusOnce={len(inner_once)} zipRise={zip_rise:.2f} zipNyMin={zip_ny_min:.2f} "
        f"(below-envelope {zip_ny_low}/{len(zip_tris)}) "
        + (f"footCourse={fc_n} fcNyMin={fc_ny_min:.2f} " if fc_n else "")
        + f"rockRigid={worst_rig * 100:.1f}% apronSlope={g_worst:.1f}deg")
    if down or nm or inner_once or maxe >= MTN_MAX_EDGE:
        raise CarveRefused("geometry", "mountain geometry gate failed (down/near-miss/annulus-crack/edge)",
                           [((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2) for e in inner_once[:12]]
                           + ([maxe_at] if maxe >= MTN_MAX_EDGE and maxe_at else []),
                           detail=", ".join(w for w, on in ((f"{down} down face(s)", down),
                                                            (f"{nm // 2} near miss(es)", nm),
                                                            (f"{len(inner_once)} crack edge(s)", inner_once),
                                                            (f"an edge of {maxe:.1f}u", maxe >= MTN_MAX_EDGE)) if on))
    if zip_rise > MTN_ZIP_RISE or zip_ny_min < MTN_ZIP_NY_FLOOR \
            or zip_ny_low > MTN_ZIP_BANK_MAX:
        raise CarveRefused("zip", f"zip steeper than the grass envelope (rise {zip_rise:.2f}, "
                           f"ny min {zip_ny_min:.2f} < floor {MTN_ZIP_NY_FLOOR}, or "
                           f"{zip_ny_low} banks below {MTN_ZIP_NY_MIN} > "
                           f"{MTN_ZIP_BANK_MAX} allowed)",
                           [zip_rise_at] if zip_rise > MTN_ZIP_RISE and zip_rise_at else [])
    if fc_n and fc_ny_min < MTN_FOOT_NY_FLOOR:
        raise ValueError(f"foot-course tri steeper than the sliver floor "
                         f"(ny {fc_ny_min:.2f} < {MTN_FOOT_NY_FLOOR})")
    if fc_rects and not fc_n:
        raise ValueError("foot-course window set but no rock foot course emitted -- "
                         "either the rect misses the zip (check it against the printed "
                         "placement) or the rim inside it sits at lawn height everywhere "
                         "(THE PROFILE LAW relief gate: a mountain that does not rise "
                         "gets no rock course)")
    if worst_rig >= MTN_ROCK_RIGID:
        raise CarveRefused("rigid", "carried rock deformed beyond the de-tilt affine"
                         + (f" and its declared x{rock_height:g} height" if rh else "")
                         + (f" and x{SPREAD:g} spread" if SPREAD != 1.0 else ""))
    if rh:
        _peak = max(p[1] for ps in carried.values() for p in ps)
        if _peak > STOCK_TERRAIN_MAX_Y:
            _pk = max((p for ps in carried.values() for p in ps), key=lambda p: p[1])
            raise CarveRefused("peak", f"--rock-height x{rock_height:g} lifts the peak to y {_peak:.2f}, above stock's "
                               f"tallest terrain ({STOCK_TERRAIN_MAX_Y}): a flying airship (42.1875) would sit "
                               f"inside the rock. Use a lower --rock-height", [(_pk[0], _pk[2])])
    if g_worst > MTN_APRON_SLOPE:
        raise CarveRefused("apron", "the ground apron exceeds the grass slope envelope",
                           [g_worst_at] if g_worst_at else [], detail=f"{g_worst:.1f} deg > {MTN_APRON_SLOPE}")

    # placement probes on the assembled meshes: the blob centre must ground on carried
    # rock, and the grass just outside the rim must still ground as plain grass
    from . import placement as P

    class _W:
        pass

    _w = _W()
    _wv, _wt, _wf = [], [], []
    for blk, bmB in sorted(changed.items()):
        sbx, sby = blk
        base = len(_wv)
        for k in range(bmB.vcount):
            v_ = bmB.chan_arrays[X.CH_POS][k]
            _wv.append((v_[0] + BLOCK * sbx, v_[1], v_[2] - BLOCK * (sby + 1) + BLOCK))
            _wt.append(bmB.chan_arrays[X.CH_TAN][k])
        _wf.extend(i + base for i in bmB.flat_index)
    _w.verts, _w.tangents, _w.flat_index = _wv, _wt, _wf
    _wml = [("Terrain", _w)]
    # probe the carried PEAK tri's centroid, not the bbox centre -- a horseshoe-class
    # massif's bbox centre sits over the open mouth (a lawful hole), the peak is always
    # carried rock
    peak_t = max((t for t in blob if dtopo[t] in ROCK),
                 key=lambda t: max(p[1] for p in carried[t]))
    ppx = sum(p[0] for p in carried[peak_t]) / 3
    ppz = sum(p[2] for p in carried[peak_t]) / 3
    gy, nm_, _, tp = P.place(_wml, ppx, ppz)
    log(f"carried peak grounds: y={gy:.2f} {nm_} topo {tp}")
    if nm_ != "Terrain" or tp not in ROCK:
        raise CarveRefused("probe", f"carried peak grounds on {nm_} topo {tp}, want carried rock", [(ppx, ppz)])
    r_out = max(math.hypot(px - TX, pz - TZ) for (px, pz) in rim_poly) + 4.0
    _probe_pt = (TX - r_out, TZ)
    if fc_rects:
        # a foot-course window puts lawful ROCK just outside the rim -- probe the
        # nearest surround point outside every window (span-bounded); a window set
        # covering the whole surround leaves nothing to check
        _cands = [(TX + rr * math.cos(th), TZ + rr * math.sin(th))
                  for rr in (r_out, r_out + 2.0, r_out + 4.0, r_out + 6.0)
                  for th in (math.pi, 0.0, math.pi / 2, -math.pi / 2,
                             3 * math.pi / 4, -3 * math.pi / 4, math.pi / 4,
                             -math.pi / 4)]
        _probe_pt = next((c for c in _cands if not _in_fc(c[0], c[1])
                          and SPX0 + 1.0 < c[0] < SPX1 - 1.0
                          and SPZ0 + 1.0 < c[1] < SPZ1 - 1.0), None)
    if _probe_pt is None:
        log("plain-ground probe SKIPPED (foot-course windows cover the surround)")
    else:
        gy2, nm2, _, tp2 = P.place(_wml, _probe_pt[0], _probe_pt[1])
        log(f"ground probe outside the rim: y={gy2:.2f} {nm2} topo {tp2}")
        if nm2 != "Terrain" or tp2 != g_topo:
            raise CarveRefused("probe", f"outside-rim ground probe grounds on {nm2} topo {tp2}, "
                               f"want plain ground topo {g_topo}", [_probe_pt])

    _atlas_gate_mountain(new_parents, game=game, log=log)

    # ---- 7. THE ENSEMBLE CARRY: the massif's auxiliary parts ride the same rigid map --
    # (only when the blob has ensemble apertures -- object-only donors like Uaho keep
    # the byte-frozen plug path above). Each donor part's weld components that sit in
    # the massif footprint carry WHOLE (stock ships them per-block already): positions
    # de-tilt + rotate + translate exactly like the rock, normals by inverse-transpose,
    # UVs verbatim (the water materials bind by part name). Components assign to the
    # bench block holding their transformed centroid, unsplit.
    # THE SCENERY SEAL (the horseshoe round-2 walk defects, 2026-07-15): the worldmap
    # ground query reads the hit tri's tangent.x as the IDALL for MOVEMENT LEGALITY
    # ((id & 0xFC) >> 2 vs the per-vehicle 64-topo limit mask, ff9.cs
    # w_movementCheckTopographID), and stock aux parts carry leftover REAL tangents
    # whose x (~0/+-1) garbage-decodes to topo 0 = WALKABLE -- so the player could walk
    # the bridge, UP the falls sheets, and onto the river (stock never noticed: its
    # interior is unreachable on foot). Worldmap shaders never consume tangents (the
    # Terrain channel stores IDALL floats and shades fine), so the carried aux parts
    # store a BLOCKED-topo IDALL instead: the whole ensemble becomes look-but-don't-
    # touch scenery, matching stock semantics.
    changed_parts = {}
    donor_ref = None
    n_ens_tris = 0
    if ensemble_apertures:
        SCENERY_ID = float(X.encode_id(topograph=49))      # blocked on foot + chocobos
        rim_poly_d = [(p[0], p[2]) for p in rim]
        ens_keys_d = set()                                 # donor-frame carried aux verts
        parts_deployed = set()
        for part in ENSEMBLE_PARTS:
            for (dbx, dby) in B["read_blocks"]:
                try:
                    pm = X.read_block(dbx, dby, disc=disc, game=game, part=part.lower())
                except Exception:
                    continue
                doff_b = np.array([BLOCK * dbx, 0.0, -BLOCK * dby])
                pV = np.asarray(pm.verts, dtype=np.float64) + doff_b
                pN, pU = pm.normals, pm.uvs
                nt = len(pm.flat_index) // 3
                ptri = [pm.flat_index[3 * t:3 * t + 3] for t in range(nt)]
                e2t = defaultdict(list)
                for t, tri in enumerate(ptri):
                    for a, b in ((0, 1), (1, 2), (2, 0)):
                        e2t[tuple(sorted((kk3(pV[tri[a]]), kk3(pV[tri[b]]))))].append(t)
                padj = defaultdict(set)
                for ts2 in e2t.values():
                    for i2 in range(len(ts2)):
                        for j2 in range(i2 + 1, len(ts2)):
                            padj[ts2[i2]].add(ts2[j2]); padj[ts2[j2]].add(ts2[i2])
                seenp = set()
                for s in range(nt):
                    if s in seenp:
                        continue
                    comp = {s}; stq = [s]
                    while stq:
                        t = stq.pop()
                        for t2 in padj[t]:
                            if t2 not in comp:
                                comp.add(t2); stq.append(t2)
                    seenp |= comp
                    cpts = [pV[i] for t in comp for i in ptri[t]]
                    if not any(pip(p[0], p[2], rim_poly_d) for p in cpts):
                        continue                           # outside the massif footprint
                    tv = {}
                    for t in comp:
                        for i in ptri[t]:
                            if i not in tv:
                                pr = rot_pt(detilt_p(pV[i]), ROT)
                                tv[i] = tuple(_fc_steep(
                                    [pr[0] + DX, pr[1] + DY, pr[2] + DZ]))
                                _nk = kk3(tv[i])
                                if _nk in rim_adjust:      # the high-foot conform's weld
                                    tv[i] = (tv[i][0], rim_adjust[_nk], tv[i][2])
                                if not (SPX0 - 1.0 < tv[i][0] < SPX1 + 1.0 and
                                        SPZ0 - 1.0 < tv[i][2] < SPZ1 + 1.0):
                                    raise ValueError(f"ensemble {part} vert leaves the "
                                                     f"span: {tv[i]}")
                                ens_keys_d.add(kk3(pV[i]))
                    ccx = sum(p[0] for p in tv.values()) / len(tv)
                    ccz = sum(p[2] for p in tv.values()) / len(tv)
                    blk = (int(math.floor(ccx / BLOCK)), int(math.floor(-ccz / BLOCK)))
                    if blk not in span:
                        raise ValueError(f"ensemble {part} component centres outside "
                                         f"the span at ({ccx:.0f},{ccz:.0f})")
                    dst = changed_parts.setdefault(blk, {}).setdefault(
                        part, dict(pos=[], nrm=[], uv=[], tan=[], flat=[], tris=[]))
                    sbx, sby = blk
                    for t in comp:
                        for i in ptri[t]:
                            w = tv[i]
                            dst["pos"].append([w[0] - BLOCK * sbx, w[1],
                                               w[2] + BLOCK * (sby + 1) - BLOCK])
                            dst["nrm"].append(rot_n(detilt_n(pN[i]), ROT))
                            dst["uv"].append([pU[i][0], pU[i][1]])
                            dst["tan"].append([SCENERY_ID, 0.0, 0.0, 1.0])
                            dst["flat"].append(len(dst["pos"]) - 1)
                        dst["tris"].append([dst["flat"][-3], dst["flat"][-2],
                                            dst["flat"][-1]])
                        n_ens_tris += 1
                    parts_deployed.add(part)
        # THE COVERAGE GATE: every ensemble-aperture ring point must be a vert of some
        # carried component (in the donor frame -- ring keys ARE part-vert keys)
        for r in ensemble_apertures:
            miss = [p for p in r if p not in ens_keys_d]
            if miss:
                raise ValueError(f"ensemble aperture not covered by carried parts "
                                 f"(e.g. {miss[:2]}) -- a needed component was culled")
        # the Donor.txt divert: ONE donor block must carry every deployed part transform
        for (dbx, dby) in B["read_blocks"]:
            ok = True
            for part in parts_deployed:
                try:
                    X.read_block(dbx, dby, disc=disc, game=game, part=part.lower())
                except Exception:
                    ok = False
                    break
            if ok:
                donor_ref = (dbx, dby)
                break
        if donor_ref is None:
            raise ValueError(f"no single donor block carries all ensemble parts "
                             f"{sorted(parts_deployed)} -- the Donor.txt divert needs "
                             f"one prefab with every transform")
        for blk, parts in changed_parts.items():
            sbx, sby = blk
            bm0 = soup["blocks"][blk]
            for part, dst in list(parts.items()):
                parts[part] = X.BlockMesh(
                    name=f"Block[{sbx}][{sby}] {part}", disc=bm0.disc, x=sbx, y=sby,
                    lod=bm0.lod, vcount=len(dst["pos"]), stride=48,
                    channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2),
                              X.CH_TAN: (32, 4)},
                    chan_arrays={X.CH_POS: dst["pos"], X.CH_NRM: dst["nrm"],
                                 X.CH_UV: dst["uv"], X.CH_TAN: dst["tan"]},
                    flat_index=dst["flat"], tris=dst["tris"], raw_vbuf=b"",
                    raw_ibuf=b"", use32=True, submeshes=[])
        log(f"ensemble carry: {n_ens_tris} aux tris "
            f"({', '.join(sorted(parts_deployed))}) across "
            f"{sorted(changed_parts)}; Donor.txt divert -> {donor_ref}")

    return {"changed": changed, "center": (TX, TZ), "rot": ROT, "drop": drop,
            "changed_parts": changed_parts, "donor_ref": donor_ref,
            "report": {"blob_tris": len(blob), "dropped": len(drop),
                       "zip_tris": len(zip_tris), "foot_tris": fc_n,
                       "plugs": len(plug_parents),
                       "ensemble_tris": n_ens_tris,
                       "rot_deg": ROT * 90 if isinstance(ROT, int) else round(ROT * 90, 6),
                       "blocks": [list(b) for b in span],
                       "peak_y": round(float(
                           max(p[1] for ps in carried.values() for p in ps)), 2),
                       "zip_rise": round(zip_rise, 2), "rock_rigid": round(worst_rig, 4),
                       "rock_height": rh, "spread": SPREAD, "rim_splits": rim_splits,
                       "skip_parity": {k: skip_gate[k] for k in ("checked", "flipped")},
                       "apron_slope": round(g_worst, 1), "lifted": len(lift_of),
                       "patched_holes": patched_holes,
                       "lawn_snapped": lawn_snap["entries"],
                       "seam_unified": seam_unify["entries"],
                       "teleport": (math.floor(TX - r_out - 2) + 0.5,
                                    math.floor(TZ) + 0.5)}}


def _lawn_line_snap(new_parents, *, rock_topos, log=print):
    """THE LAWN-LINE SNAP (R5 U5 / UAHO-LAWN-LINE-BENCH.md). Stock seats every fringe contact edge
    -- rock wearing the r10 c6-9 chart tile, against grass -- on the tile's painted lawn line (v =
    phase + 11 rows on 2,081 of 2,088 disc-1 contact-edge ends). A donor rim vertex that stood off it
    at home (Uaho t404/t405, a 2u shore strip nobody sees) reads as bare rock hitting the lawn once the
    zip grass meets it on open ground: the owner's "no transition tile". Each carried fringe-tile
    ("mountain") corner on an edge it shares with a ZIP tri, further than LAWN_LINE_TOL off the line,
    snaps onto it -- in every rock corner at that position, and only where all of them are such
    contacts (an interior tri fanning there would take a v seam instead; that position is left and
    named). UV only: no position moves. Returns (new_parents, {"positions", "entries", "left"})."""
    puA, pvA = ROCK_CHART_PHASE
    lawn = pvA + 11 * 0.03125

    def topo(idall):
        return (int(round(idall)) >> 2) & 0x3F

    zip_edges = set()
    for corners, _idall, fam in new_parents:
        if fam == "zip":
            ks = [kk3(c) for c in corners]
            zip_edges.update(tuple(sorted((ks[a], ks[b]))) for a, b in ((0, 1), (1, 2), (2, 0)))
    rock_at = defaultdict(set)                   # position -> every rock corner (parent, corner) there
    contact_at = defaultdict(set)                # position -> the fringe zip-contact corners there
    off = set()                                  # positions with a contact end off the lawn line
    for pi, (corners, idall, fam) in enumerate(new_parents):
        if topo(idall) not in rock_topos:
            continue
        ks = [kk3(c) for c in corners]
        for ci, k in enumerate(ks):
            rock_at[k].add((pi, ci))
        if fam != "mountain":
            continue
        row = int((sum(c[4] for c in corners) / 3 - pvA) / 0.03125)
        col = int((sum(c[3] for c in corners) / 3 - puA) / 0.0625)
        if row != 10 or col not in (6, 7, 8, 9):
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if tuple(sorted((ks[a], ks[b]))) not in zip_edges:
                continue
            for ci in (a, b):
                contact_at[ks[ci]].add((pi, ci))
                if abs((corners[ci][4] - pvA) / 0.03125 - 11.0) > LAWN_LINE_TOL:
                    off.add(ks[ci])
    snap, left = {}, []
    for k in sorted(off):
        if rock_at[k] <= contact_at[k]:
            for pc in rock_at[k]:
                snap[pc] = lawn
        else:
            left.append(k)
    snap = {pc: v for pc, v in snap.items() if new_parents[pc[0]][0][pc[1]][4] != v}   # real moves only
    out = list(new_parents)
    for pi in sorted({pi for pi, _ci in snap}):
        corners, idall, fam = out[pi]
        out[pi] = (tuple((*c[:4], snap[(pi, ci)], *c[5:]) if (pi, ci) in snap else c
                         for ci, c in enumerate(corners)), idall, fam)
    n_pos = len(off) - len(left)
    if n_pos:
        log(f"lawn-line snap: {n_pos} rim position{'s' if n_pos != 1 else ''}, {len(snap)} carried "
            f"corner{'s' if len(snap) != 1 else ''} onto the fringe row's painted lawn line")
    n_left = sum(1 for k in left for pc in contact_at[k]
                 if abs((new_parents[pc[0]][0][pc[1]][4] - pvA) / 0.03125 - 11.0) > LAWN_LINE_TOL)
    if left:
        log(f"!! lawn-line: {n_left} zip contact end(s) left OFF the lawn line at {len(left)} position(s) "
            f"-- an interior rock tri fans there, a snap would seam it: {left[:3]}")
    return out, {"positions": n_pos, "entries": len(snap), "left": n_left}


def _fringe_seam_unify(new_parents, *, rock_topos, log=print):
    """THE FRINGE-SEAM UNIFY (UAHO-SEAM-BENCH.md, R5b's tooth). Two donor uv charts can meet at a contact tri's
    corner with different v: the fringe band (the blades, at the tile's bottom) then ends at a different height
    either side of their shared edge. Stock has 6 such seams (> FRINGE_SEAM_TOL) in 2,536 shared fringe
    positions on disc 1, every one on a contact tri -- 3 in Uaho's home. At every corner of a carried fringe tri
    with a ZIP contact edge whose fringe corners disagree by more than that, every rock corner there moves to ONE
    v: a value already present (nothing invented) that inverts no rock tri there (the texture never flips),
    moving the fewest corners (then the lower worst density, then the lower v). A position holding a non-carried
    rock corner (plug chart, foot course) or with no flip-free value is left and named. UV only. Returns
    (new_parents, {"positions", "entries", "left"})."""
    puA, pvA = ROCK_CHART_PHASE

    def topo(idall):
        return (int(round(idall)) >> 2) & 0x3F

    def vt(v):
        return (v - pvA) / 0.03125

    def fringe(corners):
        row = int((sum(c[4] for c in corners) / 3 - pvA) / 0.03125)
        col = int((sum(c[3] for c in corners) / 3 - puA) / 0.0625)
        return row == 10 and col in (6, 7, 8, 9)

    def flips(pts):                              # pairs whose v order disagrees with the height order
        return {(i, j) for i in range(3) for j in range(3)
                if pts[i][0] < pts[j][0] - 0.05 and pts[i][1] < pts[j][1] - 1e-3}

    zip_edges = set()
    for corners, _idall, fam in new_parents:
        if fam == "zip":
            ks = [kk3(c) for c in corners]
            zip_edges.update(tuple(sorted((ks[a], ks[b]))) for a, b in ((0, 1), (1, 2), (2, 0)))
    cur = [list(corners) for corners, _i, _f in new_parents]
    rock_at = defaultdict(list)                  # position -> [(parent, corner)] of every rock corner there
    scope = set()
    for pi, (corners, idall, fam) in enumerate(new_parents):
        if topo(idall) not in rock_topos:
            continue
        ks = [kk3(c) for c in corners]
        for ci, k in enumerate(ks):
            rock_at[k].append((pi, ci))
        if fam == "mountain" and fringe(corners) and any(
                tuple(sorted((ks[a], ks[b]))) in zip_edges for a, b in ((0, 1), (1, 2), (2, 0))):
            scope.update(ks)
    n_pos, moved, left = 0, set(), []
    for k in sorted(scope):
        here = rock_at[k]
        fr = [vt(cur[pi][ci][4]) for pi, ci in here if fringe(cur[pi])]
        if len(fr) < 2 or max(fr) - min(fr) <= FRINGE_SEAM_TOL:
            continue
        if any(new_parents[pi][2] != "mountain" for pi, _ci in here):
            left.append(k)
            continue
        best = None
        for cand in sorted({cur[pi][ci][4] for pi, ci in here}):
            n_move, worst, ok = 0, 0.0, True
            for pi, ci in here:
                before = [(c[1], vt(c[4])) for c in cur[pi]]
                after = [(c[1], vt(cand) if j == ci else vt(c[4])) for j, c in enumerate(cur[pi])]
                if flips(after) - flips(before):
                    ok = False
                    break
                n_move += cur[pi][ci][4] != cand
                ys, vs = [p[0] for p in after], [p[1] for p in after]
                worst = max(worst, (max(vs) - min(vs)) / max(1e-6, max(ys) - min(ys)))
            if ok and (best is None or (n_move, worst, cand) < best):
                best = (n_move, worst, cand)
        if best is None:
            left.append(k)
            continue
        n_pos += 1
        for pi, ci in here:
            if cur[pi][ci][4] != best[2]:
                c = cur[pi][ci]
                cur[pi][ci] = (*c[:4], best[2], *c[5:])
                moved.add((pi, ci))
    out = [(tuple(cur[pi]), idall, fam) if any((pi, ci) in moved for ci in range(3)) else (corners, idall, fam)
           for pi, (corners, idall, fam) in enumerate(new_parents)]
    if n_pos:
        log(f"fringe-seam unify: {n_pos} position{'s' if n_pos != 1 else ''}, {len(moved)} carried "
            f"corner{'s' if len(moved) != 1 else ''} onto one present v (no flip, fewest moves)")
    if left:
        log(f"!! fringe-seam: {len(left)} seam position(s) left (a non-carried rock corner there, or every "
            f"present value would flip a tri): {left[:3]}")
    return out, {"positions": n_pos, "entries": len(moved), "left": len(left)}


def _atlas_gate_mountain(new_parents, *, game=None, log=print):
    """The Moguri-atlas alpha gate (the study's section 7 gate, minus the eye renders):
    every new tri's interior must sample painted texels -- blank = transparent AND dark
    (Moguri paints some in-tile edge strips with alpha 0 that an alpha-ignored opaque
    shader renders fine; true gutter garbage is transparent AND near-black) -- and none may
    sample a pure-WHITE gutter texel (every RGB >= :data:`ATLAS_GUTTER_WHITE`): the 1-texel
    lines between the atlas's painted regions, which render as a white sliver (round 21's
    comp9 plug). Calibrated by snowmassif/gutter_census.py: 0 of disc 1's stock Terrain tris
    sample one at this sampler. Skips with a log line when the Moguri worldmap atlas isn't
    installed -- it is a texture-source check, not a geometry gate."""
    from .. import config
    gp = Path(config.find_game_path(game))
    mog = gp / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
        "textures" / "res(1_24)_terrain.png"
    if not mog.exists():
        log("atlas gate SKIPPED (no Moguri worldmap atlas found)")
        return
    from PIL import Image
    atlas = Image.open(mog).convert("RGBA")
    AW, AH = atlas.size
    APX = atlas.load()

    def at_b(u_, v_):
        fx = (u_ % 1.0) * AW - 0.5
        fy = (1.0 - v_ % 1.0) * AH - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        a4 = [0.0, 0.0, 0.0, 0.0]
        for (dx2, dy2, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                               (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            px_, py_ = min(max(x0 + dx2, 0), AW - 1), min(max(y0 + dy2, 0), AH - 1)
            r, g2, b2, al = APX[px_, py_]
            a4[0] += r * wg; a4[1] += g2 * wg; a4[2] += b2 * wg; a4[3] += al * wg
        return a4[3], (int(a4[0]), int(a4[1]), int(a4[2]))

    blank = gutter = 0
    for corners, _, fam in new_parents:
        nb = nw = 0
        for ii in range(11):
            for jj in range(11 - ii):
                w0, w1 = ii / 10.0, jj / 10.0
                w2 = 1 - w0 - w1
                if w2 < -1e-9:
                    continue
                u_ = w0 * corners[0][3] + w1 * corners[1][3] + w2 * corners[2][3]
                v_ = w0 * corners[0][4] + w1 * corners[1][4] + w2 * corners[2][4]
                aa_, rgb_ = at_b(u_, v_)
                if aa_ < 24 and sum(rgb_) < 90:
                    nb += 1
                elif min(rgb_) >= ATLAS_GUTTER_WHITE:
                    nw += 1
        if nb:
            blank += 1
            log(f"  BLANK {fam} nb={nb} uv "
                f"{[(round(c[3], 4), round(c[4], 4)) for c in corners]} "
                f"at ({corners[0][0]:.1f},{corners[0][2]:.1f})")
        if nw:
            gutter += 1
            log(f"  GUTTER {fam} white={nw} uv "
                f"{[(round(c[3], 4), round(c[4], 4)) for c in corners]} "
                f"at ({corners[0][0]:.1f},{corners[0][2]:.1f})")
    log(f"atlas gate: transparent-sampling tris = {blank}, white-gutter tris = {gutter} (want 0 and 0)")
    if blank:
        raise ValueError(f"{blank} new tri(s) sample transparent atlas texels")
    if gutter:
        raise ValueError(f"{gutter} new tri(s) sample the atlas's white gutter texels (a white sliver in game)")


# ---- census + deploy ------------------------------------------------------------------------
def census_gate(changed, *, disc: int = 1, game=None, log=print, probe=None, baseline=None,
                parts=None, stack=None):
    """Per changed block: the engine placement census (hidden aux parts + the CUT sea plane)
    must ground EVERYWHERE (MISS=0). ``probe = ((wx, wz), expected_topo)`` additionally
    grounds one world point.

    THE SEA IS CUT, NOT WHOLE (dead-gate revival, audit rec 4): the island lane deploys
    ``_cut_plane`` Sea4 -- no ocean under land (SEA4-UNDER-LAND) -- so censusing an UNCUT
    plane made ``MISS == 0`` unreachable for the terrain-hole class this gate exists to
    catch (a hole grounded on phantom sea at y=0). ``baseline`` maps blk -> the PRE-EDIT
    terrain: the disk's Sea4 was cut against THAT footprint, so a hole the edit opens has
    nothing beneath it exactly when the gate cuts against the same baseline. Without
    ``baseline`` the cut falls back to the edited bm (the island-lane configuration --
    still strictly closer to shipping bytes than the whole plane).

    THE REAL CARRIED PARTS (audit rec 11): ``parts`` maps blk -> {part: BlockMesh} of the
    auxiliary overrides the deploy actually ships (``world-mountain``'s ensemble
    Object/Falls/River/RiverJoint from ``res["changed_parts"]``). They REPLACE the hidden
    blanks, so the census measures the deployed stack: Object registers AHEAD of Terrain,
    so a carried massif Object over the probe point now FAILS the probe instead of passing
    by omission.

    THE SEAM WRAP: ``changed`` keys may be unwrapped seam columns (:func:`read_deployed_blocks`);
    the stack is censused under the WRAPPED label it deploys as (one label per block-local
    census), while the probe's world->local step keeps the unwrapped key -- the soup's frame.

    THE DEPLOYED STACK (the river island, RUNG5.md "The forest after the seam rung"): ``stack``
    maps blk -> {part: BlockMesh} of every override the block already ships besides Terrain
    (:func:`read_deployed_stack`). Given it, the census measures what the game loads -- the
    deployed parts stand in for the hidden blanks and the re-cut sea (a river's Stream /
    RiverJoint cover its channel) -- and it measures the CARVE, not the island: the same census
    runs on the PRISTINE stack (the ``baseline`` Terrain under the same parts), and a MISS or
    stacked sample the pristine stack already has is the island's own (``world-river``'s
    home-miss subtraction, ``river.audit_written``): logged, not refused. A sample the carve
    newly strands still refuses. ``parts`` keeps its meaning: a block it names ships exactly
    those :data:`ENSEMBLE_PARTS` (carried content, else the blank ``deploy_mountain_parts``
    writes -- :func:`census_parts`), so the deployed ones it replaces leave the edited stack."""
    from . import placement as P
    if stack is not None and baseline is None:
        raise ValueError("census_gate: stack= measures the carve against the pristine stack -- "
                         "pass baseline= (the blocks as read before the carve)")
    if stack is None:
        from .island import _sea_plane, _cut_plane
        plane = _sea_plane(disc, game=game)
    home_miss = home_stacked = 0
    for blk, bm in sorted(changed.items()):
        bx, by = blk
        wbx = M.wrap_block_col(bx)
        if stack is None:
            hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=disc, x=wbx, y=by)  # noqa: E731
            under = baseline.get(blk, bm) if baseline is not None else bm
            by_name = {"Object": hid("Object"), "Terrain": _wrap_label(bm, "Terrain"), "Sea1": hid("Sea1"),
                       "Sea2": hid("Sea2"), "Sea3": hid("Sea3"),
                       # the census's sea MODEL keeps the corner rule: a hole the carve punched in the land
                       # loses the sea beneath it and reads MISS (an area cut would keep that sea, hiding it)
                       "Sea4": _cut_plane(plane, bx, by, frozenset(), under, label_x=wbx, rule="corners"),
                       "Sea5": hid("Sea5")}
            by_name.update((p_, _wrap_label(m_, p_)) for p_, m_ in ((parts or {}).get(blk) or {}).items())
            meshlist = P.build_meshlist(by_name)
            cen = P.census(meshlist, frame="block_local")
            miss, stacked = cen["miss"], cen["stacked"]
        else:
            if blk not in baseline:
                raise ValueError(f"census_gate: no baseline Terrain for {blk} -- the pristine stack "
                                 f"is what the carve is measured against")
            aux = {P.canonical_part(p_): _wrap_label(m_, P.canonical_part(p_))
                   for p_, m_ in (stack.get(blk) or {}).items() if P.canonical_part(p_) != "Terrain"}
            pristine = P.build_meshlist({**aux, "Terrain": _wrap_label(baseline[blk], "Terrain")})
            if parts is not None and blk in parts:
                aux = {p_: m_ for p_, m_ in aux.items() if p_ not in ENSEMBLE_PARTS}
                aux.update((P.canonical_part(p_), _wrap_label(m_, P.canonical_part(p_)))
                           for p_, m_ in (parts[blk] or {}).items())
            meshlist = P.build_meshlist({**aux, "Terrain": _wrap_label(bm, "Terrain")})
            cen = P.census(meshlist, frame="block_local")
            cen0 = P.census(pristine, frame="block_local")
            had_miss, had_stack = set(cen0["miss"]), {r["at"] for r in cen0["stacked"]}
            miss = [m_ for m_ in cen["miss"] if m_ not in had_miss]
            stacked = [r for r in cen["stacked"] if r["at"] not in had_stack]
            home_miss += len(cen["miss"]) - len(miss)
            home_stacked += len(cen["stacked"]) - len(stacked)
        def _world(pts):                                # block-local census samples -> world (x, z)
            return [(px + BLOCK * bx, pz - BLOCK * by) for px, pz in pts]
        if miss:
            raise CarveRefused("census", f"placement MISS in {blk}: {miss[:4]}", _world(miss))
        if stacked:
            # the lawn-under-hill class (BENCH-WALK-SIM's playtest pin): a walkable sheet
            # UNDER a walkable sheet -- first-in-buffer wins, so the player grounds beneath
            # the surface. A carve must REMOVE the ground it covers, not leave it stacked.
            worst = max(stacked, key=lambda r: r["gap"])
            raise CarveRefused("census", f"stacked walkable sheets in {blk}: {len(stacked)} sample(s), "
                               f"worst at {worst['at']} gap {worst['gap']}u "
                               f"({sum(1 for r in stacked if r['shadowed'])} shadowed)",
                               _world([r["at"] for r in stacked]))
        if probe:
            (wx, wz), want_topo = probe
            lx, lz = wx - BLOCK * bx, wz + BLOCK * (by + 1) - BLOCK
            if 0.0 <= lx <= BLOCK and -BLOCK <= lz <= 0.0:
                gy, nm_, _, topo = P.place(meshlist, lx, lz)
                log(f"probe grounds in {blk}: y={gy:.2f} {nm_} topo {topo}")
                if nm_ != "Terrain" or topo != want_topo:
                    raise CarveRefused("census", f"probe grounded on {nm_} topo {topo}, "
                                       f"expected Terrain topo {want_topo}", [(wx, wz)])
    if stack is None:
        log("placement census: MISS=0 in changed blocks")
    else:
        log(f"placement census (deployed stack): no new MISS in changed blocks"
            + (f" ({home_miss} MISS / {home_stacked} stacked sample(s) the pristine stack already has: "
               f"the island's own)" if home_miss or home_stacked else ""))


def read_deployed_stack(mod_folder: str, blocks, *, disc: int = 1, lod: str = "0_1", game=None,
                        target_disc: int | None = None) -> dict:
    """blk -> {part: BlockMesh}: every override each of ``blocks`` already ships BESIDES its
    Terrain -- what :func:`census_gate`'s ``stack=`` measures (an island's cut Sea4 and blanks,
    a river island's Stream/River/RiverJoint/Beach/Sea parts). The read of
    :func:`read_deployed_blocks`, same namespace (``target_disc``) and same seam wrap: the key
    stays the unwrapped column, the file read is its wrapped label's. Only parts the engine
    registers (:data:`placement.REGISTRATION_ORDER`) are read; a block with none maps to {}."""
    from .. import config
    from . import placement as P
    if not blocks:
        return {}
    rtarget = disc if target_disc is None else int(target_disc)
    root = Path(config.find_game_path(game)) / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{rtarget}" / lod
    out = {}
    for bx, by in sorted(blocks):
        wbx = M.wrap_block_col(bx)
        pre = f"Block[{wbx}][{by}] "
        got = {}
        for f in sorted((root / f"r{by}").glob(f"Block[[]{wbx}[]][[]{by}[]] *.ff9mesh")):
            part = P.canonical_part(f.name[len(pre):-len(".ff9mesh")])
            if part is None or part == "Terrain":
                continue
            got[part] = M.blockmesh_from_ff9mesh(f, disc=rtarget, x=bx, y=by, lod=lod, part=part.lower())
        out[(bx, by)] = got
    return out


def census_parts(res) -> dict:
    """``census_gate``'s ``parts=`` for a ``carve_mountain`` result: exactly the
    :data:`ENSEMBLE_PARTS` :func:`deploy_mountain_parts` writes. With an ensemble divert
    (``donor_ref``) it writes every part on EVERY span block -- carried content, else a blank --
    so each span block maps to its carried parts, possibly none; without one it writes no aux
    part and this is ``changed_parts`` as before."""
    cp = res.get("changed_parts") or {}
    if res.get("donor_ref") is None:
        return cp
    return {**{tuple(b): {} for b in res["report"]["blocks"]}, **cp}


def deploy_mountain_parts(res, *, mod_folder: str, disc: int = 1, lod: str = "0_1",
                          game=None, skip_mirror: bool = False, log=print,
                          target_disc: int | None = None) -> list:
    """Deploy an ENSEMBLE carve's auxiliary part overrides: every span block gets ALL
    of :data:`ENSEMBLE_PARTS` (carried content or a hidden blank -- the donor prefab's
    own parts would otherwise FREE-RIDE verbatim at rot0/shift0), plus a ``Donor.txt``
    naming the part-carrying donor block (the s34 divert binds each override to the
    prefab's part transform BY NAME, so the donor must carry every deployed part). Auto-
    mirrors the written overrides to Disc4 (THE DISC-4 GAP; ``skip_mirror=True`` opts out --
    the ``world-mountain`` CLI passes ``skip_mirror=DEFERRED`` to BOTH this and its
    :func:`deploy_changed` call, then makes the one mirror pass itself over the union
    of both writers' written paths)."""
    changed_parts = res.get("changed_parts") or {}
    donor_ref = res.get("donor_ref")
    if donor_ref is None:
        return []
    rtarget = disc if target_disc is None else int(target_disc)   # THE READ/WRITE DISC SPLIT
    out = []
    span = [tuple(b) for b in res["report"]["blocks"]]
    # THE SEAM WRAP: span keys are the soup's unwrapped columns; everything this writer names,
    # probes or writes is the WRAPPED label (_wrap_label -- the island lane's deploy-stage relabel)
    _require_one_label_per_cell(span, "deploy_mountain_parts")
    wspan = [(M.wrap_block_col(bx), by) for bx, by in span]
    # THE MOD-OVERWRITE GATE, as a WARN ROW -- deliberately NOT a refusal. The interior verbs
    # reshape an ALREADY-DEPLOYED kit island (`read_deployed_blocks` refuses when the mod tree is
    # EMPTY), so occupancy at a span block is the normal case and a refusal would be a wall, not a
    # guard rail -- the same reason `terrain.reshape` and `transplant.morph_in_place` are ungated.
    # The hazard worth NAMING is narrower and real: this writer replaces every ENSEMBLE_PART with
    # carried content OR A HIDDEN BLANK, and it never reads those parts back, so a prior deploy's
    # Object (e.g. a `world-entrance` building) at a span block is erased without a word.
    prior = M.existing_overrides(wspan, mod_folder, disc=rtarget, lod=lod, game=game,
                                 parts=ENSEMBLE_PARTS)
    if prior:
        log(f"!! WARNING: {len(prior)} {'/'.join(ENSEMBLE_PARTS)} override(s) already deployed on "
            f"the span -- this deploy REPLACES each with carried content or a hidden blank "
            f"(a prior building/falls/river at these blocks is erased): {prior[:6]}")
    for blk, (wbx, by) in zip(span, wspan):
        for part in ENSEMBLE_PARTS:
            bmP = changed_parts.get(blk, {}).get(part)
            if bmP is None:
                bmP = M.hidden_block_mesh(name=f"Block[{wbx}][{by}] {part}", disc=rtarget,
                                          x=wbx, y=by, lod=lod)
            p = M.deploy_override(_wrap_label(bmP, part), mod_folder=mod_folder, game=game,
                                  lod=lod, part=part, disc=rtarget)
            if len(bmP.tris):
                log(f"deployed {part} -> {p} ({len(bmP.tris)} tris)")
            out.append(p)
        out.append(M.deploy_donor_sidecar(donor_ref[0], donor_ref[1], mod_folder=mod_folder,
                                          disc=rtarget, x=wbx, y=by, lod=lod, game=game))
    log(f"Donor.txt -> {donor_ref} on {len(span)} span block(s) "
        f"(+ blanks for uncarried parts)")
    from . import discmirror as DM
    DM.auto_mirror(out, mod_folder=mod_folder, skip_mirror=skip_mirror, log=log)
    return out


def deploy_changed(changed, *, mod_folder: str, disc: int = 1, lod: str = "0_1",
                   game=None, backup: bool = True, skip_mirror: bool = False, log=print,
                   target_disc: int | None = None) -> list:
    """Deploy every block whose bytes actually change (byte-compare converge). An
    existing override backs up beside itself as ``<name>.ff9mesh.bak-<ts>`` (a suffixed
    name never matches the engine's override pattern). When anything actually deployed,
    auto-mirrors the written overrides to Disc4 (THE DISC-4 GAP; ``skip_mirror=True`` opts
    out -- the ``world-mountain`` CLI passes ``skip_mirror=DEFERRED`` to BOTH this and
    :func:`deploy_mountain_parts`, then makes the one mirror pass itself over the union
    of both writers' written paths)."""
    from .. import config
    import tempfile
    rtarget = disc if target_disc is None else int(target_disc)   # THE READ/WRITE DISC SPLIT:
    # the byte-compare/backup root and the write must aim at the SAME namespace -- comparing
    # against Disc1 while writing Disc9 would defeat the converge check AND back up the wrong file.
    gp = Path(config.find_game_path(game))
    root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{rtarget}" / lod
    # NO MOD-OVERWRITE GATE HERE, and that is the measured answer, not an oversight. Every block in
    # `changed` came from `read_deployed_blocks` -- this writer READS the deployed Terrain override
    # and writes the morphed bytes back -- so an occupancy gate would fire on 100% of legitimate runs
    # (and a warn row would be 100% vacuous). The byte-compare converge below is the real guard: a
    # block whose bytes do not change is not written at all.
    # THE SEAM WRAP: keys may be the soup's unwrapped seam columns -- the compare reads, and the
    # write lands at, the WRAPPED label (_wrap_label, the island lane's deploy-stage relabel).
    _require_one_label_per_cell(changed, "deploy_changed")
    out = []
    with tempfile.TemporaryDirectory(prefix="ff9_interior_") as tmpdir:
        tmp = Path(tmpdir)
        for blk, bm in sorted(changed.items()):
            bx, by = blk
            wbx = M.wrap_block_col(bx)
            dep = root / f"r{by}" / f"Block[{wbx}][{by}] Terrain.ff9mesh"
            bm = _wrap_label(bm, "Terrain")
            new = M.write_ff9mesh(bm, tmp / f"fin_{wbx}_{by}.ff9mesh").read_bytes()
            if dep.exists() and dep.read_bytes() == new:
                continue
            # the backup now lives at THE one write seam (deploy_override, audit rec 6)
            p = M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part="Terrain",
                                  disc=rtarget, backup=backup)
            log(f"deployed -> {p} ({len(bm.tris)} tris)")
            out.append(p)
    if not out:
        log("no block's bytes changed -- nothing deployed")
    else:
        from . import discmirror as DM
        DM.auto_mirror(out, mod_folder=mod_folder, skip_mirror=skip_mirror, log=log)
    return out
