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
MTN_MAX_EDGE = 9.0               # max new-tri edge length
MTN_ZIP_RISE = 2.34              # zip-tri vertical span ceiling (engine step 2.34375)
MTN_ZIP_NY_MIN = 0.83            # the zip winding ENVELOPE (~34 deg -- admits the Uaho
#                                  alcove-mouth bank); a real donor rim may force a FEW
#                                  steeper banks (the horseshoe's falls outlet: 2/137)
MTN_ZIP_NY_FLOOR = 0.5           # the hard per-tri floor (~60 deg) for those banks
MTN_ZIP_BANK_MAX = 2             # max zip tris allowed between FLOOR and ENVELOPE
MTN_ROCK_RIGID = 0.035           # THE ROCK-RIGID GATE: max carried-edge length drift
MTN_APRON_SLOPE = 29.5           # the grass apron's slope envelope (deg)
# The terrain atlas's rock-band UV phase (u, v) -- measured by daguerreo_massif_anatomy.py
# (its out/daguerreo_massif.json "phase"); the aperture-plug chart gate quantizes against
# it (cols 5-10, rows 6-12 = the painted rock band).
ROCK_CHART_PHASE = (0.015625, 0.01953125)
# THE ENSEMBLE CARRY's auxiliary part universe (canonical override spellings): a big
# massif's aperture is a river/falls MOUTH whose ring is owned by the UNION of these
# parts (the horseshoe: object 22 + falls 12 + river 15 + riverjoint 4 of 43 ring pts) --
# the parts carry under the same rigid map and cover the hole in-game exactly as stock.
ENSEMBLE_PARTS = ("Object", "Falls", "River", "RiverJoint")

kk3 = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))  # noqa: E731


# ---- the island soup ----------------------------------------------------------------------
def soup_from_blocks(blocks: dict) -> dict:
    """Build the WORLD-frame island soup from ``{(bx, by): BlockMesh}`` (freshly built or
    deployed-and-read-back -- one code path). Fams classify from the BYTES (the hill
    study's proven derivation): topo 37 = forest, 58 = rock, other nonzero = topoN,
    topo 0 = ``main`` when every corner u sits in the mains atlas region else ``stamp``.
    ``coast`` = the (x, z) of every topo-58 vert (the rim-clearance proxy)."""
    order = sorted(blocks)
    pos, nrm, tris, meta, coast = [], [], [], [], []
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
    return {"pos": pos, "nrm": nrm, "tris": tris, "meta": meta,
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
    ``census_gate``), which is why it is a separate parameter."""
    from .. import config
    rtarget = disc if target_disc is None else int(target_disc)
    gp = Path(config.find_game_path(game))
    root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{rtarget}" / lod
    wx, wz = near
    bx0, bx1 = int(math.floor((wx - reach) / BLOCK)), int(math.floor((wx + reach) / BLOCK))
    by0, by1 = int(math.floor(-(wz + reach) / BLOCK)), int(math.floor(-(wz - reach) / BLOCK))
    out = {}
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
            if p.exists():
                out[(bx, by)] = M.blockmesh_from_ff9mesh(p, disc=rtarget, x=bx, y=by,
                                                         lod=lod, part="terrain")
    if not out:
        raise ValueError(f"no deployed Terrain overrides near world ({wx:.0f},{wz:.0f}) "
                         f"in {mod_folder} -- these verbs reshape DEPLOYED kit islands only")
    return out


# ---- shared geometry helpers ---------------------------------------------------------------
def chain_ring(edges, what: str):
    """Chain once-edges into one simple cycle (raises on degeneracy)."""
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
    if len(ring) != len({*ring}) or len(ring) < 12:
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


# ---- THE FOREST CARVE -----------------------------------------------------------------------
def carve_forest(soup, *, center=None, near=None, donor=FOREST_DONOR, disc: int = 1,
                 game=None, log=print) -> dict:
    """Carry the donor block's topo-37 canopy blob onto the island at ``center`` (exact
    blob centre) or the best lawful placement near ``near``. Returns ``{"changed",
    "center", "report"}``; raises ``ValueError`` on any gate."""
    import numpy as np
    gpos, gtris, gmeta, gnrm = soup["pos"], soup["tris"], soup["meta"], soup["nrm"]

    # donor blob, verbatim, world frame
    don = X.read_block(donor[0], donor[1], disc=disc, game=game)
    dv = np.asarray(don.verts, dtype=np.float64)
    dv_w = dv + np.array([BLOCK * donor[0], 0.0, -BLOCK * donor[1]])
    duv = np.asarray(don.uvs, dtype=np.float64)
    dnrm = don.normals
    dtan = don.tangents
    dtopo = [X.decode_id(int(dtan[t[0]][0]))["topograph"] for t in don.tris]
    blob = [t for t in range(len(don.tris)) if dtopo[t] == 37]
    if not blob:
        raise ValueError(f"donor block {donor} has no topo-37 canopy")
    bpts = np.array([dv_w[i] for t in blob for i in don.tris[t]])
    c_local = ((bpts[:, 0].min() + bpts[:, 0].max()) / 2, (bpts[:, 2].min() + bpts[:, 2].max()) / 2)
    edge_use = Counter()
    for t in blob:
        tri = don.tris[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_use[tuple(sorted((kk3(dv_w[tri[a]]), kk3(dv_w[tri[b]]))))] += 1
    rim = chain_ring([e for e, n in edge_use.items() if n == 1], "donor rim")
    rim_set = set(rim)
    rim_poly_local = [(p[0], p[2]) for p in rim]
    log(f"donor blob: {len(blob)} tris, rim ring {len(rim)} positions")

    tri_c = _tri_centroids(soup)

    def poly_at(dx, dz):
        return [(x + dx, z + dz) for (x, z) in rim_poly_local]

    def footprint_lawful(poly):
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
                return None
            for i in tri:
                if _coast_d2(soup, gpos[i][0], gpos[i][2]) < RIM_MARGIN ** 2:
                    return None
        return seen

    if center is not None:
        TX, TZ = center
        poly = poly_at(TX - c_local[0], TZ - c_local[1])
        seen = footprint_lawful(poly)
        if seen is None or seen < 40:
            raise ValueError(f"footprint at ({TX},{TZ}) is not lawful plain-grass mains "
                             f"clear of the rim (seen={seen})")
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
            raise ValueError("no lawful placement -- the island has no plain-grass pocket "
                             "for this blob near the given point")
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
        raise ValueError(f"hole reaches non-mains island tris (fams {dict(dropped_fams)})")
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
        tri = don.tris[t]
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
            tri = don.tris[t]
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

    carried = {t: [carry_vert(i) for i in don.tris[t]] for t in blob}
    c_edge_use = Counter()
    c_float = {}
    for t in blob:
        ps = carried[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = kk3(ps[a]), kk3(ps[b])
            c_float.setdefault(ka, ps[a])
            c_float.setdefault(kb, ps[b])
            c_edge_use[tuple(sorted((ka, kb)))] += 1
    crim = chain_ring([e for e, n in c_edge_use.items() if n == 1], "carried rim")
    rim_nrm = {}
    for t in blob:
        tri = don.tris[t]
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

    hole_ord = list(hole)
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
        tri = don.tris[t]
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
        raise ValueError(f"carve leaks outside the deployed blocks: "
                         f"{sorted(set(new_by_block) - set(soup['blocks']))}")

    changed = _assemble(soup, drop, new_by_block)

    # gates (the study's section 9)
    worst_wall = 0.0
    crim_keys = {kk3(c_float[r]) for r in crim}
    for t in blob:
        ps = carried[t]
        if any(kk3(p) in crim_keys for p in ps):
            worst_wall = max(worst_wall, max(p[1] for p in ps) - min(p[1] for p in ps))
    va = np.array([[c[0], c[1], c[2]] for corners, _, _ in new_parents for c in corners])
    maxe = 0.0
    down = 0
    for kdx in range(0, len(va), 3):
        a, b, c = va[kdx], va[kdx + 1], va[kdx + 2]
        n = np.cross(b - a, c - a)
        if n[1] < 0:
            down += 1
        for pq in ((a, b), (b, c), (c, a)):
            maxe = max(maxe, float(np.linalg.norm(pq[0] - pq[1])))
    ring_pts = np.array([list(p) for p in hole_ord] + [list(rimw(p)) for p in rim_ord])
    nm = 0
    for a_ in range(len(ring_pts)):
        dd = np.sum((ring_pts - ring_pts[a_]) ** 2, axis=1)
        nm += int(((dd > 1e-9) & (dd < 0.0025)).sum())
    eu = Counter()
    for blk, bm in changed.items():
        v_ = bm.chan_arrays[X.CH_POS]
        bx, by = blk
        for tri in bm.tris:
            w = [(v_[i][0] + BLOCK * bx, v_[i][1], v_[i][2] - BLOCK * (by + 1) + BLOCK)
                 for i in tri]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
    inner_once = [e for e, n in eu.items() if n == 1
                  and near_poly((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2,
                                poly, RING_BAND + 2.0)]
    log(f"gates: down={down} maxEdge={maxe:.1f} nearMiss={nm // 2} "
        f"annulusOnce={len(inner_once)} wallRise={worst_wall:.2f} "
        f"zipRise={worst_zip_rise:.2f} zipNyMin={zip_ny_min:.2f}")
    if down or nm or inner_once or maxe >= 9.0:
        raise ValueError("forest geometry gate failed (down/near-miss/annulus-crack/edge)")
    if worst_wall > 2.34 or worst_zip_rise > 2.34 or zip_ny_min <= 0.1:
        raise ValueError("THE CANOPY STEP LAW gate failed (wall/zip rise or zip winding)")

    _perimeter_walk_in_gate(changed, [rimw(p) for p in rim_ord], poly, log=log)

    return {"changed": changed, "center": (TX, TZ), "drop": drop,
            "zip_cells": cell_qo, "zip_fallback": dropped,
            "report": {"blob_tris": len(blob), "dropped": len(drop),
                       "zip_tris": len(zip_tris), "zip_fallback_cells": len(dropped),
                       "wall_rise": round(worst_wall, 2),
                       "zip_rise": round(worst_zip_rise, 2)}}


def _assemble(soup, drop, new_by_block):
    """Re-emit per-block meshes: kept tris byte-exact from the soup, new tris appended."""
    gpos, gtris, gmeta, gnrm = soup["pos"], soup["tris"], soup["meta"], soup["nrm"]
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
                     (u, v), gnrm[vid], [idall, 0.0, 0.0, 1.0])
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
    _wml = [("Terrain", _w)]
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
                hy, nm_, _, _tp = P2.place(_wml, sx + nxo * d, sz + nzo * d, sky=True)
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
        raise ValueError(f"a rim segment climbs {worst[0]:.2f} > {GATE_CLIMB} at {worst[1]}")


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

    eu = Counter()
    for i, tri in enumerate(gtris):
        if math.hypot(tri_cx[i] - CX, tri_cz[i] - CZ) > radius + 8:
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((kk3(gpos2[tri[a]]), kk3(gpos2[tri[b]]))))] += 1
    inner_once = [e for e, n in eu.items() if n == 1
                  and math.hypot((e[0][0] + e[1][0]) / 2 - CX,
                                 (e[0][2] + e[1][2]) / 2 - CZ) < radius + 4]
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
                       "peak_y": round(peak_y, 2)}}


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
    if alcove_box is not None:
        (nx0, nx1), (nz0, nz1), ny_min = alcove_box
        NBOX = lambda c: nx0 < c[0] < nx1 and nz0 < c[2] < nz1  # noqa: E731
        seeds = []
        for e in once_edges(blob):
            for t in d_edge[e]:
                if t not in blob and dtopo[t] == 0:        # floor tris only, never canopy
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
                    if t2 not in blob and dtopo[t2] == 0:
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


def carve_mountain(soup, *, center=None, near=None, donor=MOUNTAIN_DONOR,
                   rock_topos=MOUNTAIN_ROCK_TOPOS, alcove="auto", clear=MTN_CLEAR,
                   scan_band=None, gblend=MTN_GBLEND, search_radius=10, search_step=2,
                   scan_cutoff=60, ground: str = "grass", disc: int = 1, game=None,
                   log=print) -> dict:
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
    donor's own anatomy pass first -- see the studies README).

    ``ground`` picks the bench's walkable ground family (:data:`grassland.GROUNDS` --
    the byte-measured TRANSLATION LAWS): the plain-ground classification, the zip
    annulus's mains UVs + topograph, and the outside-the-rim probe all speak that
    family. ``"grass"`` is the bit-frozen identity (the Uaho acceptance).

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

    # THE DONOR-DISPATCH STRIP: a carried IDALL keeps its topograph + flags but drops the
    # donor's event/area bits -- those are DISPATCH CONTEXT (area feeds the overworld
    # camera's place bucket via w_cameraArea2Place -- Uaho's baked area=63 is bucket 2 =
    # cameraDistance 6000, the alcove zoom-out quirk -- and event 1-3 marks a PLACE
    # ENTRANCE tile that fires the world .eb), meaningless and hazardous on a custom
    # island. The kit's own synthetic emitters default to area=0/event=0.
    def strip_dispatch(idall_f):
        d = X.decode_id(int(round(idall_f)))
        return float(X.encode_id(topograph=d["topograph"], flags=d["flags"]))

    # ---- 1. the donor blob ----------------------------------------------------------------
    B = _mountain_blob(donor_blocks, rock_topos=ROCK, alcove_box=alcove_box,
                       disc=disc, game=game, log=log)
    dV, dU, dN, dT = B["dV"], B["dU"], B["dN"], B["dT"]
    dtri, dtopo, d_edge = B["dtri"], B["dtopo"], B["d_edge"]
    blob, rim, rim_set, apertures = B["blob"], B["rim"], B["rim_set"], B["apertures"]
    ensemble_apertures = B["ensemble_apertures"]
    sweep = B["sweep"]
    oV, oN, otris = B["oV"], B["oN"], B["otris"]
    c_local, r_rim, ta, tb = B["c_local"], B["r_rim"], B["ta"], B["tb"]
    dV2, dN2, rim2 = B["dV2"], B["dN2"], B["rim2"]

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
    if 2.0 * half <= BLOCK:
        # the proven single-block pipeline (byte-frozen -- the Uaho identity acceptance)
        span = [seed_blk]
    else:
        def rect(h):
            sx0 = int(math.floor((CX - h) / BLOCK))
            sx1 = int(math.floor((CX + h) / BLOCK))
            sy0 = int(math.floor(-(CZ + h) / BLOCK))
            sy1 = int(math.floor(-(CZ - h) / BLOCK))
            return [(sbx, sby) for sby in range(sy0, sy1 + 1)
                    for sbx in range(sx0, sx1 + 1)]
        # the CORE rect (rim + band) must be fully covered -- the hole/zip live there.
        # Around it, widen the span with every PRESENT block of the APRON rect (rim +
        # gblend): the lift taper only fires at borders facing non-span blocks, and a
        # rim within gblend of such a border starves the apron (the horseshoe's 0.59-ny
        # zip bank). Present neighbours weld through the per-POSITION lift; absent ones
        # (true ocean, no twin verts) keep the taper, which is then exactly right.
        core = rect(half)
        missing = [b for b in core if b not in soup["blocks"]]
        if missing:
            raise ValueError(f"the massif footprint around ({CX:.0f},{CZ:.0f}) needs "
                             f"deployed Terrain overrides on blocks {sorted(core)}, but "
                             f"{sorted(missing)} have none -- mint a bigger island first")
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
        raise ValueError(f"the massif footprint around ({CX:.0f},{CZ:.0f}) needs deployed "
                         f"Terrain overrides on blocks {sorted(span)}, but "
                         f"{sorted(missing)} have none -- mint a bigger island first")
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
    if not len(nonplain_c):
        raise ValueError(f"block span {span} has no non-plain tris at all -- not a kit "
                         f"island (no coast to place against)")
    log(f"bench: {len(gtris)} tris ({sum(plain)} plain-grass mains)")
    # PRISTINE once-edge baseline, captured BEFORE any mutation: computed after the lift
    # it cancels self-consistent weld splits and the crack gate goes blind
    eu0 = Counter()
    for tri in gtris:
        w = [gpos[i] for i in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu0[tuple(sorted((kk3(w[a]), kk3(w[b]))))] += 1
    once0 = {e for e, n in eu0.items() if n == 1}

    def rot_pt(p, k):
        dx3, dz3 = p[0] - c_local[0], p[2] - c_local[1]
        for _ in range(k):
            dx3, dz3 = dz3, -dx3
        return (c_local[0] + dx3, p[1], c_local[1] + dz3)

    def rot_n(n, k):
        nx, nz = n[0], n[2]
        for _ in range(k):
            nx, nz = nz, -nx
        return [nx, n[1], nz]

    def in_span(ROT, gx, gz):
        """The hole band must stay inside the covered span (a mint can spill a few coast
        tris into a neighbor block the pipeline can't see)."""
        poly_pts = np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
        pp = poly_pts + np.array([gx - c_local[0], gz - c_local[1]])
        return not (pp[:, 0].min() < SPX0 + SCAN_BAND + 2 or pp[:, 0].max() > SPX1 - SCAN_BAND - 2
                    or pp[:, 1].min() < SPZ0 + SCAN_BAND + 2 or pp[:, 1].max() > SPZ1 - SCAN_BAND - 2)

    def band_clean(ROT, gx, gz):
        """Exact: no non-plain tri inside or near the placed rim polygon's band."""
        DXc, DZc = gx - c_local[0], gz - c_local[1]
        rp = [(p[0] + DXc, p[2] + DZc) for p in (rot_pt(q, ROT) for q in rim)]
        for tdx, tri in enumerate(gtris):
            if plain[tdx]:
                continue
            cx2, cz2 = tri_c[tdx]
            if pip(cx2, cz2, rp) or near_poly(cx2, cz2, rp, SCAN_BAND) or any(
                    pip(gpos[i][0], gpos[i][2], rp) or
                    near_poly(gpos[i][0], gpos[i][2], rp, SCAN_BAND) for i in tri):
                return False
        return True

    if center is not None:
        ROT, TX, TZ = 0, CX, CZ
        if not in_span(ROT, TX, TZ):
            raise ValueError(f"massif at ({TX:.0f},{TZ:.0f}) leaves block span "
                             f"{span} (the working band must stay on covered ground)")
        if not band_clean(ROT, TX, TZ):
            raise ValueError(f"massif footprint at ({TX:.0f},{TZ:.0f}) is not clear "
                             f"plain-grass mains (band {SCAN_BAND}u)")
        pp = (np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
              + np.array([TX - c_local[0], TZ - c_local[1]]))
        dmin = float(np.sqrt(((nonplain_c[:, None, :] - pp[None, :, :]) ** 2)
                             .sum(axis=2).min()))
        log(f"placement (exact): rot 0deg, blob centre -> ({TX},{TZ}) "
            f"(raw clearance {dmin:.1f}u)")
    else:
        cands = []                                         # (score, dmin, ROT, gx, gz)
        for ROT in (0, 1, 2, 3):
            poly_pts = np.array([(p[0], p[2]) for p in (rot_pt(q, ROT) for q in rim)])
            for gx in range(int(CX) - search_radius, int(CX) + search_radius + 1, search_step):
                for gz in range(int(CZ) - search_radius, int(CZ) + search_radius + 1, search_step):
                    pp = poly_pts + np.array([gx - c_local[0], gz - c_local[1]])
                    if pp[:, 0].min() < SPX0 + SCAN_BAND + 2 or pp[:, 0].max() > SPX1 - SCAN_BAND - 2 \
                            or pp[:, 1].min() < SPZ0 + SCAN_BAND + 2 or pp[:, 1].max() > SPZ1 - SCAN_BAND - 2:
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
        log(f"scan: best raw clearance {cands[0][1]:.1f}u (rot {cands[0][2] * 90}deg) "
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
                             f"{cands[0][1]:.1f}u vs the {SCAN_BAND}u band")
        ROT, TX, TZ, dmin = chosen
        log(f"placement: rot {ROT * 90}deg, blob centre -> ({TX},{TZ}) "
            f"(clearance {dmin:.1f}u)")
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
        raise ValueError("no plain-grass ground around the rim to anchor against")
    ground_med = float(np.median(near_ys))
    DY = ground_med - rim_med

    def carry_vert(i):
        pr = rot_pt(dV2[i], ROT)
        return [pr[0] + DX, pr[1] + DY, pr[2] + DZ]

    # NOTE: rim_nodes iterates rim_set (a set) -- CPython's set order is deterministic
    # for identical insertion sequences of identical (numeric-tuple) values, and the
    # ground_lift float accumulation below inherits that order. The in-game-approved
    # bytes were produced through this exact order; do NOT "clean this up" to sorted().
    rim_nodes = []                                         # (x, z, RIGID rim height)
    for p in rim_set:
        pr = rot_pt(detilt_p(p), ROT)
        rim_nodes.append((pr[0] + DX, pr[2] + DZ, pr[1] + DY))
    log(f"rigid rim heights: [{min(n[2] for n in rim_nodes):.2f},"
        f"{max(n[2] for n in rim_nodes):.2f}] vs ground med {ground_med:.2f} "
        f"(the grass apron absorbs the difference over {gblend}u)")
    # positions touched by ANY non-plain tri: the lift must be EXACTLY zero there --
    # worldmap meshes don't share vertex entries (welds = coincident positions), so a
    # lift applied to the grass-side entry but not the coast-side twin SPLITS the weld
    nonplain_pos = np.array(sorted({(kk3(gpos[i])[0], kk3(gpos[i])[2])
                                    for tdx, tri in enumerate(gtris) if not plain[tdx]
                                    for i in tri}))

    def ground_lift(px, pz, py, dnp):
        """Pure-Y apron field: 0 far away -> (rim height - ground) at the rim."""
        wsum = hsum = 0.0
        dmin2 = 1e18
        for (nx2, nz2, hy) in rim_nodes:
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
            dnp = float(np.sqrt(((nonplain_pos - np.array([k[0], k[2]])) ** 2)
                                .sum(axis=1).min()))
            cand[k] = ground_lift(k[0], k[2], gpos[i][1], dnp)
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
    drop = set()
    for tdx, tri in enumerate(gtris):
        for i in tri:
            if pip(gpos[i][0], gpos[i][2], rim_poly) or \
                    near_poly(gpos[i][0], gpos[i][2], rim_poly, clear):
                drop.add(tdx)
                break
    fams = Counter(gtopo[t] for t in drop)
    log(f"bench tris dropped: {len(drop)} (topos {dict(fams)})")
    if set(fams) != {g_topo}:
        raise ValueError(f"hole reaches non-ground island tris (topos {dict(fams)}, "
                         f"ground topo {g_topo})")

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
    log(f"hole ring: {len(hole)} positions")

    carried = {t: [carry_vert(i) for i in dtri[t]] for t in blob}
    for t in sweep:                                        # verbatim extras, outside the
        carried[t] = [carry_vert(i) for i in dtri[t]]      # ring accounting
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
            return [pr[0] + DX, pr[1] + DY, pr[2] + DZ]

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

        def plug_uv(p):
            v4 = np.array([p[0], p[1], p[2], 1.0])
            return float(v4 @ cu_), float(v4 @ cv_)

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
            f"(id {plug_id:.0f}, chart cols {pcols} rows {prows})")
        if not (min(pcols) >= 5 and max(pcols) <= 10
                and min(prows) >= 6 and max(prows) <= 12):
            raise ValueError("plug chart left the rock band")
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

    i0, j0 = min(((i, j) for i in range(len(hole_ord)) for j in range(len(rim_base))),
                 key=lambda ij: d2(hole_ord[ij[0]], rimw(rim_base[ij[1]])))
    H = hole_ord[i0:] + hole_ord[:i0]
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
                if nc < cost[i + 1][j]:
                    cost[i + 1][j] = nc
                    back[i + 1][j] = "h"
            if j < NR:
                nc = c0 + math.sqrt(d2(H[i % NH], Rw[(j + 1) % NR]))
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
    for t in blob:                                         # the mountain, verbatim channels
        tri = dtri[t]
        idall = strip_dispatch(float(dT[tri[0]][0]))
        nr = [rot_n(dN2[tri[k]], ROT) for k in range(3)]
        corners = tuple((*carried[t][k], dU[tri[k]][0], dU[tri[k]][1], *nr[k])
                        for k in range(3))
        new_parents.append((corners, idall, "mountain"))
    for t in sweep:                                        # the footprint sweep, verbatim
        tri = dtri[t]
        idall = strip_dispatch(float(dT[tri[0]][0]))
        nr = [rot_n(dN2[tri[k]], ROT) for k in range(3)]
        corners = tuple((*carried[t][k], dU[tri[k]][0], dU[tri[k]][1], *nr[k])
                        for k in range(3))
        new_parents.append((corners, idall, "mountain"))
    new_parents.extend(plug_parents)
    zip_rise = 0.0
    zip_ny_min = 1.0
    zip_ny_low = 0
    for tri3 in zip_tris:
        a, b, c = (np.asarray(p, dtype=float) for p in tri3)
        nrm = np.cross(b - a, c - a)
        nl = float(np.linalg.norm(nrm)) or 1.0
        zip_ny_low += (abs(float(nrm[1])) / nl) < MTN_ZIP_NY_MIN
        zip_ny_min = min(zip_ny_min, abs(float(nrm[1])) / nl)
        zip_rise = max(zip_rise, float(max(p[1] for p in tri3) - min(p[1] for p in tri3)))
        order = tri3 if nrm[1] > 0 else (tri3[0], tri3[2], tri3[1])
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

    # ---- 6. gates + assembly ------------------------------------------------------------
    for corners, idall, fam in new_parents:
        for p in corners:
            if not (SPX0 + 0.5 < p[0] < SPX1 - 0.5 and SPZ0 + 0.5 < p[2] < SPZ1 - 0.5):
                raise ValueError(f"{fam} leaves block span {span}: {p[:3]}")
    down = 0
    maxe = 0.0
    for corners, _, fam in new_parents:
        a, b, c = (np.asarray(p[:3]) for p in corners)
        if np.cross(b - a, c - a)[1] < 0:
            down += 1
        if fam != "zip":
            continue                                       # verbatim rock/plug edges are stock-given
        for pq in ((a, b), (b, c), (c, a)):
            maxe = max(maxe, float(np.linalg.norm(pq[0] - pq[1])))
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
        raise ValueError(f"carve leaks outside the span blocks: "
                         f"{sorted(set(new_by_block) - set(span))}")
    changed = {}
    for blk in span:
        sbx, sby = blk
        bm0 = soup["blocks"][blk]
        pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []

        def emit(p3, u2, n3, idall):
            pos.append([p3[0] - BLOCK * sbx, p3[1], p3[2] + BLOCK * (sby + 1) - BLOCK])
            uv.append(list(u2)); nrm.append(list(n3)); tan.append([idall, 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)

        for tdx, tri in enumerate(gtris):
            if gblk[tdx] != blk or tdx in drop:
                continue
            for i in tri:
                emit(gpos[i], guv[i], gnrm[i], gtan[i][0])
            tris.append([flat[-3], flat[-2], flat[-1]])
        for corners, idall, fam in new_by_block.get(blk, []):
            for p in corners:
                emit(p[:3], (p[3], p[4]), (p[5], p[6], p[7]), idall)
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
    for t in list(blob) + list(sweep):
        tri = dtri[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            d0 = float(np.linalg.norm(dV[tri[a]] - dV[tri[b]]))
            if d0 > 0.05:
                worst_rig = max(worst_rig,
                                abs(math.dist(carried[t][a], carried[t][b]) / d0 - 1.0))
    g_worst = 0.0                                          # the apron slope envelope
    for tdx, tri in enumerate(gtris):
        if tdx in drop or not plain[tdx]:
            continue
        a, b, c3 = (np.array(gpos[i]) for i in tri)
        fn = np.cross(b - a, c3 - a)
        L = float(np.linalg.norm(fn)) or 1.0
        g_worst = max(g_worst, math.degrees(math.acos(max(-1, min(1, abs(fn[1]) / L)))))
    log(f"gates: down={down} maxEdge={maxe:.1f} nearMiss={nm // 2} "
        f"annulusOnce={len(inner_once)} zipRise={zip_rise:.2f} zipNyMin={zip_ny_min:.2f} "
        f"(below-envelope {zip_ny_low}/{len(zip_tris)}) "
        f"rockRigid={worst_rig * 100:.1f}% apronSlope={g_worst:.1f}deg")
    if down or nm or inner_once or maxe >= MTN_MAX_EDGE:
        raise ValueError("mountain geometry gate failed (down/near-miss/annulus-crack/edge)")
    if zip_rise > MTN_ZIP_RISE or zip_ny_min < MTN_ZIP_NY_FLOOR \
            or zip_ny_low > MTN_ZIP_BANK_MAX:
        raise ValueError(f"zip steeper than the grass envelope (rise {zip_rise:.2f}, "
                         f"ny min {zip_ny_min:.2f} < floor {MTN_ZIP_NY_FLOOR}, or "
                         f"{zip_ny_low} banks below {MTN_ZIP_NY_MIN} > "
                         f"{MTN_ZIP_BANK_MAX} allowed)")
    if worst_rig >= MTN_ROCK_RIGID:
        raise ValueError("carried rock deformed beyond the de-tilt affine")
    if g_worst > MTN_APRON_SLOPE:
        raise ValueError("the ground apron exceeds the grass slope envelope")

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
        raise ValueError(f"carried peak grounds on {nm_} topo {tp}, want carried rock")
    r_out = max(math.hypot(px - TX, pz - TZ) for (px, pz) in rim_poly) + 4.0
    gy2, nm2, _, tp2 = P.place(_wml, TX - r_out, TZ)
    log(f"ground probe west of the rim: y={gy2:.2f} {nm2} topo {tp2}")
    if nm2 != "Terrain" or tp2 != g_topo:
        raise ValueError(f"west ground probe grounds on {nm2} topo {tp2}, want plain "
                         f"ground topo {g_topo}")

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
                                tv[i] = (pr[0] + DX, pr[1] + DY, pr[2] + DZ)
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
                       "zip_tris": len(zip_tris), "plugs": len(plug_parents),
                       "ensemble_tris": n_ens_tris,
                       "rot_deg": ROT * 90, "blocks": [list(b) for b in span],
                       "peak_y": round(float(
                           max(p[1] for ps in carried.values() for p in ps)), 2),
                       "zip_rise": round(zip_rise, 2), "rock_rigid": round(worst_rig, 4),
                       "apron_slope": round(g_worst, 1), "lifted": len(lift_of),
                       "patched_holes": patched_holes,
                       "teleport": (math.floor(TX - r_out - 2) + 0.5,
                                    math.floor(TZ) + 0.5)}}


def _atlas_gate_mountain(new_parents, *, game=None, log=print):
    """The Moguri-atlas alpha gate (the study's section 7 gate, minus the eye renders):
    every new tri's interior must sample painted texels -- blank = transparent AND dark
    (Moguri paints some in-tile edge strips with alpha 0 that an alpha-ignored opaque
    shader renders fine; true gutter garbage is transparent AND near-black). Skips with a
    log line when the Moguri worldmap atlas isn't installed -- it is a texture-source
    check, not a geometry gate."""
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

    blank = 0
    for corners, _, fam in new_parents:
        nb = 0
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
        if nb:
            blank += 1
            log(f"  BLANK {fam} nb={nb} uv "
                f"{[(round(c[3], 4), round(c[4], 4)) for c in corners]} "
                f"at ({corners[0][0]:.1f},{corners[0][2]:.1f})")
    log(f"atlas gate: transparent-sampling tris = {blank} (want 0)")
    if blank:
        raise ValueError(f"{blank} new tri(s) sample transparent atlas texels")


# ---- census + deploy ------------------------------------------------------------------------
def census_gate(changed, *, disc: int = 1, game=None, log=print, probe=None, baseline=None):
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
    still strictly closer to shipping bytes than the whole plane)."""
    from . import placement as P
    from .island import _sea_plane, _cut_plane
    plane = _sea_plane(disc, game=game)
    for blk, bm in sorted(changed.items()):
        bx, by = blk
        hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=disc, x=bx, y=by)  # noqa: E731
        under = baseline.get(blk, bm) if baseline is not None else bm
        sea = _cut_plane(plane, bx, by, frozenset(), under)
        meshlist = [("Object", hid("Object")), ("Terrain", bm), ("Sea1", hid("Sea1")),
                    ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")), ("Sea4", sea),
                    ("Sea5", hid("Sea5"))]
        cen = P.census(meshlist)
        if cen["miss"]:
            raise ValueError(f"placement MISS in {blk}: {cen['miss'][:4]}")
        if cen["stacked"]:
            # the lawn-under-hill class (BENCH-WALK-SIM's playtest pin): a walkable sheet
            # UNDER a walkable sheet -- first-in-buffer wins, so the player grounds beneath
            # the surface. A carve must REMOVE the ground it covers, not leave it stacked.
            worst = max(cen["stacked"], key=lambda r: r["gap"])
            raise ValueError(f"stacked walkable sheets in {blk}: {len(cen['stacked'])} sample(s), "
                             f"worst at {worst['at']} gap {worst['gap']}u "
                             f"({len(cen['inversions'])} shadowed)")
        if probe:
            (wx, wz), want_topo = probe
            lx, lz = wx - BLOCK * bx, wz + BLOCK * (by + 1) - BLOCK
            if 0.0 <= lx <= BLOCK and -BLOCK <= lz <= 0.0:
                gy, nm_, _, topo = P.place(meshlist, lx, lz)
                log(f"probe grounds in {blk}: y={gy:.2f} {nm_} topo {topo}")
                if nm_ != "Terrain" or topo != want_topo:
                    raise ValueError(f"probe grounded on {nm_} topo {topo}, "
                                     f"expected Terrain topo {want_topo}")
    log("placement census: MISS=0 in changed blocks")


def deploy_mountain_parts(res, *, mod_folder: str, disc: int = 1, lod: str = "0_1",
                          game=None, skip_mirror: bool = False, log=print,
                          target_disc: int | None = None) -> list:
    """Deploy an ENSEMBLE carve's auxiliary part overrides: every span block gets ALL
    of :data:`ENSEMBLE_PARTS` (carried content or a hidden blank -- the donor prefab's
    own parts would otherwise FREE-RIDE verbatim at rot0/shift0), plus a ``Donor.txt``
    naming the part-carrying donor block (the s34 divert binds each override to the
    prefab's part transform BY NAME, so the donor must carry every deployed part). Auto-
    mirrors the written overrides to Disc4 (THE DISC-4 GAP; ``skip_mirror=True`` opts out --
    the ``world-mountain`` CLI passes ``skip_mirror=True`` to BOTH this and its
    :func:`deploy_changed` call, then makes the one mirror pass itself over the union
    of both writers' written paths)."""
    changed_parts = res.get("changed_parts") or {}
    donor_ref = res.get("donor_ref")
    if donor_ref is None:
        return []
    rtarget = disc if target_disc is None else int(target_disc)   # THE READ/WRITE DISC SPLIT
    out = []
    span = [tuple(b) for b in res["report"]["blocks"]]
    for blk in span:
        bx, by = blk
        for part in ENSEMBLE_PARTS:
            bmP = changed_parts.get(blk, {}).get(part)
            if bmP is None:
                bmP = M.hidden_block_mesh(name=f"Block[{bx}][{by}] {part}", disc=rtarget,
                                          x=bx, y=by, lod=lod)
            p = M.deploy_override(bmP, mod_folder=mod_folder, game=game, lod=lod,
                                  part=part, disc=rtarget)
            if len(bmP.tris):
                log(f"deployed {part} -> {p} ({len(bmP.tris)} tris)")
            out.append(p)
        out.append(M.deploy_donor_sidecar(donor_ref[0], donor_ref[1], mod_folder=mod_folder,
                                          disc=rtarget, x=bx, y=by, lod=lod, game=game))
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
    out -- the ``world-mountain`` CLI passes ``skip_mirror=True`` to BOTH this and
    :func:`deploy_mountain_parts`, then makes the one mirror pass itself over the union
    of both writers' written paths)."""
    from .. import config
    import tempfile
    rtarget = disc if target_disc is None else int(target_disc)   # THE READ/WRITE DISC SPLIT:
    # the byte-compare/backup root and the write must aim at the SAME namespace -- comparing
    # against Disc1 while writing Disc9 would defeat the converge check AND back up the wrong file.
    gp = Path(config.find_game_path(game))
    root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{rtarget}" / lod
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = []
    with tempfile.TemporaryDirectory(prefix="ff9_interior_") as tmpdir:
        tmp = Path(tmpdir)
        for blk, bm in sorted(changed.items()):
            bx, by = blk
            dep = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
            new = M.write_ff9mesh(bm, tmp / f"fin_{bx}_{by}.ff9mesh").read_bytes()
            if dep.exists() and dep.read_bytes() == new:
                continue
            if backup and dep.exists():
                import shutil
                shutil.copyfile(dep, dep.with_name(dep.name + f".bak-{ts}"))
            p = M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part="Terrain",
                                  disc=rtarget)
            log(f"deployed -> {p} ({len(bm.tris)} tris)")
            out.append(p)
    if not out:
        log("no block's bytes changed -- nothing deployed")
    else:
        from . import discmirror as DM
        DM.auto_mirror(out, mod_folder=mod_folder, skip_mirror=skip_mirror, log=log)
    return out
