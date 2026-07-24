"""RUNG F LAYOUT -- THE MIXED-BIOME BUILD (2026-07-24), the composition half.

THE CONCEPT (fixed by THE APPROVED DESIGN, out/rung_f/design_round1.json):
  A large minted FLAT-GRASS 4x4 island at site (0,16) + THE TRUE MESH CARRY (byte-rigid) of stock's
  ONE grass|desert junction ensemble (blocks 13-15,11-12, cells x[212,251] y[-210,-177]) -- BOTH skin
  lobes + the internal rock band + the 143-cell dunes backing -- translated rigid by (-201,-94) cells
  = (-804,-376)u, rot 0, EW/NS-centered in the site so every carried ecotone feature stands >= ~50u
  realized from every coast (THE ALL-COASTS LAW). R2/R3 pass BY CONSTRUCTION (the carry deploys stock's
  own 6-block core bytes, so saturation/arrangement/backing are stock's identical ratios); R1 clears
  every floor with the EW straddle standoff (~50u) the tight axis to measure on the staged build.

WHY THE FULL ENSEMBLE (design F1): a west-dunes-backed-core-only cut FAILS R2 arrangement (stock's
  0.8022 fringe is carried by the shallow EAST skin lobe) -- so BOTH lobes deploy.

THE CARRY MECHANISM -- THE TRUE MESH CARRY, adapted from dunes_true_carry.py (proven in-game 2026-07-
  21/22) for a MINTED grass host instead of a deployed one, and STRIPPED of every dunes-specific
  redress (dunes_true_carry re-dresses topo-0 grass -> desert, which would DESTROY our minted grass +
  carried grass fringe -- so it is NOT reused; only the generic rigid-shift / re-partition / conform-
  weld machinery is, re-implemented here so the redress can never fire):
    * the donor Terrain tris are copied VERBATIM (pos/nrm/uv/tangent) and translated by a WHOLE-CELL
      xz shift (preserves every fractional-in-cell coord -> the per-corner UV decode is byte-identical)
      + a uniform DY that seats the ensemble's lowland floor at the host's flat land_height;
    * THE DONOR-DISPATCH STRIP: each carried IDALL is re-encoded event=0/area=0, KEEPING topo+flags
      (the carried place-entrance dispatch on all 6 core blocks -- S1 -- must not survive a bytes-only
      carry); Object/building + water parts are DROPPED (carry Terrain only);
    * the shift (-804,-376)u is NOT a block multiple (block=64u), so the host block partition is
      PHASE-SHIFTED -- every carried tri is RE-PARTITIONED at the host 64u block borders (transplant.
      clip_poly / _split_at_borders law: an interior tri passes byte-identical, a straddler keeps its
      inside part exactly, pos/nrm/uv lerped on the cut, tangent/IDALL verbatim, bit-identical cut t
      on both sides -> watertight);
    * THE WELD: the minted grass frame is a DENSE 4u lattice (island.build_landmass GRID=4), so the
      carried 4u cells align on-grid; grass cells under the carried footprint are removed and every
      kept-grass boundary-corner vert is SNAPPED to the coincident carried boundary vert (the conform
      weld -- deformation goes to the GRASS frame, the carried ensemble stays RIGID, the massif-carry
      apron law). The ensemble is LOWLAND (heights 1.37-11.87u, p50 3u; design_probe), so the aprons
      are shallow and every seam welds crack-free.

READ-ONLY vs the game install. This module composes IN MEMORY only. rung_f_build.py runs the gate
stack, stages the file set under out/rung_f/FF9CustomMap-world/, and renders. NO --apply here.

Run:  py studies/overworld-topography/rung_f_build.py   (this module is imported, not run directly)
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                        # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import island as ISL                   # noqa: E402
from ff9mapkit.world import mesh as M                        # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402

BLOCK = 64.0
CELL = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
MOD = "FF9CustomMap-world"

# ============================================================================================
# SITE + FRAME (THE APPROVED DESIGN)
# ============================================================================================
SITE_ANCHOR = (0, 16)                     # cols 0-3, rows 16-19 (world x[0,256], z[-1280,-1024])
SITE_W_BLOCKS = 4
SITE_H_BLOCKS = 4
SITE_BLOCKS = frozenset((bx, by) for bx in range(0, 4) for by in range(16, 20))

ISLAND_CENTER = (128.0, -1152.0)          # centre of the 4x4 rect
# radius 118 keeps the wobbled coast inside x[~1,255] z[~-1025,-1279] -- WITHIN blocks 0-3/16-19
# (never reaches block 4/x>=256 or row 15/z>-1024, both stock-land margins); re-asserted in stage0.
ISLAND_RADIUS = 112.0
LAND_HEIGHT = 3.0                         # the carried ecotone floor is lowland p50 3.04u -> flat weld
ISLAND_SEED = 1607.0                      # deterministic
ISLAND_UNDULATION = 0.12                  # inside the measured FF9 coast language (med_turn 8-35 deg)
ISLAND_N_CORNERS = 4
ISLAND_CORNER_STRENGTH = 0.22

# ============================================================================================
# THE CARRY WINDOW (donor) + transform
# ============================================================================================
# BUILD CORRECTION to THE APPROVED DESIGN (round 1 measurement): the design's window x[212,251]
# y[-210,-177] (a) includes 2 extra by=13 rows -> +20 desert-body tris -> R2 saturation 0.5204 >
# stock 0.5024, and (b) cuts straight through the valley's mountain ring (90/140 boundary cells are
# 12-40u tall rock -> no lowland weld boundary). BOTH are closed by carrying stock's OWN 6-block core
# EXACTLY -- blocks 13-15,11-12 = cell rect x[208,255] y[-208,-177]. That is the very region the
# contract itself measures (core_blocks=ECOTONE_CORE), so R2/R3 reproduce stock's 422/0.5024/0.6351 +
# 143/125/129 BY CONSTRUCTION (identical cells). The mountain ring is carried too (THE VALLEY CARRY --
# the massif precedent): its walls become interior hills, the grass frame ramps UP to the carried
# outer boundary (the apron law -- deformation to the grass, the carry stays rigid).
DONOR_CELL_X = (208, 255)
DONOR_CELL_Y = (-208, -177)
DONOR_BLOCKS = [(bx, by) for bx in range(12, 17) for by in range(10, 14)]   # 13-15,11-12 + read margin
# shift the 6-block core centre (world (928,-768)) to the island centre (128,-1152): (-800,-384)u =
# (-200,-96) cells (integer cells -> clean-weld / lattice-edge law), rot 0. Ecotone lands EW/NS-centered.
SHIFT_CELLS = (-200, -96)
SHIFT_WORLD = (CELL * SHIFT_CELLS[0], CELL * SHIFT_CELLS[1])
FIXH_TAU = 2.6                            # pre-quantize a carried vert this close to a block border ONTO
#                                          it (BEFORE re-partition) so border corners weld both sides
#                                          in-frame -- the phase-shifted-notch fix (dunes_true_carry).
# THE LOWLAND-WELD CAP (round-1 finding): the ecotone is a MOUNTAIN-LOCKED valley (S1) -- the 6-block
# core's own outer boundary is 12-40u rock wall, so a full-valley carry has no lowland weld boundary
# and the grass must ramp ~37u up to a cliff (max_lift 36.8u -> steep aprons, non-watertight seam). The
# ecotone floor itself is LOWLAND (design: heights 1.37-11.87u). Dropping donor cells whose max height
# exceeds this cap (the tall mountain-ring walls) leaves the lowland ecotone (skin+dunes+low rock) with
# a LOWLAND boundary that welds to grass with a gentle apron; the dropped wall cells are filled by the
# grass frame. R2/R3 are re-measured after the drop (they must still reproduce stock -- verified in the
# build). None (0 or a huge cap) = the full valley carry. ROUND-1 FINDING: dropping cells EXPOSES the
# carried mesh's interior conform edges (a dropped cell's tris vanish -> its neighbour's shared conform
# edge goes single-owner), un-weldable to the on-grid grass -> 177 interior open edges. The full no-drop
# carry keeps stock's own watertight interior (0 interior once-edges); only the outer-boundary +
# block-border seams need welding. HEIGHT_CAP=0 (no drop) is the cleaner topology despite the tall
# mountain-wall boundary (grass aprons UP to it, 2-owner = watertight, just steep -> an eye concern).
HEIGHT_CAP = 0.0

# THE SEAM COLLAR (the robust weld, replacing dunes_true_carry's conform-snap for a MINTED host): the
# carried region's OUTER boundary CORNERS are snapped to the exact 4u grid at LAND_HEIGHT, coinciding
# bit-for-bit with the minted grass frame's own lattice verts there -> the seam is a clean flat on-grid
# ring, guaranteed watertight (no poke, no crack, no T-junction), a gentle apron into the lowland
# interior. The ecotone INTERIOR (every carried tri NOT touching a boundary corner) stays byte-rigid.
# TOL admits a conform offset up to this magnitude at a boundary corner.
SEAM_SNAP_TOL = 2.6
# seat the ensemble so its low 15th-percentile height sits at LAND_HEIGHT (keeps the lowland floor near
# grass level, the low dunes just above sea; the boundary ring flattens to LAND_HEIGHT regardless).
SEAT_PCTL = 15.0

# THE SEAM STITCH tuning (rung_f_stitch, build-fix round 1) -----------------------------------------
# WELD_REACH: a grass hole-rim vert this far (XZ) from the conform mesh boundary dC is snapped ONTO it.
# The grass hole is cut by CELL membership, so the rim sits <= the conform offset (~2u) off dC; 4.6u
# (just over one cell) catches exactly the immediate rim ring and leaves the interior grass untouched.
SEAM_WELD_REACH = 4.6
# TOL_XZ: a vertex within this XZ distance of an edge (and colinear) is a T-vertex on it -> split.
SEAM_TOL_XZ = 0.05
# YTOL: after the weld the grass rim lies on dC, so a T-vertex's Y matches the edge's lerped Y closely;
# a generous band admits the small chord-vs-curve gap where dC bends between two welded rim verts.
SEAM_YTOL = 0.75


def log(m):
    print(m, flush=True)


# ============================================================================================
# generic cell / soup helpers (adapted from dunes_true_carry.py -- the SAFE generic subset only;
# NONE of its dunes-specific redress is imported or reused)
# ============================================================================================
def in_window(cell):
    return (DONOR_CELL_X[0] <= cell[0] <= DONOR_CELL_X[1]
            and DONOR_CELL_Y[0] <= cell[1] <= DONOR_CELL_Y[1])


def tri_cell(tri):
    cx = sum(v[0][0] for v in tri) / 3.0
    cz = sum(v[0][2] for v in tri) / 3.0
    return (math.floor(cx / CELL), math.floor(cz / CELL))


def boundary_of(cellset):
    return {c for c in cellset if any((c[0] + di, c[1] + dj) not in cellset for di, dj in NEI4)}


def boundary_corners(placed_R):
    """grid corners (gi,gj) incident to at least one placed_R cell AND at least one non-R cell."""
    pr = set(placed_R)
    out = set()
    for (ci, cj) in pr:
        for (gi, gj) in ((ci, cj), (ci + 1, cj), (ci, cj + 1), (ci + 1, cj + 1)):
            incident = {(gi - 1, gj - 1), (gi - 1, gj), (gi, gj - 1), (gi, gj)}
            if any(ic not in pr for ic in incident):
                out.add((gi, gj))
    return out


def cell_block(c):
    wx = CELL * c[0] + CELL / 2.0
    wz = CELL * c[1] + CELL / 2.0
    return (int(math.floor(wx / BLOCK)), int(math.floor(-wz / BLOCK)))


def bm_world_soup(bm, bx, by):
    """A BlockMesh -> list of world-coord tris, each [(pos,nrm,uv,tan) x3]."""
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
    """A list of WORLD-coord tris -> a flat/unindexed Terrain BlockMesh in the block LOCAL frame
    (verts==idx, THE FLAT-MESH invariant)."""
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


def strip_event_area(idall_float):
    """THE DONOR-DISPATCH STRIP: re-encode an IDALL with event=0/area=0, KEEPING topo+flags."""
    d = X.decode_id(int(round(idall_float)))
    return float(X.encode_id(0, 0, d["topograph"], d["flags"]))


# ============================================================================================
# STAGE 1 -- mint the flat grass frame
# ============================================================================================
def mint_grass_frame(game_root):
    built = ISL.build_landmass(center=ISLAND_CENTER, base_radius=ISLAND_RADIUS, seed=ISLAND_SEED,
                               lobes=1, land_height=LAND_HEIGHT, ground="grass", relief_amp=0.0,
                               undulation=ISLAND_UNDULATION, n_corners=ISLAND_N_CORNERS,
                               corner_strength=ISLAND_CORNER_STRENGTH, n_patches=0,
                               disc=1, game=game_root)
    return built


# ============================================================================================
# STAGE 2 -- load the donor window (byte-rigid capture)
# ============================================================================================
def load_donor_window(game_root):
    """Read the donor Terrain world tris over the window cell rect. Returns:
      by_cell : {cell: [donor_world_tri, ...]} for every window cell (rigid-carry input)
      raw_tris: the flat list of donor window tris (byte-rigidity baseline, pre-transform)
    """
    raw_by_cell = defaultdict(list)
    for (bx, by) in DONOR_BLOCKS:
        for tri in TR.world_tris(bx, by, "terrain", disc=1, game=game_root):
            c = tri_cell(tri)
            if in_window(c):
                raw_by_cell[c].append(tri)
    # THE LOWLAND-WELD CAP: drop cells whose max vertex height exceeds HEIGHT_CAP (the tall mountain-
    # ring walls) so the carry keeps the lowland ecotone with a lowland weld boundary; the grass frame
    # fills the dropped cells.
    by_cell = {}
    dropped = []
    for c, tris in raw_by_cell.items():
        cmax = max(v[0][1] for tri in tris for v in tri)
        if HEIGHT_CAP and cmax > HEIGHT_CAP:
            dropped.append(c)
            continue
        by_cell[c] = tris
    raw = [(c, tri) for c, tris in by_cell.items() for tri in tris]
    return dict(by_cell=by_cell, raw=raw, n_dropped_tall=len(dropped),
                n_cells_kept=len(by_cell), n_cells_raw=len(raw_by_cell))


# ============================================================================================
# STAGE 3 -- THE CARRY: donor rigid (whole-cell shift + DY + event/area strip + re-partition),
# host grass conforms.
# ============================================================================================
def carry(donor, host_bms, land_height):
    """Translate the donor window rigid into the host frame, re-partition at host 64u borders, remove
    grass under the carried footprint, weld kept-grass boundary verts to the carried verts.

    Returns (out_soup_by_block, placed_R, carried_translated_by_cell, diag) where
      out_soup_by_block  : {block: world_soup} for every touched block (composite terrain)
      placed_R           : the set of TARGET cells the carry occupies
      carried_translated : {cell: [translated (pre-clip) donor tris]} -- byte-rigidity baseline
      diag               : diagnostics dict
    """
    by_cell = donor["by_cell"]
    R = set(by_cell.keys())                                 # every window cell that carries a tri
    Tx, Tz = SHIFT_CELLS
    placed_R = {(c[0] + Tx, c[1] + Tz) for c in R}
    bcorners = boundary_corners(placed_R)                   # world grid corners on the carry seam

    # DY: seat the ensemble's DESERT-FAMILY floor (the ecotone) at land_height so the walkable ecotone
    # sits level with the grass. The mountain-ring rock rises above (carried rigid); the grass frame
    # ramps UP to the carried outer boundary (the apron law). Desert-family = topo {16,17,19,20,41}.
    des_ys = []
    all_ys = []
    for tris in by_cell.values():
        for tri in tris:
            y = sum(v[0][1] for v in tri) / 3.0
            all_ys.append(y)
            topo = X.decode_id(int(round(tri[0][3][0])))["topograph"]
            if topo in (16, 17, 19, 20, 41):
                des_ys.append(y)
    ens_seat = float(np.median(des_ys)) if des_ys else float(np.median(all_ys))
    DY = land_height - ens_seat
    log(f"  DY = land_height({land_height:.3f}) - ecotone_floor_median({ens_seat:.3f}) = {DY:+.4f}  "
        f"(ensemble y range {min(all_ys):.2f}..{max(all_ys):.2f})")

    # 1) translate every carried donor tri to host WORLD coords (whole-cell xz + uniform DY), STRIP
    #    event/area (topo+flags kept). FIX-H: a carried vert within FIXH_TAU of a host block border is
    #    pre-quantized ONTO the border (deterministic per world position -> every soup copy snaps
    #    identically, welds preserved), so a border-corner vert clips identically on both sides and its
    #    grass weld lands in-frame (the phase-shift notch fix).
    Tw_x, Tw_z = SHIFT_WORLD
    carried_translated = defaultdict(list)                  # target cell -> translated pre-clip tris
    carried_world = []
    n_fixh = 0
    for c in R:
        tc = (c[0] + Tx, c[1] + Tz)
        for tri in by_cell[c]:
            new = []
            for (p, n, u, tg) in tri:
                nid = strip_event_area(tg[0])
                px, py, pz = p[0] + Tw_x, p[1] + DY, p[2] + Tw_z
                nx = round(px / BLOCK) * BLOCK
                nz = round(pz / BLOCK) * BLOCK
                npx = nx if 1e-4 < abs(px - nx) < FIXH_TAU else px
                npz = nz if 1e-4 < abs(pz - nz) < FIXH_TAU else pz
                if npx != px or npz != pz:
                    n_fixh += 1
                new.append(((npx, py, npz), n, u, (nid,) + tuple(tg[1:])))
            carried_translated[tc].append(new)
            carried_world.append(new)

    # 2) RE-PARTITION at the host 64u borders (transplant clip_poly). An interior tri passes whole;
    #    a straddler keeps its inside part exactly. Degenerate slivers drop.
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

    # 3+4) THE SEAM STITCH (rung_f_stitch, build-fix round 1) -- replaces the round-1 grid-corner snap
    #      (which left 243 once-edges because a coarse grass lattice cannot weld a fine-conform donor
    #      boundary: an 8u carried edge x=56->64 has no vertex at the grass's x=60 corner -> a
    #      T-junction). THE APRON WELD pulls every grass hole-rim vert onto the true conform mesh
    #      boundary dC (deformation to the grass, the carry stays RIGID), then THE T-JUNCTION
    #      ELIMINATION splits every seam edge at the interior vertex on it -> watertight. Carried
    #      pure-interior tris are untouched (only boundary-ring carried edges carrying a T-vertex split).
    import rung_f_stitch as STITCH
    out, sdiag = STITCH.stitch(carried_by_block, host_bms, placed_R, land_height,
                               weld_reach=SEAM_WELD_REACH, tol_xz=SEAM_TOL_XZ, ytol=SEAM_YTOL, log=log)

    diag = dict(n_R_cells=len(R), n_placed_R=len(placed_R), DY=round(DY, 5), ecotone_floor_y=round(ens_seat, 4),
                ensemble_y_min=round(min(all_ys), 3), ensemble_y_max=round(max(all_ys), 3),
                n_bcorners=len(bcorners), n_fixh=n_fixh, max_poke=round(max_poke, 5),
                dropped_area2=round(dropped_area2, 6),
                grass_snaps=sdiag["n_weld"], n_lifted=sdiag["n_weld"], max_lift=sdiag["max_lift"],
                seam_splits=sdiag["n_split"], seam_iters=sdiag["tj_iters"], apron_flips=sdiag["n_flip"],
                stitch=sdiag, touched_blocks=[list(b) for b in sorted(out)])
    return out, placed_R, dict(carried_translated), diag


# ============================================================================================
# compose: the full in-memory build (frame + carry). Returns everything the gate stack needs.
# ============================================================================================
def compose(game_root):
    log("=" * 96)
    log("RUNG F COMPOSE -- mint grass frame + THE TRUE MESH CARRY of the 6-block junction ensemble")
    log("=" * 96)
    built = mint_grass_frame(game_root)
    frame_blocks = dict(built["blocks"])
    log(f"  grass frame: {len(frame_blocks)} land blocks {sorted(frame_blocks)}")

    host_bms = {blk: bm_world_soup(bm, blk[0], blk[1]) for blk, bm in frame_blocks.items()}

    donor = load_donor_window(game_root)
    log(f"  donor window: {len(donor['by_cell'])} cells, {len(donor['raw'])} tris "
        f"(rect x{DONOR_CELL_X} y{DONOR_CELL_Y})")

    out_soup, placed_R, carried_translated, diag = carry(donor, host_bms, LAND_HEIGHT)
    log(f"  carry: placed_R={len(placed_R)} cells, touched {len(out_soup)} blocks; "
        f"fixh={diag['n_fixh']} grass_snaps={diag['grass_snaps']} max_lift={diag['max_lift']} "
        f"max_poke={diag['max_poke']} dropped_area2={diag['dropped_area2']}")

    # final composite Terrain blocks: every touched block from the carry, PLUS every untouched frame
    # block (kept verbatim -- the coast/interior grass the carry never reached).
    final_blocks = {}
    for blk, bm in frame_blocks.items():
        final_blocks[blk] = bm
    for blk, soup in out_soup.items():
        final_blocks[blk] = soup_to_bm(soup, blk[0], blk[1])
    log(f"  composite: {len(final_blocks)} Terrain blocks")

    return dict(built=built, frame_blocks=frame_blocks, host_bms=host_bms, donor=donor,
                out_soup=out_soup, placed_R=placed_R, carried_translated=carried_translated,
                diag=diag, final_blocks=final_blocks)


if __name__ == "__main__":
    gr = Path(_cfg.find_game_path(None))
    c = compose(gr)
    log(f"\ncompose OK: {len(c['final_blocks'])} blocks, placed_R={len(c['placed_R'])}")
