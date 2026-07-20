"""THE SEA-HOLE PATCH -- diagnose + fix the (763,-1216) unnavigable holes on the (8,17)-donor desert
beach island at cells (11,18)/(12,18)/(11,19)/(12,19) (mod folder ``FF9CustomMap-world``).

The playtest verdict: island carry PASSES ("looks and walks verbatim"); the ONE open defect is
missing sea tiles around world ~(763,-1216) -- unnavigable even by boat/airship. The deploy's own
census gate saw ``miss=3 inherited=3 introduced=0`` and called them "the donor's own real in-situ
gaps, backmapped" -- this script TESTS that claim byte-for-byte rather than accepting it, then
patches whatever holes actually exist using the PROVEN mint sea-plane mechanism
(:func:`ff9mapkit.world.island._sea_plane` -- the same full-cell deep-``Sea4`` plane every
``world-island``/``world-mountain`` mint deploys under its land).

Reads the DEPLOYED override files (exactly the engine's registration set: Object, Terrain, Beach1,
Beach2, Stream, River, RiverJoint, Falls, Sea1..Sea6, first mesh with a passing hit wins -- see
``ff9mapkit/world/placement.py``) for the live 2x2, and the PRISTINE stock bytes for the donor's own
cells + every neighbour, to settle whether stock genuinely has a gap there or whether the carry lost
neighbour-block coverage the donor never depended on (it can't -- the engine grounds per CONTAINING
block only; this script proves that empirically too, not by assertion).

NO deploys by default -- prints the would-write list and a report. ``--deploy`` performs the actual
writes (Disc1 + Disc4 mirror) after re-verifying the post-patch census is clean.

Run: py studies/overworld-topography/beach_island_sea_patch.py [--deploy]
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

from ff9mapkit import config                                    # noqa: E402
from ff9mapkit.world import extract as X                        # noqa: E402
from ff9mapkit.world import mesh as M                            # noqa: E402
from ff9mapkit.world import placement as P                       # noqa: E402
from ff9mapkit.world import entrance as E                        # noqa: E402  (read_block_stacked)
from ff9mapkit.world import island as ISL                        # noqa: E402  (_sea_plane, the mint mechanism)
from ff9mapkit.world import discmirror as DM                      # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
DISC = 1
LOD = "0_1"
GAME = None

TARGET_ANCHOR = (11, 18)     # bx, by -- our island's NW cell
DONOR_ANCHOR = (8, 17)
SIZE = (2, 2)

# the engine's REGISTRATION order (placement.py docstring): first mesh with a passing hit wins.
REG_ORDER = ("Object", "Terrain", "Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls",
             "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6")

BOAT_TOPO = {53, 54, 57}      # water.py: mode-7 (boat) traversal mask admits sea topos 53/54/57


# --------------------------------------------------------------------------- tiny mesh-view glue

class _WM:
    """The 3 attributes P.place() reads off a BlockMesh -- world-shifted verts, everything else
    passed through untouched (tangents carry idall, unaffected by translation)."""
    __slots__ = ("verts", "tangents", "flat_index")

    def __init__(self, verts, tangents, flat_index):
        self.verts = verts
        self.tangents = tangents
        self.flat_index = flat_index


def _world_shift(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    return _WM([[v[0] + ox, v[1], v[2] + oz] for v in bm.verts], bm.tangents, bm.flat_index)


def _read_donor_sidecar(mod_folder, bx, by, *, disc=DISC, lod=LOD, game=GAME):
    """The cell's own ``Donor.txt`` -> ``(dx, dy)`` or ``None`` (mirrors ``discmirror._read`` inline --
    no shipped reader function exists, this just parses the sidecar the same way
    ``discmirror.mirror``'s free-ride-pin step does, ``sidecar.read_text().strip().split(',')``)."""
    p = config.find_game_path(game) / mod_folder / M.donor_sidecar_relpath(disc, bx, by, lod)
    if not p.is_file():
        return None
    try:
        dx, dy = (int(v) for v in p.read_text().strip().split(","))
        return dx, dy
    except ValueError:
        return None


def load_cell_meshlist(bx, by, *, mod_folder=None, disc=DISC, lod=LOD, fresh=False, game=GAME):
    """Registration-order ``[(part, world-shifted mesh-view), ...]`` for block ``(bx, by)``.
    ``mod_folder=None`` reads PRISTINE stock only (the donor-truth probe); a folder name prefers an
    already-deployed override and falls back to pristine (``entrance.read_block_stacked``) --
    exactly the engine's own load order. Any part with no override AND no stock asset is NOT simply
    absent, though: the s34 THE FREE-RIDE LAW (``discmirror.py`` -- "un-overridden donor-prefab parts
    ride verbatim at rot0/shift0") means an un-overridden part free-rides from the cell's own
    ``Donor.txt`` sidecar donor's REAL stock asset for that part, reusing the donor's LOCAL vertex
    data UNCHANGED, just relabelled to this block's (x, y) -- exactly ``discmirror.mirror``'s pin
    step, replicated read-side here (this is a real, load-bearing engine mechanism, not a maybe: our
    (12,18) Object -- a real settlement structure -- free-rides this way with NO override file on
    disc1 at all, and ITS collision geometry is why several 'sea holes' below turn out to be an
    Object roof/wall the census must not misread as open water)."""
    out = []
    donor = _read_donor_sidecar(mod_folder, bx, by, disc=disc, lod=lod, game=game) if mod_folder else None
    for part in REG_ORDER:
        bm = None
        try:
            if mod_folder is not None:
                bm = E.read_block_stacked(mod_folder, bx, by, disc=disc, lod=lod, part=part.lower(),
                                          game=game, missing_ok=True, fresh=fresh)
            else:
                bm = X.read_block(bx, by, disc=disc, lod=lod, part=part.lower(), game=game)
        except (ValueError, FileNotFoundError):
            bm = None
        if (bm is None or not bm.verts) and mod_folder is not None and donor is not None and not fresh:
            # no override AND no stock asset of our own -> try the free-ride donor
            try:
                bm = X.read_block(donor[0], donor[1], disc=disc, lod=lod, part=part.lower(), game=game)
            except (ValueError, FileNotFoundError):
                bm = None
        if bm is None or not bm.verts:
            continue
        out.append((part, _world_shift(bm, bx, by)))
    return out


def build_region_meshlists(anchor, size, *, mod_folder, disc=DISC, lod=LOD, fresh=False, game=GAME):
    bx0, by0 = anchor
    out = {}
    for i in range(size[0]):
        for j in range(size[1]):
            bx, by = bx0 + i, by0 + j
            out[(bx, by)] = load_cell_meshlist(bx, by, mod_folder=mod_folder, disc=disc, lod=lod,
                                               fresh=fresh, game=game)
    return out


def region_bounds(anchor, size):
    bx0, by0 = anchor
    x0, x1 = 64.0 * bx0, 64.0 * (bx0 + size[0])
    zlo, zhi = -64.0 * (by0 + size[1]), -64.0 * by0
    return x0, x1, zlo, zhi


# --------------------------------------------------------------------------- dense census

def dense_census(meshlists, anchor, size, *, step=1.0, y=400.0):
    """1u-grid sky-cast census over the WHOLE region, engine-faithful: each probe consults only its
    CONTAINING cell's meshlist (``meshlists`` keyed by ``(bx, by)``; a probe over a cell absent from
    the dict is skipped -- an undeployed / out-of-region cell)."""
    x0, x1, zlo, zhi = region_bounds(anchor, size)
    nx = int(round((x1 - x0) / step))
    nz = int(round((zhi - zlo) / step))
    misses = []
    counts = collections.Counter()
    probed = 0
    for a in range(nx):
        px = x0 + step * (a + 0.5)
        bx = int(math.floor(px / 64.0))
        for b in range(nz):
            pz = zlo + step * (b + 0.5)
            by = int(math.floor(-pz / 64.0))
            ml = meshlists.get((bx, by))
            if ml is None:
                continue
            probed += 1
            gy, name, idall, topo = P.place(ml, px, pz, y=y, sky=True)
            counts[(name, topo)] += 1
            if name == "MISS":
                misses.append((px, pz))
    return {"probed": probed, "miss": misses, "counts": {f"{k[0]}|{k[1]}": v for k, v in counts.items()}}


def window_census(meshlists, x0, x1, zlo, zhi, *, step, y=400.0):
    """Sky-cast census over an ARBITRARY world-rect window (same engine-faithful containing-cell
    rule as :func:`dense_census`) -- the ``--verify-fine`` checks run through this so the two
    review-cited figures (the 0.2u user-point window, the 0.1u whole-block re-census) are
    rerunnable rather than ad-hoc (A NUMBER WITHOUT A RERUNNABLE SCRIPT IS A WISH)."""
    nx = int(round((x1 - x0) / step))
    nz = int(round((zhi - zlo) / step))
    misses = []
    probed = 0
    for a in range(nx):
        px = x0 + step * (a + 0.5)
        bx = int(math.floor(px / 64.0))
        for b in range(nz):
            pz = zlo + step * (b + 0.5)
            by = int(math.floor(-pz / 64.0))
            ml = meshlists.get((bx, by))
            if ml is None:
                continue
            probed += 1
            gy, name, idall, topo = P.place(ml, px, pz, y=y, sky=True)
            if name == "MISS":
                misses.append((px, pz))
    return {"probed": probed, "miss": misses}


def cluster_misses(misses, step=1.0):
    """Grid-adjacency flood fill (4-connected on the census's own step grid) -> list of
    ``{"bbox": [x0,x1,z0,z1], "n": count}`` per contiguous hole region."""
    if not misses:
        return []
    idx = {(round(x / step), round(z / step)): (x, z) for (x, z) in misses}
    seen = set()
    clusters = []
    for key in list(idx):
        if key in seen:
            continue
        stack = [key]
        comp = []
        seen.add(key)
        while stack:
            k = stack.pop()
            comp.append(idx[k])
            kx, kz = k
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (kx + dx, kz + dz)
                if nb in idx and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        xs = [p[0] for p in comp]
        zs = [p[1] for p in comp]
        clusters.append({"bbox": [min(xs) - step / 2, max(xs) + step / 2,
                                  min(zs) - step / 2, max(zs) + step / 2], "n": len(comp)})
    clusters.sort(key=lambda c: -c["n"])
    return clusters


def parts_covering_point(meshlists, px, pz, *, y=400.0):
    """Per-part diagnostic at one point: for EACH registered part alone, does ITS mesh have any
    triangle whose footprint contains the point at all (ignoring the up-facing/idall filters), and
    does the full engine-order query resolve through it. Tells apart 'no tri here' from 'a tri here
    got filtered' (down-facing / IDALL_SKIP)."""
    bx = int(math.floor(px / 64.0))
    by = int(math.floor(-pz / 64.0))
    ml = meshlists.get((bx, by), [])
    report = {}
    for part, bm in ml:
        any_tri = False
        passing = False
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        for t in range(len(fi) // 3):
            i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
            a, b, c = V[i0], V[i1], V[i2]
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / d
            w1 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / d
            w2 = 1 - w0 - w1
            if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                continue
            any_tri = True
        gy, name, idall, topo = P.place(ml, px, pz, y=y, sky=True)
        if name == part:
            passing = True
        report[part] = {"any_tri_footprint": any_tri}
    gy, name, idall, topo = P.place(ml, px, pz, y=y, sky=True)
    report["_resolved"] = {"mesh": name, "idall": idall, "topo": topo, "y": gy}
    return report


# --------------------------------------------------------------------------- donor backmap truth

def cell_delta():
    tx, tz = X.block_world_origin(*TARGET_ANCHOR)
    dx, dz = X.block_world_origin(*DONOR_ANCHOR)
    return tx - dx, tz - dz


def target_to_donor(wx, wz):
    ddx, ddz = cell_delta()
    return wx - ddx, wz - ddz


def donor_home_truth(points, *, disc=DISC, lod=LOD, game=GAME):
    """For each TARGET-frame hole point: backmap to the donor frame, find the ACTUAL containing
    stock block (pure floor -- the engine never consults a neighbour), test the ENGINE query there
    (pristine bytes only, no mod folder), and -- to explicitly settle the 'a neighbour covers it'
    hypothesis -- separately test every one of its 8 neighbours' own meshes at that same point (which
    the engine would never do, but this proves whether the hypothesis is even geometrically true)."""
    # cache pristine meshlists per stock block on demand
    cache: dict = {}

    def stock_ml(bx, by):
        if (bx, by) not in cache:
            cache[(bx, by)] = load_cell_meshlist(bx, by, mod_folder=None, disc=disc, lod=lod, game=game)
        return cache[(bx, by)]

    out = []
    for (tx, tz) in points:
        dxp, dzp = target_to_donor(tx, tz)
        cbx = int(math.floor(dxp / 64.0))
        cby = int(math.floor(-dzp / 64.0))
        nom_bx = DONOR_ANCHOR[0] + (int(math.floor((tx - TARGET_ANCHOR[0] * 64.0) / 64.0)))
        nom_by = DONOR_ANCHOR[1] + (int(math.floor((-tz - TARGET_ANCHOR[1] * 64.0) / 64.0)))
        containing = stock_ml(cbx, cby)
        gy, name, idall, topo = P.place(containing, dxp, dzp, y=400.0, sky=True)
        neighbours = {}
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                nb = (cbx + ddx, cby + ddy)
                nml = stock_ml(*nb)
                if not nml:
                    neighbours[f"{nb}"] = {"has_assets": False}
                    continue
                # does THAT block's OWN mesh (in its own world frame) cover this exact world point?
                ngy, nname, nidall, ntopo = P.place(nml, dxp, dzp, y=400.0, sky=True)
                neighbours[f"{nb}"] = {"has_assets": True, "covers_point": nname != "MISS",
                                       "mesh": nname, "topo": ntopo}
        out.append({
            "target_point": [tx, tz], "donor_point": [dxp, dzp],
            "nominal_donor_cell": [nom_bx, nom_by], "actual_containing_cell": [cbx, cby],
            "cell_mismatch": (nom_bx, nom_by) != (cbx, cby),
            "stock_containing_result": {"mesh": name, "idall": idall, "topo": topo, "y": gy,
                                        "stock_covers": name != "MISS"},
            "neighbour_probe": neighbours,
        })
    return out


# --------------------------------------------------------------------------- patch construction

GRID = 4.0   # the water-tile lattice granularity (water.py G=16 -> 64/16)


def _local_cell(px, pz, bx, by):
    """4u lattice indices in the SAME ``(ix, iz) in [0,16)x[0,16)`` convention
    :func:`sea_patch_for_block` filters by (local z in ``[-64,0]`` shifted +16 cells)."""
    lx = px - 64.0 * bx
    lz = pz + 64.0 * by
    return int(math.floor(lx / GRID)), int(math.floor(lz / GRID)) + 16


def hole_cells_per_block(misses, *, margin_rings=0):
    """``{(bx, by): (core_cells, dilated_extra_cells)}``. ``core_cells`` are the 4u lattice cells that
    directly CONTAIN a census miss -- always kept, unconditionally (they are the hole; excluding one
    would leave a real gap). ``dilated_extra_cells`` are the ``margin_rings`` growth ring around them
    (0 by default -- these tiny hairline holes are fully contained by their own cell at the census
    resolution used) -- these extra cells are still subject to the Sea5/Sea6 shadow-safety filter."""
    core = collections.defaultdict(set)
    for (px, pz) in misses:
        bx = int(math.floor(px / 64.0))
        by = int(math.floor(-pz / 64.0))
        core[(bx, by)].add(_local_cell(px, pz, bx, by))
    out = {}
    for blk, cells in core.items():
        dilated = set(cells)
        for (ix, iz) in cells:
            for dx in range(-margin_rings, margin_rings + 1):
                for dz in range(-margin_rings, margin_rings + 1):
                    dilated.add((ix + dx, iz + dz))
        core_clip = {(ix, iz) for (ix, iz) in cells if 0 <= ix < 16 and 0 <= iz < 16}
        extra_clip = {(ix, iz) for (ix, iz) in (dilated - cells) if 0 <= ix < 16 and 0 <= iz < 16}
        out[blk] = (core_clip, extra_clip)
    return out


# parts REGISTERED AFTER Sea4 (placement.py REG_ORDER) -- the only ones a new Sea4 tri could ever
# SHADOW (win the raycast over) if its footprint overlaps theirs. Object/Terrain/Beach*/Sea1-3 all
# precede Sea4, so overlapping them is raycast-safe BY CONSTRUCTION (they always win first) -- only
# Sea5/Sea6 are downstream of Sea4 and must not be covered.
_SHADOW_RISK_PARTS = ("Sea5", "Sea6")


def unsafe_shadow_cells(meshlists, bx, by):
    """The 4u lattice cells at block ``(bx, by)`` whose footprint overlaps ANY real ``Sea5``/``Sea6``
    triangle's AABB (conservative -- a bbox test, never under-excludes) -- these must NOT receive a
    new Sea4 tri or it shadows (wins the raycast over) real shallower/transition water there, the
    double-render risk this round flagged. Everything else (Object/Terrain/Beach*/Sea1-3, and open
    space) is safe to add Sea4 under/into, because those parts are registered BEFORE Sea4 and always
    win the raycast wherever THEY have a passing hit regardless of our new tri's presence."""
    ml = dict(meshlists.get((bx, by), []))
    unsafe = set()
    for part in _SHADOW_RISK_PARTS:
        bm = ml.get(part)
        if bm is None:
            continue
        V, fi = bm.verts, bm.flat_index
        for t in range(len(fi) // 3):
            i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
            xs = (V[i0][0], V[i1][0], V[i2][0])
            zs = (V[i0][2], V[i1][2], V[i2][2])
            lx0, lx1 = min(xs) - 64.0 * bx, max(xs) - 64.0 * bx
            lz0, lz1 = min(zs) + 64.0 * by, max(zs) + 64.0 * by
            ix0, ix1 = int(math.floor(lx0 / GRID)), int(math.floor(lx1 / GRID))
            iz0, iz1 = int(math.floor(lz0 / GRID)) + 16, int(math.floor(lz1 / GRID)) + 16
            for ix in range(ix0, ix1 + 1):
                for iz in range(iz0, iz1 + 1):
                    unsafe.add((ix, iz))
    return unsafe


def sea_patch_for_block(bx, by, keep_cells, *, disc=DISC):
    """A LOCAL-frame BlockMesh: the mint's own full-cell Sea4 plane
    (:func:`ff9mapkit.world.island._sea_plane`, hole-patched, byte-identical to what every
    ``world-island``/``world-mountain`` deploy already stacks under its land), kept ONLY at
    ``keep_cells`` (4u lattice indices) -- i.e. :func:`ff9mapkit.world.island._cut_plane`'s law
    inverted: keep the listed cells instead of dropping them."""
    plane = ISL._sea_plane(disc, GAME)
    from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN
    ca = plane.chan_arrays
    pos, nrm, uv, tan, flat, tidx = [], [], [], [], [], []
    for tri in plane.tris:
        cx = sum(ca[CH_POS][j][0] for j in tri) / 3.0
        cz = sum(ca[CH_POS][j][2] for j in tri) / 3.0
        cell = (math.floor(cx / GRID), math.floor(cz / GRID) + 16)   # local z in [-64,0] -> iz in [0,16)
        if cell not in keep_cells:
            continue
        base = len(pos)
        for j in tri:
            pos.append(list(ca[CH_POS][j])); nrm.append(list(ca[CH_NRM][j]))
            uv.append(list(ca[CH_UV][j])); tan.append(list(ca[CH_TAN][j]))
            flat.append(len(pos) - 1)
        tidx.append([base, base + 1, base + 2])
    from ff9mapkit.world.extract import BlockMesh
    return BlockMesh(name=f"Block[{bx}][{by}] Sea4", disc=disc, x=bx, y=by, lod=LOD, vcount=len(pos),
                     stride=48, channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tidx, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def merge_local_mesh(base_bm, patch_bm):
    """Append ``patch_bm``'s (LOCAL-frame) triangles onto ``base_bm`` (also local-frame, as read from
    an already-deployed ``.ff9mesh``) -- a plain concatenation, no de-dup (the whole point is the
    patch occupies cells ``base_bm`` had NO tri in)."""
    from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN, BlockMesh
    if base_bm is None:
        return patch_bm
    ca_b, ca_p = base_bm.chan_arrays, patch_bm.chan_arrays
    n0 = len(ca_b[CH_POS])
    pos = list(ca_b[CH_POS]) + list(ca_p[CH_POS])
    nrm = list(ca_b[CH_NRM]) + list(ca_p[CH_NRM])
    uv = list(ca_b[CH_UV]) + list(ca_p[CH_UV])
    tan = list(ca_b[CH_TAN]) + list(ca_p[CH_TAN])
    flat = list(base_bm.flat_index) + [i + n0 for i in patch_bm.flat_index]
    tris = list(base_bm.tris) + [[i + n0 for i in t] for t in patch_bm.tris]
    return BlockMesh(name=base_bm.name, disc=base_bm.disc, x=base_bm.x, y=base_bm.y, lod=base_bm.lod,
                     vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


# --------------------------------------------------------------------------- bonus: event/area audit

def event_area_audit(meshlists):
    """Report-only: any tri across the deployed cells whose idall carries a nonzero event/area (a
    live entrance / chocobo-hotcold tile etc). Changes nothing."""
    from ff9mapkit.world.extract import decode_id
    hits = []
    for (bx, by), ml in meshlists.items():
        for part, bm in ml:
            seen = set()
            for t4 in bm.tangents:
                idall = int(round(t4[0]))
                d = decode_id(idall)
                if d["event"] or d["area"]:
                    key = (part, d["event"], d["area"], d["topograph"])
                    if key not in seen:
                        seen.add(key)
                        hits.append({"block": [bx, by], "part": part, **d})
    return hits


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="perform the actual writes (Disc1 + Disc4 mirror)")
    ap.add_argument("--step", type=float, default=0.5,
                    help="dense-census grid step (world units) -- 0.5u is the validated resolution "
                         "that finds this island's real (hairline) holes; 1.0u under-samples them")
    ap.add_argument("--margin-rings", type=int, default=0,
                    help="4u-cell dilation rings to START the patch at (grows automatically on a "
                         "residual post-patch miss); 0 is the validated minimal, surgical footprint")
    ap.add_argument("--verify-fine", action="store_true",
                    help="run the two fine-grained law-compliance checks the review cited: the "
                         "0.2u window around the user-reported point (pre-patch) and the 0.1u "
                         "whole-block(12,18) census pre- AND post-patch")
    args = ap.parse_args()

    out = {}
    print(f"== loading deployed meshlists for {TARGET_ANCHOR} + {SIZE} from {MOD_FOLDER} (disc {DISC}) ==")
    deployed = build_region_meshlists(TARGET_ANCHOR, SIZE, mod_folder=MOD_FOLDER, disc=DISC, lod=LOD, game=GAME)
    for blk, ml in sorted(deployed.items()):
        print(f"  block{list(blk)}: parts = {[p for p, _ in ml]}")

    print(f"\n== dense census (step={args.step}u) over the whole 2x2 ==")
    cen = dense_census(deployed, TARGET_ANCHOR, SIZE, step=args.step)
    print(f"  probed={cen['probed']}  miss={len(cen['miss'])}")
    clusters = cluster_misses(cen["miss"], step=args.step)
    print(f"  clusters: {len(clusters)}")
    for c in clusters:
        bb = c["bbox"]
        print(f"    bbox x=[{bb[0]:.1f},{bb[1]:.1f}] z=[{bb[2]:.1f},{bb[3]:.1f}]  n={c['n']}")
    target_note_pt = (763.0, -1216.0)
    in_hole = None
    for c in clusters:
        bb = c["bbox"]
        if bb[0] - 2 <= target_note_pt[0] <= bb[1] + 2 and bb[2] - 2 <= target_note_pt[1] <= bb[3] + 2:
            in_hole = c
            break
    print(f"  user point {target_note_pt} falls inside a found hole: {in_hole is not None}")
    out["census"] = cen
    out["clusters"] = clusters
    out["user_point_in_hole"] = in_hole is not None

    # per-hole part diagnostic at each cluster's centroid + a few miss samples
    print("\n== per-part diagnostic at hole centroids ==")
    part_diag = []
    for c in clusters:
        bb = c["bbox"]
        cx, cz = (bb[0] + bb[1]) / 2.0, (bb[2] + bb[3]) / 2.0
        rep = parts_covering_point(deployed, cx, cz)
        print(f"  centroid ({cx:.1f},{cz:.1f}): {rep}")
        part_diag.append({"centroid": [cx, cz], "report": rep})
    out["part_diag"] = part_diag

    print("\n== donor-home truth (backmap every miss point to stock donor frame) ==")
    truth = donor_home_truth(cen["miss"][:200] if len(cen["miss"]) > 200 else cen["miss"])
    n_mismatch = sum(1 for t in truth if t["cell_mismatch"])
    n_stock_covers = sum(1 for t in truth if t["stock_containing_result"]["stock_covers"])
    n_any_neighbour_covers = sum(1 for t in truth
                                 if any(v.get("covers_point") for v in t["neighbour_probe"].values()))
    print(f"  points tested: {len(truth)}")
    print(f"  cell_mismatch (nominal donor cell != actual floor-containing cell): {n_mismatch}")
    print(f"  stock CONTAINING block covers the point (real stock hit): {n_stock_covers}")
    print(f"  ANY neighbour block's own mesh geometrically covers the point "
          f"(would NOT be used by the engine -- info only): {n_any_neighbour_covers}")
    if truth:
        print(f"  sample: {json.dumps(truth[0], indent=1)[:1600]}")
    out["donor_truth_summary"] = {"n": len(truth), "cell_mismatch": n_mismatch,
                                  "stock_containing_covers": n_stock_covers,
                                  "any_neighbour_covers": n_any_neighbour_covers}
    out["donor_truth_sample"] = truth[:20]

    # ------------------------------------------------------------------- patch (iterative: grow the
    # margin ring only if a first pass leaves residual misses -- these holes are hairline-small, so
    # margin_rings=0 (the exact 4u cell(s) containing a miss, nothing more) is tried first).
    would_write = []
    patch_report = {}
    cur_misses = list(cen["miss"])
    patched_meshlists = None
    merged_cache = {}
    for attempt, margin in enumerate([args.margin_rings] + list(range(args.margin_rings + 1, args.margin_rings + 4))):
        print(f"\n== building the hole-spanning Sea4 patch (attempt {attempt+1}, margin_rings={margin}) ==")
        hole_cells = hole_cells_per_block(cur_misses, margin_rings=margin)
        would_write = []
        patched_meshlists = {k: list(v) for k, v in deployed.items()}
        patch_report = {}
        merged_cache = {}
        for blk, (core_cells, extra_cells) in sorted(hole_cells.items()):
            bx, by = blk
            unsafe = unsafe_shadow_cells(deployed, bx, by)
            unsafe_core = core_cells & unsafe
            keep = core_cells | (extra_cells - unsafe)
            if unsafe_core:
                print(f"  block{list(blk)}: WARNING -- {len(unsafe_core)} core hole cell(s) overlap real "
                      f"Sea5/Sea6 (kept anyway -- a real hole always outranks the shadow-safety margin)")
            patch = sea_patch_for_block(bx, by, keep)
            print(f"  block{list(blk)}: core={len(core_cells)} extra_kept={len(extra_cells - unsafe)} "
                  f"extra_excluded(unsafe)={len(extra_cells & unsafe)} patch tris={len(patch.tris)}")
            patch_report[f"{blk}"] = {"core_cells": len(core_cells), "extra_kept": len(extra_cells - unsafe),
                                      "extra_excluded_unsafe": len(extra_cells & unsafe),
                                      "patch_tris": len(patch.tris)}
            existing_path = (config.find_game_path(GAME) / MOD_FOLDER
                             / M.override_relpath(DISC, bx, by, LOD, "Sea4"))
            base_bm = M.blockmesh_from_ff9mesh(existing_path, disc=DISC, x=bx, y=by, lod=LOD, part="sea4") \
                if existing_path.is_file() else None
            merged = merge_local_mesh(base_bm, patch)
            would_write.append(str(existing_path))
            new_ml = [(p, m) for (p, m) in patched_meshlists[blk] if p != "Sea4"]
            new_ml.append(("Sea4", _world_shift(merged, bx, by)))
            new_ml.sort(key=lambda pm: REG_ORDER.index(pm[0]))
            patched_meshlists[blk] = new_ml
            merged_cache[blk] = merged
        cen2 = dense_census(patched_meshlists, TARGET_ANCHOR, SIZE, step=args.step)
        print(f"  post-patch census (this attempt): probed={cen2['probed']} miss={len(cen2['miss'])}")
        if not cen2["miss"]:
            break
        cur_misses = cen2["miss"]
    main._merged_cache = merged_cache
    out["patch_report"] = patch_report
    print(f"\n== FINAL post-patch dense census (must be ZERO misses everywhere) ==")
    print(f"  probed={cen2['probed']}  miss={len(cen2['miss'])}")
    out["post_patch_census"] = {"probed": cen2["probed"], "miss": len(cen2["miss"]),
                                "miss_points": cen2["miss"][:20]}
    clean = len(cen2["miss"]) == 0

    # gate: every ORIGINAL miss point (the real holes this round found) + the user-reported point
    # ground on Sea4 with a boat-legal topo, post-patch.
    print("\n== original census-gate miss points + the user-reported point, post-patch resolution ==")
    orig3 = []
    check_pts = [target_note_pt] + list(cen["miss"])
    boat_ok = True
    for (px, pz) in check_pts:
        bx = int(math.floor(px / 64.0)); by = int(math.floor(-pz / 64.0))
        gy, name, idall, topo = P.place(patched_meshlists.get((bx, by), []), px, pz, y=400.0, sky=True)
        ok = name != "MISS" and topo in BOAT_TOPO
        boat_ok &= ok
        print(f"  ({px:.1f},{pz:.1f}) -> mesh={name} topo={topo} boat_legal={ok}")
        orig3.append({"point": [px, pz], "mesh": name, "topo": topo, "boat_legal": ok})
    out["boat_gate"] = {"all_ok": boat_ok, "points": orig3}

    if args.verify_fine:
        print("\n== --verify-fine: the review's two ad-hoc checks, now rerunnable ==")
        ux, uz = target_note_pt
        w = window_census(deployed, ux - 20, ux + 20, uz - 20, uz + 20, step=0.2)
        print(f"  (a) user-point 40x40u window @0.2u, PRE-patch: probed={w['probed']} "
              f"miss={len(w['miss'])} -> {'PASS (no hole at the reported point)' if not w['miss'] else 'HOLE FOUND'}")
        hb = (12, 18)
        bx0, bz_hi = hb[0] * 64.0, -(hb[1] * 64.0)
        pre = window_census(deployed, bx0, bx0 + 64.0, bz_hi - 64.0, bz_hi, step=0.1)
        post = window_census(patched_meshlists, bx0, bx0 + 64.0, bz_hi - 64.0, bz_hi, step=0.1)
        print(f"  (b) block{list(hb)} @0.1u: PRE-patch probed={pre['probed']} miss={len(pre['miss'])}; "
              f"POST-patch probed={post['probed']} miss={len(post['miss'])} "
              f"-> {'PASS' if not post['miss'] else 'FAIL'}")
        out["verify_fine"] = {
            "user_window_pre": {"probed": w["probed"], "miss": len(w["miss"])},
            "block_12_18_pre": {"probed": pre["probed"], "miss": len(pre["miss"]),
                                "miss_points": pre["miss"][:40]},
            "block_12_18_post": {"probed": post["probed"], "miss": len(post["miss"]),
                                 "miss_points": post["miss"][:40]},
        }

    print(f"\nclean(post-patch miss==0) = {clean}   boat_gate_ok = {boat_ok}")
    print(f"would_write ({len(would_write)}):")
    for w in would_write:
        print(f"  {w}")
    out["would_write_disc1"] = would_write
    out["clean"] = clean

    print("\n== bonus: event/area audit on the carried cells (report-only) ==")
    ev = event_area_audit(deployed)
    print(f"  live event/area tiles found: {len(ev)}")
    for h in ev[:20]:
        print(f"    {h}")
    out["event_area_audit"] = ev

    out_path = Path(__file__).resolve().parent / "out" / "beach_island_sea_patch.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {out_path}")

    if args.deploy:
        if not clean or not boat_ok:
            raise SystemExit("gate failure -- refusing to deploy (see report above)")
        print("\n== DEPLOYING (Disc1 writes + Disc4 mirror) ==")
        written = []
        for blk in sorted(main._merged_cache) if hasattr(main, "_merged_cache") else []:
            bx, by = blk
            merged = main._merged_cache[blk]
            p = M.deploy_override(merged, mod_folder=MOD_FOLDER, game=GAME, lod=LOD, part="Sea4")
            written.append(str(p))
            print(f"  wrote {p}")
        mirrored = DM.auto_mirror(written, mod_folder=MOD_FOLDER)
        print(f"  disc-4 mirror: {mirrored}")
    else:
        print("\n(dry run -- pass --deploy to actually write the patch)")


if __name__ == "__main__":
    main()
