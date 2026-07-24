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
# SITE + FRAME (THE APPROVED DESIGN -- design2_round3.json PRIMARY, VERBATIM CORE + MINTED CONTEXT)
# ============================================================================================
# BUILD CORRECTION to design2_round3's PRIMARY (167.8,-1127.3): stage0's OPEN-OCEAN gate + the ground-
# truth non-wrapping open-ocean scan (rung_f_ocean_scan2) REFUTED that centre -- its r132 disc reaches
# block (4,15) (stock terrain) / (3,15) (coastal sea overrides). The largest NON-WRAPPING TRUE-OCEAN
# circle in the world is Rmax=132 @ centre (144,-1144), block (2,17) -- the corrected primary. R=132
# exactly (zero site margin, rim pulled to 131u -> covered cells clear). undulation 0.02 (<=0.05, the
# design's own allowance) + seed 42: build_landmass BUILDS + verifies CLEAN at r132 (undulation 0 alone
# hit the Delaunay ring-recovery degeneracy -- the r132 scale risk; a 0.02 wobble breaks it, R1-safe).
SITE_BLOCKS = frozenset((bx, by) for bx in range(0, 5) for by in range(15, 20))

ISLAND_CENTER = (160.0, -1152.0)          # REBUILD ATTEMPT 2: centre the island on the BLOB centre
#   (world [64,256]x[-1216,-1088] mid = (160,-1152)), NOT on the ecotone MEC (167.8,-1151.3). The blob
#   is 192x128u; centring on the ecotone put the blob's WEST corners at 122u (past the R=125 coast once
#   the grass rim is dilated -> the grass hole opened to the coast, one merged loop -> the tiling had no
#   clean rim). Blob-centred, all 4 corners sit at ~115u (symmetric) -> the dilated grass rim (~119u) is
#   >=6u inside the coast everywhere -> a CLEAN annulus. The ecotone (MEC at 167.8, 7.8u east of centre)
#   still clears the R1 floor on BOTH sides (guide standoff ~47u east / ~63u west, both > 44.635).
#   Verified open-ocean: R=125 @ (160,-1152) covers EXACTLY the 20 site blocks (0-4,16-19), all clear.
ISLAND_RADIUS = 125.0
LAND_HEIGHT = 3.0                         # the carried ecotone floor is lowland p50 2.95u -> flat weld
ISLAND_SEED = 40.0                        # REBUILD ATTEMPT 2: seed 40 -> the grass frame has ZERO weld-audit
#   near-miss pairs at centre (160,-1152) R125 (seed 42 left 2 hairline coast-border Y-mismatches; a seed
#   scan found 40/41/47/50/55/60/7/99 all clean, verify_landmass clean). Builds + verifies clean at r125.
ISLAND_UNDULATION = 0.02                  # near-round (<=0.05 design allowance); breaks the r132 Delaunay
ISLAND_N_CORNERS = 0                      #          ring degeneracy; a round coast, corners OFF for R1.
ISLAND_CORNER_STRENGTH = 0.0

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
# SHIFT_CELLS=(-192,-96) = the WHOLE-BLOCK shift (-768,-384)u = (-12,-6) blocks. THE ROOT-CAUSE FIX
# (build-fix round 4): a whole-block shift on BOTH axes maps the 6 donor blocks (13-15,11-12) onto 6
# target blocks (1-3,17-18) with ZERO re-partition -- every stock per-block mesh lands whole in one
# target block, so stock's OWN watertight cross-block borders are PRESERVED (a phase shift instead
# re-partitions every border tri, minting hundreds of un-weldable T-junctions -> the cascade). Only the
# 3x2-rect OUTER perimeter needs welding to the grass frame. Seats the ecotone MEC at (167.8,-1151.3).
SHIFT_CELLS = (-192, -96)
SHIFT_WORLD = (CELL * SHIFT_CELLS[0], CELL * SHIFT_CELLS[1])
FIXH_TAU = 0.05                           # ROUND-3: FIX-H disabled (0.05 = only already-on-border float
#   slop). With the WATERTIGHT-WINDOW carry (kept + flatten-fill = stock's full triangulation), the
#   re-partition crossings are conforming BY CONSTRUCTION; FIX-H's border-snap instead STRANDED verts on
#   one side (a tri snapped fully into one block leaves the other side without the vert -> a T-junction).
_FIXH_TAU_OLD = 2.6                        # pre-quantize a carried vert this close to a block border ONTO
#                                          it (BEFORE re-partition) so border corners weld both sides
#                                          in-frame -- the phase-shifted-notch fix (dunes_true_carry).
# THE VERBATIM-CORE DROP SET (design2_round3.json part1): carry every core tri whose topo is NOT in
# DROP, byte-verbatim. DROP = the interwoven mountains/rock/lip/forest/canyon/snow/highland/river/falls
# + topo-10 PLATEAU-GRASS (h~27, tall) + topo-59 BUILDING footprint. MEASURED (rung_f_extract_components
# / rung_f_drop_probe): 742 kept cells forming ONE 4-conn component (ZERO cell-fragmentation), 1454 kept
# tris, height p50 2.95 / p99 6.09 / max 7.08u (uniformly LOWLAND -> the whole carried rim welds). It
# PRESERVES R2 body topo-16 = 276 cells/422 tris + R3 backing topo-41 = 143 cells/279 tris + all 104
# straddle cells (ALL in the main component) -> R2/R3 pass BY CONSTRUCTION. The dropped features become
# holes: 765 cells drop to NOTHING (the grass frame fills them) + 105 PARTIAL cells keep some tris.
DROP_SET = frozenset({49, 50, 58, 7, 62, 45, 46, 36, 37, 27, 28, 48, 51, 10, 59})
# the carried rim (kept<->dropped boundary) is all lowland now; APRON_MAX lets the stitch weld the WHOLE
# rim (round-1's apron_max=6 left the tall walls open -- moot after the drop; the max rim height is ~7u).
APRON_MAX = 9.0

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
SEAM_WELD_REACH = 6.0
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


def _tri_area2_xz(tri):
    """Absolute XZ (plan) area of a tri -- catches a near-vertical face collapsed by the flatten to a
    thin sliver (small plan area) that an exact-coincidence check misses."""
    (ax, _ay, az) = tri[0][0]
    (bx, _by, bz) = tri[1][0]
    (cx, _cy, cz) = tri[2][0]
    return 0.5 * abs((bx - ax) * (cz - az) - (cx - ax) * (bz - az))


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
    """Read the donor Terrain world tris over the window cell rect, THEN apply THE VERBATIM-CORE DROP
    (tri-level topo filter, design2_round3): keep every tri whose topo is NOT in DROP_SET. Returns:
      by_cell : {cell: [kept donor_world_tri, ...]} for every window cell with a kept tri
      raw     : the flat list of KEPT donor window tris (byte-rigidity baseline, pre-transform)
    The dropped tris are recorded (dropped_tris_by_cell) so the fill can grass the exposed footprints.
    """
    raw_by_cell = defaultdict(list)
    for (bx, by) in DONOR_BLOCKS:
        for tri in TR.world_tris(bx, by, "terrain", disc=1, game=game_root):
            c = tri_cell(tri)
            if in_window(c):
                raw_by_cell[c].append(tri)

    def topo_of(tri):
        return X.decode_id(int(round(tri[0][3][0])))["topograph"]

    by_cell = {}                             # cell -> kept tris (topo NOT in DROP_SET)
    dropped_by_cell = defaultdict(list)      # cell -> dropped tris (topo IN DROP_SET)
    n_dropped = 0
    for c, tris in raw_by_cell.items():
        keep = [t for t in tris if topo_of(t) not in DROP_SET]
        drop = [t for t in tris if topo_of(t) in DROP_SET]
        n_dropped += len(drop)
        if drop:
            dropped_by_cell[c] = drop
        if keep:
            by_cell[c] = keep
    kept_cells = set(by_cell)
    fully_dropped = set(dropped_by_cell) - kept_cells   # grass frame fills these
    partial = {c for c in kept_cells if c in dropped_by_cell}
    raw = [(c, tri) for c, tris in by_cell.items() for tri in tris]
    log(f"  DROP: kept {len(raw)} tris / {len(kept_cells)} cells; dropped {n_dropped} tris; "
        f"fully-dropped cells {len(fully_dropped)} (grass-fill); partial cells {len(partial)} (hole-fill)")
    return dict(by_cell=by_cell, raw=raw, dropped_by_cell=dict(dropped_by_cell),
                n_dropped=n_dropped, n_cells_kept=len(by_cell), n_cells_raw=len(raw_by_cell),
                fully_dropped_cells=sorted(fully_dropped), partial_cells=sorted(partial))


# ============================================================================================
# STAGE 3 -- THE CARRY: donor rigid (whole-cell shift + DY + event/area strip + re-partition),
# host grass conforms.
# ============================================================================================
def _grass_stamp(host_bms):
    """A flat-grass vertex stamp (idall event0/area0, up normal, a grass UV) sampled from the minted grass
    frame's MAJORITY grass tile -- used to re-clothe the dropped-feature FILL tris. Picking the majority
    topo (the frame is ~93% topo-0 grass, ~7% a topo-58 coast variant) keeps the fill's grass tile
    IDENTICAL to the surrounding frame -> no rectangular grass-variant patch in-game (the first-tri stamp
    grabbed the topo-58 minority -> the render's grey rectangle)."""
    from collections import Counter
    tally = Counter()
    sample = {}
    for soup in host_bms.values():
        for tri in soup:
            (p, n, u, tg) = tri[0]
            d = X.decode_id(int(round(tg[0])))
            key = (d["topograph"], d["flags"])
            tally[key] += 1
            sample.setdefault(key, (tg[0], (float(u[0]), float(u[1]))))
    if not tally:
        return (float(X.encode_id(0, 0, 0, 0)), (0.0, 0.0))
    (topo, flags), _n = tally.most_common(1)[0]
    _idall, uv = sample[(topo, flags)]
    return (float(X.encode_id(0, 0, topo, flags)), uv)


def carry(donor, host_bms, land_height):
    """THE VERBATIM CORE + MINTED CONTEXT carry. The KEPT ecotone tris translate BYTE-VERBATIM (rigid
    whole-cell xz shift + uniform DY + event/area strip); the DROPPED-feature footprints are FILLED with
    conformed lowland grass whose triangulation IS the dropped tris' own (guaranteed to match the kept
    component rim EXACTLY -> watertight by construction), FLATTENED to land_height on every vertex that
    the kept ecotone does NOT share (a shared vertex keeps its ecotone Y so the core stays RIGID and the
    fill welds to it 2-owner) and re-clothed grass. The composite window is thus stock's FULL watertight
    triangulation with the ecotone verbatim + the context flattened to lowland grass; its ONLY once-edges
    are the window OUTER perimeter, all lowland -> welded to the r132 grass frame by the stitch.

    Returns (out_soup_by_block, placed_R, carried_translated_by_cell, diag).
    """
    by_cell = donor["by_cell"]                              # kept ecotone tris (verbatim)
    dropped_by_cell = donor["dropped_by_cell"]              # dropped-feature tris (become grass fill)
    R = set(by_cell.keys()) | set(dropped_by_cell.keys())  # EVERY window cell (kept OR dropped)
    Tx, Tz = SHIFT_CELLS
    placed_R = {(c[0] + Tx, c[1] + Tz) for c in R}          # grass frame is removed under the WHOLE window
    bcorners = boundary_corners(placed_R)

    # DY: seat the ecotone (desert-family floor) at land_height. Desert-family = topo {16,17,19,20,41}.
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
        f"(ecotone y range {min(all_ys):.2f}..{max(all_ys):.2f})")

    # KEPT vertex XZ keys (donor frame) -- a FILL vertex sharing one of these keeps the (rigid) ecotone
    # Y so the fill welds to the core 2-owner; a fill vertex NOT in this set flattens to land_height.
    kept_xz = set()
    for tris in by_cell.values():
        for tri in tris:
            for (p, _n, _u, _t) in tri:
                kept_xz.add((round(p[0], 3), round(p[2], 3)))

    Tw_x, Tw_z = SHIFT_WORLD
    grass_id, grass_uv = _grass_stamp(host_bms)

    def _fixh(px, pz):
        nx = round(px / BLOCK) * BLOCK
        nz = round(pz / BLOCK) * BLOCK
        npx = nx if 1e-4 < abs(px - nx) < FIXH_TAU else px
        npz = nz if 1e-4 < abs(pz - nz) < FIXH_TAU else pz
        return npx, npz, (npx != px or npz != pz)

    carried_translated = defaultdict(list)
    carried_world = []                                     # kept (verbatim) tris in world coords
    fill_world = []                                        # grass-fill tris in world coords
    n_fixh = 0
    n_fill = 0
    # 1a) KEPT ecotone tris -- BYTE-VERBATIM (pos+T, uv/nrm/tangent verbatim, event/area stripped)
    for c, tris in by_cell.items():
        tc = (c[0] + Tx, c[1] + Tz)
        for tri in tris:
            new = []
            for (p, n, u, tg) in tri:
                nid = strip_event_area(tg[0])
                px, py, pz = p[0] + Tw_x, p[1] + DY, p[2] + Tw_z
                npx, npz, moved = _fixh(px, pz)
                if moved:
                    n_fixh += 1
                new.append(((npx, py, npz), n, u, (nid,) + tuple(tg[1:])))
            carried_translated[tc].append(new)
            carried_world.append(new)
    # 1b) DROPPED-feature FILL -- the hole's own donor triangulation, FLATTENED (shared verts keep ecotone
    #     Y, exclusive verts -> land_height) + re-clothed grass. Watertight to the core by construction
    #     (shares donor edges with the kept ecotone). This dense conforming fill beats an ear-clip of the
    #     big sparse dropped region (which minted huge border-crossing tris -> 607 once-edges); the ONE
    #     residual it leaves is a handful of stock donor internal T-junctions, closed by conform below.
    n_fill_collapsed = 0
    for c, tris in dropped_by_cell.items():
        for tri in tris:
            new = []
            for (p, _n, _u, _tg) in tri:
                shared = (round(p[0], 3), round(p[2], 3)) in kept_xz
                py = (p[1] + DY) if shared else land_height
                px, pz = p[0] + Tw_x, p[2] + Tw_z
                npx, npz, moved = _fixh(px, pz)
                if moved:
                    n_fixh += 1
                new.append(((npx, py, npz), (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0)))
            # DROP a COLLAPSED VERTICAL FACE: a donor tri with two verts at (nearly) the same XZ is a
            # near-vertical step; flattening both to land_height collapses it to a degenerate/sliver tri
            # (the stock non-manifold T-junction source -- rung_f_diag4 measured 0.01u slivers). Dropping
            # it welds its two neighbours (their now-coincident donor edges become one shared edge).
            xz = [(round(v[0][0], 2), round(v[0][2], 2)) for v in new]
            if xz[0] == xz[1] or xz[1] == xz[2] or xz[0] == xz[2] or _tri_area2_xz(new) < 0.08:
                n_fill_collapsed += 1
                continue
            fill_world.append(new)
            n_fill += 1
    log(f"  fill: dropped {n_fill_collapsed} collapsed-vertical-face sliver tris (flatten degeneracies)")
    log(f"  carry: {len(carried_world)} verbatim ecotone tris + {n_fill} grass-fill tris "
        f"(kept_xz verts {len(kept_xz)}, fixh {n_fixh})")

    # 1c) UN-GRASS the enclosed stranded-patch cells (donor-mesh "missing" cells enclosed by the blob).
    #     Their grass is removed here; the blob's interior HOLES around them are EAR-CLIP filled inside
    #     stitch_tile (post-re-partition, on the same directed-half-edge extraction the tile uses -- the
    #     robust place; a pre-re-partition ear-clip mis-counted the holes via down-facing carried tris).
    import rung_f_holefill as HF
    enclosed_cells = HF.enclosed_missing_cells(placed_R)
    placed_R = placed_R | enclosed_cells
    log(f"  hole prep: {len(enclosed_cells)} enclosed stranded-patch cells un-grassed "
        f"(interior holes ear-clipped in stitch_tile)")

    all_world = carried_world + fill_world

    # 2) RE-PARTITION at the host 64u borders (transplant clip_poly). An interior tri passes whole;
    #    a straddler keeps its inside part exactly. Degenerate slivers drop.
    carried_by_block = defaultdict(list)
    dropped_area2 = 0.0
    max_poke = 0.0
    for poly0 in all_world:
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
    # THE TILING STITCH (rebuild attempt 2): dilate the grass removal by 1 cell so the grass rim recedes
    # off the blob (and off the block borders -> no zero-width degenerate seam), then tile the annulus
    # between the grass rim and the blob outline -> watertight by construction.
    grass_remove = HF.dilate(placed_R, 1)
    out, sdiag = STITCH.stitch_tile(carried_by_block, host_bms, placed_R, grass_remove, land_height,
                                    grass_id, grass_uv, log=log)

    diag = dict(n_R_cells=len(R), n_placed_R=len(placed_R), n_verbatim_tris=len(carried_world),
                n_fill_tris=n_fill, DY=round(DY, 5), ecotone_floor_y=round(ens_seat, 4),
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
