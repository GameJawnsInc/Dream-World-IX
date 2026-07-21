"""THE TRUE MESH CARRY -- rung 6 of the dunes arc (2026-07-21), the correction of rung 5's
LABEL-STAMP FALLACY.

WHAT WENT WRONG (rung 5, dunes_field_mint.py -- REJECTED in-game, forensics-confirmed)
  The whole-stamp mint built a SYNTHETIC flat desert island and stamped ROW LABELS ({cell: row})
  onto it, regenerating every ecotone tile's UV from `strip_uv(world_x, world_z, cell, row, ori=0)`.
  Two defects, one root -- it carried LABELS, not MESH:
    * zero vertex motion  -> the dune|desert boundary is 100%% on the 4u grid (a staircase); stock
      comp[1] has ~15%% sub-cell CONFORMING seam verts (the boundary reads organic).
    * every tile at ori=0, UVs regenerated -> ~84%% of boundary ramps point the wrong way and only
      2.1%% of the cells' per-corner UVs byte-derive from the donor.
    * the 14-cell topo-59 hole was FILLED FLAT where stock has a real BUTTE (a ~5u mesa); the crest
      tiles were absent.
  The frozen grazing eye (`dunes_grazing_eye.py`) catches all three (GATE A/B/C); the old row eye
  (`dunes_mint_eye.py`) was blind to them.

WHAT THIS DOES -- THE CARRY LAW, applied
  Rigidly relocate stock comp[1]'s ACTUAL Terrain mesh -- verts (incl. the sub-cell conforms + the
  butte relief), per-corner UVs (orientations, crest tiles, real interior mains), tangents/topo,
  normals -- for the dune blob + its desert ecotone ring + a desert weld margin, onto the DEPLOYED
  r56 desert host at (1248,-1184), REPLACING the label-stamp cells. THE CARRY LAW: the carried
  content is RIGID (donor verts+uvs+tangents copied verbatim, translated by a WHOLE-CELL xz shift so
  the fractional-in-cell coords -- and thus the UV decode -- are preserved exactly, plus a uniform DY
  to seat the desert margin at the host's flat height); ALL seating deformation goes to the HOST at
  the carry boundary (kept-host boundary verts SNAP to the carried donor outer verts -> exact welds,
  then the host desert ramps back to flat over the conform ring). The host's coast/sea/apron beyond
  the carry region is untouched (proven fine).

  A faithful carry PASSES the frozen eye by construction: it reproduces the donor's off-grid seam
  verts (GATE A), its orientations + byte-identical UVs (GATE B, whole-cell shift preserves the
  fractional decode), and its rendered ecotone wiggle (GATE C).

Run OFFLINE (judges + renders, writes NOTHING to the game):  py studies/overworld-topography/dunes_true_carry.py
DEPLOY (guarded, both discs + backups):                       py studies/overworld-topography/dunes_true_carry.py --deploy
Artifacts -> out/dunes_true_carry.json, out/dunes_true_carry_*.png
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import discmirror as DM                  # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import grassland as GL                   # noqa: E402
from ff9mapkit.world import island as I                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import placement as P                    # noqa: E402
from ff9mapkit.world import transplant as TR                  # noqa: E402
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402

import dunes_grazing_eye as GE                                # noqa: E402  (frozen eye + loaders + judge)
import dunes_fringe_census as FC                              # noqa: E402  (the cross-block seam census)

BLOCK = 64.0
CELL = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
MOD = "FF9CustomMap-world"
DONOR_BLOCKS = [(bx, by) for bx in range(12, 16) for by in range(10, 14)]
MINT_BLOCKS = GE.MINT_BLOCKS                                  # (18-20,17-19) -- the deployed host
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)
BACKUP_DIR = HERE.parents[1] / "backups" / "dunes-true-carry.20260721"

# families we CARRY (the dune blob + its desert ecotone/margin + the butte); grass/t49/sea at the
# donor's fringe are NOT carried -- there the carried edge welds to the host's own desert.
CARRY_FAMS = frozenset({"desert", "dunes", "hole", "rock", "scrub", "brush"})
MARGIN_RINGS = 2                                              # desert weld margin past the blob
FRAME_SLACK = 0.06                                            # local-frame poke tolerance (dunes_field_mint law)
SNAP_TOL = 1.9                                                # a carried boundary vert must be within this of its grid corner
# --- rung-7 FRINGE FIX knobs (the two playtest fringe defects the true carry left; forensics
#     dunes_fringe_census.py). All three fixes live in the flat desert margin / mesa base /
#     amputation stumps, and EYE PRESERVATION is proven DIRECTLY -- the rebuilt GATE A/B equal the
#     stock donor calibration BYTE-FOR-BYTE (not via a distance proxy: the FIX-H snap at the HOLE-2
#     site is ~4u from a topo-41 ecotone cell, below the forensics' optimistic '8.9u', yet the eye
#     is byte-untouched because the fix moves no dune|desert-boundary vertex).
FIXH_TAU = 1.0                                                # FIX-H: pre-quantize a carried vert this close to a
#                                                              phase-shifted block border ONTO it (grid corners land
#                                                              exactly on a border or >=4u away, so 1.0 catches only
#                                                              off-grid conform NOTCH verts)

GATES: list = []


def gate(name: str, ok: bool, detail: str = "") -> bool:
    GATES.append((name, bool(ok), detail))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


# ============================================================================================
# cell-set helpers
# ============================================================================================
def dilate(cells, exclude):
    nxt = set()
    for c in cells:
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


def dilate_n(cells, n):
    full = set(cells)
    frontier = set(cells)
    for _ in range(n):
        ring = dilate(frontier, full)
        full |= ring
        frontier = ring
    return full


def enclosed_hole(cellset):
    xs = [c[0] for c in cellset]; zs = [c[1] for c in cellset]
    x0, x1, z0, z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
    outside, q = set(), deque()
    border = [(i, z0) for i in range(x0, x1 + 1)] + [(i, z1) for i in range(x0, x1 + 1)] \
        + [(x0, j) for j in range(z0, z1 + 1)] + [(x1, j) for j in range(z0, z1 + 1)]
    for seed in border:
        if seed not in cellset and seed not in outside:
            outside.add(seed); q.append(seed)
    while q:
        c = q.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if x0 <= n[0] <= x1 and z0 <= n[1] <= z1 and n not in cellset and n not in outside:
                outside.add(n); q.append(n)
    return {(i, j) for i in range(x0, x1 + 1) for j in range(z0, z1 + 1)
            if (i, j) not in cellset and (i, j) not in outside}


def boundary_of(cellset):
    return {c for c in cellset if any((c[0] + di, c[1] + dj) not in cellset for di, dj in NEI4)}


def boundary_corners(placed_R):
    """grid corners (gi,gj) incident to at least one placed_R cell AND at least one non-R cell --
    the carry weld ring. Cell (ci,cj) owns corners (ci,cj),(ci+1,cj),(ci,cj+1),(ci+1,cj+1);
    corner (gi,gj) is shared by cells (gi-1,gj-1),(gi-1,gj),(gi,gj-1),(gi,gj)."""
    pr = set(placed_R)
    out = set()
    for (ci, cj) in pr:
        for (gi, gj) in ((ci, cj), (ci + 1, cj), (ci, cj + 1), (ci + 1, cj + 1)):
            incident = {(gi - 1, gj - 1), (gi - 1, gj), (gi, gj - 1), (gi, gj)}
            if any(ic not in pr for ic in incident):
                out.add((gi, gj))
    return out


def cell_block(c):
    """Block owning cell (ci,cj). Canonical world<->block convention (extract/eye):
    world = (v.x + 64*bx, v.y, v.z - 64*by), v.x in [0,64], v.z in [-64,0] -> bx=floor(wx/64),
    by=floor(-wz/64). Uses the cell's world CENTRE so boundary cells resolve unambiguously."""
    wx = CELL * c[0] + CELL / 2.0
    wz = CELL * c[1] + CELL / 2.0
    return (int(math.floor(wx / BLOCK)), int(math.floor(-wz / BLOCK)))


# ============================================================================================
# mesh soup helpers (world <-> local, full-channel soup -> BlockMesh)
# ============================================================================================
def to_world_tri(bm_tri_verts):
    return bm_tri_verts


def bm_world_soup(bm, bx, by):
    """A deployed/host BlockMesh -> list of world-coord tris, each [(pos,nrm,uv,tan) x3]."""
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in [bm.flat_index[i:i + 3] for i in range(0, len(bm.flat_index), 3)]:
        vs = []
        for j in tri:
            p = (V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by)
            vs.append((p, tuple(N[j]), tuple(U[j]), tuple(TAN[j])))
        out.append(vs)
    return out


def soup_to_bm(world_tris, bx, by):
    """A list of WORLD-coord tris [(pos,nrm,uv,tan) x3] -> a flat/unindexed Terrain BlockMesh in
    the block's LOCAL frame (verts==idx, the FLAT-MESH invariant)."""
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    vi = 0
    for t in world_tris:
        base = vi
        for (p, n, u, tg) in t:
            pos.append([p[0] - BLOCK * bx, p[1], p[2] + BLOCK * by])
            nrm.append([n[0], n[1], n[2]])
            uv.append([u[0], u[1]])
            tan.append([tg[0], tg[1], tg[2], tg[3]])
            flat.append(vi); vi += 1
        tris.append([base, base + 1, base + 2])
    return BlockMesh(name=f"Block[{bx}][{by}] Terrain", disc=1, x=bx, y=by, lod="0_1", vcount=vi,
                     stride=48, channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def tri_cell(tri):
    cx = sum(v[0][0] for v in tri) / 3.0
    cz = sum(v[0][2] for v in tri) / 3.0
    return (math.floor(cx / CELL), math.floor(cz / CELL))


def redress_grass_tri(tri):
    """FIX-G (the orphan-grass-stump re-dress; forensics rung 7). A carried topo-0 tri is NOT a
    grass-mains tile -- it is a desert|grass ECOTONE decal (its UV sits in the desert-edge band
    u~0.92-0.98, paired with a topo-16 desert tri in the same cell) whose GRASS side was amputated
    by the carry (our island is all-desert), so it renders as a lone green shard against red desert
    (THE ENSEMBLE LAW's amputation-stump class). Re-dress it to plain desert exactly as stock's own
    86-desert dune-ensemble margin wears it: topo-17 + a position-generated desert-MAINS UV (the
    shipped GroundRetile 'recovered' path). VERTEX POSITIONS + NORMALS ARE VERBATIM -- only the UV
    and the IDALL topograph change, so the fix moves ZERO geometry (it cannot disturb any seam/weld
    or the frozen eye's GATE A). Input/output = a donor-frame tri [(pos,nrm,uv,tan) x3].

    Returns (tri, redressed_bool). Only topo-0 tris are re-dressed; everything else (incl. the 62
    topo-49 brown mesa murals, which are faithful ensemble content) passes through untouched."""
    if X.decode_id(int(round(tri[0][3][0])))["topograph"] != 0:
        return tri, False
    cx = sum(v[0][0] for v in tri) / 3.0
    cz = sum(v[0][2] for v in tri) / 3.0
    cell = (math.floor(cx / CELL), math.floor(cz / CELL))
    cq, co = GL.assign_mains({cell}, seed=0xF93)             # deterministic desert-mains quad/ori
    quad, ori = cq[cell], co[cell]
    out = []
    for (p, n, _uv, tan) in tri:
        d = X.decode_id(int(round(tan[0])))
        new_idall = float(X.encode_id(d["event"], d["area"], GL.GROUNDS["desert"]["topo"], d["flags"]))
        out.append((p, n, tuple(GL.ground_uv(p[0], p[2], cell, quad, ori, "desert")),
                    (new_idall,) + tuple(tan[1:])))
    return out, True


# ============================================================================================
# STEP 1 -- donor region + placement T + DY
# ============================================================================================
def load_donor():
    print("loading stock donor terrain (blocks 12-15,10-13) ...", flush=True)
    stock = GE.load_stock()                                    # eye tris (p3,uv3,n3,topo,fam)
    scfam = GE.cell_family(stock)
    scmap = GE.cells_map(stock)
    CORE = GE.dunes_footprint(scfam)
    FP41 = GE.topo41_footprint(scmap)
    HOLE = enclosed_hole(CORE)
    BLOB = CORE | HOLE
    # full-channel donor tris bucketed by centroid cell (for the actual carry)
    by_cell = defaultdict(list)
    for (bx, by) in DONOR_BLOCKS:
        for tri in TR.world_tris(bx, by, "terrain", disc=1):
            by_cell[tri_cell(tri)].append(tri)
    return dict(stock=stock, scfam=scfam, scmap=scmap, CORE=CORE, FP41=FP41, HOLE=HOLE,
                BLOB=BLOB, by_cell=dict(by_cell))


def define_region(donor):
    """R_donor = BLOB + carried (desert/butte) cells within MARGIN_RINGS of BLOB. Everything else
    at the fringe (grass/t49/sea) is left to the host."""
    scfam, BLOB = donor["scfam"], donor["BLOB"]
    near = dilate_n(BLOB, MARGIN_RINGS) - BLOB
    carry_extra = {c for c in near if scfam.get(c) in CARRY_FAMS}
    # also pull any butte/hole cell touching the blob (the mesa can poke past the enclosed hole)
    butte_adj = {c for c in dilate(BLOB, BLOB) if scfam.get(c) in ("hole", "rock")}
    R = set(BLOB) | carry_extra | butte_adj
    return R


# ============================================================================================
# STEP 2 -- the carry: donor rigid, host conforms
# ============================================================================================
def carry(donor, R, T, host_bms, land_height):
    """Return {block: new world-soup} after replacing placed(R) host cells with the RE-PARTITIONED
    donor mesh + conforming the kept-host boundary verts. THE CARRY LAW: the donor is RIGID -- a
    whole-cell xz shift (Tw = CELL*T) preserves every vert's fractional-in-cell coord, so the UV
    decode is byte-identical (GATE B), and a uniform DY seats the desert weld ring at the host's
    flat height. Because the HOST block partition is PHASE-SHIFTED from the donor's (T mod 16 != 0
    -- here (7,11)), a rigid carry's sub-cell conform verts would poke past the new 64u block frames
    if left whole; so each carried tri is RE-PARTITIONED at the host block borders (clip_poly, the
    transplant `_split_at_borders` law): a tri fully inside a block passes byte-identical, one that
    straddles a border keeps its inside part EXACTLY (pos/nrm/uv lerped on the cut, tangent/IDALL
    verbatim; the cut t is bit-identical on both sides -> watertight). Every built block then stays
    strictly in-frame like stock (which pokes 0.0u over 112k verts). ALL seating deformation goes to
    the HOST at the carry boundary (kept-host weld-ring verts SNAP to the carried donor verts).

    RUNG 7 FRINGE FIXES (the two playtest fringe defects the rung-6 carry left; forensics
    dunes_fringe_census.py -- each proven to the vertex, each living in the flat desert margin /
    mesa base / amputation stumps; eye preservation proven DIRECTLY by GATE A/B byte-identity):
      * FIX-G -- carried topo-0 orphan-grass-stumps re-dressed to plain desert (final assembly pass,
        so it catches donor-carried AND kept-host stumps; UV/topo only, ZERO geometry moved).
      * FIX-H -- the PHASE-SHIFTED NOTCH: carried verts within FIXH_TAU of a phase-shifted block
        border pre-quantized ONTO it BEFORE the re-partition, so the notch clips identically on both
        sides (closes the blue-sliver HOLES on the [19][17]|[19][18] z=-1152 seam).
      * FIX-S -- the BLOCK-LOCAL WELD-SNAP MISS: carried border-corner weld targets mirror-registered
        into the ADJACENT block, so the neighbour host welds UP to the elevated carried margin
        (closes the dY=0.12/0.33 STEPS at x=1216/1280 -- the cross-block form of the conform-snap)."""
    by_cell = donor["by_cell"]
    Tx, Tz = T
    placed_R = {(c[0] + Tx, c[1] + Tz) for c in R}

    # DY: seat the donor OUTER weld ring at the host's flat height ------------------------------
    weld_cells = boundary_of(R)
    weld_ys = []
    for c in weld_cells:
        for tri in by_cell.get(c, []):
            weld_ys.append(sum(v[0][1] for v in tri) / 3.0)
    donor_weld_med = float(np.median(weld_ys)) if weld_ys else land_height
    DY = land_height - donor_weld_med
    print(f"  DY = host_flat({land_height:.3f}) - donor_weld_median({donor_weld_med:.3f}) = {DY:+.4f}")

    # 1) translate every carried donor tri to host WORLD coords (whole-cell xz + uniform DY). ------
    Tw_x, Tw_z = CELL * Tx, CELL * Tz
    carried_world = []
    for c in R:
        for tri in by_cell.get(c, []):
            carried_world.append([((v[0][0] + Tw_x, v[0][1] + DY, v[0][2] + Tw_z), v[1], v[2], v[3])
                                  for v in tri])

    # FIX-H (THE PHASE-SHIFTED NOTCH): a sub-cell donor CONFORM vert that lands just off a
    # phase-shifted block border survives verbatim INTERIOR to one block (notching that block's
    # boundary off the border) while the SAME geometry clips STRAIGHT at the border in the
    # neighbour -> a thin triangular void where sea shows through (the blue sliver). Pre-quantize
    # any carried vert within FIXH_TAU of a block border ONTO it BEFORE the re-partition: the notch
    # vert then clips IDENTICALLY on both sides -> watertight. Deterministic per world position, so
    # every soup copy of a shared vert snaps identically and welds are preserved. Grid corners land
    # exactly on a border (dist 0, excluded by the >1e-4 floor) or >=4u away, so FIXH_TAU=1.0
    # catches ONLY the off-grid conform notch verts.
    fixh_positions = []
    for poly in carried_world:
        for k in range(len(poly)):
            (px, py, pz) = poly[k][0]
            nx = round(px / BLOCK) * BLOCK
            nz = round(pz / BLOCK) * BLOCK
            npx = nx if 1e-4 < abs(px - nx) < FIXH_TAU else px
            npz = nz if 1e-4 < abs(pz - nz) < FIXH_TAU else pz
            if npx != px or npz != pz:
                fixh_positions.append((npx, npz))
                poly[k] = ((npx, py, npz), poly[k][1], poly[k][2], poly[k][3])

    # 2) RE-PARTITION at the host block 64u borders (transplant's _split_at_borders law). Clip each
    #    tri to every block frame it spans; degenerate slivers (2x-area <= MIN_TRI_AREA2) drop. The
    #    in-frame poke is re-measured with the CORRECT z bounds ([-64,0]) as a sanity diagnostic.
    carried_by_block = defaultdict(list)
    dropped_area2 = 0.0
    max_poke = 0.0
    for poly0 in carried_world:
        xs = [v[0][0] for v in poly0]
        zs = [v[0][2] for v in poly0]
        i0, i1 = math.floor((min(xs) + 1e-9) / BLOCK), math.floor((max(xs) - 1e-9) / BLOCK)
        j0, j1 = math.floor((-max(zs) + 1e-9) / BLOCK), math.floor((-min(zs) - 1e-9) / BLOCK)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                q = poly0
                for (axis, plane, below) in ((0, BLOCK * i, False), (0, BLOCK * (i + 1), True),
                                             (2, -BLOCK * (j + 1), False), (2, -BLOCK * j, True)):
                    q = TR.clip_poly(q, axis, plane, below)
                    if len(q) < 3:
                        break
                if len(q) < 3:
                    continue
                for k in range(1, len(q) - 1):
                    t3 = [q[0], q[k], q[k + 1]]
                    a2 = TR._tri_area2_3d(t3)
                    if a2 <= TR.MIN_TRI_AREA2:
                        dropped_area2 += a2
                        continue
                    carried_by_block[(i, j)].append(t3)
                    for (p, _n, _u, _t) in t3:
                        lx, lz = p[0] - BLOCK * i, p[2] + BLOCK * j
                        max_poke = max(max_poke, -lx, lx - BLOCK, lz, -BLOCK - lz, 0.0)

    # 3) the weld ring: carried donor verts on placed_R's boundary corners (post-clip), keyed
    #    BLOCK-LOCAL. A weld corner ON a host block border is shared by two blocks: the carried
    #    conform vert lives in-frame in ONE of them (a sub-cell wiggle interior to it) and appears
    #    as the exact z=border cut vert in the other. Snapping a kept-host vert to the WRONG block's
    #    copy pokes it past the frame; keying by (blk,gi,gj) snaps every host vert to the carried
    #    vert of ITS OWN block -> exact in-block weld, strictly in-frame.
    bcorners = boundary_corners(placed_R)
    carried_boundary = {}                                     # (blk,gi,gj) -> carried world pos in blk
    boundary_spread = 0.0
    for blk, tris in carried_by_block.items():
        for tri in tris:
            for (p, _n, _u, _t) in tri:
                gi, gj = round(p[0] / CELL), round(p[2] / CELL)
                if (gi, gj) in bcorners and abs(p[0] - CELL * gi) < SNAP_TOL and abs(p[2] - CELL * gj) < SNAP_TOL:
                    key = (blk, gi, gj)
                    prev = carried_boundary.get(key)
                    if prev is not None:
                        boundary_spread = max(boundary_spread, math.dist(prev, p))
                    carried_boundary[key] = p

    # FIX-S (THE BLOCK-LOCAL WELD-SNAP MISS): the conform-snap keys the carried weld target by
    # (block,gi,gj), so a carried vert ON a block border is registered only in the block owning its
    # cell; the neighbour host's flat vert (land_height) finds no target and stays flat while the
    # carried margin is elevated (donor+DY) -> a vertical STEP (the lifted/shrunken seam). Mirror-
    # register every carried border-corner vert into the ADJACENT block so the neighbour host welds
    # UP to it -- the cross-block form of the conform-snap. A corner at grid index gi (x) or gj (z)
    # is on a block border iff the index is a multiple of 16 (world = 4*index, block = 64u = 16
    # cells); the two blocks meeting there differ by one in that axis.
    fixs_mirrors = 0
    fixs_mirror_blocks = set()                                # blocks a mirror LIFTS -> must be rebuilt
    for (blk, gi, gj), p in list(carried_boundary.items()):
        adj = set()
        if gi % 16 == 0:                                      # on an x block border (x = 4*gi = 64*(gi//16))
            b = gi // 16
            adj |= {(b - 1, blk[1]), (b, blk[1])}
        if gj % 16 == 0:                                      # on a z block border (z = 4*gj = -64*(-gj//16))
            b = -gj // 16
            adj |= {(blk[0], b - 1), (blk[0], b)}
        for mb in adj - {blk}:
            mkey = (mb, gi, gj)
            prev = carried_boundary.get(mkey)
            if prev is None:
                carried_boundary[mkey] = p
                fixs_mirrors += 1
                fixs_mirror_blocks.add(mb)
            else:
                boundary_spread = max(boundary_spread, math.dist(prev, p))

    # 4) assemble each touched block: kept host tris (dropped placed_R cells) + carried donor tris -
    out = {}
    conform_snaps = 0
    fixs_snap_positions = []                                  # host verts a mirror actually LIFTED (steps)
    # touched = the carried blocks + the placed-cell blocks + every FIX-S mirror block (a host block
    # with NO carried content but whose border verts must weld UP to a carried margin across the
    # block boundary -- e.g. the flat-desert host [18][18] at the x=1216 step). Without this the
    # carry would leave that block's deployed (buggy) bytes untouched and the step would persist,
    # invisible to an in-memory census that only sees the rebuilt blocks (the arc's blind spot).
    touched = sorted(set(carried_by_block) | {cell_block(c) for c in placed_R}
                     | {mb for mb in fixs_mirror_blocks if mb in host_bms})
    for blk in touched:
        host_soup = host_bms.get(blk, {}).get("soup", [])
        kept = [tri for tri in host_soup if tri_cell(tri) not in placed_R]
        # conform-snap kept host verts sitting on a boundary corner -> the carried donor vert of THIS block
        new_kept = []
        for tri in kept:
            nt = []
            for (p, n, u, t) in tri:
                gi, gj = round(p[0] / CELL), round(p[2] / CELL)
                tgt = carried_boundary.get((blk, gi, gj))
                if tgt is not None:
                    if math.dist(p, tgt) > 1e-6:
                        fixs_snap_positions.append((tgt[0], tgt[2]))
                    p = (tgt[0], tgt[1], tgt[2]); conform_snaps += 1
                nt.append((p, n, u, t))
            new_kept.append(nt)
        out[blk] = new_kept + carried_by_block.get(blk, [])

    # FIX-G (a FINAL pass over the assembled output, so it catches a topo-0 orphan-grass-stump
    # whether it rode in on a carried DONOR tri OR survived in a KEPT HOST cell -- both render as a
    # lone green shard against the all-desert island). Re-dress every remaining topo-0 tri to plain
    # desert (UV + IDALL topograph only; VERTEX POSITIONS ARE VERBATIM -> zero geometry moved, so
    # this can never disturb a seam/weld/the frozen eye's GATE A). The 62 topo-49 mesa murals are
    # NOT topo-0, so they pass through untouched (KEPT -- faithful dunes-ensemble content).
    n_redress = 0
    redress_positions = []
    for blk in out:
        redressed_tris = []
        for tri in out[blk]:
            rt, ok = redress_grass_tri(tri)
            if ok:
                n_redress += 1
                redress_positions += [(v[0][0], v[0][2]) for v in rt]
            redressed_tris.append(rt)
        out[blk] = redressed_tris

    # the FRINGE-FIX touch set (world XZ) for the EYE-CLEAR gate = only the GEOMETRY-MOVING fixes
    # (FIX-H notch pre-quantize + FIX-S host lifts). FIX-G moves ZERO geometry (UV/topo only), so
    # its verts -- which sit right against the dune-ensemble margin -- are excluded by design: they
    # cannot disturb GATE A/B/C, and counting them would false-fail the distance test.
    fix_touch_xz = sorted({(round(x, 3), round(z, 3))
                           for (x, z) in (fixh_positions + fixs_snap_positions)})
    diag = dict(placed_R=len(placed_R), weld_cells=len(weld_cells), DY=DY,
                donor_weld_med=donor_weld_med, n_bcorners=len(bcorners),
                n_carried_boundary=len(carried_boundary), boundary_spread=boundary_spread,
                max_poke=max_poke, dropped_area2=dropped_area2, conform_snaps=conform_snaps,
                n_redress=n_redress, n_fixh=len(fixh_positions), n_fixs_mirrors=fixs_mirrors,
                n_fixs_lifts=len(fixs_snap_positions), fix_touch_xz=fix_touch_xz,
                n_redress_positions=len(redress_positions), touched_blocks=touched)
    return out, placed_R, diag


# ============================================================================================
# STEP 3 -- gates
# ============================================================================================
def _sea_meshlist(bx, by, terrain_bm, plane):
    import dataclasses
    hid = lambda nm: M.hidden_block_mesh(name=nm, disc=1, x=bx, y=by)  # noqa: E731
    return [("Object", hid("Object")), ("Terrain", terrain_bm),
            ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")),
            ("Sea4", dataclasses.replace(plane, x=bx, y=by)), ("Sea5", hid("Sea5"))]


def run_gates(built_bms, placed_R, donor, T, land_height):
    plane = I._sea_plane(disc=1, game=None)

    # (a) FLAT-MESH verts==idx, grid bounds, weld audit -- per block
    flat_ok = grid_ok = True
    weld_total = 0
    weld_detail = {}
    for blk, bm in built_bms.items():
        flat_ok = flat_ok and (bm.vcount == len(bm.flat_index))
        grid_ok = grid_ok and M.block_in_grid(blk[0], blk[1])
        w = len(M.weld_audit([bm]))
        weld_detail[f"{blk[0]},{blk[1]}"] = w
        weld_total += w
    gate("FLAT-MESH invariant (vcount == indexCount, every built block)", flat_ok)
    gate("grid bounds (every built block on the 24x20 engine grid)", grid_ok)
    gate("weld audit at the carry ring (0 near-miss vertex pairs, every block in its own frame)",
         weld_total == 0, f"per-block={{b:n for b,n in weld_detail.items() if n}}={ {b: n for b, n in weld_detail.items() if n} } total={weld_total}")

    # (b) frame bounds
    fok = True
    fdet = {}
    for blk, bm in built_bms.items():
        lx = [v[0] for v in bm.verts]; lz = [v[2] for v in bm.verts]
        ok = (-FRAME_SLACK <= min(lx) and max(lx) <= BLOCK + FRAME_SLACK
              and -BLOCK - FRAME_SLACK <= min(lz) and max(lz) <= FRAME_SLACK)
        fok = fok and ok
        if not ok:
            fdet[blk] = (round(min(lx), 3), round(max(lx), 3), round(min(lz), 3), round(max(lz), 3))
    gate("frame bounds (local verts inside the block frame +/- slack, every block)", fok, f"{fdet}")

    # (c) MISS census: the butte (topo-59) is lawful non-walkable; dunes/desert must be walkable ----
    butte_placed = set()
    for c in donor["scmap"]:
        if any(topo == 59 for (topo, _w, _uv) in donor["scmap"][c]):
            butte_placed.add((c[0] + T[0], c[1] + T[1]))
    butte_placed &= placed_R
    miss_all = []
    miss_off_butte = []
    for blk, bm in built_bms.items():
        bx, by = blk
        cen = P.census(_sea_meshlist(bx, by, bm, plane), samples=24)
        for (px, pz) in cen["miss"]:
            wx, wz = px + BLOCK * bx, pz - BLOCK * by
            cell = (math.floor(wx / CELL), math.floor(wz / CELL))
            miss_all.append((blk, cell))
            if cell not in butte_placed:
                miss_off_butte.append((blk, cell))
    gate("MISS census: every MISS sits on a carried topo-59 BUTTE cell (lawful non-walkable); "
         "zero MISS on dunes/desert", len(miss_off_butte) == 0,
         f"miss_total={len(miss_all)} off_butte={len(miss_off_butte)} butte_cells={len(butte_placed)} "
         f"sample_off={miss_off_butte[:4]}")

    # (d) IDALL_SKIP not present as walkable ground (structurally the carry has no 4078 stubs)
    skip = any(int(round(bm.tangents[j][0])) in P.IDALL_SKIP
               for bm in built_bms.values() for j in range(bm.vcount))
    gate("no IDALL_SKIP tiles in the carried terrain", not skip)
    return dict(weld=weld_detail, butte_cells=len(butte_placed), miss_total=len(miss_all),
                miss_off_butte=len(miss_off_butte))


def _pt_cell_dist(px, pz, ci, cj):
    """Euclidean distance from world point (px,pz) to cell (ci,cj)'s AABB [4ci,4ci+4]x[4cj,4cj+4]."""
    dx = max(CELL * ci - px, 0.0, px - CELL * (ci + 1))
    dz = max(CELL * cj - pz, 0.0, pz - CELL * (cj + 1))
    return math.hypot(dx, dz)


def run_fringe_gates(built_bms, donor, T, diag, eye_verdict):
    """THE RUNG-7 FRINGE GATES -- the cross-block instruments the dunes arc never had (the
    memory's own recorded blind spot: weld_audit is per-block LOCAL-frame, so a coincident
    edge ACROSS a block boundary is structurally invisible to it). Calibration law honored:
    the STOCK donor region must census 0/0 FIRST, then the built blocks are judged.

    The census covers the FULL deployed mint region (rebuilt bytes where a block was rebuilt,
    DEPLOYED bytes for every un-rebuilt neighbour) -- so a step at a rebuilt|un-rebuilt border (e.g.
    the flat-desert [18][18] against the carried [19][18]) is caught, never vacuously passed by an
    in-memory census that sees only the rebuilt subset. This equals the post-deploy state exactly."""
    world_by_block = {}
    for blk in FC.MINT_BLOCKS:
        if blk in built_bms:
            world_by_block[blk] = FC.bm_world_tris(built_bms[blk], blk[0], blk[1])
        else:
            dep = FC.deployed_world_tris(blk[0], blk[1])
            if dep is not None:
                world_by_block[blk] = dep

    # (1) the calibration NULL -- stock donor region censuses clean (the instrument is calibrated)
    _null_recs, null_tot = FC.run_crack_census(FC.stock_world_tris, FC.DONOR_BLOCKS, "STOCK donor region (NULL)")
    gate("cross-block seam NULL (stock donor region: 0 steps, 0 holes -- the instrument is calibrated)",
         null_tot["steps"] == 0 and null_tot["holes"] == 0,
         f"stock steps={null_tot['steps']} holes={null_tot['holes']}")

    # (2) the built blocks census clean across every shared border (steps + holes both -> 0)
    recs, tot = FC.census_built_blocks(world_by_block)
    defect_detail = "; ".join(f"{r['border']} steps={r['n_steps']} holes={r['n_holes']}"
                              for r in recs if r["n_steps"] or r["n_holes"]) or "none"
    gate("cross-block seam integrity (the REBUILT carry ring: 0 vertical steps across every shared "
         "border)", tot["steps"] == 0, f"steps={tot['steps']} | {defect_detail}")
    gate("cross-block coincident-edge integrity (the REBUILT carry ring: 0 border HOLES / phase-"
         "shifted notches)", tot["holes"] == 0, f"holes={tot['holes']} | {defect_detail}")

    # (3) no orphan grass shard (topo-0 tile) in the REBUILT blocks (what FIX-G can re-dress); the
    #     full-region count is reported so a stray topo-0 in an un-rebuilt neighbour can't hide.
    rebuilt_world = {blk: world_by_block[blk] for blk in built_bms if blk in world_by_block}
    n_green = FC.green_shard_count(rebuilt_world)
    n_green_region = FC.green_shard_count(world_by_block)
    gate("no orphan grass shard (0 topo-0 tris in the rebuilt carry; the 62 topo-49 mesa murals "
         "are KEPT)", n_green == 0,
         f"topo-0 in rebuilt blocks={n_green} (full mint region incl. un-rebuilt neighbours="
         f"{n_green_region})")

    # (4) THE EYE-PRESERVED gate -- the DIRECT proof (stronger than a distance proxy): the frozen
    #     eye's GATE A (sub-cell boundary conformance) + GATE B (orientation fidelity + byte-
    #     derivation) on the REBUILT carry must equal the STOCK donor's CALIBRATED values byte-for-
    #     byte. The true carry reproduces the donor's dune|desert boundary exactly and the three
    #     fringe fixes live entirely in the flat desert margin / mesa base / amputation stumps, so a
    #     faithful fix leaves every number the eye reads UNCHANGED (0 disturbance, not merely 'still
    #     in-band'). This is what makes GATE A/B/C's PASS meaningful: the fix did not move the tree.
    crit = GE.load_criteria()
    dref = crit["donor"]["boundary_conformance"]
    dsf = crit["donor"]["self_fidelity"]
    ga = eye_verdict["gates"]["A_sub_cell_conformance"][0]
    gb = eye_verdict["gates"]["B_orientation_fidelity"][0]
    a_same = (ga["n"] == dref["n"]
              and abs((ga["off_grid_frac"] or -9) - dref["off_grid_frac"]) < 1e-4
              and abs((ga["mean_offcell"] or -9) - dref["mean_offcell"]) < 1e-4)
    b_same = (gb["n_decodable"] == dsf["n_decodable"]
              and abs((gb["paired_same_ori"] or -9) - dsf["paired_same_ori"]) < 1e-4
              and abs((gb["byte_derivation"] or -9) - dsf["byte_derivation"]) < 1e-4)
    gate("fringe fix is EYE-PRESERVING (rebuilt GATE A + GATE B == the STOCK donor calibration "
         "byte-for-byte -> the fix did not move the dune|desert boundary the eye judges)",
         a_same and b_same,
         f"A rebuilt(n={ga['n']},off={ga['off_grid_frac']},mean={ga['mean_offcell']}) vs "
         f"donor(n={dref['n']},off={dref['off_grid_frac']},mean={round(dref['mean_offcell'],5)}); "
         f"B rebuilt(n={gb['n_decodable']},ori={gb['paired_same_ori']},byte={gb['byte_derivation']}) vs "
         f"donor(n={dsf['n_decodable']},ori={dsf['paired_same_ori']},byte={dsf['byte_derivation']})")

    # informational (not a gate): how far the GEOMETRY-MOVING fixes (FIX-H/FIX-S) sit from the dune
    # footprint the eye judges -- to both the centroid-dominant CORE (GATE A) and the topo-41 set.
    touch = diag.get("fix_touch_xz", [])
    def _min_dist(cells):
        cs = {(c[0] + T[0], c[1] + T[1]) for c in cells}
        m = None
        for (px, pz) in touch:
            d = min((_pt_cell_dist(px, pz, ci, cj) for (ci, cj) in cs), default=1e9)
            if m is None or d < m[0]:
                m = (d, px, pz)
        return m
    d_core = _min_dist(donor["CORE"])
    d_41 = _min_dist(donor["FP41"])
    print(f"  [info] geometry-moving fixes (FIX-H/FIX-S): {len(touch)} distinct XZ; min dist to the "
          f"centroid-dominant dune CORE = {round(d_core[0],2) if d_core else None}u, to the topo-41 "
          f"set = {round(d_41[0],2) if d_41 else None}u. HONEST CORRECTION: these are BELOW the "
          f"forensics' optimistic '>=8.9u' (a differently-measured figure) -- the FIX-H snap at the "
          f"x~1252 HOLE-2 site is ~4u from a topo-41 ecotone cell. The eye is preserved not by "
          f"distance but by the GATE A/B BYTE-IDENTITY above (the binding proof): the dune|desert "
          f"boundary the eye judges is untouched to the decimal.")

    return dict(null=null_tot, built=tot, n_green=n_green, eye_preserved=bool(a_same and b_same),
                min_dist_core=(round(d_core[0], 3) if d_core else None),
                min_dist_topo41=(round(d_41[0], 3) if d_41 else None),
                seam_defects=[r for r in recs if r["n_steps"] or r["n_holes"]])


# ============================================================================================
# STEP 4 -- the frozen eye (GATE A/B/C)
# ============================================================================================
def run_eye(built_bms, donor, render_tag="truecarry"):
    crit = GE.load_criteria()
    cand_tris = []
    for blk, bm in built_bms.items():
        cand_tris += GE._tris_of(bm, blk[0], blk[1])
    cand_fam = GE.cell_family(cand_tris)
    cand_cmap = GE.cells_map(cand_tris)
    cand_fp = GE.dunes_footprint(cand_fam)
    cand_fp41 = GE.topo41_footprint(cand_cmap)
    donor_cmap = donor["scmap"]
    donor_fp41 = donor["FP41"]
    T_eye = GE.translation(donor_fp41, cand_fp41)
    print(f"  eye translation T = {T_eye}  (cand dunes footprint={len(cand_fp)} topo41={len(cand_fp41)})")
    verdict = GE.judge_mesh(cand_tris, cand_cmap, cand_fp, cand_fp41, donor_cmap, donor_fp41,
                            T_eye, crit, cand_fam=cand_fam, label="TRUE CARRY", render=True,
                            render_tag=render_tag)
    gate("THE FROZEN EYE -- GATE A sub-cell conformance", verdict["gates"]["A_sub_cell_conformance"][1],
         f"{verdict['gates']['A_sub_cell_conformance'][0]}")
    gate("THE FROZEN EYE -- GATE B orientation fidelity + byte-derivation",
         verdict["gates"]["B_orientation_fidelity"][1], f"{verdict['gates']['B_orientation_fidelity'][0]}")
    gate("THE FROZEN EYE -- GATE C boundary-framed render organicity",
         verdict["gates"]["C_boundary_render"][1], f"{verdict['gates']['C_boundary_render'][0]}")
    return verdict, cand_tris, cand_fp


# ============================================================================================
# STEP 5 -- grazing A/B render (stock comp[1] beside the true carry)
# ============================================================================================
def render_ab(donor, cand_tris, cand_fp):
    from PIL import Image, ImageDraw
    stock = donor["stock"]
    scfam = donor["scfam"]
    FP = donor["CORE"]
    AZ, _ = GE.best_desert_azimuth(FP, scfam)
    W, H = 960, 600
    paths = []
    for pitch in (22.0, 34.0):
        cam_s, look_s = GE.make_camera(FP, stock, AZ, pitch)
        cam_c, look_c = GE.make_camera(cand_fp, cand_tris, AZ, pitch)
        s_img = GE.render_grazing(stock, cam_s, look_s, 34.0, W, H, shade=False)
        c_img = GE.render_grazing(cand_tris, cam_c, look_c, 34.0, W, H, shade=False)
        pad, lh = 8, 20
        sheet = Image.new("RGB", (W * 2 + pad * 3, H + lh + pad * 2 + 24), (16, 16, 16))
        dr = ImageDraw.Draw(sheet)
        dr.text((pad, 6), f"TRUE MESH CARRY grazing A/B pitch={pitch:.0f} -- LEFT stock comp[1] in situ "
                          f"(smooth/organic) / RIGHT the true carry at (1248,-1184). Painter-sorted, per-corner UV.",
                fill=(255, 230, 140))
        dr.text((pad, 24 + pad), "STOCK comp[1] -- the reference twin", fill=(220, 220, 220))
        dr.text((pad + W + pad, 24 + pad), "TRUE CARRY -- must read as comp[1] relocated", fill=(220, 220, 220))
        sheet.paste(s_img, (pad, 24 + pad + lh))
        sheet.paste(c_img, (pad + W + pad, 24 + pad + lh))
        p = OUTD / f"dunes_true_carry_ab_pitch{int(pitch)}.png"
        sheet.save(p)
        paths.append(str(p))
        print(f"  -> {p}")
    return paths


# ============================================================================================
# STEP 5b -- the FRINGE-FRAMED render (the carry RING, not the dune boundary): PRE deployed vs
# POST rebuilt. The rung-6 A/B frames the dune|desert boundary; the fringe defects live at the
# carry ring (the [19][17]|[19][18] z=-1152 seam + the x=1216/1280 step columns), so this render
# must include the ring. Sky-blue (the render bg) peeking through the terrain = a HOLE; a small
# cliff at a step column = a STEP. Both must be present in PRE (deployed) and gone in POST (rebuilt).
# ============================================================================================
def _fringe_cameras():
    """Two oblique overhead views framed on the carry-ring seams (world coords). View 1 grazes the
    z=-1152 hole seam from the south; view 2 grazes the x=1280 step column from the west."""
    return [
        dict(tag="z1152_holes", look=(1236.0, 3.4, -1156.0),
             cam=(1236.0, 3.4 + 30.0, -1156.0 - 30.0), fov=42.0,
             cap="the [19][17]|[19][18] z=-1152 HOLE seam (the (1220,-1152) sliver) from the south"),
        dict(tag="x_steps", look=(1264.0, 3.35, -1168.0),
             cam=(1264.0 - 34.0, 3.35 + 26.0, -1168.0), fov=42.0,
             cap="the x=1216/1280 STEP columns from the west"),
    ]


def render_fringe(built_bms, *, deployed_tris=None):
    """Render the carry ring PRE (currently-deployed buggy bytes) vs POST (the rebuilt fix). If
    deployed_tris is None it is read from the live mod folder (so this must run BEFORE the deploy).
    Returns the list of saved sheet paths."""
    from PIL import Image, ImageDraw
    if deployed_tris is None:
        deployed_tris = GE.load_mod(GE.MINT_BLOCKS)
    # POST = the full deployed state after the fix: rebuilt bytes for rebuilt blocks + the unchanged
    # deployed bytes for every other mint block (so the render shows complete terrain, not just the
    # rebuilt subset -- otherwise the un-rebuilt neighbours read as a false 'hole').
    rebuilt = set(built_bms)
    built_tris = []
    for blk in built_bms:
        built_tris += GE._tris_of(built_bms[blk], blk[0], blk[1])
    for (p3, uv3, n3, topo, fam) in deployed_tris:
        cx = sum(pp[0] for pp in p3) / 3.0
        cz = sum(pp[2] for pp in p3) / 3.0
        if (math.floor(cx / BLOCK), math.floor(-cz / BLOCK)) not in rebuilt:
            built_tris.append((p3, uv3, n3, topo, fam))
    W, H = 900, 560
    paths = []
    for view in _fringe_cameras():
        cam, look, fov = view["cam"], view["look"], view["fov"]
        pre = GE.render_grazing(deployed_tris, cam, look, fov, W, H, shade=True)
        post = GE.render_grazing(built_tris, cam, look, fov, W, H, shade=True)
        pad, lh = 8, 20
        sheet = Image.new("RGB", (W * 2 + pad * 3, H + lh + pad * 2 + 24), (16, 16, 16))
        dr = ImageDraw.Draw(sheet)
        dr.text((pad, 6), f"FRINGE-FRAMED carry-ring render -- {view['cap']}. "
                          f"LEFT deployed (fringe defects) / RIGHT rebuilt fix. Sky-blue through the "
                          f"terrain = a HOLE.", fill=(255, 230, 140))
        dr.text((pad, 24 + pad), "PRE -- currently deployed (blue slivers / steps)", fill=(220, 220, 220))
        dr.text((pad + W + pad, 24 + pad), "POST -- the rebuilt fringe fix (seams closed)", fill=(220, 220, 220))
        sheet.paste(pre, (pad, 24 + pad + lh))
        sheet.paste(post, (pad + W + pad, 24 + pad + lh))
        p = OUTD / f"dunes_fringe_frame_{view['tag']}.png"
        sheet.save(p)
        paths.append(str(p))
        print(f"  -> {p}")
    return paths


# ============================================================================================
# STEP 6 -- what the carry brings that the stamp lacked (measured)
# ============================================================================================
def measure_vs_stamp(donor, built_bms, T):
    scmap = donor["scmap"]
    # butte relief carried
    b59 = [p[1] for (p3, uv3, n3, topo, fam) in donor["stock"] if topo == 59 for p in p3]
    butte = dict(cells=sum(1 for c in scmap if any(t == 59 for (t, _w, _u) in scmap[c])),
                 y_lo=round(min(b59), 2), y_hi=round(max(b59), 2), y_med=round(sorted(b59)[len(b59) // 2], 2)) if b59 else {}
    # crest tiles present? (a proxy: distinct topo-41 UV rows in the carried footprint)
    carried_uv = set()
    for bm in built_bms.values():
        for j in range(bm.vcount):
            topo = X.decode_id(int(round(bm.tangents[j][0])))["topograph"]
            if topo == 41:
                carried_uv.add((round(bm.uvs[j][0], 5), round(bm.uvs[j][1], 5)))
    return dict(butte=butte, distinct_dune_uv=len(carried_uv))


# ============================================================================================
# STEP 7 -- deploy (guarded) + Disc4 mirror
# ============================================================================================
def deploy(built_bms):
    game_root = Path(_cfg.find_game_path(None))
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # back up BOTH discs' Terrain files for every block we touch BEFORE any write / the Disc4 mirror
    # (auto_mirror byte-copies Disc1 -> Disc4, overwriting them) -- MOD-OVERWRITE is lawful here
    # (the target cells carry OUR OWN prior label-stamp mint), but the base game is the source of truth.
    n_bk = 0
    for blk in sorted(built_bms):
        bx, by = blk
        for disc in (1, 4):
            rel = M.override_relpath(disc, bx, by, part="Terrain")
            p = game_root / MOD / rel
            if p.exists():
                dst = BACKUP_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                n_bk += 1
    print(f"  backed up {n_bk} Terrain files (both discs) -> {BACKUP_DIR}")
    written = []
    for blk, bm in sorted(built_bms.items()):
        written.append(M.deploy_override(bm, mod_folder=MOD, part="Terrain"))
    DM.auto_mirror(written, mod_folder=MOD)
    return written


# ============================================================================================
# BUILD + GATE (the reusable pipeline -- dunes_fringe_fix.py imports this, main() wraps it)
# ============================================================================================
def build_and_gate(*, render=True):
    """Rebuild the carry from the stock donor onto the current DEPLOYED host, run the full gate
    suite + the frozen eye + the rung-7 fringe gates (+ optional renders), and return everything.
    Writes NOTHING to the game. Returns a dict incl. built_bms + n_fail (0 => deploy-safe). GATES
    is reset at entry so re-invocation is clean."""
    GATES.clear()
    print("=== dunes_true_carry.build_and_gate -- THE TRUE MESH CARRY + rung-7 fringe fixes ===\n")
    donor = load_donor()
    print(f"donor: CORE(dunes)={len(donor['CORE'])} HOLE={len(donor['HOLE'])} BLOB={len(donor['BLOB'])} "
          f"topo41={len(donor['FP41'])}")

    print("loading deployed mint footprint for T ...", flush=True)
    mint = GE.load_mod(MINT_BLOCKS)
    MFP41 = GE.topo41_footprint(GE.cells_map(mint))
    T = GE.translation(donor["FP41"], MFP41)
    print(f"placement T (donor->deployed) = {T}")

    R = define_region(donor)
    print(f"R_donor = {len(R)} cells (BLOB {len(donor['BLOB'])} + carried margin/butte {len(R) - len(donor['BLOB'])})")

    placed_R_blocks = sorted({cell_block((c[0] + T[0], c[1] + T[1])) for c in R})
    game_root = Path(_cfg.find_game_path(None))
    host_bms = {}
    land_ys = []
    for blk in MINT_BLOCKS:
        bx, by = blk
        p = game_root / MOD / M.override_relpath(1, bx, by, part="Terrain")
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        soup = bm_world_soup(bm, bx, by)
        host_bms[blk] = dict(bm=bm, soup=soup)
        land_ys += [v[0][1] for tri in soup for v in tri
                    if X.decode_id(int(round(v[3][0])))["topograph"] in (17,)]
    land_height = float(np.median(land_ys)) if land_ys else 3.2
    miss_host = [b for b in placed_R_blocks if b not in host_bms]
    print(f"deployed host: {len(host_bms)} MINT blocks loaded, flat desert Y median = {land_height:.3f}"
          + (f"  WARN: placed_R blocks missing a host override: {miss_host}" if miss_host else ""))

    built_soups, placed_R, diag = carry(donor, R, T, host_bms, land_height)
    print(f"carry diagnostics: {json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in diag.items()}, default=str)}")
    built_bms = {blk: soup_to_bm(soup, blk[0], blk[1]) for blk, soup in built_soups.items()}

    print("\n--- gates: FLAT/grid/weld/frame/MISS ---")
    escaped = sorted(b for b in built_bms if b not in host_bms)
    gate("carry stays within the deployed mint footprint (no built block outside the loaded host "
         "region)", not escaped, f"escaped={escaped}")
    gate_info = run_gates(built_bms, placed_R, donor, T, land_height)

    print("\n--- the frozen eye (GATE A/B/C) ---")
    verdict, cand_tris, cand_fp = run_eye(built_bms, donor)

    print("\n--- rung-7 FRINGE gates (cross-block seam NULL + steps + holes + orphan-grass + eye-preserved) ---")
    fringe_info = run_fringe_gates(built_bms, donor, T, diag, verdict)

    renders = fringe_renders = []
    if render:
        print("\n--- grazing A/B render (stock vs true carry) ---")
        renders = render_ab(donor, cand_tris, cand_fp)
        print("\n--- FRINGE-FRAMED carry-ring render (PRE deployed vs POST rebuilt) ---")
        fringe_renders = render_fringe(built_bms, deployed_tris=mint)

    vs_stamp = measure_vs_stamp(donor, built_bms, T)
    print(f"\ncarry brings (vs the flat stamp): butte {vs_stamp['butte']}  distinct dune UVs {vs_stamp['distinct_dune_uv']}")

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates, {n_fail} FAILED ===")

    out = dict(
        mod_folder=MOD, site=[1248.0, -1184.0], T=list(T), R_cells=len(R),
        margin_rings=MARGIN_RINGS, land_height=land_height, DY=diag["DY"],
        touched_blocks=[list(b) for b in sorted(built_bms)],
        carry_diag={k: v for k, v in diag.items() if k != "touched_blocks"},
        gate_info=gate_info, vs_stamp=vs_stamp, fringe_info=fringe_info,
        eye=dict(passed=verdict["passed"], gates={g: [str(v), p] for g, (v, p) in verdict["gates"].items()}),
        n_gates=len(GATES), n_failed=n_fail,
        gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES],
        renders=renders, fringe_renders=fringe_renders,
    )
    return dict(built_bms=built_bms, n_fail=n_fail, out=out, diag=diag, verdict=verdict,
                fringe_info=fringe_info)


# ============================================================================================
# main
# ============================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    res = build_and_gate()
    built_bms, n_fail, out = res["built_bms"], res["n_fail"], res["out"]

    deployed = False
    if args.deploy:
        if n_fail:
            sys.exit(f"REFUSING --deploy: {n_fail} gate(s) failed")
        print("\n--- DEPLOY (both discs via auto-mirror) ---")
        written = deploy(built_bms)
        print(f"deployed {len(written)} Disc1 Terrain files (+ Disc4 mirror); blocks {sorted(built_bms)}")
        deployed = True
    out["deployed"] = deployed

    (OUTD / "dunes_true_carry.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_true_carry.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
