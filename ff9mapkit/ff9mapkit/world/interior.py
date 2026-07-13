"""INTERIOR topography on a DEPLOYED kit island: ``world-forest`` (carry a real canopy
blob) and ``world-hill`` (a raised-cosine grass hill) -- the productized forms of the two
in-game-proven island-E studies (2026-07-12: the forest re-home "walked the whole rim
aggressively, no more sticking"; the hill "looks natural, walkable from all sides").

Both verbs RESHAPE the deployed override bytes (never a real map block -- reshaping stock
land is ``world-terrain``'s job) and refuse when the working footprint leaves the deployed
blocks. Everything below is a faithful port of ``studies/overworld-topography/
forest_rehome.py`` + ``hill_at_scale.py`` -- the laws it encodes (full statements in
memory ``project-ff9-overworld-interior-topography``):

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
  hypotheses, exact); fully-dropped cells take a deterministic in-language pick.
* THE GRASS-HILL LANGUAGE -- lowland slope envelope p99 28.6 deg, pure-grass summits are
  real, prominence 3.5-5.2 over 20-26u, peaks <= the lowland band top (~8.6); the hill is
  a PURE-Y raised-cosine displacement (mains UVs are XZ-linear, so vertical motion keeps
  every tile lawful) with LOCAL normal re-smoothing.
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
                         lod: str = "0_1", game=None) -> dict:
    """Read every deployed ``Block[x][y] Terrain.ff9mesh`` override whose block rect
    intersects the ``near +- reach`` window. Blocks without an override are OCEAN and
    load nothing (the safety is downstream: the footprint-lawful gates, the rim-clearance
    margins, the carve leak assert, and the crack gate all refuse work that would leave
    the deployed island). Refuses only when NO override exists in the window -- these
    verbs reshape DEPLOYED kit islands only (reshaping a real block is ``world-terrain``'s
    job)."""
    from .. import config
    gp = Path(config.find_game_path(game))
    root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{disc}" / lod
    wx, wz = near
    bx0, bx1 = int(math.floor((wx - reach) / BLOCK)), int(math.floor((wx + reach) / BLOCK))
    by0, by1 = int(math.floor(-(wz + reach) / BLOCK)), int(math.floor(-(wz - reach) / BLOCK))
    out = {}
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
            if p.exists():
                out[(bx, by)] = M.blockmesh_from_ff9mesh(p, disc=disc, x=bx, y=by,
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
    """Deterministic in-language (quad, ori) for a fully-dropped mains cell -- avoid the
    W/S neighbours' quads (the anti-tiling discipline)."""
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
    _decoded = {}

    def decode_cell(cell):
        if cell in _decoded:
            return _decoded[cell]
        best = None
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
                        best = (quad, ori)
                        break
                if best:
                    break
            if best:
                break
        if best is None:
            best = decode_cell_pick(cell, _decoded)
        _decoded[cell] = best
        return best

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
        quad, ori = decode_cell(cell)
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
            "report": {"blob_tris": len(blob), "dropped": len(drop),
                       "zip_tris": len(zip_tris), "wall_rise": round(worst_wall, 2),
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
        # slope envelope; the mint's rolling relief spans well under this)
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


# ---- census + deploy ------------------------------------------------------------------------
def census_gate(changed, *, disc: int = 1, game=None, log=print, probe=None):
    """Per changed block: the engine placement census (hidden aux parts + the synthetic
    full sea plane, the studies' exact configuration) must ground EVERYWHERE (MISS=0).
    ``probe = ((wx, wz), expected_topo)`` additionally grounds one world point."""
    import dataclasses
    from . import placement as P
    from .island import _sea_plane
    plane = _sea_plane(disc, game=game)
    for blk, bm in sorted(changed.items()):
        bx, by = blk
        hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=disc, x=bx, y=by)  # noqa: E731
        sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
        meshlist = [("Object", hid("Object")), ("Terrain", bm), ("Sea1", hid("Sea1")),
                    ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")), ("Sea4", sea),
                    ("Sea5", hid("Sea5"))]
        cen = P.census(meshlist)
        if cen["miss"]:
            raise ValueError(f"placement MISS in {blk}: {cen['miss'][:4]}")
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


def deploy_changed(changed, *, mod_folder: str, disc: int = 1, lod: str = "0_1",
                   game=None, backup: bool = True, log=print) -> list:
    """Deploy every block whose bytes actually change (byte-compare converge). An
    existing override backs up beside itself as ``<name>.ff9mesh.bak-<ts>`` (a suffixed
    name never matches the engine's override pattern)."""
    from .. import config
    import tempfile
    gp = Path(config.find_game_path(game))
    root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{disc}" / lod
    tmp = Path(tempfile.mkdtemp(prefix="ff9_interior_"))
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = []
    for blk, bm in sorted(changed.items()):
        bx, by = blk
        dep = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        new = M.write_ff9mesh(bm, tmp / f"fin_{bx}_{by}.ff9mesh").read_bytes()
        if dep.exists() and dep.read_bytes() == new:
            continue
        if backup and dep.exists():
            import shutil
            shutil.copyfile(dep, dep.with_name(dep.name + f".bak-{ts}"))
        p = M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part="Terrain")
        log(f"deployed -> {p} ({len(bm.tris)} tris)")
        out.append(p)
    if not out:
        log("no block's bytes changed -- nothing deployed")
    return out
