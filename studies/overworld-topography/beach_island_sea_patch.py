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

--- v2 (2026-07-20): THE Z-FIGHT FIX -----------------------------------------------------------------

The v1 patch above fixed navigability but the user then reported Z-FIGHTING water flicker near the
patched cells while the camera moves. MEASURED root cause (see the constants block + the new
functions below, all rerunnable): v1's :func:`hole_cells_per_block` filled the WHOLE containing 4u
macro cell for every hairline miss (:func:`sea_patch_for_block`) -- but 3 of its 5 patched cells are
69-99%-covered in plan by the REAL CARRIED **Sea3**, and every sea layer in this data (real or minted)
sits at Y=0.0 exactly. Two coplanar meshes covering the same footprint at the same Y is the textbook
z-fight. v2 (:func:`build_v2_patch_for_block`, :func:`fine_patch_for_block`) strips the v1 patch
(:func:`split_v1_patch`, geometry-verified), re-censuses the TRUE pre-patch hole at fine (0.1u)
resolution, and fills ONLY that footprint with sub-cell quads CLIPPED (:func:`clip_tri_to_box`, exact
Sutherland-Hodgman, not resampled) from the same mint sea-plane source -- never re-entering Sea3's
territory. A new gate, :func:`coplanar_overlap_gate` (exact 2D triangle-triangle overlap area, not a
bbox test), proves this: it FAILS on the live v1 patch and must PASS on v2's replacement before
``--deploy`` is honoured. Also measured (:func:`pristine_coexistence_scan`): real stock NEVER stacks
two sea layers at a Y offset anywhere sampled -- coexistence is 100% by disjoint plan coverage, so
there is no positive "lawful separation" to fall back to; ``MIN_LAWFUL_SEP`` is the task's specified
0.05u FLOOR, not a measured number.

Run: py studies/overworld-topography/beach_island_sea_patch.py [--deploy] [--verify-fine]

--- v3 (2026-07-20): THE COVERAGE-FIRST FIX -----------------------------------------------------------

v2 above was REFUSED: at a finer 0.02u re-census it reopened 15 sub-0.1u navigability holes, all inside
2 of the 28 fine cells v2's own gate had excluded as "unsafe" (Sea3-adjacent). The root cause was NOT
the shave mechanism (that part worked) -- it was that :func:`unsafe_fine_cells` was allowed to drop a
margin (``extra``) cell purely because it sat near real Sea3, WITHOUT first checking whether that cell
was also genuinely holed. Two of the 28 happened to be both. v3's fix is exactly the refusing gate's own
prescription: a candidate "unsafe" cell may only be dropped once a fine (``FINE_VERIFY_STEP`` = 0.02u)
re-census of the REAL (patch-stripped) geometry proves it has no true hole in it
(:func:`genuinely_holed_fine_cells`); a cell that IS genuinely holed is kept unconditionally and
:func:`shave_patch_y` (already the mechanism's whole purpose) is the thing that reconciles any resulting
coplanar conflict -- iterated with escalating depth across up to ``MAX_SHAVE_PASSES`` passes rather than
ever dropping coverage to satisfy the cosmetics gate. **Coverage beats cosmetics only via the lawful
shave, never via a hole.**

This also corrects two report-prose defects from the v2-round text above: (1) "the other 2 of 5 [v1]
patched cells are dominantly Terrain-covered -- safe" was WRONG -- those 2 cells ((4,5) and (5,4) in
block-local 4u lattice indices) are exactly where 5 of the 18 v1 gate offenders live, all against real
**Object** geometry (3 of the 5 exactly ``dY=0.0``), not merely Terrain-shadowed. The full v1 offender
breakdown is 18 offenders across 8 of the patch's 10 tris: ``v1_patch_0/1/2/3/5/8`` (6 tris, 13 rows) vs
**Sea3**, ``v1_patch_4/9`` (2 tris, 5 rows, 3 exactly coplanar) vs **Object** -- only tris 6 and 7 of the
10 were ever clean. (2) the pristine-law sample set (``sample_blocks`` in ``main()``) DOES include the
donor's own home cell (8,17) as ``dh`` itself; (9,17) is one of its 4 NEIGHBOUR samples
(``dh[0]+1, dh[1]``), not the home cell -- any report text that named (9,17) as "the donor's own home"
was in error.

Also adds (task requirement 2c) a NEW first-class ``--verify-fine`` gate: a 0.02u census over the FULL
64x64u block footprint (not just the patch's own bounding box) -- the resolution that caught v2's defect
-- via a bucketed hit-index (:func:`fast_hit_index`/:func:`fast_block_census`; a naive per-point
O(all-tris) sweep at 0.02u is ~10.24M probes and intractable in pure Python) that is CROSS-VALIDATED
against the byte-exact (but slow) :func:`ff9mapkit.world.placement.place`-based census at a coarse step
before either result is trusted.

Run: py studies/overworld-topography/beach_island_sea_patch.py [--deploy] [--verify-fine]
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

# --------------------------------------------------------------------------- v2: Z-FIGHT FIX
#
# THE MEASURED LAYER STORY (2026-07-20, this round -- see measure_layer_stats/pristine_coexistence_scan
# below for the rerunnable proof):
#
#   1. Every sea/beach sub-layer this donor carry uses (Sea1/Sea2/Sea3/Sea4/Sea5, the mint's own
#      borrowed Sea4 plane, and the STOCK donor's own Sea1..Sea5 sampled fresh from 5 pristine blocks
#      incl. the donor's own home) sits at EXACTLY Y=0.0. Only Terrain/Beach1 (actual landform/berm
#      geometry) ever leave Y=0.
#   2. Across every pristine stock sample AND the live carried cells, TWO sea parts NEVER horizontally
#      overlap each other in plan -- zero counterexamples. Real FF9 coexists multiple sea layers by
#      DISJOINT PLAN COVERAGE at one shared Y, never by a Y offset. There is therefore no POSITIVE
#      "lawful inter-layer separation" to read off; MIN_LAWFUL_SEP below is the task's specified 0.05u
#      FLOOR, not a measured number -- the real law is stronger: never overlap AT ALL.
#   3. The deployed v1 patch violates this: :func:`hole_cells_per_block`/:func:`sea_patch_for_block`
#      filled the WHOLE containing 4u macro cell for every hairline miss, and 3 of its 5 patched cells
#      are 69-99%-covered by the real carried **Sea3** in plan -- both exactly Y=0.0, i.e. LITERALLY
#      coplanar. But Sea3 is NOT the only z-fight partner: the MEASURED gate offender breakdown is 18
#      offenders across 8 of the patch's 10 tris -- ``v1_patch_0/1/2/3/5/8`` (6 tris, 13 rows) vs Sea3,
#      AND ``v1_patch_4/9`` (2 tris, 5 rows, 3 of them exactly ``dY=0.0``) vs real **Object** geometry in
#      the OTHER 2 of the 5 patched cells (block-local 4u cells (4,5) and (5,4)) -- those two are NOT
#      merely "dominantly Terrain-covered, safe" as an earlier pass of this note claimed; they coplanar-
#      overlap a carried settlement structure's roof/wall tris just as directly as the Sea3 pair does.
#      Only 2 of the patch's 10 tris (indices 6, 7) were ever actually clean.
#   4. v2's fix is law (1): CLIP the patch to the TRUE (fine-grained, sub-4u) hole footprint instead of
#      the whole containing macro cell, so it never re-enters Sea3's (or any other real part's)
#      territory in the first place -- no Y-offset trick, because none is lawful here.
FINE_GRID = 0.5                # v2's own patch lattice -- 8 fine cells per macro 4u GRID cell; the
                                # resolution the 0.1u navigability census's hairline holes need clipped
                                # to (v1's whole-4u-cell fill is the defect, not the resolution of the
                                # original navigability finding, which was always sub-cell).
MIN_LAWFUL_SEP = 0.05           # NO-COPLANAR-OVERLAP gate floor -- see the law note above: there is no
                                # measured POSITIVE lawful separation (real layers never overlap at all),
                                # so this is the task-specified floor, applied as-is.
# Every water-adjacent part a new Sea4 tri could coplanar-overlap. Sea4 itself is handled separately
# by the caller (only the REAL, patch-stripped portion counts -- a patch must never be checked against
# itself).
OVERLAP_CHECK_PARTS = ("Beach1", "Beach2", "Sea1", "Sea2", "Sea3", "Sea5", "Sea6")

# v3: the finer re-check resolution that actually caught the REFUSED v2's reopened holes. Used for (a)
# the requirement-1 "is this 'unsafe' fine cell genuinely holed, or just cosmetically close to real
# water" proof (:func:`genuinely_holed_fine_cells`) and (b) the requirement-2c whole-block gate
# (:func:`fast_block_census`). 0.1u (the v2 build/verify default) is demonstrably NOT fine enough --
# it is what let 2 of v2's 28 unsafe-excluded margin cells hide a genuine sub-0.1u hole.
FINE_VERIFY_STEP = 0.02
MAX_SHAVE_PASSES = 12           # v3: escalated from v2's 3 -- "iterate the shave, never drop coverage".


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


# --------------------------------------------------------------------------- v3: fast whole-block census
#
# requirement 2c: a 0.02u census over the FULL 64x64u block footprint is ~10.24M probes. Each
# :func:`ff9mapkit.world.placement.place` call is O(all tris in the meshlist), so a naive port of
# :func:`window_census` to that resolution is intractable in pure Python. A MISS-only census doesn't
# need to know WHICH part/order wins, though (it only needs "is there ANY passing tri here at all") --
# so :func:`fast_hit_index` buckets every up-facing, non-skipped tri (the identical per-tri filter
# :func:`ff9mapkit.world.placement.place` applies) into small XZ tiles once, and :func:`fast_block_census`
# does a cheap few-triangle bucket lookup per probe instead of a scan of the whole meshlist. This is
# CROSS-VALIDATED against the byte-exact (but slow) ``place``-based census at a coarse step in ``main()``
# before either result is trusted (a faster implementation of a different algorithm would be worthless).

def fast_hit_index(meshlist, *, cell=1.0):
    """``{(cell_x, cell_z): [(a, b, c), ...]}`` -- every triangle (world-frame ``[x,y,z]`` verts) from
    every part in ``meshlist`` that would ever pass :func:`ff9mapkit.world.placement.place`'s per-tri
    filter (idall not in ``P.IDALL_SKIP``, geometric up-facing winding ``ny/L > 0.1``), bucketed into
    every ``cell``-sized XZ tile its AABB overlaps."""
    idx = collections.defaultdict(list)
    for part, bm in meshlist:
        V, T = bm.verts, bm.tangents
        for tri in _tris_of(bm):
            i0, i1, i2 = tri
            idall = int(round(T[i0][0]))
            if idall in P.IDALL_SKIP:
                continue
            a, b, c = V[i0], V[i1], V[i2]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            ny = uz * vx - ux * vz
            L = math.sqrt((uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2) or 1.0
            if ny / L <= 0.1:
                continue
            x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
            z0, z1 = min(a[2], b[2], c[2]), max(a[2], b[2], c[2])
            cx0, cx1 = int(math.floor(x0 / cell)), int(math.floor(x1 / cell))
            cz0, cz1 = int(math.floor(z0 / cell)), int(math.floor(z1 / cell))
            for cx in range(cx0, cx1 + 1):
                for cz in range(cz0, cz1 + 1):
                    idx[(cx, cz)].append((a, b, c))
    return idx


def _fast_hit(idx, cell, px, pz):
    key = (int(math.floor(px / cell)), int(math.floor(pz / cell)))
    bucket = idx.get(key)
    if not bucket:
        return False
    for (a, b, c) in bucket:
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / d
        w1 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / d
        w2 = 1 - w0 - w1
        if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
            continue
        return True
    return False


def fast_block_census(meshlist, bx, by, *, step=FINE_VERIFY_STEP, cell=1.0):
    """The full-64x64u-block MISS-only census at ``step`` resolution, via :func:`fast_hit_index` --
    the only way requirement 2c's 0.02u whole-block gate finishes in reasonable time. Returns the same
    shape as :func:`window_census` (``probed``/``miss``)."""
    ox, oz = X.block_world_origin(bx, by)
    idx = fast_hit_index(meshlist, cell=cell)
    n = int(round(64.0 / step))
    miss = []
    for a_ in range(n):
        px = ox + step * (a_ + 0.5)
        for b_ in range(n):
            pz = oz - 64.0 + step * (b_ + 0.5)
            if not _fast_hit(idx, cell, px, pz):
                miss.append((px, pz))
    return {"probed": n * n, "miss": miss}


def cross_validate_fast_census(meshlist, bx, by, *, step=1.0, cell=1.0):
    """Self-check (run once under ``--verify-fine`` before the 0.02u gate is trusted): the byte-exact
    ``place``-based :func:`window_census` and the bucketed :func:`fast_block_census` must agree
    EXACTLY (same miss-point set) at a coarse, cheap-enough-for-both step over the whole block --
    proving the fast path is a faster INDEX over the identical per-tri math, not a silently different
    algorithm."""
    ox, oz = X.block_world_origin(bx, by)
    slow = window_census({(bx, by): meshlist}, ox, ox + 64.0, oz - 64.0, oz, step=step)
    fast = fast_block_census(meshlist, bx, by, step=step, cell=cell)
    slow_set = {(round(p[0], 6), round(p[1], 6)) for p in slow["miss"]}
    fast_set = {(round(p[0], 6), round(p[1], 6)) for p in fast["miss"]}
    return {"step": step, "slow_probed": slow["probed"], "fast_probed": fast["probed"],
           "slow_miss": len(slow_set), "fast_miss": len(fast_set),
           "agree": slow_set == fast_set,
           "only_slow": len(slow_set - fast_set), "only_fast": len(fast_set - slow_set)}


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
    an already-deployed ``.ff9mesh``) -- then FLATTEN. **THE FLAT-MESH INVARIANT (learned in-game
    2026-07-20, the hard way):** every real ``.ff9mesh`` is strictly flat/unindexed -- vertex count ==
    index count, each tri owning its own 3 verts -- and the engine's s34 loader ASSUMES it:
    a merged mesh carrying orphan verts (the v3 clip's polygon corner pool left 30) made
    ``WMWorld.RegisterBlockComponent`` throw IndexOutOfRange, aborting ``LoadBlocks`` mid-world --
    every block after ours loaded unregistered (pale unnavigable sea map-wide + the arrival fix-up
    relocating the player). The flatten below re-expands every channel per-tri from ``flat_index``
    (orphans dropped by construction) and the caller-facing invariant is asserted."""
    from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN, BlockMesh
    if base_bm is None:
        merged = patch_bm
    else:
        ca_b, ca_p = base_bm.chan_arrays, patch_bm.chan_arrays
        n0 = len(ca_b[CH_POS])
        pos = list(ca_b[CH_POS]) + list(ca_p[CH_POS])
        nrm = list(ca_b[CH_NRM]) + list(ca_p[CH_NRM])
        uv = list(ca_b[CH_UV]) + list(ca_p[CH_UV])
        tan = list(ca_b[CH_TAN]) + list(ca_p[CH_TAN])
        flat = list(base_bm.flat_index) + [i + n0 for i in patch_bm.flat_index]
        tris = list(base_bm.tris) + [[i + n0 for i in t] for t in patch_bm.tris]
        merged = BlockMesh(name=base_bm.name, disc=base_bm.disc, x=base_bm.x, y=base_bm.y,
                           lod=base_bm.lod, vcount=len(pos), stride=48,
                           channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                           chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                           flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                           submeshes=[])
    # FLATTEN: per-tri vertex expansion in flat_index order; index buffer becomes 0..3N-1.
    ca = merged.chan_arrays
    idx = list(merged.flat_index)
    pos = [ca[CH_POS][j] for j in idx]
    nrm = [ca[CH_NRM][j] for j in idx]
    uv = [ca[CH_UV][j] for j in idx]
    tan = [ca[CH_TAN][j] for j in idx]
    flat = list(range(len(idx)))
    tris = [[3 * t, 3 * t + 1, 3 * t + 2] for t in range(len(idx) // 3)]
    out = BlockMesh(name=merged.name, disc=merged.disc, x=merged.x, y=merged.y, lod=merged.lod,
                    vcount=len(pos), stride=48,
                    channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                    chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                    flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    assert len(out.chan_arrays[CH_POS]) == len(out.flat_index) == 3 * (len(out.flat_index) // 3), \
        "FLAT-MESH INVARIANT violated"
    print(f"  FLAT-MESH INVARIANT: verts={len(pos)} == idx={len(flat)} "
          f"({len(flat)//3} tris, orphans dropped: {len(ca[CH_POS]) - len(set(idx))} unreferenced) -> ok")
    return out


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


# --------------------------------------------------------------------------- v2: measurement primitives

def _tri_bary_y(a, b, c, px, pz):
    """Barycentric height at ``(px, pz)`` inside triangle ``a,b,c`` -- ``None`` if outside. No
    orientation/idall filtering (unlike :func:`ff9mapkit.world.placement.place`): this answers "is
    anything here", the render question, not "what does the engine's raycast resolve to"."""
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) < 1e-12:
        return None
    w0 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / d
    w1 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / d
    w2 = 1 - w0 - w1
    if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
        return None
    return w0 * a[1] + w1 * b[1] + w2 * c[1]


def _raw_hits(bm, px, pz):
    """EVERY triangle in ``bm`` (any winding, any idall) whose XZ footprint contains ``(px, pz)`` --
    the render-pass question, not the raycast question. Returns the list of Y hits (usually 0 or 1;
    >1 if the mesh itself already overlaps itself in plan)."""
    V, fi = bm.verts, bm.flat_index
    out = []
    for t in range(len(fi) // 3):
        i0, i1, i2 = fi[3 * t], fi[3 * t + 1], fi[3 * t + 2]
        y = _tri_bary_y(V[i0], V[i1], V[i2], px, pz)
        if y is not None:
            out.append(y)
    return out


def _tris_of(bm):
    """``bm.tris`` if present (a real :class:`~ff9mapkit.world.extract.BlockMesh`), else the
    ``flat_index`` regrouped in 3s (a world-shifted ``_WM`` view, which drops ``.tris`` -- it only
    carries what :func:`~ff9mapkit.world.placement.place` reads). Works uniformly on either."""
    if hasattr(bm, "tris"):
        return bm.tris
    fi = bm.flat_index
    return [fi[i:i + 3] for i in range(0, len(fi), 3)]


def layer_y_stats(meshlists_for_block):
    """``{part: {"tris", "y_min", "y_max", "y_mean", "top_y"}}`` -- the per-part Y distribution for one
    block's meshlist (:func:`load_cell_meshlist`'s list-of-tuples shape, world- or local-frame -- only
    relative Y matters)."""
    out = {}
    for part, bm in meshlists_for_block:
        V = bm.verts
        if not V:
            continue
        ys = [v[1] for v in V]
        c = collections.Counter(round(y, 3) for y in ys)
        out[part] = {"tris": len(_tris_of(bm)), "y_min": min(ys), "y_max": max(ys),
                     "y_mean": sum(ys) / len(ys), "top_y": c.most_common(5)}
    return out


def part_coverage_fractions(meshlists_for_block, bx, by, macro_cells, *, n=9, grid=GRID):
    """For each MACRO (``grid``-u) cell in ``macro_cells``: sample an ``n x n`` subgrid and report, for
    every part present in the block, the fraction of samples it renders over -- pinpoints exactly which
    real part(s) a patch tri placed there would coplanar-overlap."""
    ml = dict(meshlists_for_block)
    ox, oz = X.block_world_origin(bx, by)
    n_cells = int(round(64.0 / grid))
    out = {}
    for (ix, iz) in sorted(macro_cells):
        lx0, lz0 = ix * grid, (iz - n_cells) * grid
        cover = collections.Counter()
        total = n * n
        for si in range(n):
            for sj in range(n):
                px = lx0 + grid * (si + 0.5) / n + ox
                pz = lz0 + grid * (sj + 0.5) / n + oz
                for part, bm in ml.items():
                    if _raw_hits(bm, px, pz):
                        cover[part] += 1
        out[f"{(ix, iz)}"] = {k: round(v / total, 3) for k, v in cover.items()}
    return out


def whole_block_overlap_census(meshlists_for_block, bx, by, *, step=0.5):
    """Every ``step``-grid point across the whole block, tagged with the SET of parts whose raw
    (unfiltered) geometry covers it. Any key naming >1 part is a coplanar RENDER overlap -- a key
    naming a REAL part alongside another real part would mean stock double-covers itself (the measured
    law says this never happens); a key naming ``Sea4patch`` alongside anything else is exactly the
    z-fight this round chases."""
    ml = dict(meshlists_for_block)
    ox, oz = X.block_world_origin(bx, by)
    counts = collections.Counter()
    examples = {}
    n = int(round(64.0 / step))
    for a in range(n):
        px = ox + step * (a + 0.5)
        for b in range(n):
            pz = oz - 64.0 + step * (b + 0.5)
            present = [part for part, bm in ml.items() if _raw_hits(bm, px, pz)]
            key = tuple(sorted(present))
            counts[key] += 1
            if len(present) > 1 and key not in examples:
                examples[key] = (round(px, 2), round(pz, 2))
    return {"counts": {("|".join(k) if k else "(none)"): v for k, v in counts.items()},
           "examples": {"|".join(k): v for k, v in examples.items()}}


def pristine_coexistence_scan(blocks, *, step=1.0, disc=DISC, lod=LOD, game=GAME):
    """THE GENERAL LAW PROBE: for each PRISTINE stock block (mod_folder=None -- untouched bytes),
    load every present sea/beach/terrain part and census for ANY multi-part plan overlap. Settles
    whether real FF9 ever stacks two coexisting sea layers at a Y offset, or only by disjoint plan
    coverage -- "the lawful inter-layer dY vocabulary"."""
    out = {}
    for (bx, by) in blocks:
        parts = {}
        for p in ("Terrain", "Beach1", "Beach2", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"):
            try:
                bm = X.read_block(bx, by, disc=disc, lod=lod, part=p.lower(), game=game)
            except (ValueError, FileNotFoundError):
                bm = None
            if bm is not None and bm.verts:
                parts[p] = bm
        if not parts:
            out[f"{(bx, by)}"] = {"parts": [], "y_ranges": {}, "multi_overlap": {}, "multi_overlap_examples": {}}
            continue
        counts, examples = collections.Counter(), {}
        n = int(round(64.0 / step))
        for a in range(n):
            px = step * (a + 0.5)
            for b in range(n):
                pz = -64.0 + step * (b + 0.5)
                present = [p for p, bm in parts.items() if _raw_hits(bm, px, pz)]
                if len(present) > 1:
                    key = tuple(sorted(present))
                    counts[key] += 1
                    if key not in examples:
                        examples[key] = (round(px, 2), round(pz, 2))
        y_ranges = {p: (min(v[1] for v in bm.verts), max(v[1] for v in bm.verts)) for p, bm in parts.items()}
        out[f"{(bx, by)}"] = {"parts": list(parts), "y_ranges": y_ranges,
                              "multi_overlap": {"|".join(k): v for k, v in counts.items()},
                              "multi_overlap_examples": {"|".join(k): v for k, v in examples.items()}}
    return out


# --------------------------------------------------------------------------- v2: strip the v1 patch

def donor_cell_for_block(bx, by, *, mod_folder=MOD_FOLDER, disc=DISC, lod=LOD, game=GAME):
    """The block's real donor cell straight from its own ``Donor.txt`` sidecar (the s34 free-ride
    mechanism's OWN ground truth) -- falls back to the ``TARGET_ANCHOR``/``DONOR_ANCHOR`` delta only
    if no sidecar is deployed there."""
    d = _read_donor_sidecar(mod_folder, bx, by, disc=disc, lod=lod, game=game)
    if d is not None:
        return d
    tx, tz = target_to_donor(64.0 * bx + 0.01, -64.0 * by - 0.01)
    return int(math.floor(tx / 64.0)), int(math.floor(-tz / 64.0))


def split_v1_patch(bx, by, *, mod_folder=MOD_FOLDER, disc=DISC, lod=LOD, game=GAME):
    """Strip any already-deployed v1-style Sea4 patch off block ``(bx, by)``, returning
    ``(pre_bm, patch_tris_local, verified)``:

    - ``pre_bm`` -- the block's REAL (carried-donor) Sea4 with the patch tris removed (``None`` if no
      Sea4 override is deployed at all).
    - ``patch_tris_local`` -- the removed tris (LOCAL frame, ``[[x,y,z]x3, ...]``) -- ``[]`` if there
      is nothing to strip (deployed tri count == the pristine donor's own).
    - ``verified`` -- True iff the removed tris are BYTE-EQUAL (as a set, rounded 4dp) to what
      :func:`sea_patch_for_block` reconstructs from their OWN cell footprint -- proves they really are
      THIS mechanism's v1 output (count-only would not prove that); refuses to trust a mismatch.

    Method: deployed tri count minus the PRISTINE DONOR's own Sea4 tri count (via the cell's own
    ``Donor.txt`` -- not an assumed offset) is the candidate patch length; :func:`merge_local_mesh`
    always APPENDS, so those are always the TRAILING tris -- geometry-verified below before anything
    downstream trusts the split."""
    existing_path = (config.find_game_path(game) / mod_folder / M.override_relpath(disc, bx, by, lod, "Sea4"))
    if not existing_path.is_file():
        return None, [], True
    deployed_bm = M.blockmesh_from_ff9mesh(existing_path, disc=disc, x=bx, y=by, lod=lod, part="sea4")
    donor = donor_cell_for_block(bx, by, mod_folder=mod_folder, disc=disc, lod=lod, game=game)
    pristine_bm = X.read_block(*donor, disc=disc, lod=lod, part="sea4", game=game)
    n_patch = len(deployed_bm.tris) - len(pristine_bm.tris)
    if n_patch <= 0:
        return deployed_bm, [], True
    V = deployed_bm.verts
    trailing = deployed_bm.tris[-n_patch:]
    keep_cells = set()
    for tri in trailing:
        cx = sum(V[j][0] for j in tri) / 3.0
        cz = sum(V[j][2] for j in tri) / 3.0
        keep_cells.add((math.floor(cx / GRID), math.floor(cz / GRID) + 16))
    recon = sea_patch_for_block(bx, by, keep_cells, disc=disc)

    def _triset(verts, tris):
        return {tuple(sorted(tuple(round(c, 4) for c in verts[j]) for j in tri)) for tri in tris}
    verified = (len(recon.tris) == n_patch and _triset(V, trailing) == _triset(recon.verts, recon.tris))
    keep_tris = deployed_bm.tris[:-n_patch]
    keep_flat = [j for tri in keep_tris for j in tri]
    pre_bm = dataclasses.replace(deployed_bm, tris=keep_tris, flat_index=keep_flat)
    patch_tris_local = [[list(V[j]) for j in tri] for tri in trailing]
    return pre_bm, patch_tris_local, verified


def _world_shift_tris(tris_local_xyz, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    return [[[p[0] + ox, p[1], p[2] + oz] for p in tri] for tri in tris_local_xyz]


def other_real_tris_for_gate(meshlists_for_block, pre_sea4_world_bm):
    """``{part: [[3 (x,y,z)], ...]}`` (world frame) for every OTHER real part in a block's deployed
    meshlist, plus the block's own REAL (patch-stripped) Sea4 under key ``"Sea4"`` -- exactly the set a
    new Sea4 patch tri must never coplanar-overlap."""
    ml = dict(meshlists_for_block)
    out = {}
    for part, bm in ml.items():
        if part == "Sea4":
            continue
        V = bm.verts
        out[part] = [[V[j] for j in tri] for tri in _tris_of(bm)]
    if pre_sea4_world_bm is not None:
        tris = _tris_of(pre_sea4_world_bm)
        if tris:
            V = pre_sea4_world_bm.verts
            out["Sea4"] = [[V[j] for j in tri] for tri in tris]
    return out


# --------------------------------------------------------------------------- v2: fine-clipped patch

def _n_fine(grid):
    return int(round(64.0 / grid))


def local_cell_fine(px, pz, bx, by, grid=FINE_GRID):
    lx = px - 64.0 * bx
    lz = pz + 64.0 * by
    return int(math.floor(lx / grid)), int(math.floor(lz / grid)) + _n_fine(grid)


def fine_cell_local_box(fx, fz, grid=FINE_GRID):
    n = _n_fine(grid)
    lx0 = fx * grid
    lz0 = (fz - n) * grid
    return lx0, lx0 + grid, lz0, lz0 + grid


def fine_cell_world_box(fx, fz, bx, by, grid=FINE_GRID):
    lx0, lx1, lz0, lz1 = fine_cell_local_box(fx, fz, grid)
    ox, oz = X.block_world_origin(bx, by)
    return lx0 + ox, lx1 + ox, lz0 + oz, lz1 + oz


def hole_cells_per_block_fine(misses, *, grid=FINE_GRID, margin_rings=1):
    """The FINE-grid analogue of :func:`hole_cells_per_block` -- ``{(bx,by): (core, extra)}`` at
    ``grid``-u resolution (default 0.5u, vs v1's whole-4u-cell version)."""
    n = _n_fine(grid)
    core = collections.defaultdict(set)
    for (px, pz) in misses:
        bx = int(math.floor(px / 64.0))
        by = int(math.floor(-pz / 64.0))
        core[(bx, by)].add(local_cell_fine(px, pz, bx, by, grid))
    out = {}
    for blk, cells in core.items():
        dilated = set(cells)
        for (ix, iz) in cells:
            for dx in range(-margin_rings, margin_rings + 1):
                for dz in range(-margin_rings, margin_rings + 1):
                    dilated.add((ix + dx, iz + dz))
        core_clip = {(ix, iz) for (ix, iz) in cells if 0 <= ix < n and 0 <= iz < n}
        extra_clip = {(ix, iz) for (ix, iz) in (dilated - cells) if 0 <= ix < n and 0 <= iz < n}
        out[blk] = (core_clip, extra_clip)
    return out


def clip_tri_to_box(pos3, attrs3, x0, x1, z0, z1):
    """Sutherland-Hodgman clip of ONE triangle (``pos3`` = 3 ``[x,y,z]``, ``attrs3`` = 3
    ``{"nrm":,"uv":,"tan":}``) against an axis-aligned XZ box. Every interior clip point lands ON an
    original triangle EDGE, so linear interpolation of every channel along that edge is EXACT (not an
    approximation) -- the clipped polygon carries the source plane's own normal/UV/topo unchanged, just
    a smaller footprint. Returns the clipped convex polygon as ``[(x,y,z,attrs), ...]`` (``[]``/<3
    entries if fully outside/degenerate)."""
    poly = [(pos3[i][0], pos3[i][1], pos3[i][2], attrs3[i]) for i in range(3)]

    def lerp(a, b, t):
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t
        z = a[2] + (b[2] - a[2]) * t
        na, nb = a[3], b[3]
        attrs = {"nrm": [na["nrm"][k] + (nb["nrm"][k] - na["nrm"][k]) * t for k in range(3)],
                 "uv": [na["uv"][k] + (nb["uv"][k] - na["uv"][k]) * t for k in range(2)],
                 "tan": [na["tan"][k] + (nb["tan"][k] - na["tan"][k]) * t for k in range(4)]}
        return (x, y, z, attrs)

    def clip_plane(poly, inside, intersect):
        if not poly:
            return []
        out = []
        n = len(poly)
        for i in range(n):
            cur, nxt = poly[i], poly[(i + 1) % n]
            cur_in, nxt_in = inside(cur), inside(nxt)
            if cur_in:
                out.append(cur)
            if cur_in != nxt_in:
                out.append(intersect(cur, nxt))
        return out

    poly = clip_plane(poly, lambda v: v[0] >= x0 - 1e-9,
                      lambda a, b: lerp(a, b, (x0 - a[0]) / (b[0] - a[0])))
    poly = clip_plane(poly, lambda v: v[0] <= x1 + 1e-9,
                      lambda a, b: lerp(a, b, (x1 - a[0]) / (b[0] - a[0])))
    poly = clip_plane(poly, lambda v: v[2] >= z0 - 1e-9,
                      lambda a, b: lerp(a, b, (z0 - a[2]) / (b[2] - a[2])))
    poly = clip_plane(poly, lambda v: v[2] <= z1 + 1e-9,
                      lambda a, b: lerp(a, b, (z1 - a[2]) / (b[2] - a[2])))
    return poly


def _plane_indexed(plane, *, grid=GRID):
    """``{macro_cell: [(pos3, attrs3), ...]}`` for every tri in the mint's sea plane -- same cell math
    as :func:`sea_patch_for_block`."""
    ca = plane.chan_arrays
    n = _n_fine(grid)
    out = collections.defaultdict(list)
    for tri in plane.tris:
        pos3 = [ca[X.CH_POS][j] for j in tri]
        attrs3 = [{"nrm": ca[X.CH_NRM][j], "uv": ca[X.CH_UV][j], "tan": ca[X.CH_TAN][j]} for j in tri]
        cx = sum(p[0] for p in pos3) / 3.0
        cz = sum(p[2] for p in pos3) / 3.0
        out[(math.floor(cx / grid), math.floor(cz / grid) + n)].append((pos3, attrs3))
    return out


def fine_patch_for_block(bx, by, keep_fine_cells, *, fine_grid=FINE_GRID, disc=DISC, game=GAME):
    """v2's own patch mechanism: instead of v1's whole-macro-4u-cell :func:`sea_patch_for_block`, this
    CLIPS the SAME mint sea-plane source (:func:`ff9mapkit.world.island._sea_plane` -- the game's only
    full-cell deep Sea4 plane, byte-identical donor every ``world-island``/``world-mountain`` mint
    already stacks under its land) down to the exact fine-cell footprint kept. Every emitted tri is an
    exact sub-piece of a REAL plane tri (same topo-57 idall, same normal, correctly-interpolated UV) --
    just with its outer boundary pulled in to the true hole extent instead of blanketing the whole
    macro cell, so it can no longer re-enter real carried Sea1/Sea3/Sea5 territory the way v1's
    whole-cell fill did."""
    plane = ISL._sea_plane(disc, game)
    by_macro = _plane_indexed(plane)
    pos, nrm, uv, tan, flat, tidx = [], [], [], [], [], []
    for (fx, fz) in sorted(keep_fine_cells):
        lx0, lx1, lz0, lz1 = fine_cell_local_box(fx, fz, fine_grid)
        cx, cz = (lx0 + lx1) / 2.0, (lz0 + lz1) / 2.0
        macro_cell = (math.floor(cx / GRID), math.floor(cz / GRID) + 16)
        for (pos3, attrs3) in by_macro.get(macro_cell, []):
            poly = clip_tri_to_box(pos3, attrs3, lx0, lx1, lz0, lz1)
            if len(poly) < 3:
                continue
            for i in range(1, len(poly) - 1):
                tri_pts = (poly[0], poly[i], poly[i + 1])
                base = len(pos)
                for (x, y, z, at) in tri_pts:
                    pos.append([x, y, z]); nrm.append(list(at["nrm"]))
                    uv.append(list(at["uv"])); tan.append(list(at["tan"]))
                    flat.append(len(pos) - 1)
                tidx.append([base, base + 1, base + 2])
    from ff9mapkit.world.extract import BlockMesh
    return BlockMesh(name=f"Block[{bx}][{by}] Sea4", disc=disc, x=bx, y=by, lod=LOD, vcount=len(pos),
                     stride=48, channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                     chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
                     flat_index=flat, tris=tidx, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def shave_patch_y(patch_bm, offending_tri_indices, *, drop):
    """Vertical fallback (task requirement 2b) for the tiny residual slivers a FIXED fine grid cannot
    fully avoid at an organic (non-grid-aligned) real coastline edge (requirement 2a's clip handles
    the bulk; this handles what's left): push ONLY the flagged tris' own 3 vertices down by ``drop``
    (>= the gate's min_sep) -- never the whole patch. Safe because (1) every tri in
    :func:`fine_patch_for_block`'s output owns its OWN 3 vertex slots (nothing shared across tris, incl.
    within the same fine cell -- confirmed by construction), so this cannot drag a neighbouring tri
    out of plane; (2) the ground-query gate reads TOPOGRAPH off the tangent, never the exact Y, so a
    sub-0.1u depth nudge changes nothing about navigability/boat-legality."""
    ca = patch_bm.chan_arrays
    pos = [list(p) for p in ca[X.CH_POS]]
    touched = {j for ti in offending_tri_indices for j in patch_bm.tris[ti]}
    for j in touched:
        pos[j][1] -= drop
    return dataclasses.replace(patch_bm, chan_arrays={**ca, X.CH_POS: pos})


def unsafe_fine_cells(meshlists_for_block, bx, by, candidate_cells, *, fine_grid=FINE_GRID,
                      check_parts=OVERLAP_CHECK_PARTS, min_sep=MIN_LAWFUL_SEP, samples=5, patch_y=0.0):
    """Which of ``candidate_cells`` (fine-grid indices, meant for the DILATION margin only -- core miss
    cells are unconditionally kept by the caller) have ANY real tri from ``check_parts`` rendering
    within ``min_sep`` of the patch plane's own Y (measured 0.0 here) anywhere in their footprint --
    would-be z-fight territory a margin-only cell is a CANDIDATE to skip. v2 treated "unsafe" as
    sufficient reason to drop a cell outright -- WRONG, per the refusing gate: dropping it CAN reopen a
    real hole if the cell also happens to be genuinely holed (2 of v2's 28 unsafe-excluded cells were).
    The caller (:func:`build_v2_patch_for_block`, v3) now runs every result of this function through
    :func:`genuinely_holed_fine_cells` before honouring the exclusion."""
    ml = dict(meshlists_for_block)
    unsafe = {}
    for (fx, fz) in sorted(candidate_cells):
        wx0, wx1, wz0, wz1 = fine_cell_world_box(fx, fz, bx, by, fine_grid)
        hits = collections.Counter()
        for si in range(samples):
            for sj in range(samples):
                px = wx0 + (wx1 - wx0) * (si + 0.5) / samples
                pz = wz0 + (wz1 - wz0) * (sj + 0.5) / samples
                for part in check_parts:
                    bm = ml.get(part)
                    if bm is None:
                        continue
                    for y in _raw_hits(bm, px, pz):
                        if abs(y - patch_y) < min_sep:
                            hits[part] += 1
        if hits:
            unsafe[(fx, fz)] = dict(hits)
    return unsafe


def genuinely_holed_fine_cells(pre_ml_for_block, bx, by, candidate_cells, *, fine_grid=FINE_GRID,
                               step=FINE_VERIFY_STEP):
    """THE REQUIREMENT-1 GATE: which of ``candidate_cells`` (fine-grid indices) are GENUINELY holed --
    i.e. the REAL (v1-patch-stripped) meshlist ``pre_ml_for_block`` still MISSES somewhere inside them
    at ``step`` resolution -- as opposed to merely being flagged by :func:`unsafe_fine_cells` for sitting
    near real Sea3/Sea5/Sea6 territory. A cell this function returns must NEVER be dropped from the v2/v3
    patch clip, no matter what :func:`unsafe_fine_cells` said about it: coverage beats cosmetics, and the
    ONLY lawful way to reconcile the resulting coplanar conflict is :func:`shave_patch_y`, never a hole.
    A single :func:`window_census` over the union bbox of ``candidate_cells`` (not one call per cell) --
    cheap, since ``candidate_cells`` is always just the current attempt's small dilation margin."""
    if not candidate_cells:
        return set()
    fx0 = min(fx for fx, _ in candidate_cells); fx1 = max(fx for fx, _ in candidate_cells) + 1
    fz0 = min(fz for _, fz in candidate_cells); fz1 = max(fz for _, fz in candidate_cells) + 1
    lx0, _, lz0, _ = fine_cell_local_box(fx0, fz0, fine_grid)
    _, lx1, _, lz1 = fine_cell_local_box(fx1 - 1, fz1 - 1, fine_grid)
    ox, oz = X.block_world_origin(bx, by)
    wx0, wx1, wz0, wz1 = lx0 + ox, lx1 + ox, lz0 + oz, lz1 + oz
    truth = window_census({(bx, by): pre_ml_for_block}, wx0, wx1, wz0, wz1, step=step)
    holed = set()
    for (px, pz) in truth["miss"]:
        cell = local_cell_fine(px, pz, bx, by, fine_grid)
        if cell in candidate_cells:
            holed.add(cell)
    return holed


def build_v2_patch_for_block(bx, by, deployed, *, rebuild_step=0.1, fine_grid=FINE_GRID,
                             margin_rings=1, max_growth=4, window_margin=8.0, min_sep=MIN_LAWFUL_SEP,
                             fine_verify_step=FINE_VERIFY_STEP, max_shave_passes=MAX_SHAVE_PASSES,
                             disc=DISC, game=GAME):
    """Rebuild block ``(bx, by)``'s Sea4 override as v3: strip any v1 patch, re-census the TRUE
    (pre-patch) hole at fine resolution, and fill it with fine-clipped sub-cell quads instead of whole
    4u-cell ones -- keeping EVERY genuinely-holed fine cell regardless of Sea3/Sea5/Sea6 adjacency
    (requirement 1: :func:`genuinely_holed_fine_cells` re-proves each "unsafe"-flagged margin cell at
    ``fine_verify_step`` before it may be dropped) and reconciling any resulting coplanar conflict by
    depth-shaving, never by a hole. Returns a report dict; private (``_``-prefixed) keys carry live
    objects for the caller's gate check + deploy, and are stripped before JSON serialization."""
    existing_path = (config.find_game_path(game) / MOD_FOLDER / M.override_relpath(disc, bx, by, LOD, "Sea4"))
    report = {"block": [bx, by], "existing_path": str(existing_path)}
    pre_bm, v1_patch_tris_local, verified = split_v1_patch(bx, by, disc=disc, game=game)
    report["v1_patch_tris"] = len(v1_patch_tris_local)
    report["v1_strip_verified"] = verified
    if pre_bm is None:
        report["note"] = "no Sea4 override deployed here"
        return report
    if v1_patch_tris_local and not verified:
        report["note"] = "REFUSING -- trailing tris do not geometry-match the v1 patch constructor"
        return report
    report["_pre_bm"] = pre_bm

    pre_ml = [(p, m) for (p, m) in deployed[(bx, by)] if p != "Sea4"]
    pre_ml.append(("Sea4", _world_shift(pre_bm, bx, by)))
    pre_ml.sort(key=lambda pm: REG_ORDER.index(pm[0]))
    ox, oz = X.block_world_origin(bx, by)

    # Restrict the (expensive, fine-resolution) re-census to a small window around the v1 patch's OWN
    # footprint + a safety margin, not the whole 64x64u block -- v1's hole_cells_per_block always maps
    # a miss to its OWN containing macro cell, so the true (pre-strip) hole is a strict subset of the
    # v1 patch's macro-cell footprint; growth only ever needs a few rings beyond that. This is what
    # makes a --margin-rings growth loop at 0.1u tractable (the whole-BLOCK 0.1u check still runs once,
    # unrestricted, under --verify-fine, as the final honest proof).
    if v1_patch_tris_local:
        xs = [p[0] for tri in v1_patch_tris_local for p in tri]
        zs = [p[2] for tri in v1_patch_tris_local for p in tri]
        lx0 = max(0.0, min(xs) - window_margin); lx1 = min(64.0, max(xs) + window_margin)
        lz0 = max(-64.0, min(zs) - window_margin); lz1 = min(0.0, max(zs) + window_margin)
    else:
        lx0, lx1, lz0, lz1 = 0.0, 64.0, -64.0, 0.0
    wx0, wx1, wz0, wz1 = lx0 + ox, lx1 + ox, lz0 + oz, lz1 + oz
    report["rebuild_window_world"] = [round(wx0, 1), round(wx1, 1), round(wz0, 1), round(wz1, 1)]

    truth = window_census({(bx, by): pre_ml}, wx0, wx1, wz0, wz1, step=rebuild_step)
    report["true_holes_found"] = len(truth["miss"])
    report["true_hole_points_sample"] = [[round(p, 2) for p in pt] for pt in truth["miss"][:10]]
    if not truth["miss"]:
        report["note"] = "no residual hole once the v1 patch is stripped -- nothing to rebuild"
        return report

    cur_misses = list(truth["miss"])
    patch_v2, post = None, {"miss": cur_misses}
    for attempt in range(max_growth):
        mr = margin_rings + attempt
        cells = hole_cells_per_block_fine(cur_misses, grid=fine_grid, margin_rings=mr)
        core, extra = cells.get((bx, by), (set(), set()))
        unsafe = set(unsafe_fine_cells(deployed[(bx, by)], bx, by, extra, fine_grid=fine_grid,
                                       min_sep=min_sep))
        # requirement 1: an "unsafe" (Sea3/Sea5/Sea6-adjacent) MARGIN cell may be dropped only once a
        # fine (fine_verify_step) re-census of the REAL geometry proves it has no true hole in it --
        # never on the adjacency flag alone (that is exactly the bug the refusing gate caught: 2 of 28
        # unsafe-excluded cells at v2's 0.1u resolution were ALSO genuinely holed at 0.02u). A cell this
        # proves is genuinely holed is kept unconditionally; shave_patch_y (below) -- not a hole -- is
        # what reconciles the resulting coplanar conflict.
        really_holed = genuinely_holed_fine_cells(pre_ml, bx, by, unsafe & extra, fine_grid=fine_grid,
                                                   step=fine_verify_step)
        if really_holed:
            report.setdefault("warnings", []).append(
                f"{len(really_holed)} 'unsafe' fine cell(s) PROVEN genuinely holed at {fine_verify_step}u "
                f"-- KEPT (coverage beats cosmetics, never dropped): {sorted(really_holed)}")
        safe_to_drop = (unsafe & extra) - really_holed
        keep_fine = core | (extra - safe_to_drop)
        patch_v2 = fine_patch_for_block(bx, by, keep_fine, fine_grid=fine_grid, disc=disc, game=game)
        new_ml = [(p, m) for (p, m) in deployed[(bx, by)] if p != "Sea4"]
        new_ml.append(("Sea4", _world_shift(merge_local_mesh(pre_bm, patch_v2), bx, by)))
        new_ml.sort(key=lambda pm: REG_ORDER.index(pm[0]))
        post = window_census({(bx, by): new_ml}, wx0, wx1, wz0, wz1, step=rebuild_step)
        report[f"attempt_{attempt}"] = {"margin_rings": mr, "core_cells": len(core),
                                        "extra_kept": len(extra) - len(safe_to_drop),
                                        "extra_excluded_safe": len(safe_to_drop),
                                        "extra_genuinely_holed_kept": len(really_holed),
                                        "patch_tris": len(patch_v2.tris), "post_miss": len(post["miss"])}
        if not post["miss"]:
            break
        cur_misses = post["miss"]
    report["final_post_miss"] = len(post["miss"])

    # ---- requirement 2: shave any residual coplanar sliver clipping (+ the requirement-1 genuinely-
    # holed cells above) couldn't avoid. A FIXED fine grid cannot always perfectly hug an organic
    # (non-grid-aligned) real coastline edge -- clip_tri_to_box gets the bulk of the footprint exactly
    # right, but a handful of edge tris can still sliver-overlap a real part by a hair, and a
    # genuinely-holed cell kept over an unsafe flag can overlap a real part by more than a hair. Gate,
    # and only if it finds something, nudge exactly those tris down and re-gate -- shave_patch_y
    # SUBTRACTS from each tri's own current Y, so repeated passes on the same tri are CUMULATIVE (never
    # reset), and the per-pass depth escalates too: coverage beats cosmetics via the shave, iterated as
    # many times as it takes (up to max_shave_passes) -- a tri is NEVER dropped to satisfy this gate.
    other = other_real_tris_for_gate(deployed[(bx, by)], _world_shift(pre_bm, bx, by))
    shave_log = []
    for shave_pass in range(max_shave_passes):
        local_tris = [[list(patch_v2.verts[j]) for j in tri] for tri in patch_v2.tris]
        world_tris = _world_shift_tris(local_tris, bx, by)
        labeled = [(i, tri) for i, tri in enumerate(world_tris)]
        offenders = coplanar_overlap_gate(labeled, other, min_sep=min_sep)
        if not offenders:
            break
        idx = sorted({o["patch_tri"] for o in offenders})
        depth = min_sep + 0.02 * (shave_pass + 1)
        shave_log.append({"pass": shave_pass, "offenders": len(offenders), "tris_shaved": len(idx),
                          "drop": round(depth, 4)})
        patch_v2 = shave_patch_y(patch_v2, idx, drop=depth)
    else:
        report.setdefault("warnings", []).append(
            f"shave did NOT converge after {max_shave_passes} passes -- coverage KEPT anyway (never "
            f"dropped for cosmetics); inspect shave_passes")
    if shave_log:
        report["shave_passes"] = shave_log
    merged = merge_local_mesh(pre_bm, patch_v2)
    report["_merged_bm"] = merged
    report["_patch_v2_bm"] = patch_v2
    report["_true_hole_points_all"] = truth["miss"]
    return report


# --------------------------------------------------------------------------- v2: NO-COPLANAR-OVERLAP gate

def _signed_area_xz(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, z1 = pts[i]; x2, z2 = pts[(i + 1) % n]
        s += x1 * z2 - x2 * z1
    return s * 0.5


def _clip_poly_by_tri_xz(poly, tri):
    """Sutherland-Hodgman: clip convex polygon ``poly`` (list of ``(x,z)``) against triangle ``tri``'s
    3 half-planes."""
    t = list(tri)
    if _signed_area_xz(t) < 0:
        t = t[::-1]
    out = poly
    n = len(t)
    for i in range(n):
        if not out:
            break
        a, b = t[i], t[(i + 1) % n]

        def inside(p, a=a, b=b):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9
        new_out = []
        m = len(out)
        for j in range(m):
            cur, nxt = out[j], out[(j + 1) % m]
            cur_in, nxt_in = inside(cur), inside(nxt)
            if cur_in:
                new_out.append(cur)
            if cur_in != nxt_in:
                x1, z1 = cur; x2, z2 = nxt
                dax, daz = b[0] - a[0], b[1] - a[1]
                denom = dax * (z2 - z1) - daz * (x2 - x1)
                if abs(denom) < 1e-12:
                    continue
                tt = (dax * (a[1] - z1) - daz * (a[0] - x1)) / denom
                new_out.append((x1 + tt * (x2 - x1), z1 + tt * (z2 - z1)))
        out = new_out
    return out


def _poly_area_xz(pts):
    return 0.0 if len(pts) < 3 else abs(_signed_area_xz(pts))


def tri_tri_xz_overlap_area(tri_a, tri_b):
    """Exact 2D (XZ-plane) overlap area between two triangles (each 3 ``[x,y,z]``) -- a real convex
    polygon clip, not a bbox estimate."""
    poly = [(p[0], p[2]) for p in tri_b]
    tri = [(p[0], p[2]) for p in tri_a]
    return _poly_area_xz(_clip_poly_by_tri_xz(poly, tri))


def coplanar_overlap_gate(patch_tris, other_tris_by_part, *, min_sep=MIN_LAWFUL_SEP, area_eps=1e-4):
    """THE NO-COPLANAR-OVERLAP GATE. ``patch_tris`` = ``[(label, [3 (x,y,z)]), ...]``;
    ``other_tris_by_part`` = ``{part: [[3 (x,y,z)], ...]}`` (same frame, world here). An offender = any
    ``(patch tri, other tri)`` pair whose XZ footprints ACTUALLY overlap (real polygon area, not bbox)
    AND whose mean-Y separation is below ``min_sep`` -- exactly the two conditions a depth buffer
    flickers on."""
    offenders = []
    for (label, pa) in patch_tris:
        ay = sum(p[1] for p in pa) / 3.0
        ax0, ax1 = min(p[0] for p in pa), max(p[0] for p in pa)
        az0, az1 = min(p[2] for p in pa), max(p[2] for p in pa)
        for part, tris in other_tris_by_part.items():
            for k, pb in enumerate(tris):
                bx0, bx1 = min(p[0] for p in pb), max(p[0] for p in pb)
                bz0, bz1 = min(p[2] for p in pb), max(p[2] for p in pb)
                if bx1 < ax0 - 1e-6 or bx0 > ax1 + 1e-6 or bz1 < az0 - 1e-6 or bz0 > az1 + 1e-6:
                    continue
                area = tri_tri_xz_overlap_area(pa, pb)
                if area <= area_eps:
                    continue
                by_ = sum(p[1] for p in pb) / 3.0
                dY = abs(ay - by_)
                if dY < min_sep:
                    offenders.append({"patch_tri": label, "part": part, "other_tri_idx": k,
                                      "overlap_area": round(area, 4), "dY": round(dY, 5)})
    return offenders


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="perform the actual writes (Disc1 + Disc4 mirror)")
    ap.add_argument("--step", type=float, default=0.5,
                    help="whole-region dense-census step (world units) for the final zero-miss gate")
    ap.add_argument("--rebuild-step", type=float, default=0.1,
                    help="per-block fine re-census step used to find the TRUE (v1-patch-stripped) "
                         "hole footprint before clipping v2's patch to it -- 0.1u is the validated "
                         "hairline resolution")
    ap.add_argument("--fine-grid", type=float, default=FINE_GRID,
                    help="v2 patch lattice (world units) -- must evenly divide the macro GRID (4.0)")
    ap.add_argument("--margin-rings", type=int, default=1,
                    help="FINE-cell (--fine-grid-sized) dilation rings to start v2's patch at (grows "
                         "automatically on a residual post-patch miss)")
    ap.add_argument("--min-sep", type=float, default=MIN_LAWFUL_SEP,
                    help="NO-COPLANAR-OVERLAP gate floor (world units) -- see the measured-law note "
                         "at the top of the file (no positive lawful separation was ever measured)")
    ap.add_argument("--verify-fine", action="store_true",
                    help="also run the 0.1u whole-block census AND the NEW 0.02u whole-block census "
                         "(requirement 2c) per patched block, post-patch")
    ap.add_argument("--fine-verify-step", type=float, default=FINE_VERIFY_STEP,
                    help="requirement-1/2c fine re-check resolution -- the resolution that caught v2's "
                         "reopened holes; also used to decide whether an 'unsafe' margin cell is "
                         "genuinely holed before it may be dropped")
    ap.add_argument("--max-shave-passes", type=int, default=MAX_SHAVE_PASSES,
                    help="cap on shave_patch_y iterations before giving up (coverage is KEPT regardless "
                         "-- this only bounds how long the script tries before flagging a warning)")
    args = ap.parse_args()
    n_fine_check = GRID / args.fine_grid
    assert abs(n_fine_check - round(n_fine_check)) < 1e-9, "--fine-grid must evenly divide GRID=4.0"
    if args.deploy and not args.verify_fine:
        print("-- --deploy implies --verify-fine: the 0.02u whole-block census (requirement 2c) is now "
              "load-bearing for a real deploy, not merely reported -- enabling it --")
        args.verify_fine = True
    cross_ok, fine02_ok, boat02_ok = True, True, True   # only meaningfully computed under --verify-fine
                                        # below; a plain dry run without it never reaches the --deploy
                                        # gate that reads them (--deploy forces --verify-fine on above)

    out = {}
    print(f"== loading deployed meshlists for {TARGET_ANCHOR} + {SIZE} from {MOD_FOLDER} (disc {DISC}) ==")
    deployed = build_region_meshlists(TARGET_ANCHOR, SIZE, mod_folder=MOD_FOLDER, disc=DISC, lod=LOD, game=GAME)
    for blk, ml in sorted(deployed.items()):
        print(f"  block{list(blk)}: parts = {[p for p, _ in ml]}")

    # ================================================================= PHASE 1 -- MEASURE
    print("\n" + "=" * 78)
    print("PHASE 1 -- MEASURE (per-part Y layers, the v1 z-fight partner, the stock coexistence law)")
    print("=" * 78)
    measure_report = {}
    patched_blocks = []
    for blk in sorted(deployed):
        bx, by = blk
        pre_bm, v1_tris, verified = split_v1_patch(bx, by, disc=DISC, lod=LOD, game=GAME)
        if pre_bm is None:
            continue
        ystats = layer_y_stats(deployed[blk])
        print(f"\n-- block{list(blk)} per-part Y stats --")
        for part, s in ystats.items():
            print(f"   {part}: tris={s['tris']} Y=[{s['y_min']:.4f},{s['y_max']:.4f}] "
                  f"mean={s['y_mean']:.4f} top_y={s['top_y']}")
        entry = {"y_stats": ystats, "v1_patch_tris": len(v1_tris), "v1_strip_verified": verified}
        if not v1_tris and blk == (12, 18):
            # THE FROM-SCRATCH PATH (the flat-invariant incident's reset, 2026-07-20): after
            # sea_patch_reset.py strips a bad deploy back to the pristine carried Sea4, there is no
            # v1 delta to replace -- but the block's REAL stock holes still exist and the rebuild
            # machinery handles an empty strip (it censuses the whole block). Keep the known patched
            # block rebuild-eligible so the flat v3 can be built from the clean baseline.
            print("   no deployed patch delta, but this is the known holed block -- "
                  "rebuild-eligible from scratch")
            patched_blocks.append(blk)
        if v1_tris:
            patched_blocks.append(blk)
            macro_cells = {(math.floor(sum(p[0] for p in tri) / 3.0 / GRID),
                           math.floor(sum(p[2] for p in tri) / 3.0 / GRID) + 16) for tri in v1_tris}
            print(f"   v1 patch occupies {len(v1_tris)} tris across {len(macro_cells)} macro cell(s): "
                  f"{sorted(macro_cells)}")
            cov = part_coverage_fractions(deployed[blk], bx, by, macro_cells)
            print("   per-cell coverage fraction (any non-Sea4 part >0 sharing a cell with the patch "
                  "IS a z-fight candidate at Y=0):")
            for cell, frac in cov.items():
                print(f"     cell{cell}: {frac}")
            entry["v1_patch_macro_cells"] = sorted(f"{c}" for c in macro_cells)
            entry["v1_patch_cell_coverage"] = cov

            # split-Sea4 whole-block overlap census: real carried Sea4 vs the v1 patch tris vs everyone else
            deployed_sea4 = dict(deployed[blk])["Sea4"]           # a world-shifted _WM (no .tris)
            n_real = len(pre_bm.tris)
            sea4_tris_all = _tris_of(deployed_sea4)
            real_flat = [j for t in sea4_tris_all[:n_real] for j in t]
            patch_flat = [j for t in sea4_tris_all[n_real:] for j in t]
            split_ml = [(p, m) for p, m in deployed[blk] if p != "Sea4"]
            split_ml.append(("Sea4real", _WM(deployed_sea4.verts, deployed_sea4.tangents, real_flat)))
            split_ml.append(("Sea4patch", _WM(deployed_sea4.verts, deployed_sea4.tangents, patch_flat)))
            wb = whole_block_overlap_census(split_ml, bx, by, step=args.step)
            multi = {k: v for k, v in wb["counts"].items() if "|" in k}
            print(f"   whole-block ({args.step}u) multi-part overlap keys: {multi}")
            print(f"   overlap examples (world xz): {wb['examples']}")
            entry["whole_block_overlap"] = wb

            # THE V1 GATE PROOF -- must FAIL on the currently-deployed patch (proves the gate sees it)
            other = other_real_tris_for_gate(deployed[blk], _world_shift(pre_bm, bx, by))
            v1_world_tris = [(f"v1_patch_{i}", tri) for i, tri in
                             enumerate(_world_shift_tris(v1_tris, bx, by))]
            v1_offenders = coplanar_overlap_gate(v1_world_tris, other, min_sep=args.min_sep)
            print(f"   NO-COPLANAR-OVERLAP gate on the CURRENTLY-DEPLOYED v1 patch: "
                  f"{len(v1_offenders)} offender(s) -- "
                  f"{'gate correctly FAILS (confirms the live defect)' if v1_offenders else 'UNEXPECTED: gate did not see a defect'}")
            for o in v1_offenders[:12]:
                print(f"     {o}")
            entry["v1_gate_offenders"] = v1_offenders
        measure_report[f"{blk}"] = entry
    out["measure"] = measure_report

    print("\n-- the general stock coexistence law (pristine donor-neighbourhood sample, incl. the "
          "donor's own home) --")
    dh = DONOR_ANCHOR
    sample_blocks = sorted({dh, (dh[0] + 1, dh[1]), (dh[0], dh[1] + 1), (dh[0] + 2, dh[1]),
                           (dh[0] + 1, dh[1] - 1)})
    coex = pristine_coexistence_scan(sample_blocks, step=1.0, disc=DISC, lod=LOD, game=GAME)
    for blk_s, r in coex.items():
        print(f"   pristine{blk_s}: parts={r['parts']} y_ranges={r['y_ranges']} "
              f"multi_overlap={r['multi_overlap']}")
    out["stock_coexistence_law"] = coex
    any_overlap = any(r["multi_overlap"] for r in coex.values())
    print(f"\n   *** LAW: real stock sea/beach/terrain layers coexist by DISJOINT PLAN COVERAGE at a "
          f"UNIFORM Y (measured 0.0), never by a positive Y offset "
          f"({'COUNTEREXAMPLE FOUND -- see above' if any_overlap else 'zero counterexamples across the sample'}). "
          f"MIN_LAWFUL_SEP={args.min_sep}u is therefore the task's FLOOR, not a measured positive value. ***")
    out["law_zero_counterexamples"] = not any_overlap

    if not patched_blocks:
        print("\nno v1 Sea4 patch found anywhere in the region -- nothing to rebuild. Exiting.")
        out_path = Path(__file__).resolve().parent / "out" / "beach_island_sea_patch_v3.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
        return

    # ================================================================= PHASE 2 -- REBUILD (v3)
    print("\n" + "=" * 78)
    print("PHASE 2 -- REBUILD v3 (strip the v1 patch; fine-clip to the TRUE hole extent, keeping EVERY "
          "genuinely-holed cell; shave to reconcile, never drop coverage)")
    print("=" * 78)
    rebuild_report = {}
    would_write = []
    merged_cache = {}
    v2_gate_all_offenders = []
    true_holes_by_block = {}
    for blk in patched_blocks:
        bx, by = blk
        print(f"\n-- rebuilding block{list(blk)} --")
        rep = build_v2_patch_for_block(bx, by, deployed, rebuild_step=args.rebuild_step,
                                       fine_grid=args.fine_grid, margin_rings=args.margin_rings,
                                       min_sep=args.min_sep, fine_verify_step=args.fine_verify_step,
                                       max_shave_passes=args.max_shave_passes)
        for k, v in rep.items():
            if not k.startswith("_"):
                print(f"   {k}: {v}")
        true_holes_by_block[blk] = rep.get("_true_hole_points_all", [])
        merged, patch_v2, pre_bm = rep.get("_merged_bm"), rep.get("_patch_v2_bm"), rep.get("_pre_bm")
        if merged is not None and patch_v2 is not None:
            other = other_real_tris_for_gate(deployed[blk], _world_shift(pre_bm, bx, by))
            patch_v2_local_tris = [[list(patch_v2.verts[j]) for j in tri] for tri in patch_v2.tris]
            patch_v2_world = _world_shift_tris(patch_v2_local_tris, bx, by)
            labeled = [(f"v3_patch_{i}", tri) for i, tri in enumerate(patch_v2_world)]
            offenders = coplanar_overlap_gate(labeled, other, min_sep=args.min_sep)
            shave_recs = rep.get("shave_passes", [])
            # the LAST shave pass's tris_shaved is the final (post-convergence) shaved-tri count -- each
            # pass re-tests and re-shaves only the tris still offending, so it's monotonically shrinking,
            # not additive across passes.
            shaved_tri_count = shave_recs[-1]["tris_shaved"] if shave_recs else 0
            print(f"   FINAL PATCH SHAPE: {len(patch_v2.tris)} tris, "
                  f"{shaved_tri_count} tri(s) shaved on the final pass (depths per pass: "
                  f"{[rec['drop'] for rec in shave_recs] if shave_recs else 'none needed'})")
            print(f"   NO-COPLANAR-OVERLAP gate on v3's patch ({len(patch_v2.tris)} tris): "
                  f"{len(offenders)} offender(s) -- {'FAIL, refusing this block' if offenders else 'PASS'}")
            for o in offenders[:12]:
                print(f"     {o}")
            rep["v2_gate_offenders"] = offenders
            v2_gate_all_offenders += offenders
            if not offenders:
                merged_cache[blk] = merged
                would_write.append(rep["existing_path"])
            else:
                rep["note"] = rep.get("note", "") + " | v3 gate FAILED -- not queued for write"
        rebuild_report[f"{blk}"] = {k: v for k, v in rep.items() if not k.startswith("_")}
    out["rebuild"] = rebuild_report

    # ================================================================= PHASE 3 -- WHOLE-REGION VERIFY
    print("\n" + "=" * 78)
    print("PHASE 3 -- whole-region verification with v2 substituted in")
    print("=" * 78)
    patched_meshlists = {k: list(v) for k, v in deployed.items()}
    for blk, merged in merged_cache.items():
        bx, by = blk
        new_ml = [(p, m) for (p, m) in patched_meshlists[blk] if p != "Sea4"]
        new_ml.append(("Sea4", _world_shift(merged, bx, by)))
        new_ml.sort(key=lambda pm: REG_ORDER.index(pm[0]))
        patched_meshlists[blk] = new_ml
    cen2 = dense_census(patched_meshlists, TARGET_ANCHOR, SIZE, step=args.step)
    print(f"  probed={cen2['probed']}  miss={len(cen2['miss'])}")
    clean = len(cen2["miss"]) == 0
    out["post_patch_census"] = {"probed": cen2["probed"], "miss": len(cen2["miss"]),
                                "miss_points": cen2["miss"][:20]}

    def boat_check(points):
        """requirement 2d: every point given must, post-patch, resolve to a boat-legal (topo in
        ``BOAT_TOPO``) tile -- returns ``(all_ok, [{point, mesh, topo, boat_legal}, ...])``."""
        ok_all = True
        rows = []
        for (px, pz) in points:
            bx_ = int(math.floor(px / 64.0)); by_ = int(math.floor(-pz / 64.0))
            gy, name, idall, topo = P.place(patched_meshlists.get((bx_, by_), []), px, pz, y=400.0, sky=True)
            ok = name != "MISS" and topo in BOAT_TOPO
            ok_all &= ok
            rows.append({"point": [px, pz], "mesh": name, "topo": topo, "boat_legal": ok})
        return ok_all, rows

    print("\n== boat-legality of EVERY 0.1u-discovered TRUE hole point (requirement 2d) + the "
          "historically-reported point ==")
    target_note_pt = (763.0, -1216.0)
    check_pts = [target_note_pt]
    for blk in patched_blocks:
        check_pts += [tuple(p) for p in true_holes_by_block.get(blk, [])]
    print(f"  checking {len(check_pts)} point(s) (full 0.1u true-hole set, not a capped sample)")
    boat_ok, boat_report = boat_check(check_pts)
    for row in boat_report[:30]:
        print(f"  ({row['point'][0]:.2f},{row['point'][1]:.2f}) -> mesh={row['mesh']} topo={row['topo']} "
              f"boat_legal={row['boat_legal']}")
    if len(boat_report) > 30:
        print(f"  ... ({len(boat_report) - 30} more, all {'OK' if boat_ok else 'see JSON for failures'})")
    out["boat_gate"] = {"all_ok": boat_ok, "n_points": len(boat_report), "points_sample": boat_report[:40]}

    v2_gate_clean = len(v2_gate_all_offenders) == 0
    print(f"\nclean(post-patch miss==0) = {clean}   boat_gate_ok = {boat_ok}   "
          f"v2_no_coplanar_overlap_gate_clean = {v2_gate_clean}")
    print(f"would_write ({len(would_write)}):")
    for w in would_write:
        print(f"  {w}")
    out["would_write_disc1"] = would_write
    out["clean"] = clean
    out["v2_gate_clean"] = v2_gate_clean

    if args.verify_fine:
        print("\n== --verify-fine: 0.1u whole-block census per patched block, PRE (v1-stripped) vs POST (v3) ==")
        vf = {}
        for blk in patched_blocks:
            bx, by = blk
            ox, oz = X.block_world_origin(bx, by)
            post = window_census(patched_meshlists, ox, ox + 64.0, oz - 64.0, oz, step=0.1)
            print(f"  block{list(blk)} @0.1u POST-v3: probed={post['probed']} miss={len(post['miss'])} "
                  f"-> {'PASS' if not post['miss'] else 'FAIL'}")
            vf[f"{blk}"] = {"probed": post["probed"], "miss": len(post["miss"]),
                            "miss_points": post["miss"][:40],
                            "pre_v1_strip_true_holes": rebuild_report[f"{blk}"].get("true_holes_found")}
        out["verify_fine"] = vf

        # ------------------------------------------------------------------- requirement 2c: THE 0.02u
        # FULL-BLOCK CENSUS -- the resolution that actually caught v2's defect, run over the WHOLE
        # 64x64u block footprint (not just the patch bbox), as its own first-class gate.
        print(f"\n== --verify-fine: cross-validating the fast bucketed census before trusting it "
              f"(coarse {args.step}u, whole block) ==")
        cross_ok = True
        cross = {}
        for blk in patched_blocks:
            bx, by = blk
            cv = cross_validate_fast_census(patched_meshlists[blk], bx, by, step=args.step)
            cross_ok &= cv["agree"]
            print(f"  block{list(blk)}: slow_miss={cv['slow_miss']} fast_miss={cv['fast_miss']} "
                  f"agree={cv['agree']} (only_slow={cv['only_slow']} only_fast={cv['only_fast']})")
            cross[f"{blk}"] = cv
        out["fast_census_cross_validation"] = {"all_agree": cross_ok, "by_block": cross}
        if not cross_ok:
            print("  CROSS-VALIDATION FAILED -- the fast census diverges from the byte-exact one; "
                  "the 0.02u gate below is NOT trustworthy this run (see JSON).")

        print(f"\n== --verify-fine: THE 0.02u WHOLE-BLOCK census (requirement 2c) -- the resolution "
              f"that caught v2's defect ==")
        fine02 = {}
        fine02_ok = True
        fine02_boat_pts = []
        for blk in patched_blocks:
            bx, by = blk
            f02 = fast_block_census(patched_meshlists[blk], bx, by, step=args.fine_verify_step)
            ok = len(f02["miss"]) == 0
            fine02_ok &= ok
            print(f"  block{list(blk)} @{args.fine_verify_step}u FULL-BLOCK POST-v3: "
                  f"probed={f02['probed']} miss={len(f02['miss'])} -> {'PASS' if ok else 'FAIL'}")
            fine02[f"{blk}"] = {"probed": f02["probed"], "miss": len(f02["miss"]),
                                "miss_points_sample": [[round(p, 3) for p in pt] for pt in f02["miss"][:40]]}
            fine02_boat_pts += f02["miss"]
        out["verify_fine_0_02"] = {"trusted": cross_ok, "clean": fine02_ok, "by_block": fine02}
        print(f"  0.02u whole-block gate: {'PASS (zero-miss on every patched block)' if fine02_ok else 'FAIL'}"
              f"{'' if cross_ok else '  (UNTRUSTED -- cross-validation failed)'}")

        if fine02_boat_pts:
            print(f"\n== boat-legality of the {len(fine02_boat_pts)} point(s) the 0.02u gate found ==")
            boat02_ok, boat02_report = boat_check(fine02_boat_pts)
            out["boat_gate_0_02"] = {"all_ok": boat02_ok, "n_points": len(boat02_report),
                                     "points_sample": boat02_report[:40]}
            print(f"  boat_gate_0_02_ok = {boat02_ok}")

    print("\n== bonus: event/area audit on the carried cells (report-only) ==")
    ev = event_area_audit(deployed)
    print(f"  live event/area tiles found: {len(ev)}")
    for h in ev[:20]:
        print(f"    {h}")
    out["event_area_audit"] = ev

    out_path = Path(__file__).resolve().parent / "out" / "beach_island_sea_patch_v3.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {out_path}")

    if args.deploy:
        # requirement 2c made the 0.02u whole-block gate first-class: a real deploy is refused unless it
        # ran (forced above), the fast/slow census agreed (cross_ok), it found zero misses (fine02_ok),
        # and every point it DID find (if cross-validation somehow still let a stale run through) is
        # boat-legal (boat02_ok) -- alongside every prior gate.
        if not (clean and boat_ok and v2_gate_clean and cross_ok and fine02_ok and boat02_ok):
            raise SystemExit(
                f"gate failure -- refusing to deploy (see report above): clean={clean} boat_ok={boat_ok} "
                f"v2_gate_clean={v2_gate_clean} cross_ok={cross_ok} fine02_ok={fine02_ok} "
                f"boat02_ok={boat02_ok}")
        print("\n== DEPLOYING v3 (Disc1 writes + Disc4 mirror; REPLACES the stripped v1 patch) ==")
        written = []
        for blk in sorted(merged_cache):
            bx, by = blk
            merged = merged_cache[blk]
            p = M.deploy_override(merged, mod_folder=MOD_FOLDER, game=GAME, lod=LOD, part="Sea4")
            written.append(str(p))
            print(f"  wrote {p}")
        mirrored = DM.auto_mirror(written, mod_folder=MOD_FOLDER)
        print(f"  disc-4 mirror: {mirrored}")
    else:
        print("\n(dry run -- pass --deploy to actually write the v2 patch)")


if __name__ == "__main__":
    main()
