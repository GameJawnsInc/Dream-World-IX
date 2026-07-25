"""RUNG F AFTERMATH -- LANE C: THE STOCK FUNDAMENTALS CENSUS (2026-07-24).

Independent forensics round for THE UNTEXTURED-FILL DEFECT (playtest: "a big weird mess -- strange
solid green 'floors' that don't appear anywhere in the game"; a crater dunes mass with flat facets
and a sky-toned pool on top; one SE coast arc reads correct). Two suspects: (1) synthesized fill/
stitch/apron tris emitted without the per-cell mains UV decode that gives stock terrain its grass
tiles (renders flat/solid-color); (2) sea-layer plan overlap onto land (translucent wedges).

This round does NOT re-examine Rung F's own provenance (that is Phase 2) -- it builds the
STOCK REFERENCE the Phase-2 provenance split will be judged against: over a stratified sample of
REAL stock terrain, measure (a) UV-VALIDITY (fraction of terrain tris whose UVs land in a
catalogued family rect), (b) UV DEGENERACY (near-zero-UV-area tris; UV-area/true-3D-area ratio
stats -- the "flat solid colour" signature), (c) SEA/LAND PLAN-COVERAGE overlap per 4u cell (the
translucent-wedge suspect). Then runs the identical instrument, coarse (no provenance split), on
the 20 Rung F staged blocks.

Bootstrap/import + UV-classification machinery copied verbatim in spirit from
rung_f_falsify.py / seam_null_recon.py (FAM_OF, classify_tri, RECTS, GD/DD strip constants,
X.read_block, M.blockmesh_from_ff9mesh) -- reused, not reimplemented, so this round's numbers are
directly comparable to the earlier gate work. The one NEW piece is the wall/rock-band
sub-classifier (ISL.ROCK_U/ROCK_V + each family's own wall_du/wall_dv) added here to separate
"rock cliff face -- a real catalogued vocabulary the SNR classifier was never taught" from
"genuinely uncatalogued" inside the leftover "other" bucket.

READ-ONLY vs the game install for STOCK reference bytes (the toolkit's standing convention --
every cited script in this arc reads stock via X.read_block this way). The RUNG F SPECIMEN is
read EXCLUSIVELY from the staged tree (out/rung_f/FF9CustomMap-world), never from the install, per
this round's brief. No positive controls are available (see main() banner) -- the only staged
trees under studies/overworld-topography/out/ belong to Rung D and Rung E, both offline-eye
REJECTED before any deploy, so neither qualifies as a "previously deployed, in-game-proven" island;
this round proceeds stock-vs-specimen only, as the brief's own fallback instructs.

Writes only out/rung_f/uvf_stock_census.json + this script.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                      # noqa: E402
from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M               # noqa: E402
from ff9mapkit.world import grassland as G          # noqa: E402
from ff9mapkit.world import island as ISL           # noqa: E402

CELL = 4.0
STAGED = HERE / "out" / "rung_f" / "FF9CustomMap-world"
OUT = HERE / "out" / "rung_f" / "uvf_stock_census.json"

TERRAIN = "Terrain"
SEA_PARTS = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1", "Beach2")
ALL_PARTS = (TERRAIN,) + SEA_PARTS

ZERO_UV_THRESH = 1e-6          # "near-zero UV area" per the brief, in atlas-unit-square terms
MIN_AREA3D = 1e-4              # guard for the uv/plan and uv/area3d ratio denominators


def log(m): print(m, flush=True)


# ============================================================================================
# STRATIFIED STOCK SAMPLE -- every block cited by name below is a documented real block from an
# earlier proven census in this same study directory (not guessed): see the function docstring
# for the exact source of each list.
# ============================================================================================
def sample_groups() -> dict:
    """The stratified stock sample. Provenance of each block list (so the numbers are
    re-derivable, not folklore):
      * pure_grass -- grassland._STAMP_BLOCKS (the 10 grass-stamp blocks the mint's meadow-patch
        carry is captured from) + Uaho (0,0) + (13,3) (both cited elsewhere in this study as real
        grass-majority blocks).
      * grass_coast -- transplant._PREFAB_CANDIDATES: the beach-donor blocks proven (by an
        earlier map-wide screen) to carry the FULLEST coastal part sets (beach1+sea1..sea5) on a
        grass-family landmass.
      * junction -- the ONE real grass|desert cluster this whole arc has been chasing: all 6 core
        blocks of (13-15,11-12) (seam_null_recon.py's own PART B footprint).
      * dunes -- 4 of the 6 real desert|dunes seam blocks from biome_seam_anatomy.py's PAIRS
        table (the other 2, (13,12)/(14,12), are already in `junction`).
      * snow -- 2 of the 8 real Lost-Continent snow blocks from scrub_arrangement_probe.py's
        SPEC["snow"].
      * desert -- 2 of the 5 real blocks from grassland.DESERT_MAINS_SECONDARY (a documented
        pure-desert cluster, disjoint from the junction blocks).
    """
    pure_grass = sorted(set(G._STAMP_BLOCKS) | {(0, 0), (13, 3)})
    grass_coast = [(7, 17), (10, 17), (16, 5), (13, 8), (9, 17), (3, 13)]
    junction = [(13, 11), (14, 11), (15, 11), (13, 12), (14, 12), (15, 12)]
    dunes = [(18, 3), (19, 3), (19, 4), (18, 4)]
    snow = [(6, 2), (7, 3)]
    desert = [(11, 4), (12, 5)]
    return dict(pure_grass=pure_grass, grass_coast=grass_coast, junction=junction,
                dunes=dunes, snow=snow, desert=desert)


# ============================================================================================
# wall/rock-band sub-classifier -- NOT in seam_null_recon.RECTS (that table only covers the
# family MAINS + the grass|desert / desert|dunes strip decals). A terrain tri wearing the grey
# rock texture (topo 58) or any wall-adjacent tri translated per its ground family's wall_du/
# wall_dv is a REAL catalogued FF9 vocabulary item, not an unclassified anomaly -- so it must be
# pulled OUT of the "other" bucket before that bucket is reported as "uncatalogued".
# ============================================================================================
def _wall_rect(fam):
    g = G.GROUNDS[fam]
    lo_u, hi_u = min(ISL.ROCK_U) + g["wall_du"], max(ISL.ROCK_U) + g["wall_du"]
    lo_v, hi_v = min(ISL.ROCK_V) + g["wall_dv"], max(ISL.ROCK_V) + g["wall_dv"]
    return (lo_u, lo_v, hi_u, hi_v)


WALL_RECTS = {fam: _wall_rect(fam) for fam in G.GROUNDS}


def classify_tri_plus(fam, uv3):
    """SNR.classify_tri, with the "other" bucket split into wall_rock(<fam>) vs truly
    other_uncatalogued via WALL_RECTS. Returns (label, detail)."""
    cls, det = SNR.classify_tri(fam, uv3)
    if cls != "other":
        return (cls, det)
    for wfam, rect in WALL_RECTS.items():
        if SNR.in_rect(uv3, rect):
            return ("wall_rock", wfam)
    return ("other_uncatalogued", None)


# ============================================================================================
# loaders
# ============================================================================================
def load_part(bx, by, part, *, staged: bool):
    """(BlockMesh|None, src). staged=True reads EXCLUSIVELY from the Rung F staged tree (a
    missing override file there means "no override, not covered" -- never a fallback to the
    live install for the specimen). staged=False reads real stock disc-1 bytes."""
    if staged:
        p = STAGED / M.override_relpath(1, bx, by, part=part)
        if not p.exists():
            return None, None
        return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=part.lower()), "staged"
    try:
        return X.read_block(bx, by, disc=1, part=part.lower()), "stock"
    except (ValueError, FileNotFoundError):
        return None, None


def part_tris(bm, bx, by, part):
    ox, oz = X.block_world_origin(bx, by)
    is_terrain = part.lower() == "terrain"
    out = []
    verts, uvs, tans = bm.verts, bm.uvs, bm.tangents
    for tri in bm.tris:
        w = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
        uv = [(float(uvs[j][0]), float(uvs[j][1])) for j in tri] if uvs else [(0.0, 0.0)] * 3
        topo = fam = None
        if is_terrain and tans:
            idall = int(round(tans[tri[0]][0]))
            topo = X.decode_id(idall)["topograph"]
            fam = SNR.FAM_OF.get(topo)
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        out.append(dict(topo=topo, fam=fam, w=w, uv=uv,
                        cell=(math.floor(cx / CELL), math.floor(cz / CELL))))
    return out


# ============================================================================================
# per-tri geometry
# ============================================================================================
def uv_area(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def plan_area(w3):
    (x0, _y0, z0), (x1, _y1, z1), (x2, _y2, z2) = w3
    return abs((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / 2.0


def area3d(w3):
    a, b, c = w3
    e1 = tuple(b[k] - a[k] for k in range(3))
    e2 = tuple(c[k] - a[k] for k in range(3))
    cx = e1[1] * e2[2] - e1[2] * e2[1]
    cy = e1[2] * e2[0] - e1[0] * e2[2]
    cz = e1[0] * e2[1] - e1[1] * e2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def stats(vals):
    if not vals:
        return dict(n=0)
    return dict(n=len(vals), mean=sum(vals) / len(vals), min=min(vals), max=max(vals),
                p10=pct(vals, 10), p50=pct(vals, 50), p90=pct(vals, 90))


# ============================================================================================
# per-part summary (UV degeneracy always; UV-validity only for Terrain)
# ============================================================================================
def summarize_part(part, tris_info, src):
    n = len(tris_info)
    if n == 0:
        return dict(src=src, n_tris=0)
    uvA = [uv_area(t["uv"]) for t in tris_info]
    planA = [plan_area(t["w"]) for t in tris_info]
    a3d = [area3d(t["w"]) for t in tris_info]
    zero_uv = sum(1 for a in uvA if a < ZERO_UV_THRESH)
    ratio_a3d = [uvA[i] / a3d[i] for i in range(n) if a3d[i] >= MIN_AREA3D]
    ratio_plan = [uvA[i] / planA[i] for i in range(n) if planA[i] >= MIN_AREA3D]
    n_thin3d = n - len(ratio_a3d)          # true-3D-degenerate tris (collinear verts, real bug)
    n_vertical = sum(1 for i in range(n) if a3d[i] >= MIN_AREA3D and planA[i] < MIN_AREA3D)
    out = dict(src=src, n_tris=n,
               uv_area=stats(uvA), plan_area=stats(planA), area3d=stats(a3d),
               zero_uv_area_frac=zero_uv / n, n_zero_uv_area=zero_uv,
               n_thin3d_degenerate=n_thin3d,     # collinear-in-3D (a real mesh defect if >0)
               n_vertical_walls=n_vertical,       # plan~0, area3d>0 -- EXPECTED (cliff faces), not a defect
               ratio_uv_to_area3d=stats(ratio_a3d),
               ratio_uv_to_planarea=stats(ratio_plan))
    if part == TERRAIN:
        classes = Counter()
        topo_hist = Counter()
        uncls_topo_hist = Counter()
        uncls_u, uncls_v = [], []
        for t in tris_info:
            topo_hist[t["topo"]] += 1
            label, det = classify_tri_plus(t["fam"], t["uv"])
            key = f"{label}:{det}" if det is not None else label
            classes[key] += 1
            if label == "other_uncatalogued":
                uncls_topo_hist[t["topo"]] += 1
                for (u, v) in t["uv"]:
                    uncls_u.append(u)
                    uncls_v.append(v)
        n_uncatalogued = classes.get("other_uncatalogued", 0)
        out["uv_validity"] = dict(
            lawful_fraction=(n - n_uncatalogued) / n,
            other_uncatalogued_fraction=n_uncatalogued / n,
            classes=dict(classes.most_common()),
            topo_hist=dict(topo_hist.most_common()),
            uncatalogued_topo_hist=dict(uncls_topo_hist.most_common(12)),
            uncatalogued_uv_bbox=(dict(u=[min(uncls_u), max(uncls_u)], v=[min(uncls_v), max(uncls_v)])
                                  if uncls_u else None))
    return out


# ============================================================================================
# per-block / per-stratum measurement
# ============================================================================================
def measure_block(bx, by, *, staged: bool) -> dict:
    parts_out = {}
    land_cells, sea_cells = set(), set()
    sea_cells_by_part = {}
    for part in ALL_PARTS:
        bm, src = load_part(bx, by, part, staged=staged)
        if bm is None or not bm.tris:
            parts_out[part] = dict(src=src, n_tris=0)
            continue
        tris_info = part_tris(bm, bx, by, part)
        parts_out[part] = summarize_part(part, tris_info, src)
        cells = {t["cell"] for t in tris_info}
        if part == TERRAIN:
            land_cells |= cells
        else:
            sea_cells |= cells
            sea_cells_by_part[part] = sorted(cells)
    overlap = land_cells & sea_cells
    return dict(block=[bx, by], parts=parts_out,
               plan_coverage=dict(n_land_cells=len(land_cells), n_sea_cells=len(sea_cells),
                                  n_overlap_cells=len(overlap),
                                  overlap_frac_of_land=(len(overlap) / len(land_cells) if land_cells else None),
                                  overlap_frac_of_sea=(len(overlap) / len(sea_cells) if sea_cells else None),
                                  overlap_cells_sample=sorted(overlap)[:20],
                                  sea_cells_by_part_counts={p: len(c) for p, c in sea_cells_by_part.items()}))


def aggregate_stratum(name, blocks, *, staged: bool) -> dict:
    per_block = [measure_block(bx, by, staged=staged) for (bx, by) in blocks]
    # pool every terrain tri across the stratum for one aggregate UV-validity/degeneracy read
    pooled = {part: [] for part in ALL_PARTS}
    land_cells_total, sea_cells_total = 0, 0
    overlap_total = 0
    missing_blocks = []
    for (bx, by), pb in zip(blocks, per_block):
        any_data = any(pb["parts"][p]["n_tris"] for p in ALL_PARTS)
        if not any_data:
            missing_blocks.append([bx, by])
        for part in ALL_PARTS:
            bm, src = load_part(bx, by, part, staged=staged)
            if bm is not None and bm.tris:
                pooled[part].extend(part_tris(bm, bx, by, part))
        land_cells_total += pb["plan_coverage"]["n_land_cells"]
        sea_cells_total += pb["plan_coverage"]["n_sea_cells"]
        overlap_total += pb["plan_coverage"]["n_overlap_cells"]
    pooled_summary = {part: summarize_part(part, tris_info, "pooled")
                      for part, tris_info in pooled.items()}
    return dict(name=name, n_blocks=len(blocks), blocks=[list(b) for b in blocks],
               missing_blocks=missing_blocks,
               per_block=per_block,
               pooled=pooled_summary,
               plan_coverage_sum=dict(n_land_cells_summed=land_cells_total,
                                      n_sea_cells_summed=sea_cells_total,
                                      n_overlap_cells_summed=overlap_total,
                                      overlap_frac_of_land_summed=(overlap_total / land_cells_total
                                                                   if land_cells_total else None)))


# ============================================================================================
FOOTPRINT = sorted((bx, by) for bx in range(0, 5) for by in range(16, 20))     # the 20 Rung F blocks


def main():
    result = dict()

    log("=" * 100)
    log("POSITIVE CONTROLS -- checked studies/overworld-topography/out/ for a prior in-game-proven")
    log("staged FF9CustomMap-world tree. Found: out/rung_d/FF9CustomMap-world, out/rung_e/FF9CustomMap-world.")
    log("Both are DISQUALIFIED: Rung D and Rung E were BOTH rejected by the offline eye BEFORE any")
    log("deploy (CLAUDE.md SS10: 'Rung D ... ALSO REJECTED', 'Rung E ... BUILT ... then ALSO REJECTED at")
    log("zero playtest cost') -- neither was ever deployed to the live game, let alone in-game-proven.")
    log("No qualifying positive-control tree exists under out/. Per the brief's own fallback, proceeding")
    log("STOCK-vs-SPECIMEN only; controls section is reported as unavailable (not skipped silently).")
    result["controls"] = dict(available=False,
                              checked=["out/rung_d/FF9CustomMap-world", "out/rung_e/FF9CustomMap-world"],
                              reason=("both are pre-deploy offline-eye REJECTIONS (Rung D + Rung E), not "
                                     "in-game-proven islands -- no qualifying staged tree exists under "
                                     "studies/overworld-topography/out/"))

    log("=" * 100)
    log("STOCK STRATIFIED SAMPLE")
    groups = sample_groups()
    for name, blocks in groups.items():
        log(f"-- {name}: {len(blocks)} blocks {blocks}")
        result[name] = aggregate_stratum(name, blocks, staged=False)
        pt = result[name]["pooled"][TERRAIN]
        pc = result[name]["plan_coverage_sum"]
        log(f"   terrain n={pt.get('n_tris')} lawful_frac="
            f"{pt.get('uv_validity', {}).get('lawful_fraction')} zero_uv_frac={pt.get('zero_uv_area_frac')} "
            f"land_cells={pc['n_land_cells_summed']} sea_cells={pc['n_sea_cells_summed']} "
            f"overlap={pc['n_overlap_cells_summed']} missing_blocks={result[name]['missing_blocks']}")

    log("=" * 100)
    log(f"SPECIMEN -- all {len(FOOTPRINT)} Rung F staged blocks {FOOTPRINT} (staged tree ONLY, coarse)")
    result["specimen_rung_f"] = aggregate_stratum("specimen_rung_f", FOOTPRINT, staged=True)
    pt = result["specimen_rung_f"]["pooled"][TERRAIN]
    pc = result["specimen_rung_f"]["plan_coverage_sum"]
    log(f"   terrain n={pt.get('n_tris')} lawful_frac={pt.get('uv_validity', {}).get('lawful_fraction')} "
        f"zero_uv_frac={pt.get('zero_uv_area_frac')} land_cells={pc['n_land_cells_summed']} "
        f"sea_cells={pc['n_sea_cells_summed']} overlap={pc['n_overlap_cells_summed']} "
        f"missing_blocks={result['specimen_rung_f']['missing_blocks']}")

    # ---- headline numbers to seed gate thresholds -------------------------------------------
    stock_strata = ["pure_grass", "grass_coast", "junction", "dunes", "snow", "desert"]
    lawful_fracs = [result[s]["pooled"][TERRAIN].get("uv_validity", {}).get("lawful_fraction")
                    for s in stock_strata if result[s]["pooled"][TERRAIN].get("n_tris")]
    zero_uv_fracs = [result[s]["pooled"][p].get("zero_uv_area_frac")
                     for s in stock_strata for p in ALL_PARTS
                     if result[s]["pooled"][p].get("n_tris")]
    overlap_fracs = [result[s]["plan_coverage_sum"]["overlap_frac_of_land_summed"]
                     for s in stock_strata
                     if result[s]["plan_coverage_sum"]["overlap_frac_of_land_summed"] is not None]
    result["headline"] = dict(
        stock_lawful_fraction_floor=min(lawful_fracs) if lawful_fracs else None,
        stock_lawful_fraction_by_stratum={s: result[s]["pooled"][TERRAIN].get("uv_validity", {}).get("lawful_fraction")
                                          for s in stock_strata},
        stock_zero_uv_area_ceiling=max(zero_uv_fracs) if zero_uv_fracs else None,
        stock_zero_uv_area_by_stratum_terrain={s: result[s]["pooled"][TERRAIN].get("zero_uv_area_frac")
                                               for s in stock_strata},
        stock_sea_land_overlap_ceiling=max(overlap_fracs) if overlap_fracs else 0.0,
        stock_sea_land_overlap_by_stratum={s: result[s]["plan_coverage_sum"]["overlap_frac_of_land_summed"]
                                           for s in stock_strata},
        specimen_lawful_fraction=result["specimen_rung_f"]["pooled"][TERRAIN].get("uv_validity", {}).get("lawful_fraction"),
        specimen_zero_uv_area_frac_terrain=result["specimen_rung_f"]["pooled"][TERRAIN].get("zero_uv_area_frac"),
        specimen_sea_land_overlap_frac=result["specimen_rung_f"]["plan_coverage_sum"]["overlap_frac_of_land_summed"],
    )
    log("=" * 100)
    log("HEADLINE: " + json.dumps(result["headline"], indent=2, default=str))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    log(f"wrote {OUT}")


if __name__ == "__main__":
    main()
