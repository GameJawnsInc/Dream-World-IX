"""LANE C -- WHAT LIES BEYOND THE TOPO-16 BAND: THE DESERT MASS'S OWN ANATOMY
(MASS-ANATOMY CONTRACT round, 2026-07-23, mandate item (c) of the Rung-E rejection).

Every prior round measured the LINE. This lane measures the MASS. READ-ONLY vs the game
install: X.read_block (stock disc-1 bytes) + X.list_coastal_donors + reading the *staged*
(never deployed) Rung-E override bytes under out/rung_e/FF9CustomMap-world. ZERO writes to the
game, no deploy, no mirror, no --apply.

Reuses seam_null_recon.py VERBATIM (FAM_OF / load_tris / edge_index) -- the same proven vocabulary
Round 10/11 + the scout used. Consumes the scout's authoritative mass/ecotone cell sets from
out/contract_mass/sites.json (no re-derivation of the map-wide component graph).

Answers (i) band depth, (ii) interior composition, (iii) mass shape / the RIBBON DISCRIMINATOR
(stock masses vs the Rung-E staged ribbon), (iv) the desert coast, (v) the waist.

Run:  py studies/overworld-topography/contract_mass_interior.py
Artifact -> out/contract_mass/lane_c_interior.json
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

import seam_null_recon as SNR                       # noqa: E402  reuse proven machinery
from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M               # noqa: E402

CELL = 4.0
BLOCK = 64.0
SITES = HERE / "out" / "contract_mass" / "sites.json"
RUNG_E = HERE / "out" / "rung_e" / "FF9CustomMap-world"
OUT = HERE / "out" / "contract_mass" / "lane_c_interior.json"

DESERT_TOPOS = {16, 17, 19, 20}
GENUINE_DESERT_TOPOS = {16, 17}          # the biome vocabulary; 19/20 = dirt-variant (roads)
MOORE = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
VN = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def world_of_cell_center(c):
    return (c[0] * CELL + CELL / 2.0, c[1] * CELL + CELL / 2.0)


# ====================================================================================================
# STOCK: load every land block ONCE, build the cell-level census
# ====================================================================================================
def build_stock_census():
    blocks = X.list_blocks(disc=1)
    print(f"[stock] loading {len(blocks)} land blocks ...")
    all_tris, bms, srcs = SNR.load_tris(blocks, source="stock")
    print(f"[stock] {len(all_tris)} tris, {len(bms)} blocks loaded (skips: {len(blocks)-len(bms)})")

    cell_topos = defaultdict(Counter)     # cell -> Counter(topo)
    cell_fams = defaultdict(Counter)      # cell -> Counter(family)
    cell_tris = defaultdict(list)         # cell -> [tri,...]
    for t in all_tris:
        cell_topos[t["cell"]][t["topo"]] += 1
        cell_fams[t["cell"]][t["fam"]] += 1
        cell_tris[t["cell"]].append(t)
    land_cells = set(cell_topos)
    # a cell is a "desert cell" if it owns >=1 desert-family tri
    desert_cells = {c for c in land_cells if cell_fams[c].get("desert", 0) > 0}
    # "pure desert" cell = has desert tris and NO non-desert land tri
    pure_desert = {c for c in desert_cells if sum(cell_fams[c].values()) == cell_fams[c].get("desert", 0)}
    print(f"[stock] {len(land_cells)} land cells, {len(desert_cells)} desert cells, "
          f"{len(pure_desert)} pure-desert cells")
    return dict(all_tris=all_tris, bms=bms, cell_topos=cell_topos, cell_fams=cell_fams,
                cell_tris=cell_tris, land_cells=land_cells, desert_cells=desert_cells,
                pure_desert=pure_desert)


def build_sea_cells(mass_blocks):
    """Rasterize sea/beach vertices to cells, but only for coastal blocks within cheby<=1 of a mass
    block (keeps the scan bounded). Returns set of sea cells + which blocks were scanned."""
    coastal = set(X.list_coastal_donors(disc=1, beach_only=False))
    want = set()
    for (bx, by) in mass_blocks:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nb = (bx + dx, by + dy)
                if nb in coastal:
                    want.add(nb)
    sea_cells = set()
    for (bx, by) in sorted(want):
        ox, oz = X.block_world_origin(bx, by)
        for part in ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2"):
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except (ValueError, FileNotFoundError):
                continue
            for v in bm.verts:
                wx, wz = v[0] + ox, v[2] + oz
                sea_cells.add((math.floor(wx / CELL), math.floor(wz / CELL)))
    print(f"[sea] scanned {len(want)} coastal blocks near masses -> {len(sea_cells)} sea/beach cells")
    return sea_cells


# ====================================================================================================
# (iii) mass shape discriminators
# ====================================================================================================
def chessboard_inscribed_radius(mass_set):
    """Max chessboard (Chebyshev, 8-conn) distance from any mass cell to the nearest NON-mass cell.
    Two-pass DT on the mass's own bbox (mass cells only True); background = everything else."""
    if not mass_set:
        return 0
    xs = [c[0] for c in mass_set]
    ys = [c[1] for c in mass_set]
    x0, x1 = min(xs) - 1, max(xs) + 1
    y0, y1 = min(ys) - 1, max(ys) + 1
    W = x1 - x0 + 1
    H = y1 - y0 + 1
    INF = W + H + 10
    # dist grid: 0 at background, grow inward
    d = [[0 if (x0 + gx, y0 + gy) not in mass_set else INF for gy in range(H)] for gx in range(W)]
    # forward pass
    for gx in range(W):
        for gy in range(H):
            if d[gx][gy] == 0:
                continue
            best = INF
            for ddx, ddy in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
                nx, ny = gx + ddx, gy + ddy
                if 0 <= nx < W and 0 <= ny < H:
                    best = min(best, d[nx][ny] + 1)
            d[gx][gy] = min(d[gx][gy], best)
    # backward pass
    for gx in range(W - 1, -1, -1):
        for gy in range(H - 1, -1, -1):
            if d[gx][gy] == 0:
                continue
            best = d[gx][gy]
            for ddx, ddy in ((1, 1), (1, 0), (1, -1), (0, 1)):
                nx, ny = gx + ddx, gy + ddy
                if 0 <= nx < W and 0 <= ny < H:
                    best = min(best, d[nx][ny] + 1)
            d[gx][gy] = best
    return max(d[c[0] - x0][c[1] - y0] for c in mass_set)


def mass_shape(mass_cells, desert_cells, pure_desert):
    """area, interior_fraction (pure-desert cells whose 8 Moore neighbours are all desert cells),
    max inscribed disc radius (cells)."""
    mset = set(mass_cells)
    interior = 0
    for c in mset:
        if c not in pure_desert:
            continue
        if all((c[0] + dx, c[1] + dy) in desert_cells for dx, dy in MOORE):
            interior += 1
    area = len(mset)
    return dict(area_cells=area,
                interior_cells=interior,
                interior_fraction=round(interior / area, 4) if area else 0.0,
                max_inscribed_radius_cells=chessboard_inscribed_radius(mset))


# ====================================================================================================
# (iv) coast / perimeter decomposition (4-conn edges)
# ====================================================================================================
def perimeter_decomp(mass_cells, land_cells, cell_fams, sea_cells):
    """4-conn boundary edges classified by what lies across them. `land_cells`/`cell_fams` let this
    run against EITHER the stock census or the Rung-E census (generic)."""
    mset = set(mass_cells)
    tally = Counter()
    for c in mset:
        for dx, dy in VN:
            n = (c[0] + dx, c[1] + dy)
            if n in mset:
                continue
            if n not in land_cells:
                tally["open_ocean" if n in sea_cells else "open_absent"] += 1
                continue
            fams = cell_fams[n]
            if fams.get("desert", 0) > 0:
                tally["other_desert"] += 1
            elif fams.get("grass", 0) > 0:
                tally["grass_ecotone"] += 1
            elif fams.get("rock", 0) > 0:
                tally["rock"] += 1
            elif fams.get("dunes", 0) > 0:
                tally["dunes"] += 1
            else:
                dom = fams.most_common(1)[0][0] if fams else "none"
                tally[f"other_{dom}"] += 1
    total = sum(tally.values())
    open_edges = tally["open_ocean"] + tally["open_absent"]
    return dict(perimeter_edges=total, decomposition=dict(tally),
                own_coast_edges=open_edges,
                own_coast_fraction=round(open_edges / total, 4) if total else 0.0,
                sea_confirmed_edges=tally["open_ocean"],
                grass_ecotone_edges=tally["grass_ecotone"],
                grass_ecotone_fraction=round(tally["grass_ecotone"] / total, 4) if total else 0.0)


# ====================================================================================================
# (i)+(ii) band depth + interior composition -- from the grass|desert boundary INLAND
# ====================================================================================================
def band_depth_profile(S, region_blocks):
    """At the known ecotone site: find grass|desert boundary edges (a shared 3D mesh edge between a
    grass-fam and a desert-fam tri). depth-0 = the desert-side cells of those edges. BFS inland
    THROUGH desert cells; at each depth tally topo. Separately BFS from the same boundary through
    ALL land cells to see what family lies beyond the desert band."""
    region_tris = [t for t in S["all_tris"] if t["block"] in region_blocks]
    eidx = SNR.edge_index(region_tris)
    gid2tri = {t["gid"]: t for t in region_tris}
    boundary_desert_cells = set()
    boundary_grass_cells = set()
    n_gd_edges = 0
    for e, owners in eidx.items():
        fams = {gid2tri[g]["fam"] for g in owners}
        if "grass" in fams and "desert" in fams:
            n_gd_edges += 1
            for g in owners:
                t = gid2tri[g]
                if t["fam"] == "desert":
                    boundary_desert_cells.add(t["cell"])
                elif t["fam"] == "grass":
                    boundary_grass_cells.add(t["cell"])

    # BFS inland through desert cells; restrict to cells whose owning blocks are in the region
    reg_block_set = set(region_blocks)

    def cell_block(c):
        wx, wz = world_of_cell_center(c)
        # Z is negated in the world grid: block by = floor(-wz/64)
        return (math.floor(wx / BLOCK), math.floor(-wz / BLOCK))

    desert_near = {c for c in S["desert_cells"] if cell_block(c) in reg_block_set}
    depth = {c: 0 for c in boundary_desert_cells if c in desert_near}
    q = deque(depth)
    while q:
        c = q.popleft()
        for dx, dy in VN:
            n = (c[0] + dx, c[1] + dy)
            if n in desert_near and n not in depth:
                depth[n] = depth[c] + 1
                q.append(n)
    by_depth = defaultdict(Counter)     # depth -> Counter(topo)
    by_depth_fam = defaultdict(Counter)
    for c, dp in depth.items():
        for topo, n in S["cell_topos"][c].items():
            if topo in DESERT_TOPOS:
                by_depth[dp][topo] += n
        for fam, n in S["cell_fams"][c].items():
            by_depth_fam[dp][fam] += n
    profile = {}
    for dp in sorted(by_depth):
        tot = sum(by_depth[dp].values())
        f16 = by_depth[dp].get(16, 0)
        f17 = by_depth[dp].get(17, 0)
        profile[dp] = dict(n_desert_tris=tot,
                           frac_topo16=round(f16 / tot, 4) if tot else 0.0,
                           frac_topo17=round(f17 / tot, 4) if tot else 0.0,
                           topo_tally={str(k): v for k, v in sorted(by_depth[dp].items())})

    # BFS from boundary through ALL land cells -- what family lies beyond the band?
    all_near = {c for c in S["land_cells"] if cell_block(c) in reg_block_set}
    seed = {c for c in boundary_desert_cells if c in all_near}
    ddepth = {c: 0 for c in seed}
    q = deque(ddepth)
    while q:
        c = q.popleft()
        for dx, dy in VN:
            n = (c[0] + dx, c[1] + dy)
            if n in all_near and n not in ddepth:
                ddepth[n] = ddepth[c] + 1
                q.append(n)
    beyond = defaultdict(Counter)       # depth -> family census across ALL land cells
    for c, dp in ddepth.items():
        dom = S["cell_fams"][c].most_common(1)[0][0]
        beyond[dp][dom] += 1
    beyond_profile = {str(dp): dict(beyond[dp]) for dp in sorted(beyond)}
    # first depth at which a non-grass non-desert family (dunes/rock) becomes the plurality
    first_dunes = next((dp for dp in sorted(beyond) if beyond[dp].get("dunes", 0) > 0), None)
    first_topo17 = next((dp for dp in sorted(by_depth) if by_depth[dp].get(17, 0) > 0), None)
    # desert band depth = deepest desert ring reached
    max_desert_depth = max(depth.values()) if depth else 0
    return dict(n_gd_boundary_edges=n_gd_edges,
                n_boundary_desert_cells=len(boundary_desert_cells),
                n_boundary_grass_cells=len(boundary_grass_cells),
                max_desert_band_depth_cells=max_desert_depth,
                desert_band_profile_by_depth={str(k): v for k, v in profile.items()},
                first_depth_with_topo17=first_topo17,
                first_depth_with_dunes_family=first_dunes,
                beyond_band_family_by_depth=beyond_profile), boundary_desert_cells, boundary_grass_cells


# ====================================================================================================
# (v) the waist -- the two-ground landmass at the known site
# ====================================================================================================
def waist_geometry(S, region_blocks, sea_cells, boundary_desert, boundary_grass):
    """The known landmass = the 4-conn-connected land component containing the boundary. Split into
    grass-lobe vs desert-lobe cells; measure ecotone length, each lobe's own coast, area ratio, and
    the realized boundary->coast distance BOTH conventions (falsifier-style)."""
    reg_block_set = set(region_blocks)

    def cell_block(c):
        wx, wz = world_of_cell_center(c)
        return (math.floor(wx / BLOCK), math.floor(-wz / BLOCK))

    land_near = {c for c in S["land_cells"] if cell_block(c) in reg_block_set}
    # connected component (4-conn) containing a boundary cell
    seed = next(iter(boundary_desert))
    comp = {seed}
    q = deque([seed])
    while q:
        c = q.popleft()
        for dx, dy in VN:
            n = (c[0] + dx, c[1] + dy)
            if n in land_near and n not in comp:
                comp.add(n)
                q.append(n)
    grass_lobe = {c for c in comp if S["cell_fams"][c].get("grass", 0) > 0}
    desert_lobe = {c for c in comp if S["cell_fams"][c].get("desert", 0) > 0}
    dunes_lobe = {c for c in comp if S["cell_fams"][c].get("dunes", 0) > 0}
    # ecotone length = 4-conn cell edges grass-cell|desert-cell within comp
    ecotone_edges = 0
    for c in desert_lobe:
        for dx, dy in VN:
            n = (c[0] + dx, c[1] + dy)
            if n in grass_lobe:
                ecotone_edges += 1

    def own_coast(lobe):
        n = 0
        for c in lobe:
            for dx, dy in VN:
                nb = (c[0] + dx, c[1] + dy)
                if nb not in S["land_cells"]:
                    n += 1
        return n

    # realized boundary -> coast, BOTH conventions
    # convention A: boundary CELL CENTRE -> nearest sea/beach vertex (contract's + falsifier straddle)
    # convention B: boundary desert TRI centroid -> nearest sea/beach vertex
    coastal = set(X.list_coastal_donors(disc=1, beach_only=False))
    want = set()
    for (bx, by) in reg_block_set:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (bx + dx, by + dy) in coastal:
                    want.add((bx + dx, by + dy))
    sea_pts = []
    for (bx, by) in sorted(want):
        ox, oz = X.block_world_origin(bx, by)
        for part in ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2"):
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except (ValueError, FileNotFoundError):
                continue
            for v in bm.verts:
                sea_pts.append((v[0] + ox, v[2] + oz))
    conv_a = None
    for c in boundary_desert:
        wx, wz = world_of_cell_center(c)
        for (sx, sz) in sea_pts:
            d = math.hypot(wx - sx, wz - sz)
            if conv_a is None or d < conv_a:
                conv_a = d
    # convention B: boundary desert tri centroids
    bd_tris = [t for t in S["all_tris"] if t["cell"] in boundary_desert and t["fam"] == "desert"]
    conv_b = None
    for t in bd_tris:
        cx = sum(p[0] for p in t["w"]) / 3.0
        cz = sum(p[2] for p in t["w"]) / 3.0
        for (sx, sz) in sea_pts:
            d = math.hypot(cx - sx, cz - sz)
            if conv_b is None or d < conv_b:
                conv_b = d
    return dict(
        landmass_cells=len(comp),
        grass_lobe_cells=len(grass_lobe),
        desert_lobe_cells=len(desert_lobe),
        dunes_lobe_cells=len(dunes_lobe),
        lobe_area_ratio_grass_over_desert=round(len(grass_lobe) / len(desert_lobe), 3) if desert_lobe else None,
        ecotone_edges=ecotone_edges,
        grass_lobe_own_coast_edges=own_coast(grass_lobe),
        desert_lobe_own_coast_edges=own_coast(desert_lobe),
        realized_boundary_to_coast_cellcentre_u=round(conv_a, 2) if conv_a else None,
        realized_boundary_to_coast_tricentroid_u=round(conv_b, 2) if conv_b else None,
        n_sea_beach_verts_scanned=len(sea_pts),
    )


# ====================================================================================================
# RUNG E staged desert
# ====================================================================================================
def build_rung_e_desert():
    root = RUNG_E / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    files = sorted(root.glob("r*/Block[[]*[]] Terrain.ff9mesh"))
    print(f"[rungE] {len(files)} staged Terrain overrides")
    cell_fams = defaultdict(Counter)
    cell_topos = defaultdict(Counter)
    cell_tris = defaultdict(list)
    all_tris = []
    rung_blocks = set()
    for f in files:
        # parse Block[bx][by]
        name = f.name
        b = name.split("Block[")[1]
        bx = int(b.split("]")[0])
        by = int(b.split("[")[1].split("]")[0])
        rung_blocks.add((bx, by))
        bm = M.blockmesh_from_ff9mesh(f, disc=1, x=bx, y=by, part="terrain")
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            td = dict(block=(bx, by), topo=topo, fam=fam, w=w, cell=cell, gid=len(all_tris))
            all_tris.append(td)
            cell_topos[cell][topo] += 1
            cell_fams[cell][fam] += 1
            cell_tris[cell].append(td)
    desert_cells = {c for c in cell_fams if cell_fams[c].get("desert", 0) > 0}
    pure_desert = {c for c in desert_cells if sum(cell_fams[c].values()) == cell_fams[c].get("desert", 0)}
    print(f"[rungE] {len(desert_cells)} desert cells, {len(pure_desert)} pure-desert")
    # largest 8-conn component
    def components(cells):
        seen = set()
        comps = []
        cset = set(cells)
        for s in cset:
            if s in seen:
                continue
            comp = {s}
            seen.add(s)
            q = deque([s])
            while q:
                c = q.popleft()
                for dx, dy in MOORE:
                    n = (c[0] + dx, c[1] + dy)
                    if n in cset and n not in seen:
                        seen.add(n)
                        comp.add(n)
                        q.append(n)
            comps.append(comp)
        return comps
    comps = sorted(components(desert_cells), key=len, reverse=True)
    largest = comps[0] if comps else set()
    shape = mass_shape(largest, desert_cells, pure_desert)
    land_cells = set(cell_fams)
    # Rung E is staged inland over grass -- no coast; sea_cells empty, absent neighbours = surround
    coast = perimeter_decomp(largest, land_cells, cell_fams, set())
    all_coast = perimeter_decomp(desert_cells, land_cells, cell_fams, set())
    topo_tally = Counter()
    for c in desert_cells:
        topo_tally.update(cell_topos[c])
    # an S-like census so band_depth_profile can run on Rung E exactly as on stock
    S_re = dict(all_tris=all_tris, cell_topos=cell_topos, cell_fams=cell_fams,
                cell_tris=cell_tris, land_cells=land_cells, desert_cells=desert_cells,
                pure_desert=pure_desert)
    return dict(n_desert_cells=len(desert_cells), n_components=len(comps),
                largest_component_shape=shape,
                largest_component_perimeter=coast,
                all_desert_shape=mass_shape(desert_cells, desert_cells, pure_desert),
                all_desert_perimeter=all_coast,
                topo_tally={str(k): v for k, v in sorted(topo_tally.items())}), S_re, rung_blocks


# ====================================================================================================
def main():
    print(f"game root: {SNR.GAME_ROOT}")
    sites = json.loads(SITES.read_text(encoding="utf-8"))
    S = build_stock_census()

    masses = sites["desert_masses"]
    ecotone = sites["ecotone_sites"][0]
    # collect every block used by any mass (for the bounded sea scan)
    mass_blocks = set()
    for m in masses:
        for b in m["block_rect"]["blocks"]:
            mass_blocks.add(tuple(b))
    sea_cells = build_sea_cells(mass_blocks)

    # -------- (iii)+(iv) per-mass shape + coast --------
    mass_reports = []
    for i, m in enumerate(masses):
        cells = [tuple(c) for c in m["cells"]]
        topo = {int(k): v for k, v in m["topo_tally"].items()}
        dom_topo = max(topo, key=topo.get)
        genuine = set(topo) & GENUINE_DESERT_TOPOS
        klass = "biome_desert" if (dom_topo in GENUINE_DESERT_TOPOS) else "dirt_variant"
        shape = mass_shape(cells, S["desert_cells"], S["pure_desert"])
        coast = perimeter_decomp(cells, S["land_cells"], S["cell_fams"], sea_cells)
        br = m["block_rect"]
        rep = dict(mass_index=i, block_rect=[br["bx_lo"], br["by_lo"], br["bx_hi"], br["by_hi"]],
                   n_blocks=br["n_blocks"], grass_adjacent=m["grass_adjacent"],
                   dominant_topo=dom_topo, klass=klass,
                   topo_tally={str(k): v for k, v in sorted(topo.items())},
                   **shape, **coast)
        mass_reports.append(rep)
        print(f"[mass {i:2d}] {klass:12s} area={shape['area_cells']:4d} "
              f"int_frac={shape['interior_fraction']:.3f} r_insc={shape['max_inscribed_radius_cells']:2d} "
              f"coast_frac={coast['own_coast_fraction']:.3f} eco_frac={coast['grass_ecotone_fraction']:.3f} "
              f"dom_topo={dom_topo} gadj={m['grass_adjacent']}")

    # -------- (i)+(ii) band depth + interior at the known site --------
    site_blocks = {tuple(b) for b in ecotone["block_rect"]["blocks"]}
    # widen by 1 block ring so inland BFS can leave the 6-block core into whatever backs it
    wide = set()
    for (bx, by) in site_blocks:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if M.block_in_grid(bx + dx, by + dy):
                    wide.add((bx + dx, by + dy))
    print(f"[band] known-site core {sorted(site_blocks)}  +1ring -> {len(wide)} blocks")
    band, bdes, bgra = band_depth_profile(S, wide)
    print(f"[band] {band['n_gd_boundary_edges']} grass|desert edges, band depth "
          f"{band['max_desert_band_depth_cells']} cells, first topo17 depth={band['first_depth_with_topo17']}, "
          f"first dunes depth={band['first_depth_with_dunes_family']}")

    # -------- (v) the waist --------
    print("[waist] measuring the two-ground landmass ...")
    waist = waist_geometry(S, wide, sea_cells, bdes, bgra)
    print(f"[waist] landmass {waist['landmass_cells']} cells "
          f"(grass {waist['grass_lobe_cells']} / desert {waist['desert_lobe_cells']} / dunes {waist['dunes_lobe_cells']}), "
          f"ratio {waist['lobe_area_ratio_grass_over_desert']}, ecotone {waist['ecotone_edges']} edges, "
          f"boundary->coast cellcentre {waist['realized_boundary_to_coast_cellcentre_u']}u / "
          f"tricentroid {waist['realized_boundary_to_coast_tricentroid_u']}u")

    # -------- Rung E --------
    print("[rungE] measuring the staged ribbon ...")
    rung_e, S_re, rung_blocks = build_rung_e_desert()
    reS = rung_e["largest_component_shape"]
    print(f"[rungE] largest desert component: area={reS['area_cells']} "
          f"int_frac={reS['interior_fraction']} r_insc={reS['max_inscribed_radius_cells']}")
    # the SAME band-depth analysis on Rung E: what lies inland of ITS grass|desert band?
    re_band, _rbd, _rbg = band_depth_profile(S_re, rung_blocks)
    rung_e["band_depth"] = re_band
    print(f"[rungE band] {re_band['n_gd_boundary_edges']} grass|desert edges, band depth "
          f"{re_band['max_desert_band_depth_cells']} cells, first topo17 depth={re_band['first_depth_with_topo17']}, "
          f"first dunes depth={re_band['first_depth_with_dunes_family']}")

    # ================================================================================================
    # DISCRIMINATOR ANALYSIS -- stock vs Rung E, widest-margin separator
    # ================================================================================================
    biome = [r for r in mass_reports if r["klass"] == "biome_desert"]
    dirt = [r for r in mass_reports if r["klass"] == "dirt_variant"]
    reP = rung_e["largest_component_perimeter"]
    # Rung-E discriminator values (shape + perimeter ecotone-contact)
    re_vals = dict(area_cells=reS["area_cells"],
                   interior_fraction=reS["interior_fraction"],
                   max_inscribed_radius_cells=reS["max_inscribed_radius_cells"],
                   grass_ecotone_fraction=reP["grass_ecotone_fraction"])

    disc_table = {}
    # shape keys + the ecotone-contact key. For each, detect the separation DIRECTION: a ribbon may
    # sit BELOW the stock band (shape metrics) or ABOVE it (ecotone-contact fraction).
    for key in ("area_cells", "interior_fraction", "max_inscribed_radius_cells", "grass_ecotone_fraction"):
        if key == "grass_ecotone_fraction":
            stock_vals = [r["grass_ecotone_fraction"] for r in biome]
        else:
            stock_vals = [r[key] for r in biome]
        re_val = re_vals[key]
        stock_min = min(stock_vals)
        stock_max = max(stock_vals)
        stock_med = sorted(stock_vals)[len(stock_vals) // 2]
        below = re_val < stock_min
        above = re_val > stock_max
        if below:
            direction = "rung_e_below_stock"
            margin = stock_min - re_val
            rel = round(margin / stock_min, 4) if stock_min else None
        elif above:
            direction = "rung_e_above_stock"
            margin = re_val - stock_max
            rel = round(margin / stock_max, 4) if stock_max else None
        else:
            direction = "rung_e_inside_stock_band_NO_SEPARATION"
            margin = 0.0
            rel = 0.0
        disc_table[key] = dict(stock_biome_min=round(stock_min, 4), stock_biome_median=round(stock_med, 4),
                               stock_biome_max=round(stock_max, 4),
                               stock_biome_values=[round(v, 4) for v in sorted(stock_vals)],
                               rung_e_value=round(re_val, 4), separates=bool(below or above),
                               direction=direction, absolute_margin=round(margin, 4),
                               relative_margin=rel)

    # THE DECISIVE (topological) discriminator: does a desert-family interior (dunes) lie inland of
    # the topo-16 band? Stock's grass junction: yes (dunes at depth 1). Rung E: no (grass inland).
    # value = first depth at which the dunes family appears inland (None -> never; encode as 999).
    stock_backing = band["first_depth_with_dunes_family"]
    re_backing = rung_e["band_depth"]["first_depth_with_dunes_family"]
    decisive = dict(
        name="inland_backing_first_dunes_depth",
        definition="first cell-depth inland of the grass|desert boundary at which the DUNES family "
                   "appears (i.e. the topo-16 band backs onto a desert-family interior, not grass); "
                   "None means the band returns to grass = a ribbon along a line",
        stock_known_site_value=stock_backing,
        rung_e_value=re_backing,
        stock_has_desert_family_interior=stock_backing is not None,
        rung_e_has_desert_family_interior=re_backing is not None,
        separates=bool((stock_backing is not None) != (re_backing is not None)),
        n_stock_grass_desert_sites=1,
        caveat="n=1 stock grass|desert site map-wide (a CENSUS not a sample); no leave-one-SITE-out "
               "possible. The 7 plain-topo-17 desert masses are a DISJOINT population that never "
               "touches grass (grass_ecotone_fraction=0 for all).")

    # winning cell-shape discriminator (if any separates); the decisive one is topological
    best_disc = max(disc_table.items(),
                    key=lambda kv: (kv[1]["separates"], kv[1]["relative_margin"] or 0))
    key = best_disc[0]
    any_shape_separates = any(v["separates"] for v in disc_table.values())

    # -------- train/test: leave-one-mass-out on the winning discriminator --------
    def val_of(r, k):
        return r["grass_ecotone_fraction"] if k == "grass_ecotone_fraction" else r[k]

    loo = []
    biome_vals = [(r["mass_index"], val_of(r, key)) for r in biome]
    re_win = re_vals[key]
    above_sep = disc_table[key]["direction"] == "rung_e_above_stock"
    for held_idx, held_val in biome_vals:
        others = [v for i, v in biome_vals if i != held_idx]
        if above_sep:
            ceil = max(others)
            held_ok = held_val <= ceil
            re_excl = re_win > ceil
        else:
            floor = min(others)
            held_ok = held_val >= floor
            re_excl = re_win < floor
        loo.append(dict(held_mass=held_idx, held_value=round(held_val, 4),
                        others_bound=round(max(others) if above_sep else min(others), 4),
                        held_within_others_band=bool(held_ok),
                        rung_e_excluded_by_this_split=bool(re_excl)))
    loo_pass = sum(1 for r in loo if r["held_within_others_band"])
    re_excluded_all = all(r["rung_e_excluded_by_this_split"] for r in loo)

    # -------- coast: minimum mass size that has its own coast --------
    with_coast = [r for r in mass_reports if r["own_coast_edges"] > 0]
    min_coast_size = min((r["area_cells"] for r in with_coast), default=None)
    biome_with_coast = [r for r in biome if r["own_coast_edges"] > 0]

    # -------- gate-ready CONTRACT numbers (the raw min-over-all is trivial: tiny 4-6 cell
    # fragments drag it to 4/0.0/1). Characterize the two DISJOINT stock desert populations. -----
    # (a) the grass-ADJACENT desert skin -- the actual Rung-F target. n=1 site map-wide; its own
    #     desert component is the (13-15,11-12) cluster (mass_7 by cells; the waist landmass gives
    #     the lobe view). Report its exemplar metrics + the mandatory dunes backing.
    grass_adj_biome = [r for r in biome if r["grass_ecotone_fraction"] > 0]
    exemplar = max(grass_adj_biome, key=lambda r: r["area_cells"]) if grass_adj_biome else None
    # (b) free-standing plain-desert masses that actually HAVE a plain interior (int_frac>=0.2 AND
    #     inscribed radius>=3) -- the "solid desert body" the RIBBON FALLACY imagined. These are the
    #     DISJOINT topo-17 population (grass_ecotone_fraction=0 for all).
    substantial = [r for r in biome if r["interior_fraction"] >= 0.20 and r["max_inscribed_radius_cells"] >= 3]
    contract_summary = dict(
        grass_adjacent_desert_exemplar=dict(
            n_stock_grass_desert_sites_mapwide=1,
            n_grass_adjacent_biome_mass_fragments=len(grass_adj_biome),
            mass_index=exemplar["mass_index"] if exemplar else None,
            area_cells=exemplar["area_cells"] if exemplar else None,
            band_depth_cells=band["max_desert_band_depth_cells"],
            band_is_pure_topo16="yes -- frac_topo16==1.0 at every depth 0..5",
            inland_backing="dunes family at depth 1 (MANDATORY -- never plain topo-17)",
            grass_ecotone_fraction=exemplar["grass_ecotone_fraction"] if exemplar else None,
            lobe_area_ratio_grass_over_desert=waist["lobe_area_ratio_grass_over_desert"],
            note="the topo-17 plain-desert interior the RIBBON FALLACY prescribed DOES NOT EXIST "
                 "adjacent to grass anywhere in stock; the grass junction is a topo-16 skin -> dunes."),
        freestanding_plain_desert_floor=dict(
            n_masses=len(substantial),
            min_area_cells=min((r["area_cells"] for r in substantial), default=None),
            median_area_cells=(sorted(r["area_cells"] for r in substantial)[len(substantial) // 2]
                               if substantial else None),
            min_interior_fraction=round(min((r["interior_fraction"] for r in substantial), default=0), 4),
            min_inscribed_radius_cells=min((r["max_inscribed_radius_cells"] for r in substantial), default=None),
            all_grass_ecotone_fraction_zero=all(r["grass_ecotone_fraction"] == 0 for r in substantial),
            note="DISJOINT from grass -- these never border grass (a plain-desert lobe cannot meet "
                 "grass directly in stock). Use as the floor only if a Rung-F desert lobe is sited "
                 "AWAY from the grass margin (its own coast/dunes interface)."))

    numbers = dict(
        n_stock_desert_masses=len(mass_reports),
        n_biome_desert_masses=len(biome),
        n_dirt_variant_masses=len(dirt),

        # (iii) THE DISCRIMINATOR TABLE (stock biome-desert masses vs Rung-E staged ribbon)
        discriminator_table=disc_table,
        cell_shape_discriminators_separate_rung_e=any_shape_separates,
        decisive_discriminator=decisive,
        winning_cell_shape_discriminator=key,
        winning_discriminator=key,
        winning_discriminator_direction=disc_table[key]["direction"],
        winning_discriminator_stock_biome_min=disc_table[key]["stock_biome_min"],
        winning_discriminator_stock_biome_max=disc_table[key]["stock_biome_max"],
        winning_discriminator_rung_e=disc_table[key]["rung_e_value"],
        winning_discriminator_relative_margin=disc_table[key]["relative_margin"],
        winning_discriminator_separates=disc_table[key]["separates"],

        # train/test
        loo_splits=loo,
        loo_pass_count=loo_pass,
        loo_total=len(loo),
        rung_e_excluded_by_all_loo_floors=re_excluded_all,

        # (i) band depth
        known_site_grass_desert_boundary_edges=band["n_gd_boundary_edges"],
        known_site_max_desert_band_depth_cells=band["max_desert_band_depth_cells"],
        known_site_desert_band_profile_by_depth=band["desert_band_profile_by_depth"],
        known_site_first_depth_with_topo17=band["first_depth_with_topo17"],
        known_site_first_depth_with_dunes=band["first_depth_with_dunes_family"],

        # (ii) interior composition beyond the band
        known_site_beyond_band_family_by_depth=band["beyond_band_family_by_depth"],

        # THE INLAND-BACKING DISCRIMINATOR -- the separator the cell-shape metrics miss.
        # Stock's topo-16 grass-ecotone band backs onto DESERT-FAMILY interior (dunes); Rung E's
        # band backs onto GRASS again (a ribbon along a line). first_depth_with_topo17=None on stock
        # PROVES the grass junction never touches plain topo-17 desert.
        inland_backing_discriminator=dict(
            stock_known_site=dict(
                max_desert_band_depth_cells=band["max_desert_band_depth_cells"],
                first_depth_with_topo17=band["first_depth_with_topo17"],
                first_depth_with_dunes=band["first_depth_with_dunes_family"],
                beyond_band_family_by_depth=band["beyond_band_family_by_depth"]),
            rung_e=dict(
                max_desert_band_depth_cells=rung_e["band_depth"]["max_desert_band_depth_cells"],
                first_depth_with_topo17=rung_e["band_depth"]["first_depth_with_topo17"],
                first_depth_with_dunes=rung_e["band_depth"]["first_depth_with_dunes_family"],
                beyond_band_family_by_depth=rung_e["band_depth"]["beyond_band_family_by_depth"]),
            interpretation="stock band -> dunes/desert interior; Rung E band -> grass (ribbon)"),

        # (iv) coast
        min_mass_size_with_own_coast_cells=min_coast_size,
        n_biome_masses_with_own_coast=len(biome_with_coast),
        biome_masses_own_coast_fractions={str(r["mass_index"]): r["own_coast_fraction"] for r in biome},

        # (v) waist
        waist=waist,

        # Rung E full
        rung_e_desert=rung_e,

        # CONTRACT floors -- RAW min-over-all-biome-masses (trivial; tiny fragments drag it down).
        # Prefer CONTRACT_summary below for gate-ready numbers.
        CONTRACT_raw_min_desert_mass_footprint_cells=disc_table["area_cells"]["stock_biome_min"],
        CONTRACT_raw_interior_fraction_floor=disc_table["interior_fraction"]["stock_biome_min"],
        CONTRACT_raw_max_inscribed_radius_floor_cells=disc_table["max_inscribed_radius_cells"]["stock_biome_min"],
        CONTRACT_band_depth_cells_max_at_grass_junction=band["max_desert_band_depth_cells"],
        # gate-ready CONTRACT numbers (the deliverable)
        CONTRACT_summary=contract_summary,
    )

    out = dict(
        meta=dict(script="contract_mass_interior.py", read_only=True,
                  n_land_blocks=len(S["bms"]), n_tris=len(S["all_tris"]),
                  n_desert_cells=len(S["desert_cells"]), n_pure_desert_cells=len(S["pure_desert"]),
                  cell_size_u=CELL, block_size_u=BLOCK,
                  discriminator_definitions=dict(
                      area_cells="count of 4u desert-family cells in the mass",
                      interior_fraction="pure-desert cells whose 8 Moore neighbours are all desert cells / area",
                      max_inscribed_radius_cells="max Chebyshev distance-transform value within the mass (8-conn)",
                      own_coast_fraction="4-conn boundary edges facing open ocean/absent / total perimeter edges"),
                  klass_definitions=dict(
                      biome_desert="dominant topo in {16,17} (genuine desert biome vocabulary)",
                      dirt_variant="dominant topo in {19,20} (dirt gameplay-variant tiles; may be roads)")),
        mass_reports=mass_reports,
        band_depth=band,
        waist=waist,
        rung_e=rung_e,
        discriminator_analysis=dict(table=disc_table, winning=key, loo=loo,
                                    rung_e_excluded_by_all_loo_floors=re_excluded_all),
        numbers=numbers,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")
    # concise console summary
    print("\n==== DISCRIMINATOR TABLE (stock biome-desert masses vs Rung-E staged ribbon) ====")
    for k, v in disc_table.items():
        print(f"  {k:28s} stock[min={v['stock_biome_min']} med={v['stock_biome_median']} "
              f"max={v['stock_biome_max']}]  RungE={v['rung_e_value']}  sep={v['separates']} "
              f"{v['direction']} rel_margin={v['relative_margin']}")
    print(f"\n  cell-shape discriminators separate Rung E from stock: {any_shape_separates}")
    print(f"  (all 4 cell-shape metrics: Rung E sits INSIDE the stock biome-desert band -- "
          f"NO cell-resolution separation)")
    print(f"\n  DECISIVE discriminator: {decisive['name']}")
    print(f"    stock known-site value = {decisive['stock_known_site_value']} (dunes interior inland), "
          f"Rung E value = {decisive['rung_e_value']} (grass inland = ribbon)")
    print(f"    separates = {decisive['separates']}   [{decisive['caveat'][:60]}...]")


if __name__ == "__main__":
    main()
