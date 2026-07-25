"""RUNG F -- ADVERSARIAL PROBE (code-disjoint, staged-bytes-only, 2026-07-24).

Does NOT import uvf_forensics. Directly byte-reads 3 staged Terrain blocks + their sea parts and
re-derives, from raw channel arrays: tri counts, UV signed areas, whether claimed-degenerate
populations really have zero UV area (and nonzero WORLD area = visible), the UV-collapse point,
whether claimed-lawful tris really land in catalogued family rects, and whether terrain<->sea plan
overlaps are real. READ-ONLY vs the install: reads ONLY out/rung_f/FF9CustomMap-world staged files.
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import mesh as M            # noqa: E402
from ff9mapkit.world import extract as X         # noqa: E402
from ff9mapkit.world import grassland as G       # noqa: E402
import seam_null_recon as SNR                     # noqa: E402  (FAM_OF, RECTS, in_rect)

CELL = 4.0
STAGED = HERE / "out" / "rung_f" / "FF9CustomMap-world"
OUT = HERE / "out" / "rung_f" / "uvf_adversary_probe.json"

# blocks: heavy-flat blob / clean SE corner / non-blob full-Sea4 sea-overlap suspect
BLOCKS = {"heavy_flat_blob": (1, 18), "clean_corner": (4, 19), "sea_overlap_nonblob": (0, 17)}
DEG_EPS = 1e-6          # UV signed-area magnitude below this = degenerate (the sweep's threshold)
COLLAPSE_EPS = 1e-4     # max pairwise UV point distance below this = collapsed to one point


def load_terr(bx, by):
    p = STAGED / M.override_relpath(1, bx, by, part="Terrain")
    return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")


def load_part(bx, by, part):
    p = STAGED / M.override_relpath(1, bx, by, part=part)
    if not p.exists():
        return None
    return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")


def tri_area2(a, b, c):
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def uv_area(bm, tri):
    u = [bm.uvs[j] for j in tri]
    return tri_area2((u[0][0], u[0][1]), (u[1][0], u[1][1]), (u[2][0], u[2][1]))


def plan_area(bm, tri, ox, oz):
    w = [(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri]
    return tri_area2(w[0], w[1], w[2])


def uv_span(bm, tri):
    u = [bm.uvs[j] for j in tri]
    return max(math.dist(u[i], u[k]) for i in range(3) for k in range(i + 1, 3))


def catalog_verdict(bm, tri, topo):
    """which catalogued family rect (mains) do all 3 UVs sit in, if any."""
    uv3 = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
    hits = [fam for fam, rect in SNR.RECTS.items() if SNR.in_rect(uv3, rect)]
    return hits


def point_in_tri(px, pz, a, b, c):
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) < 1e-12:
        return False
    s = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[1])) / d
    t = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[1])) / d
    return s >= -1e-9 and t >= -1e-9 and (s + t) <= 1 + 1e-9


def probe_block(name, bx, by):
    bm = load_terr(bx, by)
    ox, oz = X.block_world_origin(bx, by)
    n = len(bm.tris)
    rows = []
    for tri in bm.tris:
        idall = int(round(bm.tangents[tri[0]][0]))
        topo = X.decode_id(idall)["topograph"]
        ua = uv_area(bm, tri)
        pa = plan_area(bm, tri, ox, oz)
        span = uv_span(bm, tri)
        ys = [bm.verts[j][1] for j in tri]
        rows.append(dict(topo=topo, ua=ua, pa=pa, span=span,
                         collapsed=span < COLLAPSE_EPS,
                         degen=abs(ua) < DEG_EPS,
                         yspread=max(ys) - min(ys),
                         uv0=(round(float(bm.uvs[tri[0]][0]), 5), round(float(bm.uvs[tri[0]][1]), 5))))
    deg = [r for r in rows if r["degen"]]
    nondeg = [r for r in rows if not r["degen"]]
    # collapse points of degenerate tris
    collapse_pts = Counter(r["uv0"] for r in deg if r["collapsed"])
    # topo=0 non-degenerate (real grass mains) UV-area sanity
    grass_lawful = [r for r in nondeg if r["topo"] == 0]
    return bm, ox, oz, dict(
        block=[bx, by], n_tris=n,
        n_degen=len(deg), frac_degen=round(len(deg) / n, 4) if n else 0,
        degen_topo_hist=dict(Counter(r["topo"] for r in deg)),
        nondeg_topo_hist=dict(Counter(r["topo"] for r in nondeg)),
        degen_all_collapsed=all(r["collapsed"] for r in deg),
        degen_n_collapsed=sum(1 for r in deg if r["collapsed"]),
        degen_max_planarea=round(max((abs(r["pa"]) for r in deg), default=0.0), 4),
        degen_min_planarea=round(min((abs(r["pa"]) for r in deg), default=0.0), 6),
        degen_n_real_visible=sum(1 for r in deg if abs(r["pa"]) > 0.01),
        degen_yspread_max=round(max((r["yspread"] for r in deg), default=0.0), 3),
        collapse_points=[{"uv": list(k), "count": v} for k, v in collapse_pts.most_common(5)],
        grass_lawful_n=len(grass_lawful),
        grass_lawful_uvarea_min=round(min((abs(r["ua"]) for r in grass_lawful), default=0.0), 8),
        grass_lawful_uvarea_med=round(sorted(abs(r["ua"]) for r in grass_lawful)[len(grass_lawful) // 2], 8) if grass_lawful else 0,
        grass_lawful_span_min=round(min((r["span"] for r in grass_lawful), default=0.0), 6),
    )


def sea_probe(bx, by, bm_terr, ox, oz):
    """real plan area of each sea/beach/object part + terrain<->sea overlap sampling."""
    parts = {}
    sea_tris_world = []
    for part in ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1", "Object"):
        bmp = load_part(bx, by, part)
        if bmp is None:
            parts[part] = None
            continue
        pox, poz = X.block_world_origin(bx, by)
        tot = 0.0
        for tri in bmp.tris:
            a = abs(plan_area(bmp, tri, pox, poz))
            tot += a
            if a > 1e-6:
                w = [(bmp.verts[j][0] + pox, bmp.verts[j][2] + poz) for j in tri]
                sea_tris_world.append(w)
        parts[part] = dict(n_tris=len(bmp.tris), n_verts=len(bmp.verts),
                           plan_area_sum=round(tot, 4),
                           real=tot > 1e-3)
    # sample terrain cells: how many land cells also sit over a real-sea tri (double coverage)?
    overlap_cells = 0
    land_cells = set()
    cell_pt = {}
    for tri in bm_terr.tris:
        if abs(plan_area(bm_terr, tri, ox, oz)) < 1e-6:
            continue
        cx = (sum(bm_terr.verts[j][0] + ox for j in tri) / 3)
        cz = (sum(bm_terr.verts[j][2] + oz for j in tri) / 3)
        ck = (math.floor(cx / CELL), math.floor(cz / CELL))
        land_cells.add(ck)
        cell_pt[ck] = (cx, cz)
    for ck, (px, pz) in cell_pt.items():
        for w in sea_tris_world:
            if point_in_tri(px, pz, w[0], w[1], w[2]):
                overlap_cells += 1
                break
    return dict(parts=parts, n_real_sea_tris=len(sea_tris_world),
                n_land_cells=len(land_cells), n_land_cells_over_real_sea=overlap_cells)


def main():
    result = {"read_only_no_install": True, "atlas_not_sampled": "install-only asset; not opened per constraint", "blocks": {}}
    for name, (bx, by) in BLOCKS.items():
        bm, ox, oz, terr = probe_block(name, bx, by)
        sea = sea_probe(bx, by, bm, ox, oz)
        result["blocks"][name] = {"terrain": terr, "sea": sea}
        b = result["blocks"][name]
        print(f"=== {name} {(bx,by)} tris={terr['n_tris']} degen={terr['n_degen']} ({terr['frac_degen']:.1%})")
        print(f"    degen topo hist: {terr['degen_topo_hist']}  all_collapsed={terr['degen_all_collapsed']} real_visible(pa>0.01)={terr['degen_n_real_visible']}")
        print(f"    degen plan-area max={terr['degen_max_planarea']} yspread_max={terr['degen_yspread_max']}  collapse_pts={terr['collapse_points']}")
        print(f"    lawful grass topo0 n={terr['grass_lawful_n']} uvarea_min={terr['grass_lawful_uvarea_min']} span_min={terr['grass_lawful_span_min']}")
        print(f"    SEA: real_sea_tris={sea['n_real_sea_tris']} land_cells={sea['n_land_cells']} over_real_sea={sea['n_land_cells_over_real_sea']}")
        for p, d in sea["parts"].items():
            if d: print(f"       {p}: tris={d['n_tris']} plan_area={d['plan_area_sum']} real={d['real']}")
    OUT.write_text(json.dumps(result, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
