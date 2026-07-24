"""INDEPENDENT FALSIFIER for LANE C (interior / mass anatomy) -- CONTRACT round (2026-07-23).

Falsifier discipline: re-derives Lane C's gate-bound + surprising numbers from RAW BYTES with an
INDEPENDENT implementation. Reuses ONLY the calibrated atomic tri classifier (seam_null_recon.py's
FAM_OF / classify_tri / load_tris / edge_index -- the "instrument", identical to what every lane
used) and reimplements ALL census / metric / band / coast logic here. Does NOT import or read the
lane script (contract_mass_interior.py) until numbers are computed.

READ-ONLY vs the game install (X.read_block stock disc-1 bytes) + reads the already-staged Rung E
override meshes under studies/.../out/rung_e/ (a study artifact, not the game install). ZERO writes
except out/contract_mass/falsify_c.json.

Run:  py studies/overworld-topography/contract_mass_falsify_c_indep.py
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                        # noqa: E402  the calibrated instrument
from ff9mapkit.world import extract as X              # noqa: E402
from ff9mapkit.world import mesh as M                 # noqa: E402

OUT = HERE / "out" / "contract_mass" / "falsify_c.json"
RUNG_E_DIR = HERE / "out" / "rung_e" / "FF9CustomMap-world"
CELL = 4.0
KNOWN_SITE_BLOCKS = {(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)}

BIOME_TOPO = {16, 17}
DIRT_TOPO = {19, 20}


def cheby(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def components(node_set, radius=1):
    nodes = sorted(node_set)
    bw = max(1, radius)
    buckets = defaultdict(list)
    for c in nodes:
        buckets[(c[0] // bw, c[1] // bw)].append(c)
    seen = set()
    comps = []
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


def disc_metrics(cells, grass_cells):
    cs = set(cells)
    n = len(cs)
    if n == 0:
        return dict(area=0, interior_fraction=0.0, max_inscribed_radius=0, grass_ecotone_fraction=0.0)
    n_interior = 0
    n_grass_ec = 0
    for c in cs:
        full = True
        gtouch = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (c[0] + dx, c[1] + dy)
                if nb not in cs:
                    full = False
                if nb in grass_cells:
                    gtouch = True
        if full:
            n_interior += 1
        if gtouch:
            n_grass_ec += 1
    dist = {}
    frontier = set()
    for c in cs:
        on_edge = any((c[0] + dx, c[1] + dy) not in cs
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1) if not (dx == 0 and dy == 0))
        if on_edge:
            dist[c] = 1
            frontier.add(c)
    q = deque(frontier)
    while q:
        c = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (c[0] + dx, c[1] + dy)
                if nb in cs and nb not in dist:
                    dist[nb] = dist[c] + 1
                    q.append(nb)
    max_r = max(dist.values()) if dist else 0
    return dict(area=n, interior_fraction=round(n_interior / n, 4),
                max_inscribed_radius=max_r,
                grass_ecotone_fraction=round(n_grass_ec / n, 4))


def load_rung_e_terrain():
    tris = []
    bms = {}
    for p in sorted(RUNG_E_DIR.rglob("Block[[]*[]][[]*[]] Terrain.ff9mesh")):
        m = re.search(r"Block\[(\d+)\]\[(\d+)\] Terrain", p.name)
        if not m:
            continue
        bx, by = int(m.group(1)), int(m.group(2))
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        bms[(bx, by)] = bm
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(pt[0] for pt in w) / 3.0
            cz = sum(pt[2] for pt in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            tris.append(dict(block=(bx, by), topo=topo, fam=fam, w=w, uv=uv, cell=cell))
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris, bms


def main():
    t0 = time.time()
    findings = []
    print(f"game root: {SNR.GAME_ROOT}")
    land = X.list_blocks(disc=1)
    print(f"land blocks: {len(land)}")
    all_tris, bms, _ = SNR.load_tris(land, source="stock")
    print(f"tris map-wide: {len(all_tris)}  ({time.time()-t0:.1f}s)")

    cell_fams = defaultdict(set)
    cell_topo = defaultdict(Counter)
    cell_block = {}
    for t in all_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
        cell_topo[t["cell"]][t["topo"]] += 1
        cell_block[t["cell"]] = t["block"]

    desert_cells = {c for c, f in cell_fams.items() if "desert" in f}
    grass_cells = {c for c, f in cell_fams.items() if "grass" in f}
    dunes_cells = {c for c, f in cell_fams.items() if "dunes" in f}
    print(f"desert {len(desert_cells)} grass {len(grass_cells)} dunes {len(dunes_cells)}")

    # (1) MASS CENSUS
    masses = components(desert_cells, 1)
    mass_info = []
    for comp in masses:
        cs = set(comp)
        topo = Counter()
        for c in comp:
            for tp, n in cell_topo[c].items():
                if SNR.FAM_OF.get(tp) == "desert":
                    topo[tp] += n
        biome_n = sum(topo[t] for t in topo if t in BIOME_TOPO)
        dirt_n = sum(topo[t] for t in topo if t in DIRT_TOPO)
        klass = "biome" if biome_n >= dirt_n and biome_n > 0 else ("dirt" if dirt_n > 0 else "other")
        grass_adj = any((c[0] + dx, c[1] + dy) in grass_cells
                        for c in comp for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if not (dx == 0 and dy == 0))
        mass_info.append(dict(n_cells=len(comp), topo=dict(sorted(topo.items())), klass=klass,
                              grass_adjacent=grass_adj, cells=cs))
    mass_info.sort(key=lambda m: -m["n_cells"])
    n_biome = sum(1 for m in mass_info if m["klass"] == "biome")
    n_dirt = sum(1 for m in mass_info if m["klass"] == "dirt")
    n_other = sum(1 for m in mass_info if m["klass"] == "other")
    print(f"\nMASS CENSUS: {len(mass_info)} -> biome={n_biome} dirt={n_dirt} other={n_other}")
    for m in mass_info[:10]:
        print(f"  n={m['n_cells']:4d} {m['klass']:5s} grass_adj={m['grass_adjacent']} topo={m['topo']}")

    # (2) DECISIVE
    known_mass = None
    for m in mass_info:
        if {cell_block[c] for c in m["cells"] if c in cell_block} & KNOWN_SITE_BLOCKS:
            known_mass = m
            break
    assert known_mass, "CALIBRATION FAIL"
    known_topo_ids = set(known_mass["topo"])
    pure_topo16 = known_topo_ids == {16}
    has_17 = 17 in known_topo_ids
    print(f"\nKNOWN mass: {known_mass['n_cells']} cells topo={known_mass['topo']} "
          f"pure16={pure_topo16} has17={has_17}")

    topo17_cells = {c for c in cell_topo if 17 in cell_topo[c]}
    kmcells = known_mass["cells"]
    nearest17 = min(((cheby(c, c17), c17) for c17 in topo17_cells for c in kmcells),
                    default=None)
    nearest17_u = nearest17[0] * CELL if nearest17 else None
    print(f"  nearest topo-17: {nearest17[0] if nearest17 else None} cells = {nearest17_u}u")

    inland_fams_d1 = Counter()
    for c in kmcells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (c[0] + dx, c[1] + dy)
                if nb in kmcells:
                    continue
                for f in cell_fams.get(nb, ()):
                    inland_fams_d1[f] += 1
    dunes_adjacent = "dunes" in inland_fams_d1
    print(f"  cheby=1 neighbour families: {dict(inland_fams_d1)}  dunes_adj={dunes_adjacent}")

    edge_owner = SNR.edge_index(all_tris)
    gd_edges = [(e, ow) for e, ow in edge_owner.items()
                if {all_tris[g]["fam"] for g in ow} == {"grass", "desert"}]
    gd_bd_desert = set()
    for e, ow in gd_edges:
        for g in ow:
            if all_tris[g]["fam"] == "desert":
                gd_bd_desert.add(all_tris[g]["cell"])
    seed = gd_bd_desert & kmcells
    depth = {c: 0 for c in seed}
    q = deque(seed)
    while q:
        c = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (c[0] + dx, c[1] + dy)
                if nb in kmcells and nb not in depth:
                    depth[nb] = depth[c] + 1
                    q.append(nb)
    tris_by_depth = Counter()
    topo_by_depth = defaultdict(Counter)
    site_tris = [t for t in all_tris if t["cell"] in kmcells]
    for t in site_tris:
        d = depth.get(t["cell"])
        if d is None:
            continue
        tris_by_depth[d] += 1
        topo_by_depth[d][t["topo"]] += 1
    max_depth = max(depth.values()) if depth else 0
    taper = [tris_by_depth.get(d, 0) for d in range(max_depth + 1)]
    frac16 = {}
    for d in range(max_depth + 1):
        tot = sum(topo_by_depth[d].values())
        frac16[d] = round(topo_by_depth[d].get(16, 0) / tot, 4) if tot else None
    print(f"  band_i max_depth={max_depth} taper={taper} frac16={frac16}")

    # (3) COAST cross-check
    core_ring = sorted({(bx + dx, by + dy) for (bx, by) in KNOWN_SITE_BLOCKS
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)})
    coastal = set(X.list_coastal_donors(disc=1, beach_only=False))
    sea_pts = []
    for (bx, by) in core_ring:
        if (bx, by) not in coastal:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for part in ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2"):
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except (ValueError, FileNotFoundError):
                continue
            for v in bm.verts:
                sea_pts.append((v[0] + ox, v[2] + oz))
    bd_cells = gd_bd_desert & kmcells
    cc_min = min((math.hypot(c[0] * CELL + 2 - sx, c[1] * CELL + 2 - sz)
                  for c in bd_cells for (sx, sz) in sea_pts), default=None)
    tc_min = None
    for t in site_tris:
        if t["topo"] != 16:
            continue
        cx = sum(p[0] for p in t["w"]) / 3.0
        cz = sum(p[2] for p in t["w"]) / 3.0
        for (sx, sz) in sea_pts:
            d = math.hypot(cx - sx, cz - sz)
            if tc_min is None or d < tc_min:
                tc_min = d
    print(f"\nCOAST {len(sea_pts)} verts: cellcentre={cc_min:.2f}u tricentroid={tc_min:.2f}u")

    # (4) waist lobes
    ground_cells = set(cell_fams)
    site_seed = next(iter(kmcells))
    land_comp = None
    for comp in components(ground_cells, 1):
        if site_seed in set(comp):
            land_comp = set(comp)
            break
    grass_lobe = len([c for c in land_comp if "grass" in cell_fams[c]])
    desert_lobe = len([c for c in land_comp if "desert" in cell_fams[c]])
    dunes_lobe = len([c for c in land_comp if "dunes" in cell_fams[c]])
    ratio_g_d = round(grass_lobe / desert_lobe, 3) if desert_lobe else None
    print(f"WAIST land {len(land_comp)}: grass={grass_lobe} desert={desert_lobe} "
          f"dunes={dunes_lobe} g/d={ratio_g_d}")

    # (5) stock shape ranges + (6) Rung E
    biome_masses = [m for m in mass_info if m["klass"] == "biome"]
    stock_metrics = [disc_metrics(m["cells"], grass_cells) for m in biome_masses]

    def mmm(key):
        vals = sorted(x[key] for x in stock_metrics)
        n = len(vals)
        med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        return [vals[0], round(med, 4), vals[-1]]

    stock_ranges = {k: mmm(k) for k in ("area", "interior_fraction", "max_inscribed_radius",
                                        "grass_ecotone_fraction")}
    print(f"\nSTOCK biome ranges: {stock_ranges}")

    re_tris, _ = load_rung_e_terrain()
    re_topo = Counter(t["topo"] for t in re_tris)
    re_cell_fam = defaultdict(set)
    re_cell_topo = defaultdict(Counter)
    for t in re_tris:
        if t["fam"]:
            re_cell_fam[t["cell"]].add(t["fam"])
        re_cell_topo[t["cell"]][t["topo"]] += 1
    re_desert_cells = {c for c, f in re_cell_fam.items() if "desert" in f}
    re_grass_cells = {c for c, f in re_cell_fam.items() if "grass" in f}
    re_desert_topo = Counter()
    for c in re_desert_cells:
        for tp, n in re_cell_topo[c].items():
            if SNR.FAM_OF.get(tp) == "desert":
                re_desert_topo[tp] += n
    re_comps = components(re_desert_cells, 1)
    re_largest = max(re_comps, key=len) if re_comps else []
    re_metric = disc_metrics(set(re_largest), re_grass_cells)
    print(f"RUNG E terrain tris {len(re_tris)} topo_top={dict(sorted(re_topo.items(),key=lambda kv:-kv[1])[:6])}")
    print(f"  desert cells {len(re_desert_cells)} topo {dict(re_desert_topo)} "
          f"comps {len(re_comps)} largest {len(re_largest)} metric {re_metric}")

    sep = {}
    for k in ("area", "interior_fraction", "max_inscribed_radius", "grass_ecotone_fraction"):
        lo, _, hi = stock_ranges[k]
        v = re_metric[k]
        sep[k] = dict(rung_e=v, stock_min=lo, stock_max=hi, inside=bool(lo <= v <= hi))
    any_sep = any(not s["inside"] for s in sep.values())
    print(f"SEP: {sep} any_separates={any_sep}")

    if not pure_topo16:
        findings.append(f"known mass NOT pure topo-16: {known_mass['topo']}")
    if has_17:
        findings.append("known mass CONTAINS topo-17")
    if not dunes_adjacent:
        findings.append(f"known mass NOT dunes-adjacent: {dict(inland_fams_d1)}")

    out = dict(
        meta=dict(script="contract_mass_falsify_c_indep.py", n_land=len(land),
                  n_tris=len(all_tris), elapsed_s=round(time.time() - t0, 1)),
        mass_census=dict(n_masses=len(mass_info), n_biome=n_biome, n_dirt=n_dirt, n_other=n_other,
                         top=[dict(n=m["n_cells"], klass=m["klass"], grass_adj=m["grass_adjacent"],
                                   topo=m["topo"]) for m in mass_info[:12]]),
        decisive=dict(known_mass_cells=known_mass["n_cells"], known_mass_topo=known_mass["topo"],
                      pure_topo16=pure_topo16, contains_topo17=has_17,
                      nearest_topo17_cells=nearest17[0] if nearest17 else None,
                      nearest_topo17_u=nearest17_u, inland_neighbours=dict(inland_fams_d1),
                      dunes_adjacent=dunes_adjacent, band_i_max_depth=max_depth,
                      band_i_tri_taper=taper, band_i_frac_topo16_by_depth=frac16,
                      band_i_topo_by_depth={str(d): dict(topo_by_depth[d]) for d in range(max_depth + 1)}),
        coast_crosscheck=dict(n_sea_verts=len(sea_pts), n_boundary_desert_cells=len(bd_cells),
                              cellcentre_u=round(cc_min, 2) if cc_min else None,
                              tricentroid_u=round(tc_min, 2) if tc_min else None),
        waist=dict(landmass_cells=len(land_comp), grass_lobe=grass_lobe, desert_lobe=desert_lobe,
                   dunes_lobe=dunes_lobe, grass_over_desert=ratio_g_d),
        shape_discriminators=dict(stock_biome_ranges=stock_ranges, rung_e=re_metric,
                                  separation=sep, any_metric_separates=any_sep),
        rung_e=dict(n_terrain_tris=len(re_tris), topo_hist=dict(re_topo),
                    desert_cells=len(re_desert_cells), desert_topo=dict(re_desert_topo),
                    n_components=len(re_comps), largest_component=len(re_largest)),
        findings=findings,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nfindings: {findings}\n-> {OUT}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
