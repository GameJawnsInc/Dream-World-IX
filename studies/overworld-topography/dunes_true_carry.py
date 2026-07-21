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
from ff9mapkit.world import island as I                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import placement as P                    # noqa: E402
from ff9mapkit.world import transplant as TR                  # noqa: E402
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402

import dunes_grazing_eye as GE                                # noqa: E402  (frozen eye + loaders + judge)

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
    the HOST at the carry boundary (kept-host weld-ring verts SNAP to the carried donor verts)."""
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

    # 1) translate every carried donor tri to host WORLD coords (whole-cell xz + uniform DY) ------
    Tw_x, Tw_z = CELL * Tx, CELL * Tz
    carried_world = []
    for c in R:
        for tri in by_cell.get(c, []):
            carried_world.append([((v[0][0] + Tw_x, v[0][1] + DY, v[0][2] + Tw_z), v[1], v[2], v[3])
                                  for v in tri])

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

    # 4) assemble each touched block: kept host tris (dropped placed_R cells) + carried donor tris -
    out = {}
    conform_snaps = 0
    touched = sorted(set(carried_by_block) | {cell_block(c) for c in placed_R})
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
                    p = (tgt[0], tgt[1], tgt[2]); conform_snaps += 1
                nt.append((p, n, u, t))
            new_kept.append(nt)
        out[blk] = new_kept + carried_by_block.get(blk, [])
    diag = dict(placed_R=len(placed_R), weld_cells=len(weld_cells), DY=DY,
                donor_weld_med=donor_weld_med, n_bcorners=len(bcorners),
                n_carried_boundary=len(carried_boundary), boundary_spread=boundary_spread,
                max_poke=max_poke, dropped_area2=dropped_area2, conform_snaps=conform_snaps,
                touched_blocks=touched)
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
# main
# ============================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    print("=== dunes_true_carry.py -- THE TRUE MESH CARRY (comp[1] relocated onto the r56 host) ===\n")
    donor = load_donor()
    print(f"donor: CORE(dunes)={len(donor['CORE'])} HOLE={len(donor['HOLE'])} BLOB={len(donor['BLOB'])} "
          f"topo41={len(donor['FP41'])}")

    # placement T from the DEPLOYED mint (so the carry lands exactly on the label-stamp cells)
    print("loading deployed mint footprint for T ...", flush=True)
    mint = GE.load_mod(MINT_BLOCKS)
    mcmap = GE.cells_map(mint)
    MFP41 = GE.topo41_footprint(mcmap)
    T = GE.translation(donor["FP41"], MFP41)
    print(f"placement T (donor->deployed) = {T}")

    R = define_region(donor)
    print(f"R_donor = {len(R)} cells (BLOB {len(donor['BLOB'])} + carried margin/butte {len(R) - len(donor['BLOB'])})")

    # load the DEPLOYED host blocks. Load the WHOLE deployed mint region (all MINT_BLOCKS that have
    # a Terrain override) so a re-partition sliver can never land in an unloaded block and lose the
    # host desert around it; the carry only touches a subset and only touched blocks re-deploy.
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

    print("\n--- grazing A/B render (stock vs true carry) ---")
    renders = render_ab(donor, cand_tris, cand_fp)

    vs_stamp = measure_vs_stamp(donor, built_bms, T)
    print(f"\ncarry brings (vs the flat stamp): butte {vs_stamp['butte']}  distinct dune UVs {vs_stamp['distinct_dune_uv']}")

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates, {n_fail} FAILED ===")

    deployed = False
    if args.deploy:
        if n_fail:
            sys.exit(f"REFUSING --deploy: {n_fail} gate(s) failed")
        print("\n--- DEPLOY (both discs via auto-mirror) ---")
        written = deploy(built_bms)
        print(f"deployed {len(written)} Disc1 Terrain files (+ Disc4 mirror); blocks {sorted(built_bms)}")
        deployed = True

    out = dict(
        mod_folder=MOD, site=[1248.0, -1184.0], T=list(T), R_cells=len(R),
        margin_rings=MARGIN_RINGS, land_height=land_height, DY=diag["DY"],
        touched_blocks=[list(b) for b in sorted(built_bms)],
        carry_diag={k: v for k, v in diag.items() if k != "touched_blocks"},
        gate_info=gate_info, vs_stamp=vs_stamp,
        eye=dict(passed=verdict["passed"], gates={g: [str(v), p] for g, (v, p) in verdict["gates"].items()}),
        n_gates=len(GATES), n_failed=n_fail, deployed=deployed,
        gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES],
        renders=renders,
    )
    (OUTD / "dunes_true_carry.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_true_carry.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
