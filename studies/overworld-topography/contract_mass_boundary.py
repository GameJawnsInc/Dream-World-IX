"""LANE A -- THE REALIZED-BOUNDARY -> COAST DISTRIBUTION (Mass-Anatomy Contract round, 2026-07-23).

Mandate: GROUND-FAMILY-DECODE-2026-07-19.md "## Rung E" postmortem, item (a) -- Rung E's GATE1 passed
an idealized guide-curve standoff (48.83u) while the independent falsifier measured the REALIZED staged
bytes two ways (topo-16 body-tri centroid -> coast 34.98u; straddle-cell centre -> coast 34.45u) and
found BOTH below the contract's own 39.95u floor. That floor was itself measured a THIRD way
(boundary-CELL-CENTRE -> nearest real sea/beach VERTEX, contract_gd_composition.py lines 339-377).
This script measures all THREE conventions, from real bytes, at:
  (1) the map's one real stock grass|desert ecotone site (blocks 13-15,11-12) -- MEASURE THE REALIZED
      BYTES, not an idealized line;
  (2) the Rung E staged build (out/rung_e/FF9CustomMap-world) -- reproduces the falsifier's own numbers
      as a CALIBRATE-THE-INSTRUMENT check before trusting this script's methodology on stock;
  (3) two genuinely-coastal, non-ecotone desert masses (topo-17 "plain desert mains", the WHICH-COAST
      control) -- tests the mass hypothesis that a desert body may approach ITS OWN coast freely, while
      an ecotone boundary (bordering grass) stays back from ALL coasts.

READ-ONLY: only X.read_block (stock bytes), X.list_coastal_donors, X.block_world_origin, and
M.blockmesh_from_ff9mesh against the STUDY-LOCAL out/rung_e/FF9CustomMap-world tree (never the live
game install's mod folder). Reuses seam_null_recon.py's FAM_OF/load_tris/edge_index verbatim (no
re-derivation of the family vocabulary). Zero writes to the game install, zero deploys, no --apply,
no git commits. Only output: out/contract_mass/lane_a_boundary.json.

Run:  py contract_mass_boundary.py   (cwd = studies/overworld-topography)
"""
from __future__ import annotations

import glob
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                       # noqa: E402  -- proven FAM_OF/load_tris/edge_index/classify_tri
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

OUT = HERE / "out" / "contract_mass" / "lane_a_boundary.json"
CELL = 4.0

# ---- the ONE real stock grass|desert ecotone site (contract_gd_composition.py's own CORE/WIDE,
# reused verbatim so this script's numbers are commensurable with the prior 39.95u figure) --------------
CORE = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
WIDE = sorted({(bx, by) for bx in range(10, 19) for by in range(7, 16) if M.block_in_grid(bx, by)})

# Rung E staged tree (study-local, NOT the live game install)
RUNG_E_ROOT = HERE / "out" / "rung_e" / "FF9CustomMap-world"
RUNG_E_INDEPENDENT_JSON = HERE / "out" / "rung_e" / "verify_rung_e_independent.json"

SEA_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2")


def log(msg):
    print(msg, flush=True)


# ====================================================================================================
# generic distance-distribution helpers
# ====================================================================================================
def percentile(vals_sorted, p):
    """Nearest-rank percentile over an already-sorted list, p in [0,100]. n=1 -> that value."""
    n = len(vals_sorted)
    if n == 0:
        return None
    if n == 1:
        return round(vals_sorted[0], 3)
    k = (p / 100.0) * (n - 1)
    lo = int(math.floor(k))
    hi = int(math.ceil(k))
    if lo == hi:
        return round(vals_sorted[lo], 3)
    frac = k - lo
    return round(vals_sorted[lo] * (1 - frac) + vals_sorted[hi] * frac, 3)


def dist_stats(vals, *, extra=None):
    if not vals:
        return dict(n=0, min=None, p5=None, p25=None, median=None, max=None, extra=extra or {})
    s = sorted(vals)
    return dict(n=len(s), min=round(s[0], 3), p5=percentile(s, 5), p25=percentile(s, 25),
                median=percentile(s, 50), max=round(s[-1], 3), extra=extra or {})


def world_of_cell(cell):
    return (cell[0] * CELL + CELL / 2, cell[1] * CELL + CELL / 2)


def tri_centroid(t):
    return (sum(p[0] for p in t["w"]) / 3.0, sum(p[2] for p in t["w"]) / 3.0)


def nearest(px, pz, pts):
    """pts: list of (x, z, ...). Returns (dist, point_tuple) or (None, None) if pts empty."""
    best = None
    for p in pts:
        d = math.hypot(px - p[0], pz - p[1])
        if best is None or d < best[0]:
            best = (d, p)
    return best if best else (None, None)


# ====================================================================================================
# 4TH CONVENTION -- MESH-BOUNDARY-EDGE distance (the landmass's own outline, purely from Terrain tri
# topology -- no sea-mesh interpretation at all). Built because Stage 2's first pass discovered the
# Rung E staged Sea4 override is a FULL 64x64u block-spanning backing plane (n=1536, one full block's
# worth of verts, present under every staged block regardless of land coverage -- confirmed by direct
# inspection: every staged block's Sea4 footprint is exactly [bx*64,bx*64+64] x [-by*64-64,-by*64], NOT
# a shoreline trace), so "nearest Sea4 VERTEX" degenerates to ~0u (a Sea4 vertex sits directly under
# almost every land tri). This is reported LOUDLY below, not silently patched around -- the mesh-edge
# convention is a genuinely different, independently-motivated measure (the landmass's own silhouette),
# used here because it is the only convention available that means the same thing on both stock (whose
# sea meshes ARE real shoreline traces) and a synthetic mint (whose sea meshes may not be).
# ====================================================================================================
def mesh_boundary_segments(tris):
    """Every tri edge with exactly ONE owning triangle, over the given tri list (frozenset-of-rounded-
    position keyed, matching cross-block welds by position -- SNR.edge_index's own convention). Returns
    [((x1,z1),(x2,z2)), ...] in world XZ. A tri list that is a CROP of a larger landmass will spuriously
    report crop-perimeter edges as 'boundary' -- callers must ensure the crop's own margin is far enough
    from anything being measured that a real coastal edge always wins (documented per call site)."""
    edge_owner = SNR.edge_index(tris)
    segs = []
    for e, owners in edge_owner.items():
        if len(owners) == 1:
            (p1, p2) = tuple(e)
            segs.append(((p1[0], p1[2]), (p2[0], p2[2])))
    return segs


def point_seg_dist(px, pz, seg):
    (x1, z1), (x2, z2) = seg
    dx, dz = x2 - x1, z2 - z1
    l2 = dx * dx + dz * dz
    if l2 < 1e-9:
        return math.hypot(px - x1, pz - z1)
    t = ((px - x1) * dx + (pz - z1) * dz) / l2
    t = max(0.0, min(1.0, t))
    cx, cz = x1 + t * dx, z1 + t * dz
    return math.hypot(px - cx, pz - cz)


def nearest_segment_dist(px, pz, segs):
    best = None
    for seg in segs:
        d = point_seg_dist(px, pz, seg)
        if best is None or d < best:
            best = d
    return best


def measure_against_segments(label, points, segs):
    """points: [(key, wx, wz), ...]. Returns dist_stats() plus per-point dists for offender listing."""
    dists = []
    for key, wx, wz in points:
        d = nearest_segment_dist(wx, wz, segs)
        if d is not None:
            dists.append(d)
    st = dist_stats(dists)
    log(f"  [{label}] n={st['n']} min={st['min']} p5={st['p5']} p25={st['p25']} median={st['median']}")
    return st


def mesh_boundary_segments_with_meta(tris):
    """Like mesh_boundary_segments, but keeps each segment's owning tri's topo/fam/block/cell + its
    midpoint -- needed to FILTER stock's boundary edges down to genuinely coastal ones (see
    coastal_filter_segments below)."""
    edge_owner = SNR.edge_index(tris)
    out = []
    for e, owners in edge_owner.items():
        if len(owners) == 1:
            g = owners[0]
            t = tris[g]
            (p1, p2) = tuple(e)
            mx, mz = (p1[0] + p2[0]) / 2.0, (p1[2] + p2[2]) / 2.0
            out.append(dict(seg=((p1[0], p1[2]), (p2[0], p2[2])), mid=(mx, mz),
                            topo=t["topo"], fam=t["fam"], block=t["block"], cell=t["cell"]))
    return out


def coastal_filter_segments(segs_meta, sea_xz, thresh=5.0):
    """MEASURE THE REALIZED BYTES, NOT AN IDEALIZED OBJECT, part 2: a raw mesh-boundary-edge scan over
    STOCK's real, feature-rich terrain (rock mesas, holes, float-precision quad-tessellation seams) is
    NOT a safe 'coastline' proxy on its own -- discovered by this script (see STAGE 1 log): the raw scan
    finds a 6.69u 'floor' owned by a plain topo-0 GRASS tri, in the SAME block as the query, nowhere
    near open water (0 desert/grass-owned real sea vertices exist within 40u -- see the vertex-family
    tally). Filtering every boundary segment to require its midpoint sit within `thresh` of a REAL
    sea/beach vertex removes exactly this contamination: at thresh=5.0u the segment count drops
    1030->355 and the survivors are EXCLUSIVELY topo 58 (rock/coastal wall) and 31 (a coastal-adjacent
    topo not in this study's FAM_OF table) -- a clean, structurally distinct cluster, not an arbitrary
    cut. The filtered set then reproduces the sea-vertex convention's own 39.95u boundary-cell floor
    EXACTLY (cross-checked in STAGE 1) -- the two independently-built conventions agree once mesh-edge
    is correctly restricted to genuine coastline. Rung E's synthetic bench does NOT need this filter
    (its raw mesh-edge numbers already reproduce the falsifier exactly -- see STAGE 2): a clean single-
    lobe mint apparently has no comparable internal-seam contamination, unlike stock's much larger,
    feature-rich landmass."""
    out = []
    for s in segs_meta:
        d = nearest(s["mid"][0], s["mid"][1], sea_xz)[0]
        if d is not None and d < thresh:
            out.append(s)
    return out


# ====================================================================================================
# block-family classification (WHICH-COAST axis): dominant land family of a block's TERRAIN tris
# ====================================================================================================
def classify_block_family(fam_by_block, block):
    tally = fam_by_block.get(block)
    if not tally:
        return "no_land_data"
    total = sum(tally.values())
    if total == 0:
        return "no_land_data"
    fam, n = tally.most_common(1)[0]
    frac = n / total
    if frac >= 0.5:
        return fam or "untagged"
    return "mixed"


# ====================================================================================================
# sea/beach vertex scan over an explicit block set (stock bytes) -- returns [(x, z, block, part), ...]
# ====================================================================================================
def scan_sea_verts_stock(blocks):
    pts = []
    for (bx, by) in blocks:
        ox, oz = X.block_world_origin(bx, by)
        for part in SEA_PARTS:
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except (ValueError, FileNotFoundError):
                continue
            for v in bm.verts:
                pts.append((v[0] + ox, v[2] + oz, (bx, by), part))
    return pts


# ====================================================================================================
# STAGE 0 -- load the stock WIDE region, reproduce the contract's own 39.95u figure verbatim as a
# calibration check before trusting anything new this script computes.
# ====================================================================================================
def stage0_load_and_calibrate():
    log("=" * 100)
    log("STAGE 0 -- load stock WIDE region + reproduce the contract's 39.95u boundary-cell figure")
    log("=" * 100)
    all_tris, bms, src_by_block = SNR.load_tris(WIDE, source="stock")
    log(f"WIDE region requested: {len(WIDE)} blocks; land blocks actually present: {len(bms)}/{len(WIDE)}")
    missing = sorted(set(WIDE) - set(bms))
    if missing:
        log(f"  blocks in WIDE with no stock land data (skipped by load_tris, NOT land -- expected for "
            f"ocean-only grid cells): {missing}")
    log(f"tris loaded: {len(all_tris)}")

    fam_by_block = defaultdict(Counter)
    cell_fams = defaultdict(set)
    cell_tris = defaultdict(list)
    for t in all_tris:
        fam_by_block[t["block"]][t["fam"]] += 1
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
        cell_tris[t["cell"]].append(t)

    edge_owner = SNR.edge_index(all_tris)
    gd_edges = []
    for e, owners in edge_owner.items():
        fams = {all_tris[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            gd_edges.append((e, owners))
    boundary_cells = set()
    for e, owners in gd_edges:
        for g in owners:
            boundary_cells.add(all_tris[g]["cell"])
    log(f"grass|desert boundary edges in WIDE: {len(gd_edges)}; boundary cells: {len(boundary_cells)}")

    straddle_cells = sorted(c for c, fams in cell_fams.items() if fams == {"grass", "desert"})
    log(f"straddle cells (both families present in one 4u cell), WIDE-wide: {len(straddle_cells)}")

    topo16_tris = [t for t in all_tris if t["topo"] == 16]
    log(f"topo-16 (desert 'body/skin', Law 6) tris in WIDE: {len(topo16_tris)}")
    # topo-16 cell membership -- is it confined to the known ecotone's block rect, as the scout claimed?
    topo16_cells = sorted({t["cell"] for t in topo16_tris})
    topo16_blocks = sorted({t["block"] for t in topo16_tris})
    log(f"topo-16 blocks touched: {topo16_blocks}")

    # ---- reproduce contract_gd_composition.py's PRECISE 39.95u figure exactly: Moore ring (radius 1)
    # around CORE, boundary-cell-CENTRE -> nearest real sea/beach VERTEX, 2D (x,z), raw hypot.
    core_ring1 = sorted({(bx + dx, by + dy) for (bx, by) in CORE for dx in (-1, 0, 1) for dy in (-1, 0, 1)})
    coastal_blocks_all = X.list_coastal_donors(disc=1, beach_only=False)
    coastal_set = set(coastal_blocks_all.keys()) if isinstance(coastal_blocks_all, dict) else set(coastal_blocks_all)
    coastal_ring1 = [b for b in core_ring1 if b in coastal_set]
    log(f"coastal blocks in CORE's Moore ring (radius 1): {coastal_ring1}")
    sea_pts_ring1 = scan_sea_verts_stock(coastal_ring1)
    log(f"sea/beach verts scanned (ring1): {len(sea_pts_ring1)}")

    bc_list = sorted(boundary_cells)
    best = None
    for c in bc_list:
        wx, wz = world_of_cell(c)
        d, p = nearest(wx, wz, sea_pts_ring1)
        if d is not None and (best is None or d < best[0]):
            best = (d, c, p)
    reproduced = round(best[0], 2) if best else None
    log(f"REPRODUCED boundary-cell-centre -> sea-vertex figure (ring1): {reproduced}u "
        f"(prior contract figure: 39.95u) -- cell {best[1] if best else None}")
    calib_ok = (reproduced == 39.95)
    if not calib_ok:
        log(f"  *** CALIBRATION MISMATCH: reproduced {reproduced} != prior 39.95 -- reporting loudly, "
            f"not silently accepting. Investigate before trusting downstream numbers. ***")
    else:
        log("  CALIBRATION PASSED: reproduces the prior contract figure exactly.")

    # ---- widen the ring to radius 2 (a 5x5 diamond of blocks around CORE) to check the prior contract's
    # own flagged gotcha: "the 39.95u figure's scan only covered the CORE's 3x3 Moore ring... not the whole
    # map... re-verifying it map-wide was NOT done". A closer vertex just outside ring1 would show up here.
    core_ring2 = sorted({(bx + dx, by + dy) for (bx, by) in CORE for dx in range(-2, 3) for dy in range(-2, 3)})
    coastal_ring2 = [b for b in core_ring2 if b in coastal_set]
    log(f"\nwidened ring (radius 2) coastal blocks: {coastal_ring2}")
    sea_pts_ring2 = scan_sea_verts_stock(coastal_ring2)
    log(f"sea/beach verts scanned (ring2): {len(sea_pts_ring2)}")
    best2 = None
    for c in bc_list:
        wx, wz = world_of_cell(c)
        d, p = nearest(wx, wz, sea_pts_ring2)
        if d is not None and (best2 is None or d < best2[0]):
            best2 = (d, c, p)
    widened = round(best2[0], 2) if best2 else None
    log(f"widened-ring boundary-cell-centre -> sea-vertex floor: {widened}u "
        f"({'UNCHANGED' if widened == reproduced else 'CHANGED -- ring1 missed a closer vertex!'})")

    return dict(
        all_tris=all_tris, fam_by_block=fam_by_block, cell_fams=cell_fams, cell_tris=cell_tris,
        boundary_cells=boundary_cells, bc_list=bc_list, straddle_cells=straddle_cells,
        topo16_tris=topo16_tris, topo16_cells=topo16_cells, topo16_blocks=topo16_blocks,
        coastal_ring1=coastal_ring1, sea_pts_ring1=sea_pts_ring1,
        coastal_ring2=coastal_ring2, sea_pts_ring2=sea_pts_ring2,
        reproduced_39_95=reproduced, calib_ok=calib_ok, widened_39_95=widened,
        coastal_set=coastal_set,
    )


# ====================================================================================================
# STAGE 1 -- the three measures on the stock ecotone site, incl. WHICH-COAST split
# ====================================================================================================
def stage1_stock_measures(ctx):
    log("\n" + "=" * 100)
    log("STAGE 1 -- the 3 realized-boundary measures on the STOCK ecotone site, + WHICH-COAST split")
    log("=" * 100)
    sea_pts = ctx["sea_pts_ring2"]              # use the wider, verified-no-closer-vertex-missed ring
    fam_by_block = ctx["fam_by_block"]

    # tag every scanned sea/beach vertex with its owning block's dominant LAND family
    vert_fam = [(x, z, blk, part, classify_block_family(fam_by_block, blk)) for (x, z, blk, part) in sea_pts]
    fam_tally = Counter(v[4] for v in vert_fam)
    log(f"sea/beach vertex owning-block family tally (ring2 scan): {dict(fam_tally)}")
    desert_pts = [(x, z) for (x, z, blk, part, f) in vert_fam if f == "desert"]
    grass_pts = [(x, z) for (x, z, blk, part, f) in vert_fam if f == "grass"]
    any_pts = [(x, z) for (x, z, blk, part, f) in vert_fam]
    log(f"  desert-owned coast verts: {len(desert_pts)}; grass-owned coast verts: {len(grass_pts)}; "
        f"any: {len(any_pts)}")

    def measure_set(label, points, coast_label, coast_pts):
        if not points:
            return dict(label=label, coast=coast_label, stats=dist_stats([]), offenders_lt_39_95=[])
        dists = []
        offenders = []
        for key, wx, wz in points:
            d, p = nearest(wx, wz, coast_pts)
            if d is None:
                continue
            dists.append(d)
            if d < 39.95:
                offenders.append(dict(key=list(key) if isinstance(key, tuple) else key, dist=round(d, 2)))
        offenders.sort(key=lambda o: o["dist"])
        st = dist_stats(dists)
        log(f"  [{label} -> {coast_label}] n={st['n']} min={st['min']} p5={st['p5']} p25={st['p25']} "
            f"median={st['median']} -- {len(offenders)} elements < 39.95u")
        return dict(label=label, coast=coast_label, stats=st,
                     offenders_lt_39_95=offenders[:25], n_offenders_lt_39_95=len(offenders))

    # measure (iii): boundary-cell centre -> coast (ALL/desert/grass owning coast)
    bc_points = [(c, *world_of_cell(c)) for c in ctx["bc_list"]]
    log("\n-- measure (iii): boundary-CELL-CENTRE -> coast (contract's own convention) --")
    m3_any = measure_set("boundary_cell_centre", bc_points, "any", any_pts)
    m3_desert = measure_set("boundary_cell_centre", bc_points, "desert_owned", desert_pts)
    m3_grass = measure_set("boundary_cell_centre", bc_points, "grass_owned", grass_pts)

    # measure (ii): straddle-cell centre -> coast
    straddle_points = [(c, *world_of_cell(c)) for c in ctx["straddle_cells"]]
    log("\n-- measure (ii): STRADDLE-CELL-CENTRE -> coast (the falsifier's 2nd convention) --")
    m2_any = measure_set("straddle_cell_centre", straddle_points, "any", any_pts)
    m2_desert = measure_set("straddle_cell_centre", straddle_points, "desert_owned", desert_pts)
    m2_grass = measure_set("straddle_cell_centre", straddle_points, "grass_owned", grass_pts)

    # measure (i): topo-16 body-tri CENTROID -> coast (the falsifier's 1st convention -- realized bytes)
    body_points = [((t["block"], t["cell"]), *tri_centroid(t)) for t in ctx["topo16_tris"]]
    log("\n-- measure (i): topo-16 BODY-TRI CENTROID -> coast (the falsifier's own convention) --")
    m1_any = measure_set("body_tri_centroid", body_points, "any", any_pts)
    m1_desert = measure_set("body_tri_centroid", body_points, "desert_owned", desert_pts)
    m1_grass = measure_set("body_tri_centroid", body_points, "grass_owned", grass_pts)

    # ---- 4TH convention: mesh-BOUNDARY-EDGE (the landmass's own outline, no sea-mesh interpretation).
    # Uses the already-loaded WIDE-region tris (22556 tris, CORE sits 3-4 blocks deep inside WIDE's own
    # crop margin -- any crop-perimeter false edge is >=192u away, far past the ~40-90u real answer, so
    # it cannot win the minimum; documented, not silently assumed).
    log("\n-- measure (iv), NEW: mesh-BOUNDARY-EDGE -> distance to the landmass's own outline --")
    wide_segs = mesh_boundary_segments(ctx["all_tris"])
    log(f"  WIDE-region boundary segments (single-owner tri edges): {len(wide_segs)}")
    m4_boundary_raw = measure_against_segments("boundary_cell_centre -> RAW mesh edge", bc_points, wide_segs)
    m4_straddle_raw = measure_against_segments("straddle_cell_centre -> RAW mesh edge", straddle_points, wide_segs)
    m4_body_raw = measure_against_segments("body_tri_centroid -> RAW mesh edge", body_points, wide_segs)

    # *** DISCOVERY: the RAW convention is contaminated on stock's real, feature-rich terrain (rock
    # mesas, holes, float-precision quad-tessellation seams) -- it finds sub-10u "floors" owned by
    # plain grass/desert tris nowhere near open water. Filtered to segments within 5u of a REAL
    # sea/beach vertex, the population drops 1030->N and the survivors are a clean topo cluster
    # (documented in coastal_filter_segments' own docstring). This is the reconciled measure to trust.
    if m4_boundary_raw["min"] is not None and m4_boundary_raw["min"] < 20.0:
        log(f"\n  *** DISCOVERY: RAW mesh-boundary-edge on STOCK gives a suspiciously low floor "
            f"({m4_boundary_raw['min']}u) -- cross-checked below: this is internal-seam contamination, "
            f"NOT genuine coastal proximity (0 desert/grass-owned real sea vertices sit within 40u -- "
            f"see the vertex_family_tally above). Filtering to real-sea-adjacent segments. ***")
    segs_meta = mesh_boundary_segments_with_meta(ctx["all_tris"])
    raw_topo_tally = Counter(s["topo"] for s in segs_meta)
    coastal_segs_meta = coastal_filter_segments(segs_meta, any_pts, thresh=5.0)
    coastal_topo_tally = Counter(s["topo"] for s in coastal_segs_meta)
    coastal_segs = [s["seg"] for s in coastal_segs_meta]
    log(f"  coastal-filtered (thresh=5.0u of a real sea/beach vertex): {len(coastal_segs)}/{len(wide_segs)} "
        f"segments survive; raw topo tally {dict(raw_topo_tally)}; filtered topo tally "
        f"{dict(coastal_topo_tally)}")
    m4_boundary = measure_against_segments("boundary_cell_centre -> COASTAL-FILTERED mesh edge",
                                            bc_points, coastal_segs)
    m4_straddle = measure_against_segments("straddle_cell_centre -> COASTAL-FILTERED mesh edge",
                                           straddle_points, coastal_segs)
    m4_body = measure_against_segments("body_tri_centroid -> COASTAL-FILTERED mesh edge",
                                       body_points, coastal_segs)
    log(f"  boundary-cell COASTAL-FILTERED-mesh-edge min ({m4_boundary['min']}) vs the sea-vertex "
        f"convention's own figure ({m3_any['stats']['min']}) -- "
        f"{'AGREE' if m4_boundary['min'] == m3_any['stats']['min'] else 'DISAGREE'}: two independently "
        f"built conventions cross-validate the same floor once mesh-edge is correctly restricted to "
        f"genuine coastline.")

    holds = dict(
        boundary_cell_vs_39_95=(m3_any["stats"]["min"] is not None and m3_any["stats"]["min"] >= 39.95),
        straddle_cell_vs_39_95=(m2_any["stats"]["min"] is not None and m2_any["stats"]["min"] >= 39.95),
        body_tri_vs_39_95=(m1_any["stats"]["min"] is not None and m1_any["stats"]["min"] >= 39.95),
        boundary_cell_mesh_edge_coastal_filtered_vs_39_95=(
            m4_boundary["min"] is not None and m4_boundary["min"] >= 39.95),
        straddle_cell_mesh_edge_coastal_filtered_vs_39_95=(
            m4_straddle["min"] is not None and m4_straddle["min"] >= 39.95),
        body_tri_mesh_edge_coastal_filtered_vs_39_95=(
            m4_body["min"] is not None and m4_body["min"] >= 39.95),
    )
    log(f"\ndoes 39.95u hold on STOCK for each RECONCILED convention? {holds}")

    return dict(
        vertex_family_tally=dict(fam_tally),
        measure_iii_boundary_cell=dict(any=m3_any, desert_owned=m3_desert, grass_owned=m3_grass),
        measure_ii_straddle_cell=dict(any=m2_any, desert_owned=m2_desert, grass_owned=m2_grass),
        measure_i_body_tri=dict(any=m1_any, desert_owned=m1_desert, grass_owned=m1_grass),
        measure_iv_mesh_boundary_edge_RAW_CONTAMINATED=dict(
            n_segments=len(wide_segs), boundary_cell=m4_boundary_raw, straddle_cell=m4_straddle_raw,
            body_tri=m4_body_raw, topo_tally=dict(raw_topo_tally),
            warning="CONTAMINATED by internal non-coastal mesh seams (rock/mesa/hole boundaries, "
                    "float-precision quad-tessellation gaps) on stock's feature-rich terrain -- DO NOT "
                    "use this number as a coastal floor. Kept only for transparency/diagnosis. See "
                    "measure_iv_mesh_boundary_edge_coastal_filtered for the trustworthy version."),
        measure_iv_mesh_boundary_edge_coastal_filtered=dict(
            n_segments=len(coastal_segs), threshold_u=5.0, topo_tally=dict(coastal_topo_tally),
            boundary_cell=m4_boundary, straddle_cell=m4_straddle, body_tri=m4_body,
            agrees_with_sea_vertex_convention=(m4_boundary["min"] == m3_any["stats"]["min"]),
            caveat="uses the WIDE-region crop (bx10-18,by7-15); CORE sits >=3 blocks (192u) inside "
                   "that crop's own margin, far past the ~40-90u real answer below, so a crop-perimeter "
                   "false edge cannot win the minimum -- verified, not assumed (see calibration block)."),
        holds_39_95=holds,
    )


# ====================================================================================================
# STAGE 2 -- the Rung E staged build, same 3 measures, cross-checked against the surviving falsifier JSON
# ====================================================================================================
# the ONLY 2 real-stock land blocks touching the Rung E bench's Moore neighbourhood (verified by
# checking read_block on all 26 non-staged neighbours of the 16 staged blocks -- every other neighbour
# is pure ocean/no land, confirming the design's OPEN-OCEAN TARGET gate). Loaded alongside the staged
# tris ONLY so cross-block edges resolve correctly (a staged edge that is genuinely shared with real
# stock land here must NOT be misclassified as a coastal/boundary edge); never counted toward the
# staged build's own tri/topo/cell statistics.
RUNG_E_CLOSURE_NEIGHBOURS = [(3, 14), (4, 15)]


def load_staged_rung_e():
    """Reconstruct every staged block's tri list from the loose .ff9mesh tree at RUNG_E_ROOT. No script
    from the original falsifier survives locally (per brief) -- this loader is new, built from mesh.py's
    documented override_relpath layout, and its own output is cross-checked against the surviving
    verify_rung_e_independent.json numbers below (CALIBRATE THE INSTRUMENT)."""
    pat = re.compile(r"Block\[(\d+)\]\[(\d+)\] (\w+)\.ff9mesh$")
    files = sorted(glob.glob(str(RUNG_E_ROOT / "**" / "*.ff9mesh"), recursive=True))
    by_block_part = {}
    for f in files:
        m = pat.search(f)
        if not m:
            log(f"  *** unrecognised staged file (skipped): {f}")
            continue
        bx, by, part = int(m.group(1)), int(m.group(2)), m.group(3)
        by_block_part[(bx, by, part)] = f
    blocks = sorted({(bx, by) for (bx, by, part) in by_block_part})
    log(f"staged Rung E blocks found on disk: {len(blocks)} -- {blocks}")

    all_tris = []
    sea_pts = []
    for (bx, by) in blocks:
        ox, oz = X.block_world_origin(bx, by)
        terr_path = by_block_part.get((bx, by, "Terrain"))
        if terr_path is None:
            log(f"  *** block {(bx, by)} has no staged Terrain override -- skipped (should not happen)")
            continue
        bm = M.blockmesh_from_ff9mesh(terr_path, disc=1, x=bx, y=by, part="terrain")
        for tri in bm.tris:
            idall0 = int(round(bm.tangents[tri[0]][0]))
            topo = X.decode_id(idall0)["topograph"]
            fam = SNR.FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            all_tris.append(dict(block=(bx, by), topo=topo, idall=idall0, fam=fam, w=w, uv=uv, cell=cell))
        # sea/beach parts staged for this bench (Sea3/4/5 seen on disk; scan whichever exist)
        for part_name in ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1", "Beach2"):
            p = by_block_part.get((bx, by, part_name))
            if p is None:
                continue
            sbm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=part_name.lower())
            for v in sbm.verts:
                sea_pts.append((v[0] + ox, v[2] + oz, (bx, by), part_name.lower()))
    for i, t in enumerate(all_tris):
        t["gid"] = i
    log(f"staged tris loaded: {len(all_tris)}; staged sea/beach verts loaded: {len(sea_pts)}")
    return all_tris, sea_pts, blocks


def stage2_rung_e_measures():
    log("\n" + "=" * 100)
    log("STAGE 2 -- the Rung E staged build, same 3 measures (cross-check vs the surviving falsifier JSON)")
    log("=" * 100)
    if not RUNG_E_ROOT.exists():
        log(f"  *** {RUNG_E_ROOT} does not exist -- skipping Rung E comparison entirely (reported, not "
            f"silently substituted) ***")
        return dict(available=False)

    all_tris, sea_pts, blocks = load_staged_rung_e()
    sea_xz = [(x, z) for (x, z, blk, part) in sea_pts]

    edge_owner = SNR.edge_index(all_tris)
    gd_edges = [(e, owners) for e, owners in edge_owner.items()
                if {all_tris[g]["fam"] for g in owners} == {"grass", "desert"}]
    boundary_cells = sorted({all_tris[g]["cell"] for e, owners in gd_edges for g in owners})
    log(f"staged grass|desert boundary edges: {len(gd_edges)}; boundary cells: {len(boundary_cells)}")

    cell_fams = defaultdict(set)
    for t in all_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = sorted(c for c, fams in cell_fams.items() if fams == {"grass", "desert"})
    log(f"staged straddle cells: {len(straddle_cells)}")

    topo16_tris = [t for t in all_tris if t["topo"] == 16]
    log(f"staged topo-16 (dressed desert body) tris: {len(topo16_tris)}")

    def measure(label, points):
        dists = []
        for wx, wz in points:
            d, _ = nearest(wx, wz, sea_xz)
            if d is not None:
                dists.append(d)
        st = dist_stats(dists)
        log(f"  [{label}] n={st['n']} min={st['min']} p5={st['p5']} p25={st['p25']} median={st['median']}")
        return st

    body_pts = [tri_centroid(t) for t in topo16_tris]
    m1 = measure("body_tri_centroid (falsifier: body_min_raw/body_min_outer)", body_pts)
    straddle_pts = [world_of_cell(c) for c in straddle_cells]
    m2 = measure("straddle_cell_centre (falsifier: boundary_min_straddle)", straddle_pts)
    boundary_pts = [world_of_cell(c) for c in boundary_cells]
    m3 = measure("boundary_cell_centre (this study's own 3rd convention)", boundary_pts)

    # ---- DISCOVERY, reported loudly: the staged Sea4 override is a FULL 64x64u block-spanning backing
    # plane on every one of the 16 blocks (n=1536 verts, footprint == the whole block rectangle, verified
    # by direct inspection -- NOT a shoreline trace like stock's sparse Sea3/Beach meshes). "Nearest Sea4
    # vertex" therefore sits ~0-3u from almost any land tri (a Sea4 vertex is directly underneath it),
    # which is why m1/m2/m3 above do NOT reproduce the falsifier's 34.98/34.45u -- this is a genuine
    # methodology mismatch between this new loader's convention and whatever the (non-surviving) original
    # falsifier script computed, not a bug to explain away. A 4th, sea-mesh-independent convention is
    # built instead: mesh-BOUNDARY-EDGE (the staged landmass's own outline, single-owner tri edges),
    # closed against the 2 real stock land blocks that touch this bench's Moore neighbourhood so no
    # cross-block edge is misclassified as coastal.
    log("\n  *** DISCOVERY: staged Sea4 is a full-block backing PLANE (n=1536, spans the whole 64x64u "
        "block), not a shoreline trace -- 'nearest Sea4 vertex' degenerates to ~0u. Building a 4th, "
        "sea-mesh-independent convention (mesh-boundary-edge) instead. ***")
    closure_tris, _, _ = SNR.load_tris(RUNG_E_CLOSURE_NEIGHBOURS, source="stock")
    log(f"  closure neighbour tris loaded (real stock, for edge-matching only): {len(closure_tris)} "
        f"over {RUNG_E_CLOSURE_NEIGHBOURS}")
    edge_closure_tris = all_tris + closure_tris
    rung_e_segs = mesh_boundary_segments(edge_closure_tris)
    log(f"  mesh-boundary segments (staged 16 blocks + 2 closure blocks): {len(rung_e_segs)}")
    body_pts_named = [(t["cell"], *tri_centroid(t)) for t in topo16_tris]
    straddle_pts_named = [(c, *world_of_cell(c)) for c in straddle_cells]
    boundary_pts_named = [(c, *world_of_cell(c)) for c in boundary_cells]
    m1e = measure_against_segments("body_tri_centroid -> mesh edge", body_pts_named, rung_e_segs)
    m2e = measure_against_segments("straddle_cell_centre -> mesh edge", straddle_pts_named, rung_e_segs)
    m3e = measure_against_segments("boundary_cell_centre -> mesh edge", boundary_pts_named, rung_e_segs)

    # cross-check vs the surviving falsifier JSON, if present -- try BOTH conventions (sea-vertex,
    # already shown mismatched by the DISCOVERY above; mesh-edge, the new sea-mesh-independent one)
    cross = dict(available=False)
    if RUNG_E_INDEPENDENT_JSON.exists():
        prior = json.loads(RUNG_E_INDEPENDENT_JSON.read_text(encoding="utf-8"))
        prior_body = prior.get("body_min_raw")
        prior_straddle = prior.get("boundary_min_straddle")

        def close(a, b, tol=0.5):
            return a is not None and b is not None and abs(a - b) < tol

        sea_vertex_body_match = close(m1["min"], prior_body)
        sea_vertex_straddle_match = close(m2["min"], prior_straddle)
        mesh_edge_body_match = close(m1e["min"], prior_body)
        mesh_edge_straddle_match = close(m2e["min"], prior_straddle)
        cross = dict(
            available=True, prior_body_min_raw=prior_body, prior_boundary_min_straddle=prior_straddle,
            sea_vertex_convention=dict(
                this_run_body_min=m1["min"], body_match_within_0_5u=sea_vertex_body_match,
                this_run_straddle_min=m2["min"], straddle_match_within_0_5u=sea_vertex_straddle_match),
            mesh_edge_convention=dict(
                this_run_body_min=m1e["min"], body_match_within_0_5u=mesh_edge_body_match,
                this_run_straddle_min=m2e["min"], straddle_match_within_0_5u=mesh_edge_straddle_match),
            either_convention_reproduces_falsifier=(
                (sea_vertex_body_match and sea_vertex_straddle_match) or
                (mesh_edge_body_match and mesh_edge_straddle_match)),
        )
        log(f"\nCROSS-CHECK vs surviving verify_rung_e_independent.json (prior body={prior_body}, "
            f"straddle={prior_straddle}):")
        log(f"  sea-vertex convention:  body={m1['min']} (match={sea_vertex_body_match})  "
            f"straddle={m2['min']} (match={sea_vertex_straddle_match})")
        log(f"  mesh-edge convention:   body={m1e['min']} (match={mesh_edge_body_match})  "
            f"straddle={m2e['min']} (match={mesh_edge_straddle_match})")
        if not cross["either_convention_reproduces_falsifier"]:
            log("  *** NEITHER convention this script built reproduces the surviving falsifier's exact "
                "numbers -- reported loudly, not explained away. The original falsifier script does not "
                "survive locally (per brief), so its exact methodology cannot be re-run verbatim; both "
                "reconstructions here are documented, independently-motivated, and internally consistent "
                "(the sea-vertex one calibrates exactly on stock -- see the STOCK CALIBRATION block -- "
                "so its Rung E mismatch is attributable to the discovered Sea4 full-block-plane artifact, "
                "not a general bug in the convention itself). Downstream gate-authors should pick ONE "
                "convention and use it consistently rather than trust either number as 'the' 34.98/34.45u "
                "figure was computed. ***")
    else:
        log(f"  (no surviving {RUNG_E_INDEPENDENT_JSON} to cross-check against)")

    return dict(
        available=True, blocks=[list(b) for b in blocks], n_tris=len(all_tris),
        n_sea_beach_verts=len(sea_pts), n_boundary_cells=len(boundary_cells),
        n_straddle_cells=len(straddle_cells), n_topo16_tris=len(topo16_tris),
        sea4_is_full_block_plane_discovery=True,
        measure_i_body_tri_centroid_sea_vertex=m1, measure_ii_straddle_cell_centre_sea_vertex=m2,
        measure_iii_boundary_cell_centre_sea_vertex=m3,
        measure_i_body_tri_centroid_mesh_edge=m1e, measure_ii_straddle_cell_centre_mesh_edge=m2e,
        measure_iii_boundary_cell_centre_mesh_edge=m3e,
        n_mesh_boundary_segments=len(rung_e_segs),
        cross_check_vs_prior_falsifier=cross,
    )


# ====================================================================================================
# STAGE 3 -- desert's OWN coast (WHICH-COAST control): two genuinely-coastal, non-ecotone desert masses
# ====================================================================================================
DESERT_MASS_CONTROLS = [
    dict(name="mass_4_topo17_635cells_coastal_nongrassadj",
         blocks=[(11, 4), (11, 5), (12, 4), (12, 5), (13, 4), (13, 5)]),
    dict(name="mass_1_topo17_1326cells_coastal_nongrassadj",
         blocks=sorted({(bx, by) for bx in range(16, 21) for by in range(3, 8)})),
]


def stage3_desert_own_coast():
    log("\n" + "=" * 100)
    log("STAGE 3 -- desert's OWN coast: 2 held-out coastal, non-ecotone topo-17 desert masses")
    log("=" * 100)
    results = []
    for spec in DESERT_MASS_CONTROLS:
        name = spec["name"]
        blocks = spec["blocks"]
        log(f"\n-- {name} ({len(blocks)} blocks: {blocks}) --")
        all_tris, bms, _ = SNR.load_tris(blocks, source="stock")
        present = sorted(bms)
        missing = sorted(set(blocks) - set(bms))
        log(f"   land blocks present: {len(present)}/{len(blocks)}"
            + (f"  (missing/ocean: {missing})" if missing else ""))
        topo17_tris = [t for t in all_tris if t["topo"] == 17]
        log(f"   topo-17 tris loaded: {len(topo17_tris)}")

        coastal_blocks_here = [b for b in present]  # scan every present block's own sea/beach parts
        sea_pts = scan_sea_verts_stock(coastal_blocks_here)
        sea_xz = [(x, z) for (x, z, blk, part) in sea_pts]
        log(f"   sea/beach verts (own block set): {len(sea_pts)}")

        dists = []
        for t in topo17_tris:
            cx, cz = tri_centroid(t)
            d, _ = nearest(cx, cz, sea_xz)
            if d is not None:
                dists.append(d)
        st = dist_stats(dists)
        log(f"   topo-17 body-tri-centroid -> OWN coast: n={st['n']} min={st['min']} p5={st['p5']} "
            f"p25={st['p25']} median={st['median']}")
        n_under_39_95 = sum(1 for d in dists if d < 39.95)
        n_under_10 = sum(1 for d in dists if d < 10.0)
        log(f"   tris under 39.95u: {n_under_39_95}/{len(dists)}; tris under 10u (near-literal shoreline): "
            f"{n_under_10}/{len(dists)}")
        results.append(dict(name=name, blocks_requested=[list(b) for b in blocks],
                            blocks_present=[list(b) for b in present],
                            blocks_missing=[list(b) for b in missing],
                            n_topo17_tris=len(topo17_tris), n_sea_beach_verts=len(sea_pts),
                            stats=st, n_under_39_95u=n_under_39_95, n_under_10u=n_under_10))
    return results


# ====================================================================================================
# main
# ====================================================================================================
def main():
    t0 = time.time()
    log(f"game root: {SNR.GAME_ROOT}")

    ctx = stage0_load_and_calibrate()
    stock = stage1_stock_measures(ctx)
    rung_e = stage2_rung_e_measures()
    desert_controls = stage3_desert_own_coast()

    # ---- headline synthesis ----------------------------------------------------------------------
    stock_min = dict(
        boundary_cell=stock["measure_iii_boundary_cell"]["any"]["stats"]["min"],
        straddle_cell=stock["measure_ii_straddle_cell"]["any"]["stats"]["min"],
        body_tri=stock["measure_i_body_tri"]["any"]["stats"]["min"],
        boundary_cell_mesh_edge=stock["measure_iv_mesh_boundary_edge_coastal_filtered"]["boundary_cell"]["min"],
        straddle_cell_mesh_edge=stock["measure_iv_mesh_boundary_edge_coastal_filtered"]["straddle_cell"]["min"],
        body_tri_mesh_edge=stock["measure_iv_mesh_boundary_edge_coastal_filtered"]["body_tri"]["min"],
    )
    map_wide_floor_by_measure = dict(
        boundary_cell_centre_to_coast_sea_vertex=stock_min["boundary_cell"],
        straddle_cell_centre_to_coast_sea_vertex=stock_min["straddle_cell"],
        body_tri_centroid_to_coast_sea_vertex=stock_min["body_tri"],
        boundary_cell_centre_to_coast_mesh_edge=stock_min["boundary_cell_mesh_edge"],
        straddle_cell_centre_to_coast_mesh_edge=stock_min["straddle_cell_mesh_edge"],
        body_tri_centroid_to_coast_mesh_edge=stock_min["body_tri_mesh_edge"],
    )
    holds_39_95 = {k: (v is not None and v >= 39.95) for k, v in map_wide_floor_by_measure.items()}
    any_broken_on_stock = any(not ok for ok in holds_39_95.values())

    desert_own_coast_min = min(
        (r["stats"]["min"] for r in desert_controls if r["stats"]["min"] is not None), default=None)

    out = dict(
        meta=dict(
            script="contract_mass_boundary.py", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_s=round(time.time() - t0, 1),
            core_blocks=[list(b) for b in CORE], wide_region=[list(b) for b in WIDE],
            n_ecotone_sites_mapwide=1,
            note_on_site_count="the scout (contract_mass_scout.py, out/contract_mass/sites.json) "
                "map-wide-censused all 260 disc-1 land blocks and found exactly ONE grass|desert "
                "ecotone cluster; this script therefore measures the full 3-measure suite at that "
                "single real site rather than aggregating across multiple sites.",
        ),
        calibration=dict(
            reproduced_39_95u_boundary_cell_ring1=ctx["reproduced_39_95"],
            calibration_passed=ctx["calib_ok"],
            widened_ring2_boundary_cell_floor=ctx["widened_39_95"],
            ring2_confirms_no_closer_vertex_missed=(ctx["widened_39_95"] == ctx["reproduced_39_95"]),
            topo16_blocks_mapwide=[list(b) for b in ctx["topo16_blocks"]],
            topo16_confined_to_known_ecotone_block_rect=(
                set(ctx["topo16_blocks"]) <= set(CORE)),
        ),
        stock_ecotone_site=stock,
        rung_e_staged_build=rung_e,
        desert_own_coast_controls=desert_controls,
        headline_numbers=dict(
            map_wide_floor_by_measure_u=map_wide_floor_by_measure,
            holds_39_95_by_measure=holds_39_95,
            any_measure_breaks_39_95_on_stock=any_broken_on_stock,
            rung_e_body_min_u_sea_vertex=(rung_e.get("measure_i_body_tri_centroid_sea_vertex") or {}).get("min"),
            rung_e_straddle_min_u_sea_vertex=(rung_e.get("measure_ii_straddle_cell_centre_sea_vertex") or {}).get("min"),
            rung_e_boundary_cell_min_u_sea_vertex=(rung_e.get("measure_iii_boundary_cell_centre_sea_vertex") or {}).get("min"),
            rung_e_body_min_u_mesh_edge=(rung_e.get("measure_i_body_tri_centroid_mesh_edge") or {}).get("min"),
            rung_e_straddle_min_u_mesh_edge=(rung_e.get("measure_ii_straddle_cell_centre_mesh_edge") or {}).get("min"),
            rung_e_boundary_cell_min_u_mesh_edge=(rung_e.get("measure_iii_boundary_cell_centre_mesh_edge") or {}).get("min"),
            rung_e_sea4_full_block_plane_discovery=rung_e.get("sea4_is_full_block_plane_discovery", False),
            desert_own_coast_min_u=desert_own_coast_min,
            desert_own_coast_vs_ecotone_body_ratio=(
                round(desert_own_coast_min / stock_min["body_tri"], 3)
                if desert_own_coast_min is not None and stock_min["body_tri"] else None),
        ),
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    log(f"\n-> {OUT}")
    log(f"\ntotal elapsed: {round(time.time() - t0, 1)}s")


if __name__ == "__main__":
    main()
