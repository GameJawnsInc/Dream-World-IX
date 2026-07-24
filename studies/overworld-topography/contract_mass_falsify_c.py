"""INDEPENDENT FALSIFIER for Lane C (mass anatomy / "beyond the band").

Re-derives Lane C's headline numbers from RAW BYTES with a wholly independent
implementation. Does NOT import contract_mass_interior.py. Reuses only shared
constant definitions (FAM_OF topo->family, GROUNDS UV translations via grassland)
and the byte readers X.read_block / M.blockmesh_from_ff9mesh.

READ-ONLY. Zero writes to the game install, zero deploys.
Output -> out/contract_mass/falsify_c.json
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X          # noqa
from ff9mapkit.world import mesh as M             # noqa

CELL = 4.0
BLOCK = 64.0
OUT = HERE / "out" / "contract_mass" / "falsify_c.json"

# ---- family table (verbatim, from seam_null_recon.FAM_OF / grassland.TOPO_FAMILY) ----
FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42): FAM_OF[t] = "grass"
for t in (4, 5, 6): FAM_OF[t] = "scrub"
for t in (16, 17, 19, 20): FAM_OF[t] = "desert"
for t in (27, 28): FAM_OF[t] = "snow"
FAM_OF[38] = "brush"; FAM_OF[41] = "dunes"
FAM_OF[45] = FAM_OF[46] = "canyon"; FAM_OF[58] = "rock"; FAM_OF[59] = "hole"

# desert BIOME topo ids (16=dressed skin, 17=plain mains). 19/20 = dirt gameplay variants: EXCLUDED.
DESERT_BIOME = {16, 17}
DESERT_DIRT = {19, 20}


def load_tris_stock(blocks):
    """My own loader (does NOT call seam_null_recon.load_tris). Returns list of tri dicts
    with block/topo/fam/cell/w (world verts)."""
    tris = []
    present = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        present.append((bx, by))
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            tris.append(dict(block=(bx, by), topo=topo, fam=fam, cell=cell, w=w))
    return tris, present


def load_tris_deployed(blocks, mod="FF9CustomMap-world", root=None):
    """Load Rung-E STAGED terrain bytes from the local out/rung_e tree (NOT the game install).
    root points at the FF9CustomMap-world dir holding FF9_Data/..."""
    tris = []
    present = []
    for (bx, by) in blocks:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = root / rel
        if not path.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
        present.append((bx, by))
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            tris.append(dict(block=(bx, by), topo=topo, fam=fam, cell=cell, w=w))
    return tris, present


# ---- cell-graph helpers -----------------------------------------------------
def components_cheby1(cells):
    """8-connectivity (chebyshev<=1) connected components of a set of cells."""
    cells = set(cells)
    seen = set()
    comps = []
    for c in cells:
        if c in seen:
            continue
        comp = []
        q = deque([c]); seen.add(c)
        while q:
            x = q.popleft(); comp.append(x)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0: continue
                    n = (x[0] + dx, x[1] + dy)
                    if n in cells and n not in seen:
                        seen.add(n); q.append(n)
        comps.append(comp)
    return comps


def interior_fraction(comp_cells):
    """fraction of cells whose full 8-neighborhood is inside the mass."""
    s = set(comp_cells)
    if not s: return 0.0
    interior = 0
    for c in s:
        if all((c[0]+dx, c[1]+dy) in s
               for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0)):
            interior += 1
    return interior / len(s)


def max_inscribed_radius(comp_cells):
    """max over cells of chebyshev distance to the nearest EXTERIOR cell (multi-source BFS
    from the mass's exterior boundary ring). radius in cells."""
    s = set(comp_cells)
    if not s: return 0
    # exterior neighbours = cells not in s that touch s (8-conn); seed dist for interior via BFS.
    # distance transform: dist[c] = 1 + min neighbour dist, exterior dist 0.
    dist = {}
    q = deque()
    for c in s:
        # a cell touching exterior gets dist 1
        touches_ext = any((c[0]+dx, c[1]+dy) not in s
                          for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0))
        if touches_ext:
            dist[c] = 1; q.append(c)
    while q:
        c = q.popleft()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx==0 and dy==0: continue
                n = (c[0]+dx, c[1]+dy)
                if n in s and n not in dist:
                    dist[n] = dist[c] + 1; q.append(n)
    return max(dist.values()) if dist else 0


def grass_ecotone_fraction(comp_cells, grass_cells):
    """fraction of the mass's PERIMETER cells (cells touching a non-mass cell) that are
    adjacent (8-conn) to a grass cell."""
    s = set(comp_cells)
    gs = set(grass_cells)
    perim = [c for c in s if any((c[0]+dx, c[1]+dy) not in s
             for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0))]
    if not perim: return 0.0
    touching_grass = 0
    for c in perim:
        if any((c[0]+dx, c[1]+dy) in gs
               for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0)):
            touching_grass += 1
    return touching_grass / len(perim)


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0: return None
    if n % 2: return xs[n//2]
    return (xs[n//2 - 1] + xs[n//2]) / 2.0


# =====================================================================================
def block_of_cell(c):
    # cell (i,j): x in [i*4,i*4+4), z in [j*4,j*4+4) with z<0 for by>0.
    # bx=floor(x/64)=floor(i/16); by=floor(-z/64)=floor(-j/16).
    return (math.floor(c[0] / 16.0), math.floor(-c[1] / 16.0))


def main():
    result = {"script": "contract_mass_falsify_c.py", "read_only": True}

    # ---------- PART 1: stock map-wide census ----------
    land = list(X.list_blocks(disc=1))
    stock_tris, present = load_tris_stock(land)
    print(f"stock land blocks requested {len(land)}, present {len(present)}, tris {len(stock_tris)}")
    result["stock_n_blocks_present"] = len(present)
    result["stock_n_tris"] = len(stock_tris)

    # per-cell family sets (from tri centroids)
    cell_fams = defaultdict(set)          # cell -> set(fam)
    cell_topos = defaultdict(Counter)     # cell -> Counter(topo)
    for t in stock_tris:
        cell_fams[t["cell"]].add(t["fam"])
        cell_topos[t["cell"]][t["topo"]] += 1

    grass_cells = {c for c, f in cell_fams.items() if "grass" in f}
    dunes_cells = {c for c, f in cell_fams.items() if "dunes" in f}

    # desert-BIOME cells (topo 16/17 present)
    biome_desert_cells = {c for c, tc in cell_topos.items()
                          if any(tp in DESERT_BIOME for tp in tc)}
    dirt_cells = {c for c, tc in cell_topos.items()
                  if any(tp in DESERT_DIRT for tp in tc) and not any(tp in DESERT_BIOME for tp in tc)}

    # grass|desert straddle cells (both grass AND desert-biome tri in same cell)
    straddle_cells = {c for c, f in cell_fams.items()
                      if "grass" in f and c in biome_desert_cells}
    result["stock_n_straddle_cells_mapwide"] = len(straddle_cells)

    # ecotone SITES = connected components of straddle cells merged with radius<=2
    # (match scout's site_merge_cheby=2). Count components.
    def components_radius(cells, r):
        cells = set(cells); seen = set(); comps = []
        for c0 in cells:
            if c0 in seen: continue
            comp = []; q = deque([c0]); seen.add(c0)
            while q:
                x = q.popleft(); comp.append(x)
                for dx in range(-r, r+1):
                    for dy in range(-r, r+1):
                        if dx==0 and dy==0: continue
                        n = (x[0]+dx, x[1]+dy)
                        if n in cells and n not in seen:
                            seen.add(n); q.append(n)
            comps.append(comp)
        return comps
    ecotone_sites = components_radius(straddle_cells, 2)
    result["stock_n_grass_desert_straddle_components_r2"] = len(ecotone_sites)
    # topo purity of ALL map-wide straddle cells (the load-bearing "junction is topo-16" test)
    straddle_topo = Counter()
    for c in straddle_cells:
        for tp, n in cell_topos[c].items():
            if tp in DESERT_BIOME:
                straddle_topo[tp] += n
    result["stock_all_straddle_desert_topo"] = dict(straddle_topo)
    # geographic block span of every straddle component (are they all ONE region?)
    site_block_spans = []
    for comp in ecotone_sites:
        bxs = [block_of_cell(c)[0] for c in comp]; bys = [block_of_cell(c)[1] for c in comp]
        site_block_spans.append([min(bxs), max(bxs), min(bys), max(bys), len(comp)])
    result["stock_straddle_component_block_spans"] = site_block_spans
    # single geographic cluster? merge components whose block-rects overlap/touch
    all_bx = [s[0] for s in site_block_spans] + [s[1] for s in site_block_spans]
    all_by = [s[2] for s in site_block_spans] + [s[3] for s in site_block_spans]
    result["stock_grass_desert_region_block_rect"] = [min(all_bx), max(all_bx), min(all_by), max(all_by)] if site_block_spans else None
    print(f"straddle cells {len(straddle_cells)}, straddle components(r<=2) {len(ecotone_sites)}, "
          f"straddle topo {dict(straddle_topo)}, region block rect {result['stock_grass_desert_region_block_rect']}")

    # ---------- PART 2: known-site band anatomy ----------
    # known site desert-biome cell component (8-conn) that overlaps the known blocks
    known_blocks = {(bx, by) for bx in (13,14,15) for by in (11,12,13)}
    known_desert_cells = {c for c in biome_desert_cells if block_of_cell(c) in known_blocks}
    # component containing known desert cells
    dcomps = components_cheby1(biome_desert_cells)
    # take the LARGEST 8-conn biome-desert component overlapping the known region (scout's 240-cell skin)
    overlapping = [set(comp) for comp in dcomps if set(comp) & known_desert_cells]
    site_comp = max(overlapping, key=len) if overlapping else None
    result["site_desert_component_cells"] = len(site_comp) if site_comp else 0
    result["site_desert_overlapping_component_sizes"] = sorted((len(c) for c in overlapping), reverse=True)

    # topo purity of the site component
    site_topo = Counter()
    for c in site_comp:
        for tp, n in cell_topos[c].items():
            if tp in DESERT_BIOME:  # only the desert-biome tris' topos
                site_topo[tp] += n
    result["site_component_desert_topo_tally"] = dict(site_topo)
    n16 = site_topo.get(16, 0); n17 = site_topo.get(17, 0)
    result["site_frac_topo16"] = round(n16 / (n16 + n17), 4) if (n16+n17) else None

    # nearest topo-17 cell to the site (in cells / world units)
    topo17_cells = {c for c, tc in cell_topos.items() if 17 in tc}
    if site_comp and topo17_cells:
        best = min(min(max(abs(a[0]-b[0]), abs(a[1]-b[1])) for b in topo17_cells) for a in site_comp)
        result["nearest_topo17_cells_from_site"] = best
        result["nearest_topo17_world_u"] = best * CELL
    else:
        result["nearest_topo17_cells_from_site"] = None

    # BAND I: depth from grass junction. boundary desert cells = desert-biome cells adjacent
    # (8-conn) to a grass cell. BFS INWARD through the desert component only.
    boundary_desert = {c for c in site_comp
                       if any((c[0]+dx, c[1]+dy) in grass_cells
                              for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0))}
    dist = {c: 0 for c in boundary_desert}
    q = deque(boundary_desert)
    while q:
        c = q.popleft()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx==0 and dy==0: continue
                n = (c[0]+dx, c[1]+dy)
                if n in site_comp and n not in dist:
                    dist[n] = dist[c] + 1; q.append(n)
    # per-depth topo taper (tri counts) + frac_topo16
    depth_topo = defaultdict(Counter)
    for c, d in dist.items():
        for tp, n in cell_topos[c].items():
            if tp in DESERT_BIOME:
                depth_topo[d][tp] += n
    max_depth = max(dist.values()) if dist else 0
    band_i = {}
    for d in range(0, max_depth+1):
        tc = depth_topo.get(d, Counter())
        n16d = tc.get(16, 0); n17d = tc.get(17, 0); tot = n16d + n17d
        band_i[d] = dict(n16=n16d, n17=n17d, tris=tot,
                         frac16=round(n16d/tot, 4) if tot else None)
    result["band_i_max_depth"] = max_depth
    result["band_i_by_depth"] = band_i
    result["band_i_tri_taper"] = [band_i[d]["tris"] for d in range(0, max_depth+1)]
    result["band_i_frac16_all_depths"] = [band_i[d]["frac16"] for d in range(0, max_depth+1)]

    # BAND II: what lies INLAND of the topo-16 band. For each depth, the OTHER (non-desert-biome,
    # non-grass) family present in cells at that depth. Also: first depth where topo-17 or dunes
    # appears in the neighbourhood inland.
    # Inland neighbourhood: at each depth-d desert cell, look at 8-neighbours that are NOT desert-biome
    # and NOT grass -> what family.
    first_dunes_depth = None
    first_topo17_depth = None
    inland_family_by_depth = defaultdict(Counter)
    for c, d in dist.items():
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx==0 and dy==0: continue
                n = (c[0]+dx, c[1]+dy)
                nf = cell_fams.get(n, set())
                if "dunes" in nf:
                    inland_family_by_depth[d]["dunes"] += 1
                    if first_dunes_depth is None or d < first_dunes_depth:
                        first_dunes_depth = d
                if 17 in cell_topos.get(n, {}):
                    if first_topo17_depth is None or d < first_topo17_depth:
                        first_topo17_depth = d
    result["band_ii_first_dunes_depth"] = first_dunes_depth
    result["band_ii_first_topo17_depth"] = first_topo17_depth
    result["band_ii_inland_dunes_touch_by_depth"] = {d: inland_family_by_depth[d]["dunes"]
                                                     for d in sorted(inland_family_by_depth)}

    # ---------- PART 3: cell-shape discriminators over stock biome-desert masses ----------
    biome_comps = [set(c) for c in components_cheby1(biome_desert_cells)]
    dirt_comps = [set(c) for c in components_cheby1(dirt_cells)]
    result["stock_n_biome_desert_masses"] = len(biome_comps)
    result["stock_n_dirt_variant_masses"] = len(dirt_comps)

    areas, ints, radii, ecos = [], [], [], []
    mass_rows = []
    for comp in biome_comps:
        a = len(comp)
        ifr = interior_fraction(comp)
        rad = max_inscribed_radius(comp)
        eco = grass_ecotone_fraction(comp, grass_cells)
        areas.append(a); ints.append(ifr); radii.append(rad); ecos.append(eco)
        # topo makeup
        tt = Counter()
        for c in comp:
            for tp, n in cell_topos[c].items():
                if tp in DESERT_BIOME: tt[tp] += n
        mass_rows.append(dict(area=a, interior=round(ifr,4), radius=rad, grass_eco=round(eco,4),
                              topo=dict(tt),
                              blk=[min(block_of_cell(c)[0] for c in comp),
                                   max(block_of_cell(c)[0] for c in comp),
                                   min(block_of_cell(c)[1] for c in comp),
                                   max(block_of_cell(c)[1] for c in comp)]))
    result["stock_discriminators"] = dict(
        area=[min(areas), median(areas), max(areas)],
        interior_fraction=[round(min(ints),4), round(median(ints),4), round(max(ints),4)],
        inscribed_radius=[min(radii), median(radii), max(radii)],
        grass_ecotone_fraction=[round(min(ecos),4), round(median(ecos),4), round(max(ecos),4)],
    )
    # freestanding plain-desert masses: topo-17-dominant + grass_eco==0
    free_plain = [m for m in mass_rows
                  if m["topo"].get(17,0) > m["topo"].get(16,0) and m["grass_eco"] == 0.0]
    if free_plain:
        result["freestanding_plain_desert"] = dict(
            n=len(free_plain),
            min_area=min(m["area"] for m in free_plain),
            median_area=median([m["area"] for m in free_plain]),
            min_interior=round(min(m["interior"] for m in free_plain),4),
            min_radius=min(m["radius"] for m in free_plain),
            all_grass_eco_zero=all(m["grass_eco"] == 0.0 for m in free_plain),
        )
    # topo-17-dominant masses, all, sorted by area (to reconcile Lane C's "5 substantial")
    t17 = [m for m in mass_rows if m["topo"].get(17,0) > m["topo"].get(16,0)]
    t17.sort(key=lambda m: -m["area"])
    result["stock_topo17_masses_all"] = [dict(area=m["area"], interior=m["interior"],
                                              radius=m["radius"], grass_eco=m["grass_eco"],
                                              blk=m["blk"]) for m in t17]
    # substantiality-filtered floor (area>=100, matching Lane C's "substantial >=165" spirit)
    subst = [m for m in t17 if m["area"] >= 100]
    if subst:
        result["freestanding_plain_desert_substantial_ge100"] = dict(
            n=len(subst), min_area=min(m["area"] for m in subst),
            median_area=median([m["area"] for m in subst]),
            min_interior=round(min(m["interior"] for m in subst),4),
            min_radius=min(m["radius"] for m in subst),
            all_grass_eco_zero=all(m["grass_eco"] == 0.0 for m in subst),
            max_grass_eco=round(max(m["grass_eco"] for m in subst),4),
        )
    # grass-adjacent biome desert masses
    grass_adj = [m for m in mass_rows if m["grass_eco"] > 0.0]
    result["stock_grass_adjacent_biome_masses"] = [dict(area=m["area"], grass_eco=m["grass_eco"],
                                                        topo=m["topo"], blk=m["blk"]) for m in grass_adj]
    # sort mass_rows by area desc for readability, keep top 12
    mass_rows.sort(key=lambda m: -m["area"])
    result["stock_mass_rows_top"] = mass_rows[:15]

    # ---------- PART 3b: coast cross-check at the stock known site (v_waist) ----------
    # boundary desert cells = depth-0 topo-16 skin cells adjacent to grass. Distance (2D X,Z) from
    # each cell CENTRE and from each depth-0 desert TRI centroid to the nearest sea/beach vertex,
    # scanning the known-site core's Moore block ring. Commensurable-form with the 39.95u contract.
    core = [(bx, by) for bx in (13,14,15) for by in (11,12)]
    ring = sorted({(bx+dx, by+dy) for (bx,by) in core for dx in (-1,0,1) for dy in (-1,0,1)})
    sea_verts = []
    for (bx, by) in ring:
        ox, oz = X.block_world_origin(bx, by)
        for part in ("sea1","sea2","sea3","sea4","sea5","beach1","beach2"):
            try:
                bm = X.read_block(bx, by, disc=1, part=part.lower() if part.startswith("sea") else part)
            except (ValueError, FileNotFoundError, KeyError):
                continue
            for v in bm.verts:
                sea_verts.append((v[0] + ox, v[2] + oz))
    result["coast_xcheck_n_sea_verts"] = len(sea_verts)
    if sea_verts and boundary_desert:
        # cell-centre distances (world center = i*4+2, j*4+2)
        cc = []
        for c in boundary_desert:
            wx, wz = c[0]*4.0 + 2.0, c[1]*4.0 + 2.0
            cc.append(min(math.hypot(wx-sx, wz-sz) for (sx,sz) in sea_verts))
        result["coast_xcheck_boundary_cellcentre_min_u"] = round(min(cc), 2)
        # tri-centroid distances for depth-0 desert tris (topo-16 in boundary cells)
        tc = []
        for t in stock_tris:
            if t["cell"] in boundary_desert and t["topo"] == 16:
                cx = sum(p[0] for p in t["w"])/3.0; cz = sum(p[2] for p in t["w"])/3.0
                tc.append(min(math.hypot(cx-sx, cz-sz) for (sx,sz) in sea_verts))
        result["coast_xcheck_boundary_tricentroid_min_u"] = round(min(tc), 2) if tc else None

    # ---------- PART 4: Rung E staged bytes ----------
    rung_root = HERE / "out" / "rung_e" / "FF9CustomMap-world"
    re_blocks = [(bx, by) for bx in range(0,4) for by in range(14,20)]
    re_tris, re_present = load_tris_deployed(re_blocks, root=rung_root)
    print(f"rung_e terrain blocks present {len(re_present)}: {re_present}, tris {len(re_tris)}")
    result["rung_e_blocks_present"] = re_present
    result["rung_e_n_tris"] = len(re_tris)

    re_cell_fams = defaultdict(set)
    re_cell_topos = defaultdict(Counter)
    for t in re_tris:
        re_cell_fams[t["cell"]].add(t["fam"])
        re_cell_topos[t["cell"]][t["topo"]] += 1
    re_grass_cells = {c for c, f in re_cell_fams.items() if "grass" in f}
    re_dunes_cells = {c for c, f in re_cell_fams.items() if "dunes" in f}
    re_biome_desert = {c for c, tc in re_cell_topos.items() if any(tp in DESERT_BIOME for tp in tc)}

    # full topo hist of staged terrain (sanity vs verify_rung_e)
    re_topo_hist = Counter()
    for t in re_tris:
        re_topo_hist[t["topo"]] += 1
    result["rung_e_full_topo_hist"] = dict(re_topo_hist)

    # desert component
    re_comps = components_cheby1(re_biome_desert)
    re_comps_sorted = sorted(re_comps, key=len, reverse=True)
    result["rung_e_n_desert_cells"] = len(re_biome_desert)
    result["rung_e_largest_component_cells"] = len(re_comps_sorted[0]) if re_comps_sorted else 0
    largest = set(re_comps_sorted[0]) if re_comps_sorted else set()

    # topo tally of the largest desert component's CELLS (all tris in those cells)
    re_desert_topo = Counter()
    for c in largest:
        for tp, n in re_cell_topos[c].items():
            re_desert_topo[tp] += n
    result["rung_e_desert_component_topo_tally"] = dict(re_desert_topo)

    # 4 discriminators on the largest component
    result["rung_e_discriminators"] = dict(
        area=len(largest),
        interior_fraction=round(interior_fraction(largest),4),
        inscribed_radius=max_inscribed_radius(largest),
        grass_ecotone_fraction=round(grass_ecotone_fraction(largest, re_grass_cells),4),
    )

    # DECISIVE: inland backing. Does dunes lie inland of the topo-16 band, or does grass return?
    # boundary desert cells = adjacent to grass; BFS inward; report family beyond the band.
    re_boundary = {c for c in largest
                   if any((c[0]+dx, c[1]+dy) in re_grass_cells
                          for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0))}
    re_dist = {c: 0 for c in re_boundary}
    q = deque(re_boundary)
    while q:
        c = q.popleft()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx==0 and dy==0: continue
                n = (c[0]+dx, c[1]+dy)
                if n in largest and n not in re_dist:
                    re_dist[n] = re_dist[c] + 1; q.append(n)
    re_first_dunes = None
    re_max_depth = max(re_dist.values()) if re_dist else 0
    re_inland_grass_touch = 0
    re_inland_dunes_touch = 0
    for c, d in re_dist.items():
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx==0 and dy==0: continue
                n = (c[0]+dx, c[1]+dy)
                nf = re_cell_fams.get(n, set())
                if "dunes" in nf and (re_first_dunes is None or d < re_first_dunes):
                    re_first_dunes = d
                if "dunes" in nf: re_inland_dunes_touch += 1
                if "grass" in nf: re_inland_grass_touch += 1
    result["rung_e_band_max_depth"] = re_max_depth
    result["rung_e_first_dunes_depth"] = re_first_dunes
    result["rung_e_n_dunes_cells_total"] = len(re_dunes_cells)
    result["rung_e_inland_grass_touches"] = re_inland_grass_touch
    result["rung_e_inland_dunes_touches"] = re_inland_dunes_touch

    # ---------- SEPARATION VERDICT ----------
    sd = result["stock_discriminators"]
    rd = result["rung_e_discriminators"]
    def inside(v, lohi):
        return lohi[0] <= v <= lohi[-1]
    seps = dict(
        area=not inside(rd["area"], sd["area"]),
        interior_fraction=not inside(rd["interior_fraction"], sd["interior_fraction"]),
        inscribed_radius=not inside(rd["inscribed_radius"], sd["inscribed_radius"]),
        grass_ecotone_fraction=not inside(rd["grass_ecotone_fraction"], sd["grass_ecotone_fraction"]),
    )
    result["cell_shape_separates_rung_e"] = seps
    result["any_cell_shape_separates"] = any(seps.values())
    result["decisive_stock_first_dunes_depth"] = first_dunes_depth
    result["decisive_stock_first_topo17_depth"] = first_topo17_depth
    result["decisive_rung_e_first_dunes_depth"] = re_first_dunes

    OUT.write_text(json.dumps(result, indent=1))
    print("\n==== SUMMARY ====")
    print("straddle components(r2):", result["stock_n_grass_desert_straddle_components_r2"],
          "| all in region block rect:", result["stock_grass_desert_region_block_rect"],
          "| all-straddle topo:", result["stock_all_straddle_desert_topo"])
    print("site component cells:", result["site_desert_component_cells"], "frac16:", result["site_frac_topo16"])
    print("nearest topo17:", result.get("nearest_topo17_cells_from_site"), "cells")
    print("band_i taper:", result["band_i_tri_taper"])
    print("band_i frac16:", result["band_i_frac16_all_depths"])
    print("band_ii first dunes depth:", first_dunes_depth, "first topo17:", first_topo17_depth)
    print("stock discriminators:", json.dumps(sd))
    print("rung_e discriminators:", json.dumps(rd))
    print("separates?:", seps, "ANY:", result["any_cell_shape_separates"])
    print("rung_e desert component topo tally:", dict(re_desert_topo))
    print("rung_e n_desert_cells:", len(re_biome_desert), "largest:", result["rung_e_largest_component_cells"])
    print("rung_e first dunes depth:", re_first_dunes, "(None = never / grass returns)")
    print("stock n biome masses:", len(biome_comps), "dirt masses:", len(dirt_comps))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
