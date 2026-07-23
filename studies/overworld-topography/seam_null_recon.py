"""SEAM+NULL RECON -- BRIEF agent B, bytes-only pass feeding the SEAM-DRESSING arc (2026-07-22).

READ-ONLY against the game install: reads stock bundles (X.read_block) + the live deployed
FF9CustomMap-world override files (M.blockmesh_from_ff9mesh). ZERO writes, no deploy, no mirror.

Two independent censuses, same method as Round 10 / comp1_orphan_redress.py (classify every ground
tri as grass-mains / desert-mains / STRIPS(grass,desert) row-k, via the shipped grassland.STRIPS
translation, generalized cross-block per combining_census_slice2.py's edge-index method):

PART A -- the (7,19)/(8,19) SEAM, from LIVE deployed bytes: family line, straddle cells (mixed
  family in one 4u cell), depth-1 fringe cells each side, current tile wear (mains vs strip-dressed),
  eligibility under Law 4 (modal 1-cell band width).

PART B -- THE TRANSPLANT NULL, from STOCK bytes at the real grass|desert cluster (13-15,11-12) (all
  6 core blocks + their orthogonal ring for cross-block-aware edges): row frequency table, the
  straddle row1:row3 ratio, per-family depth-1(+other-band) coverage rates, and ori usage (the
  quad/orientation grammar recovered per boundary-band cell via the ground_families_anatomy.py
  brute-force 4-quad x 4-ori exact-match method).

Run:  py studies/overworld-topography/seam_null_recon.py
Artifact -> out/seam_null_recon.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))

from ff9mapkit import config as CFG              # noqa: E402
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import grassland as G        # noqa: E402
from ff9mapkit.world import mesh as M             # noqa: E402

BLOCK = 64.0
CELL = 4.0
MOD = "FF9CustomMap-world"
OUT = HERE / "out" / "seam_null_recon.json"

GAME_ROOT = CFG.find_game_path()          # READ-ONLY use only (blockmesh_from_ff9mesh / read_block)

# ---- family table (verbatim from combining_census_slice2.py / grassland.TOPO_FAMILY) ------------
FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (16, 17, 19, 20):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
FAM_OF[45] = FAM_OF[46] = "canyon"
FAM_OF[58] = "rock"
FAM_OF[59] = "hole"

EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125


def mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {fam: mains_rect(fam) for fam in ("grass", "desert", "dunes", "scrub", "brush", "snow", "canyon")}

GD_PAIR = ("grass", "desert")
_S = G.STRIPS[GD_PAIR]
GD_DU, GD_DV = _S["du"], _S["dv"]
STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]

DD_PAIR = ("desert", "dunes")
_S2 = G.STRIPS[DD_PAIR]
DD_DU, DD_DV = _S2["du"], _S2["dv"]


def in_rect(uv3, rect, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip_pair(uv3, du, dv):
    u_lo, u_hi = STRIP_U0 + du - EPS, STRIP_U1 + du + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    row0 = ROW0_V0 + dv
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3 or abs((v_min - row0) - k * ROW_PITCH) > TOL_V:
        return None
    return int(k)


def classify_tri(fam, uv3):
    """(class, detail) -- 'strip_grass_desert'/k, 'mains_own'/fam, 'mains_foreign'/ofam,
    'strip_desert_dunes'/k, or 'other'/None. Verbatim method from combining_census_slice2.py,
    minus the raw/uncatalogued-rect fallbacks (not needed for grass/desert/dunes-only regions)."""
    k = classify_strip_pair(uv3, GD_DU, GD_DV)
    if k is not None:
        return ("strip_grass_desert", k)
    rect = RECTS.get(fam)
    if rect and in_rect(uv3, rect):
        return ("mains_own", fam)
    for ofam, orect in RECTS.items():
        if ofam != fam and in_rect(uv3, orect):
            return ("mains_foreign", ofam)
    k2 = classify_strip_pair(uv3, DD_DU, DD_DV)
    if k2 is not None:
        return ("strip_desert_dunes", k2)
    return ("other", None)


def rot_ab(fx, fz, ori):
    return G.rot_ab(fx, fz, ori)


def infer_quad_ori(fam, cell, corners):
    """Brute-force 4-quad x 4-ori exact match (ground_families_anatomy.py's grammar-gate method) for
    a set of (world_x, world_z, u, v) corners known to belong to ONE mains-classified cell of family
    `fam`. Returns (quad, ori) or None if no exact hit (bleed-clamped boundary tris can miss)."""
    (i, j) = cell
    g = G.GROUNDS[fam]
    QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
    for quad in QUADS:
        for ori in G.ORIS:
            err = 0.0
            for (wx, wz, u, v) in corners:
                mu, mv = G.ground_uv(wx, wz, cell, quad, ori, fam)
                err = max(err, abs(mu - u), abs(mv - v))
                if err >= 1e-4:
                    break
            if err < 1e-4:
                return (quad, ori)
    return None


def kk(p):
    return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


# ====================================================================================================
# shared: build a global tri list + cross-block edge index over an arbitrary block set
# ====================================================================================================
def load_tris(blocks, *, source: str, must_have=()):
    """source='stock' (X.read_block) or 'deployed' (M.blockmesh_from_ff9mesh off the live MOD
    override where one is deployed, else falls back to real stock Disc-1 bytes -- exactly
    comp1_orphan_redress._region_blockmeshes's own read discipline: only the 9-block/5-block
    *core* of a mod-touched region is guaranteed an override; its 1-block ring is mostly
    un-modded stock). `must_have` names blocks that MUST carry a deployed override (raises loudly
    if one of those specifically is missing -- never silently substitutes stock for a block this
    recon is actually trying to read as 'currently deployed')."""
    bm_by_block = {}
    src_by_block = {}
    for (bx, by) in blocks:
        if source == "stock":
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                continue
            src = "stock"
        elif source == "deployed":
            rel = M.override_relpath(1, bx, by, part="Terrain")
            path = GAME_ROOT / MOD / rel
            if path.exists():
                bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
                src = "mod"
            elif (bx, by) in must_have:
                raise FileNotFoundError(f"expected deployed override missing: {path}")
            else:
                try:
                    bm = X.read_block(bx, by, disc=1, part="terrain")
                except (ValueError, FileNotFoundError):
                    continue
                src = "stock"
        else:
            raise ValueError(source)
        bm_by_block[(bx, by)] = bm
        src_by_block[(bx, by)] = src

    tris = []
    for (bx, by), bm in bm_by_block.items():
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            idall0 = int(round(bm.tangents[tri[0]][0]))
            fam = FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            tris.append(dict(block=(bx, by), topo=topo, idall=idall0, fam=fam, w=w, uv=uv, cell=cell))
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris, bm_by_block, src_by_block


def edge_index(all_tris):
    edge_owner = defaultdict(list)
    for t in all_tris:
        ks = [kk(p) for p in t["w"]]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                edge_owner[e].append(t["gid"])
    return edge_owner


def cell_distance_bfs(all_cells, boundary_cells):
    dist = {c: 0 for c in boundary_cells if c in all_cells}
    q = deque(dist)
    while q:
        c = q.popleft()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n in all_cells and n not in dist:
                dist[n] = dist[c] + 1
                q.append(n)
    return dist


# ====================================================================================================
# PART A -- the (7,19)/(8,19) seam, LIVE deployed bytes
# ====================================================================================================
def part_a():
    print("=" * 100)
    print("PART A -- the (7,19)/(8,19) seam, LIVE deployed FF9CustomMap-world bytes")
    print("=" * 100)
    core = [(7, 19), (8, 19)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if M.block_in_grid(bx + dx, by + dy)})
    all_tris, bms, src_by_block = load_tris(ring, source="deployed", must_have=set(core))
    print(f"blocks loaded (core {core} + Moore ring): "
          f"{[(b, src_by_block[b]) for b in sorted(bms)]}")

    override_files = {}
    for (bx, by) in core:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        override_files[f"{bx},{by}"] = str((GAME_ROOT / MOD / rel))
    print(f"override files:\n  " + "\n  ".join(f"{k} -> {v}" for k, v in override_files.items()))

    # per-block family census (confirm the prompt's "pure grass"/"pure desert" framing on LIVE bytes)
    per_block_fam = defaultdict(Counter)
    for t in all_tris:
        per_block_fam[t["block"]][t["fam"]] += 1
    print("\nper-block family tri census (Moore ring):")
    for blk in sorted(per_block_fam):
        print(f"   {blk}: {dict(per_block_fam[blk])}")

    edge_owner = edge_index(all_tris)
    gd_edges = []
    for e, owners in edge_owner.items():
        fams = {all_tris[g]["fam"] for g in owners}
        if fams != {"grass", "desert"}:
            continue
        blocks_here = {all_tris[g]["block"] for g in owners}
        if not (blocks_here & set(core)):
            continue
        gd_edges.append((e, owners))
    print(f"\ngrass|desert boundary edges touching {core}: {len(gd_edges)}")

    # cell family membership (straddle detection) over the two core blocks only
    core_tris = [t for t in all_tris if t["block"] in core]
    cell_fams = defaultdict(set)
    cell_hits = defaultdict(list)
    for t in core_tris:
        if t["fam"] in ("grass", "desert"):
            cell_fams[t["cell"]].add(t["fam"])
            cell_hits[t["cell"]].append(t)
    straddle_cells = sorted(c for c, fams in cell_fams.items() if fams == {"grass", "desert"})
    print(f"\nSTRADDLE cells (one grass tri + one desert tri, same 4u cell) inside {core}: "
          f"{len(straddle_cells)} -- {straddle_cells}")

    # ---- GROUND-TRUTH GEOMETRY CHECK -- do these two landmasses even touch? The prompt/sweep-JSON
    # label calls them "directly adjacent" on block-grid adjacency alone; verify against the actual
    # mesh CONTENT footprint (both blocks are far smaller than their 64u block -- an island each,
    # ringed by its own rock/cliff wall), not merely "same/neighbouring block coordinate".
    foot = defaultdict(set)
    for t in core_tris:
        foot[t["block"]].add(t["cell"])
    foot7, foot8 = foot.get((7, 19), set()), foot.get((8, 19), set())
    any_family_adjacent = any((c[0] + dx, c[1] + dy) in foot8
                              for c in foot7 for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    g_cells = sorted(c for c, f in cell_fams.items() if "grass" in f and c in foot7)
    d_cells = sorted(c for c, f in cell_fams.items() if "desert" in f and c in foot8)
    nearest = None
    for gc in g_cells:
        for dc in d_cells:
            dist_cells = math.hypot(gc[0] - dc[0], gc[1] - dc[1])
            if nearest is None or dist_cells < nearest[0]:
                nearest = (dist_cells, gc, dc)
    gap_world_units = nearest[0] * CELL if nearest else None
    print(f"\nGROUND-TRUTH GEOMETRY: block(7,19) mesh footprint {len(foot7)} cells "
          f"(x[{min(c[0] for c in foot7)*4},{(max(c[0] for c in foot7)+1)*4}] "
          f"z[{min(c[1] for c in foot7)*4},{(max(c[1] for c in foot7)+1)*4}]); "
          f"block(8,19) mesh footprint {len(foot8)} cells "
          f"(x[{min(c[0] for c in foot8)*4},{(max(c[0] for c in foot8)+1)*4}] "
          f"z[{min(c[1] for c in foot8)*4},{(max(c[1] for c in foot8)+1)*4}])")
    print(f"any block(7,19)-cell orthogonally adjacent to any block(8,19)-cell, ANY family: "
          f"{any_family_adjacent}")
    print(f"nearest grass-cell(block7)<->desert-cell(block8) pair: {nearest} "
          f"-> {gap_world_units}u gap (0 = touching)")
    if not any_family_adjacent:
        print("  *** CORRECTION to the brief's framing: these are NOT a touching seam. Each is an "
              "independent island (its own rock/cliff coastal ring) separated by open water. "
              "\"directly adjacent\" in the sweep JSON's label is BLOCK-grid adjacency (block 7 is "
              "immediately west of block 8), not mesh-content adjacency. There is no straddle cell, "
              "no depth-1 fringe cell, and NOTHING eligible for STRIPS(grass,desert) dressing under "
              "Round 10's Laws 2/3/6 (all require genuine same-cell or near-cell family adjacency) "
              "-- because there is no lawful donor context here at all. ***")

    # boundary cells = cells owning a grass|desert edge, restricted to core blocks
    boundary_cells = {all_tris[g]["cell"] for e, owners in gd_edges for g in owners
                      if all_tris[g]["block"] in core}
    print(f"boundary cells (core, touching a grass|desert edge): {len(boundary_cells)} -- "
          f"{sorted(boundary_cells)}")

    all_cells = set(cell_fams)
    dist = cell_distance_bfs(all_cells, boundary_cells)
    band = defaultdict(lambda: defaultdict(Counter))     # dist -> fam -> classify Counter
    for t in core_tris:
        dd = dist.get(t["cell"])
        if dd is None:
            continue
        cls, detail = classify_tri(t["fam"], t["uv"])
        band[dd][t["fam"]][f"{cls}:{detail}" if detail is not None else cls] += 1
    print("\nband profile (cell-distance-from-boundary, SPLIT BY FAMILY -> classify tally):")
    for dd in sorted(band):
        for fam in sorted(band[dd]):
            print(f"   d={dd} fam={fam}: {dict(band[dd][fam])}")

    # NOTE terminology reconciliation (matches combining_census_slice2.py / Round 10 exactly): the
    # census's own BFS seeds distance=0 AT the cells that already touch a mixed-family edge -- that
    # IS "the fringe band, 1 cell wide" the doc calls "depth 1" in prose (a cell COUNT, "the boundary
    # line's own row of cells", not a further BFS hop away from it). depth1 below == dist==0.
    depth1 = defaultdict(list)   # fam -> [cell, ...] at BFS distance 0 (the fringe/boundary band)
    for c, dd in dist.items():
        if dd == 0:
            fams_here = cell_fams[c]
            for f in fams_here:
                depth1[f].append(c)
    print(f"\ndepth-1 (BFS d=0) fringe cells: grass={sorted(depth1.get('grass', []))} "
          f"desert={sorted(depth1.get('desert', []))}")

    # current tile wear: for EVERY core tri, is it plain mains or already strip-dressed?
    wear = Counter()
    dressed_cells = set()
    for t in core_tris:
        cls, detail = classify_tri(t["fam"], t["uv"])
        wear[f"{t['fam']}:{cls}"] += 1
        if cls == "strip_grass_desert":
            dressed_cells.add(t["cell"])
    print(f"\ncurrent tile-wear tally (core, both blocks): {dict(wear)}")
    print(f"cells currently wearing ANY STRIPS(grass,desert) decal: {sorted(dressed_cells)} "
          f"(expected per the prompt: ZERO)")

    # eligibility under the band-width law (Law 4 -- modal 1-cell): straddle cells (dist 0, mixed) +
    # pure-family dist-0 fringe cells (single family, still touching the line) are eligible; d>=1
    # (a further BFS hop past the boundary-touching row) is out-of-band under the modal law.
    eligible_straddle = straddle_cells
    eligible_fringe = sorted((set(depth1.get("grass", [])) | set(depth1.get("desert", []))) - set(straddle_cells))
    print(f"\nELIGIBLE under Law 4 (modal 1-cell band): {len(eligible_straddle)} straddle cell(s) + "
          f"{len(eligible_fringe)} pure-fringe (dist-0, single-family) cell(s) = "
          f"{len(eligible_straddle) + len(eligible_fringe)} total eligible cells, currently 0 dressed")

    out = dict(
        core_blocks=[list(b) for b in core], ring_blocks=[list(b) for b in ring],
        ring_block_source={f"{k[0]},{k[1]}": v for k, v in src_by_block.items()},
        override_files=override_files,
        per_block_fam_census={f"{k[0]},{k[1]}": dict(v) for k, v in per_block_fam.items()},
        n_gd_boundary_edges=len(gd_edges),
        straddle_cells=[list(c) for c in straddle_cells],
        boundary_cells=[list(c) for c in sorted(boundary_cells)],
        band_profile_by_family={f"{dd}|{fam}": dict(c) for dd, byfam in sorted(band.items())
                                for fam, c in byfam.items()},
        depth1_fringe_grass=[list(c) for c in sorted(depth1.get("grass", []))],
        depth1_fringe_desert=[list(c) for c in sorted(depth1.get("desert", []))],
        current_wear_tally=dict(wear),
        cells_currently_dressed=[list(c) for c in sorted(dressed_cells)],
        eligible_straddle_cells=[list(c) for c in eligible_straddle],
        eligible_depth1_fringe_cells=[list(c) for c in eligible_fringe],
        n_eligible_total=len(eligible_straddle) + len(eligible_fringe),
        ground_truth_geometry=dict(
            block7_footprint_cells=len(foot7), block8_footprint_cells=len(foot8),
            block7_world_x=[min(c[0] for c in foot7) * 4, (max(c[0] for c in foot7) + 1) * 4],
            block7_world_z=[min(c[1] for c in foot7) * 4, (max(c[1] for c in foot7) + 1) * 4],
            block8_world_x=[min(c[0] for c in foot8) * 4, (max(c[0] for c in foot8) + 1) * 4],
            block8_world_z=[min(c[1] for c in foot8) * 4, (max(c[1] for c in foot8) + 1) * 4],
            any_family_cell_adjacency=any_family_adjacent,
            nearest_grass_desert_cell_pair=None if nearest is None else
                dict(dist_cells=round(nearest[0], 3), grass_cell=list(nearest[1]), desert_cell=list(nearest[2])),
            gap_world_units=None if gap_world_units is None else round(gap_world_units, 2),
        ),
    )
    return out


# ====================================================================================================
# PART B -- THE TRANSPLANT NULL: stock (13-15,11-12) cluster
# ====================================================================================================
def part_b():
    print("\n" + "=" * 100)
    print("PART B -- THE TRANSPLANT NULL, STOCK bytes at the real grass|desert cluster (13-15,11-12)")
    print("=" * 100)
    core = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if M.block_in_grid(bx + dx, by + dy)})
    all_tris, bms, src_by_block = load_tris(ring, source="stock")
    print(f"blocks loaded (core {core} + Moore ring): {sorted(bms)}")

    per_block_fam = defaultdict(Counter)
    for t in all_tris:
        per_block_fam[t["block"]][t["fam"]] += 1
    print("\nper-block family tri census:")
    for blk in sorted(per_block_fam):
        print(f"   {blk}: {dict(per_block_fam[blk])}")

    edge_owner = edge_index(all_tris)
    gd_edges = []
    for e, owners in edge_owner.items():
        fams = {all_tris[g]["fam"] for g in owners}
        if fams != {"grass", "desert"}:
            continue
        blocks_here = {all_tris[g]["block"] for g in owners}
        if not (blocks_here & set(core)):
            continue
        gd_edges.append((e, owners))
    print(f"\ngrass|desert boundary edges touching the 6-block core: {len(gd_edges)}")

    core_tris = [t for t in all_tris if t["block"] in core]
    cell_fams = defaultdict(set)
    for t in core_tris:
        if t["fam"] in ("grass", "desert"):
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = sorted(c for c, fams in cell_fams.items() if fams == {"grass", "desert"})
    print(f"\nSTRADDLE cells: {len(straddle_cells)}")

    boundary_cells = {all_tris[g]["cell"] for e, owners in gd_edges for g in owners
                      if all_tris[g]["block"] in core}
    all_cells = set(cell_fams)
    dist = cell_distance_bfs(all_cells, boundary_cells)

    # classify every core grass/desert tri
    classified = []
    for t in core_tris:
        if t["fam"] not in ("grass", "desert"):
            continue
        cls, detail = classify_tri(t["fam"], t["uv"])
        dd = dist.get(t["cell"])
        classified.append(dict(t=t, cls=cls, detail=detail, dist=dd))

    # ---- row frequency table (ALL strip_grass_desert tris, both sides, by row) --------------------
    row_freq = Counter(c["detail"] for c in classified if c["cls"] == "strip_grass_desert")
    print(f"\nROW FREQUENCY (all STRIPS(grass,desert) tris, both sides, this cluster): "
          f"{dict(sorted(row_freq.items()))}")

    row_freq_by_fam = defaultdict(Counter)
    for c in classified:
        if c["cls"] == "strip_grass_desert":
            row_freq_by_fam[c["t"]["fam"]][c["detail"]] += 1
    row_freq_by_fam_disp = {fam: dict(sorted(v.items())) for fam, v in row_freq_by_fam.items()}
    print(f"row frequency SPLIT BY FAMILY-SIDE: {row_freq_by_fam_disp}")

    # ---- straddle row1:row3 ratio (Law 2) -- read the row at each GENUINE straddle cell -----------
    straddle_row_tri = Counter()   # cell -> not needed; tally rows across straddle cells' tris
    straddle_rows = []
    straddle_row_disagreements = []
    for c in straddle_cells:
        tris_here = [ct for ct in classified if ct["t"]["cell"] == c]
        rows_here = [ct["detail"] for ct in tris_here if ct["cls"] == "strip_grass_desert"]
        if not rows_here:
            continue
        if len(set(rows_here)) > 1:
            straddle_row_disagreements.append((c, rows_here))
        straddle_rows.append(rows_here[0])
    row1_n = straddle_rows.count(1)
    row3_n = straddle_rows.count(3)
    row0_n = straddle_rows.count(0)
    row2_n = straddle_rows.count(2)
    ratio = (row1_n / row3_n) if row3_n else float("inf")
    print(f"\nSTRADDLE rows observed at {len(straddle_rows)}/{len(straddle_cells)} straddle cells "
          f"(the rest classify 'other'/mains, a triangulation-diagonal tolerance gap): "
          f"row0={row0_n} row1={row1_n} row2={row2_n} row3={row3_n}")
    print(f"STRADDLE row1:row3 ratio = {row1_n}:{row3_n} ({ratio:.3f})")
    if straddle_row_disagreements:
        print(f"  ({len(straddle_row_disagreements)} straddle cells show a within-cell row DISAGREEMENT "
              f"between the 2 tris -- Law 2's 'bit-identical UV bbox' clause, flagged not silently averaged)")

    # ---- per-family depth-1 (fringe) coverage rate ----------------------------------------------
    # NOTE terminology (matches combining_census_slice2.py / Round 10 exactly, same reconciliation
    # as part_a): the census's own BFS seeds distance=0 AT the cells that already touch a mixed-
    # family edge -- that IS the doc's prose "depth 1" / "1-cell fringe band" (a cell-count, not a
    # further BFS hop past the line). dist==0 here includes BOTH straddle cells (mixed) and pure
    # single-family cells that share an edge with the opposite family -- exactly Law 3's "fringe-row"
    # population. d>=1 is reported below too, for the modal-vs-ceiling comparison Law 4 makes.
    coverage = {}
    for fam in ("grass", "desert"):
        d1 = [c for c in classified if c["t"]["fam"] == fam and c["dist"] == 0]
        n_dressed = sum(1 for c in d1 if c["cls"] == "strip_grass_desert")
        n_total = len(d1)
        coverage[fam] = dict(n_dressed=n_dressed, n_total=n_total,
                             rate=round(n_dressed / n_total, 4) if n_total else None)
    print(f"\nPER-FAMILY DEPTH-1 (BFS d=0, fringe-band) dressing coverage: {coverage}")

    # also report the d>=1 bands for completeness (Law 4's ceiling context -- these should read ~0,
    band_family_summary = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # dist -> fam -> [dressed, total]
    for c in classified:
        dd = c["dist"]
        if dd is None:
            continue
        fam = c["t"]["fam"]
        band_family_summary[dd][fam][1] += 1
        if c["cls"] == "strip_grass_desert":
            band_family_summary[dd][fam][0] += 1
    band_summary_out = {}
    print("\nFULL band-x-family coverage table (dressed/total):")
    for dd in sorted(band_family_summary):
        for fam in sorted(band_family_summary[dd]):
            dressed, total = band_family_summary[dd][fam]
            band_summary_out[f"{dd}|{fam}"] = dict(dressed=dressed, total=total,
                                                    rate=round(dressed / total, 4) if total else None)
            print(f"   d={dd} fam={fam}: {dressed}/{total} = "
                  f"{dressed / total:.1%}" if total else f"   d={dd} fam={fam}: n=0")

    # ---- ori usage: brute-force quad/ori recovery on every MAINS-classified boundary-band tri -----
    ori_tally = Counter()
    quad_tally = Counter()
    n_ori_hit = n_ori_miss = 0
    for c in classified:
        if c["cls"] != "mains_own" or c["dist"] is None or c["dist"] > 2:
            continue
        t = c["t"]
        corners = [(t["w"][k][0], t["w"][k][2], t["uv"][k][0], t["uv"][k][1]) for k in range(3)]
        hit = infer_quad_ori(t["fam"], t["cell"], corners)
        if hit is None:
            n_ori_miss += 1
            continue
        quad, ori = hit
        n_ori_hit += 1
        ori_tally[ori] += 1
        quad_tally[str(quad)] += 1
    print(f"\nORI USAGE (mains-classified tris within 2 cells of the boundary, exact 4x4 brute-force "
          f"match): {n_ori_hit} hit / {n_ori_miss} miss (bleed-clamped edge tris can miss)")
    print(f"  ori tally: {dict(sorted(ori_tally.items()))}")
    print(f"  quadrant tally: {dict(quad_tally)}")

    out = dict(
        core_blocks=[list(b) for b in core], ring_blocks=[list(b) for b in ring],
        per_block_fam_census={f"{k[0]},{k[1]}": dict(v) for k, v in per_block_fam.items()},
        n_gd_boundary_edges=len(gd_edges),
        n_straddle_cells=len(straddle_cells), straddle_cells=[list(c) for c in straddle_cells],
        row_frequency_all=dict(sorted(row_freq.items())),
        row_frequency_by_family={fam: dict(sorted(v.items())) for fam, v in row_freq_by_fam.items()},
        straddle_row_tally=dict(row0=row0_n, row1=row1_n, row2=row2_n, row3=row3_n),
        straddle_row1_row3_ratio=None if row3_n == 0 else round(ratio, 4),
        straddle_row_disagreements=[[list(c), rows] for c, rows in straddle_row_disagreements],
        n_straddle_cells_with_row_read=len(straddle_rows),
        per_family_depth1_coverage=coverage,
        band_family_coverage_table=band_summary_out,
        ori_usage=dict(n_hit=n_ori_hit, n_miss=n_ori_miss, ori_tally=dict(sorted(ori_tally.items())),
                       quad_tally=dict(quad_tally)),
    )
    return out


def main():
    print(f"game root: {GAME_ROOT}")
    a = part_a()
    b = part_b()
    out = dict(part_a_seam=a, part_b_transplant_null=b)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
