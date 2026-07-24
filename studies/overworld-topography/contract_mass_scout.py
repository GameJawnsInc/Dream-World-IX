"""THE MASS-ANATOMY CONTRACT round -- THE SCOUT (2026-07-23).

Mandated by the Rung E rejection (GROUND-FAMILY-DECODE-2026-07-19.md, "## Rung E -- the 2-LOBE
composition", section "THE RIBBON FALLACY"): rungs C/D/E all built the grass|desert composition as a
thin RIBBON along a line; the render read says stock's real ecotone is the MARGIN of a much larger
solid DESERT MASS. Before any Rung F build, a CONTRACT round must measure stock's real mass anatomy.
This script is THE SCOUT -- it produces the canonical site census + methodology/detector pins the
three downstream measurement lanes (realized-boundary floor / saturation+spine ceiling / interior
anatomy) will share, so each lane classifies tris identically and nobody re-derives the vocabulary.

READ-ONLY against the game install: only X.read_block (stock disc-1 bytes) via seam_null_recon.py's
already-proven X.list_blocks / SNR.load_tris / SNR.edge_index / SNR.classify_tri (imported, not
reimplemented -- CALIBRATE-THE-INSTRUMENT-BEFORE-YOU-JUDGE-WITH-IT: this script's OWN family/topo
classifier is byte-identical to the one contract_gd_composition.py already used to derive the 39.95u
figure this round is charged with re-testing). ZERO writes, no deploy, no mirror, no --apply. Only
new files this round may write: contract_mass_*.py (this file + any it spawns) and
out/contract_mass/*.

Run:  py studies/overworld-topography/contract_mass_scout.py
Artifact -> out/contract_mass/sites.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                       # noqa: E402 -- the proven FAM_OF/classify_tri/edge_index/load_tris
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import grassland as G           # noqa: E402

OUT_DIR = HERE / "out" / "contract_mass"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "sites.json"

CELL = 4.0
BLOCK = 64.0
KNOWN_SITE_BLOCKS = {(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)}
FRINGE_RADIUS_CHEBY = 2       # Round-10/11 Law 4's own fringe radius (cell chebyshev)
SITE_MERGE_CHEBY = 2          # dilate-and-merge radius for clustering straddle+fringe into ONE site


def world_of(cell):
    return (cell[0] * CELL + CELL / 2, cell[1] * CELL + CELL / 2)


def cheby(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def connected_components(node_set, radius):
    """8-or-wider connectivity (chebyshev <= radius) BFS components over an arbitrary cell set.
    O(n * local-window) via a bucket grid, not O(n^2) -- node_set can be tens of thousands of cells."""
    nodes = sorted(node_set)
    buckets = defaultdict(list)
    bw = max(1, radius)
    for c in nodes:
        buckets[(c[0] // bw, c[1] // bw)].append(c)
    seen = set()
    comps = []
    node_set_local = set(node_set)
    for start in nodes:
        if start in seen:
            continue
        comp = []
        q = deque([start])
        seen.add(start)
        while q:
            u = q.popleft()
            comp.append(u)
            bx, by = u[0] // bw, u[1] // bw
            for dbx in (-1, 0, 1):
                for dby in (-1, 0, 1):
                    for v in buckets.get((bx + dbx, by + dby), ()):
                        if v not in seen and cheby(u, v) <= radius:
                            seen.add(v)
                            q.append(v)
        comps.append(sorted(comp))
    return comps


def block_rect_of_cells(cells, cell_block):
    blocks = {cell_block[c] for c in cells if c in cell_block}
    if not blocks:
        return None
    bxs = [b[0] for b in blocks]
    bys = [b[1] for b in blocks]
    return dict(bx_lo=min(bxs), bx_hi=max(bxs), by_lo=min(bys), by_hi=max(bys),
                n_blocks=len(blocks), blocks=sorted(list(b) for b in blocks))


def main():
    t0 = time.time()
    print(f"game root: {SNR.GAME_ROOT}")
    land_blocks = X.list_blocks(disc=1)
    print(f"land blocks map-wide (disc 1): {len(land_blocks)}")

    all_tris, bms, src_by_block = SNR.load_tris(land_blocks, source="stock")
    print(f"tris loaded map-wide: {len(all_tris)}  ({time.time()-t0:.1f}s)")

    # ---- per-cell aggregates -------------------------------------------------------------------
    cell_fams = defaultdict(set)
    cell_topo = defaultdict(Counter)
    cell_tris = defaultdict(list)
    cell_block = {}
    for t in all_tris:
        c = t["cell"]
        if t["fam"]:
            cell_fams[c].add(t["fam"])
        cell_topo[c][t["topo"]] += 1
        cell_tris[c].append(t)
        cell_block[c] = t["block"]
    print(f"populated cells: {len(cell_tris)}  ({time.time()-t0:.1f}s)")

    # ================================================================================================
    # (a) ECOTONE SITES -- grass|desert straddle + fringe-decal clusters
    # ================================================================================================
    edge_owner = SNR.edge_index(all_tris)
    gd_edges = [(e, owners) for e, owners in edge_owner.items()
                if {all_tris[g]["fam"] for g in owners} == {"grass", "desert"}]
    boundary_cells = set()
    for e, owners in gd_edges:
        for g in owners:
            boundary_cells.add(all_tris[g]["cell"])
    print(f"\ngrass|desert boundary (straddle) edges map-wide: {len(gd_edges)}, "
          f"boundary cells: {len(boundary_cells)}")

    def has_gd_strip(cell):
        for t in cell_tris.get(cell, []):
            if t["fam"] in ("grass", "desert"):
                cls, _detail = SNR.classify_tri(t["fam"], t["uv"])
                if cls == "strip_grass_desert":
                    return True
        return False

    decal_cells = {c for c in cell_tris if has_gd_strip(c)}
    print(f"grass|desert STRIPS-decal cells map-wide: {len(decal_cells)}")

    seed_cells = boundary_cells | decal_cells
    fringe_cells = set()
    # bucket-index seed_cells once for a fast radius query (same trick as connected_components)
    seed_buckets = defaultdict(list)
    bw = max(1, FRINGE_RADIUS_CHEBY)
    for c in seed_cells:
        seed_buckets[(c[0] // bw, c[1] // bw)].append(c)
    for c, fams in cell_fams.items():
        if len(fams & {"grass", "desert"}) != 1 or c in seed_cells:
            continue
        bx, by = c[0] // bw, c[1] // bw
        near = False
        for dbx in (-1, 0, 1):
            for dby in (-1, 0, 1):
                for s in seed_buckets.get((bx + dbx, by + dby), ()):
                    if cheby(c, s) <= FRINGE_RADIUS_CHEBY:
                        near = True
                        break
                if near:
                    break
            if near:
                break
        if near:
            fringe_cells.add(c)
    print(f"monotone fringe cells within {FRINGE_RADIUS_CHEBY} cells of a boundary/decal cell: "
          f"{len(fringe_cells)}")

    site_cells = boundary_cells | decal_cells | fringe_cells
    site_comps = connected_components(site_cells, SITE_MERGE_CHEBY)
    print(f"ecotone SITES (chebyshev<={SITE_MERGE_CHEBY} merge of straddle+decal+fringe cells): "
          f"{len(site_comps)}  ({time.time()-t0:.1f}s)")

    sites_out = []
    calibration_hit = False
    for comp in site_comps:
        comp_set = set(comp)
        rect = block_rect_of_cells(comp, cell_block)
        n_boundary = len(comp_set & boundary_cells)
        n_decal = len(comp_set & decal_cells)
        n_fringe = len(comp_set & fringe_cells)
        touches_known = bool(rect and set(map(tuple, rect["blocks"])) & KNOWN_SITE_BLOCKS)
        if touches_known:
            calibration_hit = True
        sites_out.append(dict(
            n_cells=len(comp), n_boundary_cells=n_boundary, n_decal_cells=n_decal,
            n_fringe_cells=n_fringe, block_rect=rect, is_known_calibration_site=touches_known,
            cells=[list(c) for c in comp],
        ))
    sites_out.sort(key=lambda s: -s["n_cells"])
    print(f"CALIBRATION: known site (13-15,11-12) found by the detector: {calibration_hit}")
    if not calibration_hit:
        print("!!! CALIBRATION FAILED -- the detector did not recover the known-truth site. "
              "Do not trust downstream output until this is fixed.")
    print("top 8 ecotone sites by cell count:")
    for s in sites_out[:8]:
        r = s["block_rect"]
        print(f"  cells={s['n_cells']:4d} boundary={s['n_boundary_cells']:3d} decal={s['n_decal_cells']:3d} "
              f"fringe={s['n_fringe_cells']:3d} blocks=({r['bx_lo']}-{r['bx_hi']},{r['by_lo']}-{r['by_hi']}) "
              f"known={s['is_known_calibration_site']}")

    # ================================================================================================
    # (b) DESERT MASSES -- connected components of ALL desert-family cells, grass-adjacent or not
    # ================================================================================================
    desert_cells = {c for c, fams in cell_fams.items() if "desert" in fams}
    print(f"\ndesert-family cells map-wide (any desert-topo tri present): {len(desert_cells)}")
    desert_comps = connected_components(desert_cells, 1)   # true 8-connectivity, NOT dilated
    print(f"desert MASSES (8-connected desert cells, radius=1, no dilation): {len(desert_comps)}  "
          f"({time.time()-t0:.1f}s)")

    grass_cells = {c for c, fams in cell_fams.items() if "grass" in fams}

    masses_out = []
    for comp in desert_comps:
        comp_set = set(comp)
        rect = block_rect_of_cells(comp, cell_block)
        # grass-adjacent: any desert cell in this mass has a chebyshev<=1 neighbour cell carrying grass
        grass_adjacent = False
        for c in comp:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    n = (c[0] + dx, c[1] + dy)
                    if n in grass_cells:
                        grass_adjacent = True
                        break
                if grass_adjacent:
                    break
            if grass_adjacent:
                break
        # topo tally for this mass (label-blind cross-check input)
        topo_tally = Counter()
        for c in comp:
            for topo, n in cell_topo[c].items():
                if SNR.FAM_OF.get(topo) == "desert":
                    topo_tally[topo] += n
        masses_out.append(dict(
            n_cells=len(comp), block_rect=rect, grass_adjacent=grass_adjacent,
            topo_tally=dict(sorted(topo_tally.items())),
            cells=[list(c) for c in comp],
        ))
    masses_out.sort(key=lambda m: -m["n_cells"])
    print("top 10 desert masses by cell count:")
    for m in masses_out[:10]:
        r = m["block_rect"]
        print(f"  cells={m['n_cells']:4d} blocks=({r['bx_lo']}-{r['bx_hi']},{r['by_lo']}-{r['by_hi']}) "
              f"n_blocks={r['n_blocks']:3d} grass_adj={m['grass_adjacent']} topo={m['topo_tally']}")

    # ================================================================================================
    # LABEL-BLIND CROSS-CHECK -- classify every desert-family (topo-based) tri ALSO by UV geometry;
    # report disagreement instead of silently trusting the topo-only FAM_OF classifier used above.
    # ================================================================================================
    desert_tris = [t for t in all_tris if t["fam"] == "desert"]
    xcheck = Counter()
    disagreements = []
    for t in desert_tris:
        cls, detail = SNR.classify_tri("desert", t["uv"])
        if cls == "mains_own" and detail == "desert":
            xcheck["mains_own_desert"] += 1
        elif cls == "mains_foreign":
            xcheck[f"mains_foreign_{detail}"] += 1
            if len(disagreements) < 40:
                disagreements.append(dict(block=list(t["block"]), cell=list(t["cell"]),
                                          topo=t["topo"], uv_says=detail))
        elif cls == "strip_grass_desert":
            xcheck[f"strip_grass_desert_row{detail}"] += 1
        elif cls == "strip_desert_dunes":
            xcheck[f"strip_desert_dunes_row{detail}"] += 1
        else:
            xcheck["other_uncatalogued"] += 1
            if len(disagreements) < 40:
                disagreements.append(dict(block=list(t["block"]), cell=list(t["cell"]),
                                          topo=t["topo"], uv_says="other/uncatalogued"))
    print(f"\nLABEL-BLIND CROSS-CHECK over {len(desert_tris)} topo-classified desert-family tris:")
    for k, v in sorted(xcheck.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    n_disagree = sum(v for k, v in xcheck.items()
                     if k.startswith("mains_foreign_") or k == "other_uncatalogued")
    print(f"  TOTAL topo/UV disagreements: {n_disagree}/{len(desert_tris)} "
          f"({100.0*n_disagree/len(desert_tris):.2f}%)" if desert_tris else "  (no desert tris)")

    # ================================================================================================
    # write
    # ================================================================================================
    out = dict(
        meta=dict(script="contract_mass_scout.py", n_land_blocks=len(land_blocks),
                  n_tris=len(all_tris), n_populated_cells=len(cell_tris),
                  cell_size_u=CELL, block_size_u=BLOCK,
                  fringe_radius_cheby=FRINGE_RADIUS_CHEBY, site_merge_cheby=SITE_MERGE_CHEBY,
                  known_calibration_site_blocks=[list(b) for b in sorted(KNOWN_SITE_BLOCKS)],
                  calibration_passed=calibration_hit, elapsed_s=round(time.time() - t0, 1)),
        ecotone_sites=sites_out,
        desert_masses=masses_out,
        label_blind_crosscheck=dict(
            n_desert_tris=len(desert_tris), tally=dict(xcheck),
            n_disagreements=n_disagree, disagreement_samples=disagreements,
        ),
    )
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}  (total {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
