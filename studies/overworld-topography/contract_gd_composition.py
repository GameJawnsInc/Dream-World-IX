"""THE GRASS|DESERT COMPOSITION CONTRACT -- read-only census for THE FIRST MIXED-BIOME MINT task
(2026-07-23). Measures how stock composes the map's ONE grass|desert pair (blocks (13-15,11-12),
Round 10/11 of GROUND-FAMILY-DECODE-2026-07-19.md), answering the 5 questions the CONTRACT agent
was asked: TERMINATION, COAST, TOPO BAND, LINE GEOMETRY, and feeding THE VERDICT.

READ-ONLY against the game install: only X.read_block (stock bytes) and X.list_coastal_donors.
ZERO writes, no deploy, no mirror, no config.find_game_path patch (real reads only). Reuses
studies/overworld-topography/seam_null_recon.py's proven load_tris/edge_index/classify_tri/FAM_OF
(identical method to Round 10/11 -- no re-derivation of the vocabulary).

Run:  py studies/overworld-topography/contract_gd_composition.py
Artifact -> out/contract_gd_composition.json
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
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                      # noqa: E402  -- reuse proven machinery, no main()
from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

OUT = HERE / "out" / "contract_gd_composition.json"
CELL = 4.0
CORE = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
# generous margin around the core: 3 blocks N/S/E/W (still << full 24x20 map) to see topo-16->17
# depth and whatever lies past the boundary line's own two ends.
WIDE = sorted({(bx, by) for bx in range(10, 19) for by in range(7, 16) if M.block_in_grid(bx, by)})

# ---- the desert|rock v-band decal (Round 11, verbatim rect) ---------------------------------------
VBAND_V_LO, VBAND_V_HI = 0.83594, 0.86621
VBAND_V_TOL = 0.0015
DESERT_ROCK_U = (0.07129, 0.13184)   # Round 11 table, both raw sub-windows unioned
U_TOL = 0.0020


def tri_uv_bbox(uv3):
    us = [p[0] for p in uv3]
    vs = [p[1] for p in uv3]
    return min(us), min(vs), max(us), max(vs)


def is_desert_rock_vband(uv3):
    u0, v0, u1, v1 = tri_uv_bbox(uv3)
    if not (abs(v0 - VBAND_V_LO) <= VBAND_V_TOL and abs(v1 - VBAND_V_HI) <= VBAND_V_TOL):
        return False
    return (DESERT_ROCK_U[0] - U_TOL <= u0 and u1 <= DESERT_ROCK_U[1] + U_TOL)


def main():
    print(f"game root: {SNR.GAME_ROOT}")
    print(f"loading WIDE region ({len(WIDE)} blocks): {WIDE}")
    all_tris, bms, src_by_block = SNR.load_tris(WIDE, source="stock")
    print(f"blocks actually present (land): {sorted(bms)}  ({len(bms)}/{len(WIDE)})")
    print(f"tris loaded: {len(all_tris)}")

    # ---- cell-level family + topo maps over the WHOLE wide region -----------------------------------
    cell_fams = defaultdict(set)
    cell_topo = defaultdict(Counter)
    cell_tris = defaultdict(list)
    for t in all_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
        cell_topo[t["cell"]][t["topo"]] += 1
        cell_tris[t["cell"]].append(t)

    # ================================================================================================
    # LINE GEOMETRY + TERMINATION -- boundary cells = any cell owning a grass|desert edge, ANYWHERE
    # in the wide region (not restricted to the 6-block core -- lets the line's true extent speak for
    # itself; Round 10 already established this is the map's only such cluster).
    # ================================================================================================
    edge_owner = SNR.edge_index(all_tris)
    gd_edges = []
    for e, owners in edge_owner.items():
        fams = {all_tris[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            gd_edges.append((e, owners))
    print(f"\ngrass|desert boundary edges in the WIDE region: {len(gd_edges)}")

    boundary_cells = set()
    for e, owners in gd_edges:
        for g in owners:
            boundary_cells.add(all_tris[g]["cell"])
    print(f"boundary cells (own >=1 grass|desert edge): {len(boundary_cells)}")

    def world_of(cell):
        return (cell[0] * CELL + CELL / 2, cell[1] * CELL + CELL / 2)

    # 8-connectivity graph over boundary cells (diagonal steps allowed -- the line zigzags)
    adj = defaultdict(set)
    bc_list = sorted(boundary_cells)
    bc_set = set(bc_list)
    for c in bc_list:
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                n = (c[0] + di, c[1] + dj)
                if n in bc_set:
                    adj[c].add(n)

    # connected components
    seen = set()
    components = []
    for c in bc_list:
        if c in seen:
            continue
        comp = []
        q = deque([c])
        seen.add(c)
        while q:
            u = q.popleft()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        components.append(sorted(comp))
    print(f"connected components of the boundary-cell graph: {len(components)} "
          f"(sizes {[len(c) for c in components]})")

    def bfs_farthest(start, nodes_adj):
        dist = {start: 0}
        prev = {start: None}
        q = deque([start])
        far = start
        while q:
            u = q.popleft()
            if dist[u] > dist[far]:
                far = u
            for v in nodes_adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    prev[v] = u
                    q.append(v)
        return far, dist, prev

    def reconstruct(prev, end):
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def path_stats(path):
        pts = [world_of(c) for c in path]
        seglens = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                   for i in range(len(pts) - 1)]
        path_len_world = sum(seglens)
        straight = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        straightness = (straight / path_len_world) if path_len_world > 0 else 1.0
        # turning angles between consecutive segment vectors
        turns = []
        for i in range(1, len(pts) - 1):
            v1 = (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            v2 = (pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            n1, n2 = math.hypot(*v1), math.hypot(*v2)
            if n1 < 1e-9 or n2 < 1e-9:
                continue
            cosang = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
            turns.append(math.degrees(math.acos(cosang)))
        return dict(
            n_cells=len(path), path_len_world=round(path_len_world, 2),
            straight_dist_world=round(straight, 2),
            straightness_ratio=round(straightness, 4),
            turn_deg_mean=round(sum(turns) / len(turns), 1) if turns else None,
            turn_deg_max=round(max(turns), 1) if turns else None,
            n_turns_gt30deg=sum(1 for a in turns if a > 30),
            n_turns_gt60deg=sum(1 for a in turns if a > 60),
        )

    comp_reports = []
    for comp in components:
        comp_adj = {c: adj[c] for c in comp}
        a0, _, _ = bfs_farthest(comp[0], comp_adj)
        b0, dist_from_a, prev_from_a = bfs_farthest(a0, comp_adj)
        path = reconstruct(prev_from_a, b0)
        stats = path_stats(path)
        comp_reports.append(dict(
            endpoints=[list(a0), list(b0)],
            endpoint_world=[list(world_of(a0)), list(world_of(b0))],
            path_cells=[list(c) for c in path],
            **stats,
        ))
        print(f"  component: {len(comp)} cells, endpoints {a0}<->{b0}, "
              f"path {stats['n_cells']} cells / {stats['path_len_world']}u, "
              f"straight {stats['straight_dist_world']}u, straightness {stats['straightness_ratio']}, "
              f"turns>30deg={stats['n_turns_gt30deg']} turns>60deg={stats['n_turns_gt60deg']}")

    # ---- dressing density along the (largest) component's path, in quartiles ------------------------
    def strip_dressed(cell):
        for t in cell_tris.get(cell, []):
            if t["fam"] in ("grass", "desert"):
                cls, detail = SNR.classify_tri(t["fam"], t["uv"])
                if cls == "strip_grass_desert":
                    return True
        return False

    main_comp = max(comp_reports, key=lambda r: r["n_cells"])
    path = [tuple(c) for c in main_comp["path_cells"]]
    n = len(path)
    quartile_density = []
    for qi in range(4):
        lo = (n * qi) // 4
        hi = (n * (qi + 1)) // 4 if qi < 3 else n
        seg = path[lo:hi] or path[lo:lo + 1]
        dressed = sum(1 for c in seg if strip_dressed(c))
        quartile_density.append(dict(quartile=qi, n_cells=len(seg),
                                     n_dressed=dressed,
                                     rate=round(dressed / len(seg), 3) if seg else None))
    print(f"\ndressing density by path quartile (main component): {quartile_density}")

    # ================================================================================================
    # TERMINATION -- for each component endpoint, examine a radius around it
    # ================================================================================================
    RADII = (2, 4, 6, 10)
    termination_reports = []
    for comp_r in comp_reports:
        for ei, ep_cell in enumerate(comp_r["endpoints"]):
            ep_cell = tuple(ep_cell)
            ep_world = world_of(ep_cell)
            per_radius = {}
            for R in RADII:
                fam_tally = Counter()
                topo_tally = Counter()
                nearest_topo49 = None
                for t in all_tris:
                    cx = sum(p[0] for p in t["w"]) / 3.0
                    cz = sum(p[2] for p in t["w"]) / 3.0
                    d = math.hypot(cx - ep_world[0], cz - ep_world[1])
                    if d <= R:
                        fam_tally[t["fam"]] += 1
                        topo_tally[t["topo"]] += 1
                        if t["topo"] == 49:
                            if nearest_topo49 is None or d < nearest_topo49:
                                nearest_topo49 = d
                per_radius[R] = dict(fam_tally=dict(fam_tally), topo_tally=dict(topo_tally),
                                     nearest_topo49_dist=round(nearest_topo49, 2) if nearest_topo49 else None)
            # desert|rock v-band scan within the widest radius
            vband_hits = []
            for t in all_tris:
                cx = sum(p[0] for p in t["w"]) / 3.0
                cz = sum(p[2] for p in t["w"]) / 3.0
                d = math.hypot(cx - ep_world[0], cz - ep_world[1])
                if d <= RADII[-1] and is_desert_rock_vband(t["uv"]):
                    vband_hits.append(dict(block=list(t["block"]), cell=list(t["cell"]),
                                           dist=round(d, 2), topo=t["topo"]))
            termination_reports.append(dict(
                endpoint_cell=list(ep_cell), endpoint_world=list(ep_world),
                per_radius={str(r): v for r, v in per_radius.items()},
                desert_rock_vband_hits_within_10cells=vband_hits,
            ))
            print(f"\nENDPOINT {ep_cell} @ world{ep_world}:")
            for R in RADII:
                pr = per_radius[R]
                print(f"   r<={R}u: fam={pr['fam_tally']} nearest-topo49={pr['nearest_topo49_dist']}")
            print(f"   desert|rock v-band hits within {RADII[-1]}u: {len(vband_hits)}")

    # ================================================================================================
    # TOPO BAND -- for desert-family and grass-family tris in the WIDE region, bucket by min chebyshev
    # cell-distance to the nearest boundary cell, tally topo id per bucket.
    # ================================================================================================
    def cheby_dist_to_boundary(cell):
        return min(max(abs(cell[0] - b[0]), abs(cell[1] - b[1])) for b in bc_list)

    topo_band = defaultdict(lambda: defaultdict(Counter))   # fam -> band -> topo Counter
    for t in all_tris:
        if t["fam"] not in ("grass", "desert"):
            continue
        band = cheby_dist_to_boundary(t["cell"])
        topo_band[t["fam"]][band][t["topo"]] += 1

    print("\nTOPO BAND (cell chebyshev distance from nearest boundary cell -> topo id tally):")
    topo_band_out = {}
    for fam in ("desert", "grass"):
        print(f"  {fam}:")
        fam_out = {}
        for band in sorted(topo_band[fam]):
            tt = dict(sorted(topo_band[fam][band].items()))
            fam_out[str(band)] = tt
            print(f"    band {band}: {tt}")
        topo_band_out[fam] = fam_out

    # explicit topo16-vs-17 crossover depth for desert
    crossover = None
    for band in sorted(topo_band["desert"]):
        tt = topo_band["desert"][band]
        n16, n17 = tt.get(16, 0), tt.get(17, 0)
        if n17 > 0 and crossover is None:
            crossover = band
    print(f"\n  first band where topo-17 appears on the desert side: {crossover}")

    # ================================================================================================
    # COAST -- map-wide: nearest coastal (sea/beach-bearing) block to the 6-block core
    # ================================================================================================
    coastal_blocks = X.list_coastal_donors(disc=1, beach_only=False)
    print(f"\ncoastal blocks map-wide (any sea/beach sub-mesh, beach_only=False): {len(coastal_blocks)}")
    best = None
    for (cbx, cby) in CORE:
        for (sx, sy) in coastal_blocks:
            cheby = max(abs(cbx - sx), abs(cby - sy))
            eucl = math.hypot(cbx - sx, cby - sy)
            if best is None or cheby < best[0]:
                best = (cheby, eucl, (cbx, cby), (sx, sy))
    print(f"nearest coastal block to the 6-block core: {best}")
    coast_out = None
    if best is not None:
        cheby, eucl, core_blk, coast_blk = best
        # a lower-bound world-unit gap: (cheby-1) full blocks of guaranteed non-coastal land between
        # them, i.e. at least (cheby-1)*64u of clearance from the CORE block's own far edge to the
        # NEAREST edge of the coastal block; report both the naive block-center figure and this bound.
        world_gap_lower_bound = max(0, (cheby - 1)) * 64.0
        coast_out = dict(
            nearest_coastal_block=list(coast_blk), nearest_core_block=list(core_blk),
            chebyshev_block_dist=cheby, euclidean_block_dist=round(eucl, 2),
            world_gap_lower_bound_u=world_gap_lower_bound,
            world_center_to_center_u=round(eucl * 64.0, 1),
            n_coastal_blocks_mapwide=len(coastal_blocks),
        )
        print(f"  chebyshev block dist {cheby} -> world gap lower bound >= {world_gap_lower_bound}u "
              f"(center-to-center {round(eucl*64.0,1)}u)")

    # also: is the WIDE region itself (the boundary's whole neighbourhood) touched by ANY coastal
    # block at all, for a sanity cross-check independent of the CORE-only figure above
    wide_set = set(WIDE)
    coastal_in_wide = sorted(set(coastal_blocks) & wide_set)
    print(f"coastal blocks WITHIN the loaded wide region itself: {coastal_in_wide}")

    # ---- PRECISE coast distance: the block-level check above found the core's OWN block (13,11)
    # flagged coastal -- load its real sea/beach sub-mesh geometry (+ the Moore ring's) and measure
    # actual cell-level distance from the FULL boundary-cell set (not just the diameter path) to the
    # nearest real sea/beach vertex, in world units.
    core_ring = sorted({(bx + dx, by + dy) for (bx, by) in CORE for dx in (-1, 0, 1) for dy in (-1, 0, 1)})
    coastal_near_core = [b for b in core_ring if b in coastal_blocks]
    print(f"\ncoastal blocks in the core's own Moore ring: {coastal_near_core}")
    sea_pts = []   # (world_x, world_z, block, part)
    for (bx, by) in coastal_near_core:
        ox, oz = X.block_world_origin(bx, by)
        for part in ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2"):
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except ValueError:
                continue
            for v in bm.verts:
                sea_pts.append((v[0] + ox, v[2] + oz, (bx, by), part))
    print(f"sea/beach verts loaded near core: {len(sea_pts)}")

    best_precise = None
    for c in bc_list:
        wx, wz = world_of(c)
        for (sx, sz, sb, sp) in sea_pts:
            d = math.hypot(wx - sx, wz - sz)
            if best_precise is None or d < best_precise[0]:
                best_precise = (d, c, (round(sx, 2), round(sz, 2)), sb, sp)
    if best_precise:
        print(f"NEAREST real sea/beach vertex to ANY grass|desert boundary cell: "
              f"{best_precise[0]:.2f}u  (boundary cell {best_precise[1]} -> {sea_pts and best_precise[2]} "
              f"in block {best_precise[3]} part {best_precise[4]})")
    precise_coast_out = None
    if best_precise:
        precise_coast_out = dict(
            dist_u=round(best_precise[0], 2), boundary_cell=list(best_precise[1]),
            nearest_sea_vertex_world=list(best_precise[2]),
            nearest_sea_block=list(best_precise[3]), nearest_sea_part=best_precise[4],
            n_sea_beach_verts_scanned=len(sea_pts),
            coastal_blocks_scanned=[list(b) for b in coastal_near_core],
        )

    out = dict(
        meta=dict(core_blocks=[list(b) for b in CORE], wide_region=[list(b) for b in WIDE],
                  wide_region_land_blocks=[list(b) for b in sorted(bms)],
                  n_tris_loaded=len(all_tris)),
        line_geometry=dict(
            n_gd_boundary_edges=len(gd_edges), n_boundary_cells=len(boundary_cells),
            all_boundary_cells=[list(c) for c in bc_list],
            n_components=len(components), components=comp_reports,
            dressing_density_by_quartile_main_component=quartile_density,
        ),
        termination=termination_reports,
        topo_band=dict(by_family=topo_band_out,
                       desert_topo16_to_17_crossover_band=crossover),
        coast=dict(core_to_nearest_coastal_block=coast_out,
                  coastal_blocks_within_loaded_wide_region=[list(b) for b in coastal_in_wide],
                  precise_boundary_cell_to_sea_vertex=precise_coast_out),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
