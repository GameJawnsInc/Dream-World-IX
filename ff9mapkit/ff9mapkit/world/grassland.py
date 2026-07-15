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
  p90 ~0.5-0.7). A dead-flat field renders every tile border as a naked straight line at the game's
  oblique camera; the verbatim height field of a real grass region restores the masking.

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

#: GROUND FAMILIES -- byte-measured TRANSLATION LAWS (2026-07-15, the desert study):
#: another walkable ground family is the grass language TRANSLATED in the atlas -- the
#: mains 2x2 rects (same widths 0.06054/0.03028, same gutters 0.00196/0.00097) and the
#: coastal cliff-wall band (same 0.248-wide strip, one row) each sit at their own spot,
#: byte-exact at 5dp. ``topo`` is the family's walkable topograph; the ``wall_*`` deltas
#: shift the mint's ROCK_U/ROCK_V band. Real desert ground ALSO slides free fractional
#: windows over its (painted-over) internal gutter -- the locked grass-form window is a
#: common real form and the safe generative choice, so minting reuses :func:`mains_uv`.
GROUNDS = {
    "grass": dict(topo=0, mains_du=0.0, mains_dv=0.0, wall_du=0.0, wall_dv=0.0),
    "desert": dict(topo=17, mains_du=0.65332, mains_dv=-0.09863,
                   wall_du=-0.27127, wall_dv=-0.02066),
}


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


# ---- rolling relief (a verbatim real height field; real grass is never flat) ---------------------------------------

def relief_field(source=(15, 15), *, disc: int = 1, game=None) -> dict:
    """The VERBATIM lattice height field of a real grass block, plane-detrended and gap-filled (the lake):
    ``{(i, j): dY}`` keyed by 4u lattice node. Apply via :func:`relief_at`."""
    from . import extract as X
    terr = X.read_block(source[0], source[1], disc=disc, part="terrain", game=game)
    H = {}
    for t in range(len(terr.flat_index) // 3):
        if X.decode_id(int(round(terr.tangents[terr.flat_index[3 * t]][0])))["topograph"] != 0:
            continue
        for i in terr.flat_index[3 * t:3 * t + 3]:
            v = terr.verts[i]
            k = (round(v[0] / 4), round(v[2] / 4))
            if abs(v[0] - 4 * k[0]) < 0.05 and abs(v[2] - 4 * k[1]) < 0.05:
                H[k] = v[1]
    if not H:
        return {}
    n = len(H)
    sx = sum(k[0] for k in H)
    sz = sum(k[1] for k in H)
    sy = sum(H.values())
    sxx = sum(k[0] * k[0] for k in H)
    szz = sum(k[1] * k[1] for k in H)
    sxz = sum(k[0] * k[1] for k in H)
    syx = sum(k[0] * y for k, y in H.items())
    syz = sum(k[1] * y for k, y in H.items())
    Mx = [[sxx, sxz, sx], [sxz, szz, sz], [sx, sz, n]]
    Yx = [syx, syz, sy]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(Mx[r][i]))
        Mx[i], Mx[p] = Mx[p], Mx[i]
        Yx[i], Yx[p] = Yx[p], Yx[i]
        for r in range(i + 1, 3):
            f = Mx[r][i] / Mx[i][i]
            for c in range(i, 3):
                Mx[r][c] -= f * Mx[i][c]
            Yx[r] -= f * Yx[i]
    pl = [0.0, 0.0, 0.0]
    for i in (2, 1, 0):
        pl[i] = (Yx[i] - sum(Mx[i][c] * pl[c] for c in range(i + 1, 3))) / Mx[i][i]
    field = {k: y - (pl[0] * k[0] + pl[1] * k[1] + pl[2]) for k, y in H.items()}
    for _ in range(12):
        missing = [(i, j) for i in range(-16, 17) for j in range(-16, 17) if (i, j) not in field]
        if not missing:
            break
        for (i, j) in missing:
            nb = [field[m] for m in ((i+1, j), (i-1, j), (i, j+1), (i, j-1)) if m in field]
            if nb:
                field[(i, j)] = sum(nb) / len(nb)
    return field


def relief_at(field: dict, x: float, z: float, *, edge_dist: float, fade_lo: float = 2.0, fade_hi: float = 10.0):
    """Bilinear relief at ``(x, z)``, faded to 0 within ``fade_lo``..``fade_hi`` units of the land edge
    (``edge_dist`` = the caller's distance to the weld/rim -- the weld must keep its exact Y)."""
    if not field:
        return 0.0
    w = max(0.0, min(1.0, (edge_dist - fade_lo) / (fade_hi - fade_lo)))
    if w == 0.0:
        return 0.0
    gx = x / 4.0
    gz = z / 4.0
    i0 = math.floor(gx)
    j0 = math.floor(gz)
    tx = gx - i0
    tz = gz - j0
    h = 0.0
    for (di, dj, wgt) in ((0, 0, (1-tx)*(1-tz)), (1, 0, tx*(1-tz)), (0, 1, (1-tx)*tz), (1, 1, tx*tz)):
        h += field.get((i0 + di, j0 + dj), 0.0) * wgt
    return h * w


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
