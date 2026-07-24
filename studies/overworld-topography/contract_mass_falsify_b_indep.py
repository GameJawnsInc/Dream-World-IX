"""INDEPENDENT FALSIFIER for Lane B (saturation + spine ceilings).

READ-ONLY. Independent re-derivation; written under a distinct name so it never
touches the prior run's contract_mass_falsify_b.py. Reuses ONLY the calibrated UV
classifier (seam_null_recon.classify_tri / FAM_OF -- "do not reinvent the detector");
every population choice, ratio, and separation metric is computed here from scratch.

Out -> out/contract_mass/falsify_b_indep.json
"""
from __future__ import annotations
import json, math, sys, re, glob
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit")); sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X          # noqa
from ff9mapkit.world import mesh as M             # noqa
from seam_null_recon import FAM_OF, classify_tri, edge_index  # noqa  calibrated detector only

CELL = 4.0
OUT = HERE / "out" / "contract_mass" / "falsify_b_indep.json"
STAGE = HERE / "out" / "rung_e" / "FF9CustomMap-world"
STOCK_CORE = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]


def tri_records_from_bm(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    out = []
    for tri in bm.tris:
        idall0 = int(round(bm.tangents[tri[0]][0]))
        topo = X.decode_id(idall0)["topograph"]
        fam = FAM_OF.get(topo)
        w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
        uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        cell = (math.floor(cx / CELL), math.floor(cz / CELL))
        out.append(dict(block=(bx, by), topo=topo, fam=fam, uv=uv, w=w, cell=cell))
    return out


def load_stock(blocks):
    tris = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        tris += tri_records_from_bm(bm, bx, by)
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris


def load_staged():
    tris = []
    files = sorted(glob.glob(str(STAGE / "**" / "*Terrain.ff9mesh"), recursive=True))
    for f in files:
        m = re.search(r"Block\[(\d+)\]\[(\d+)\]", f)
        bx, by = int(m.group(1)), int(m.group(2))
        bm = M.blockmesh_from_ff9mesh(Path(f), disc=1, x=bx, y=by, part="terrain")
        tris += tri_records_from_bm(bm, bx, by)
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris, len(files)


def saturation_report(tris, label, dunes_side=True):
    body = [t for t in tris if t["topo"] == 16]
    n_body = len(body)
    grass_decal = plain_mains = dunes_decal = other = mains_foreign = 0
    row = Counter()
    for t in body:
        cls, detail = classify_tri(t["fam"], t["uv"])
        if cls == "strip_grass_desert":
            grass_decal += 1; row[detail] += 1
        elif cls == "strip_desert_dunes":
            dunes_decal += 1
        elif cls == "mains_own":
            plain_mains += 1
        elif cls == "mains_foreign":
            mains_foreign += 1
        else:
            other += 1
    sat_grass = grass_decal / n_body if n_body else None
    any_decal = grass_decal + (dunes_decal if dunes_side else 0)
    sat_any = any_decal / n_body if n_body else None
    tot_row = sum(row.values())
    row_frac = {k: round(row.get(k, 0) / tot_row, 4) for k in range(4)} if tot_row else {}
    return dict(label=label, n_body_topo16=n_body, n_grass_decal=grass_decal,
                n_dunes_decal=dunes_decal, n_plain_mains=plain_mains,
                n_mains_foreign=mains_foreign, n_other=other,
                saturation_grass_only=round(sat_grass, 4) if sat_grass is not None else None,
                saturation_any_decal=round(sat_any, 4) if sat_any is not None else None,
                row_counts={k: row.get(k, 0) for k in range(4)}, row_frac=row_frac)


def spine_zero_fraction(tris, label):
    """Graph-BFS robust proxy (convention 2). For every grass|desert boundary desert
    cell, march inward (opposite the grass side) counting consecutive PLAIN-mains
    undressed desert cells. zero_fraction = share of boundary cross-sections with no
    plain interior cell reachable."""
    cell_fam = defaultdict(set)
    for t in tris:
        if t["fam"] in ("grass", "desert"):
            cell_fam[t["cell"]].add(t["fam"])
    desert_state = {}
    for t in tris:
        if t["fam"] != "desert":
            continue
        cls, _ = classify_tri(t["fam"], t["uv"])
        s = desert_state.setdefault(t["cell"], {"dressed": 0, "plain": 0, "other": 0})
        if cls == "strip_grass_desert":
            s["dressed"] += 1
        elif cls == "mains_own":
            s["plain"] += 1
        else:
            s["other"] += 1
    grass_cells = {c for c, f in cell_fam.items() if "grass" in f}
    is_plain = lambda c: (c in desert_state and desert_state[c]["plain"] > 0 and desert_state[c]["dressed"] == 0)
    is_desert = lambda c: c in desert_state
    boundary = []
    for c in desert_state:
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (c[0] + d[0], c[1] + d[1]) in grass_cells:
                boundary.append((c, d)); break
    lengths, zero = [], 0
    for (c, gdir) in boundary:
        inward = (-gdir[0], -gdir[1])
        run = 0
        cur = (c[0] + inward[0], c[1] + inward[1])
        while is_desert(cur) and is_plain(cur):
            run += 1; cur = (cur[0] + inward[0], cur[1] + inward[1])
        lengths.append(run)
        if run == 0:
            zero += 1
    n = len(lengths)
    ls = sorted(lengths)
    pct = lambda p: (ls[min(len(ls) - 1, int(round(p * (len(ls) - 1))))] if ls else None)
    return dict(label=label, n_boundary_crosssections=n,
                zero_fraction=round(zero / n, 4) if n else None,
                median=pct(0.5), p90=pct(0.9), max=(max(lengths) if lengths else None),
                mean=round(sum(lengths) / n, 4) if n else None)


def mass3_recheck():
    core = [(bx, by) for bx in range(13, 17) for by in range(3, 7)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) if M.block_in_grid(bx + dx, by + dy)})
    tris = load_stock(ring)
    eo = edge_index(tris)
    gd = sum(1 for e, owners in eo.items() if {tris[g]["fam"] for g in owners} == {"grass", "desert"})
    cell_fam = defaultdict(set)
    for t in tris:
        if t["block"] in core and t["fam"] in ("grass", "desert"):
            cell_fam[t["cell"]].add(t["fam"])
    straddle = sum(1 for f in cell_fam.values() if f == {"grass", "desert"})
    return dict(region="(13-16,3-6)", gd_boundary_edges=gd, gd_straddle_cells=straddle,
                fam_census=dict(Counter(t["fam"] for t in tris if t["block"] in core)))


def control_a():
    blocks = [(bx, by) for bx in range(16, 21) for by in range(3, 8)]
    blocks += [(bx, by) for bx in range(11, 14) for by in range(4, 6)]
    tris = load_stock(blocks)
    desert = [t for t in tris if t["fam"] == "desert"]
    dressed = sum(1 for t in desert if classify_tri(t["fam"], t["uv"])[0] == "strip_grass_desert")
    return dict(n_desert_tris=len(desert), n_grass_decal_dressed=dressed)


def main():
    stock = load_stock(STOCK_CORE)
    print("stock blocks loaded:", len({t["block"] for t in stock}), "tris:", len(stock))
    stock_sat = saturation_report(stock, "stock", dunes_side=True)
    staged, nfiles = load_staged()
    print("staged terrain files:", nfiles, "tris:", len(staged))
    re_sat = saturation_report(staged, "rung_e", dunes_side=True)

    gap = round((re_sat["saturation_grass_only"] - stock_sat["saturation_grass_only"]) * 100, 2)
    row0_ratio = (round(re_sat["row_frac"].get(0, 0) / stock_sat["row_frac"][0], 3)
                  if stock_sat["row_frac"].get(0) else None)

    stock_spine = spine_zero_fraction(stock, "stock")
    re_spine = spine_zero_fraction(staged, "rung_e")
    m3 = mass3_recheck()
    ca = control_a()
    ctrlB = dict(counts=[stock_sat["n_body_topo16"], stock_sat["n_grass_decal"],
                         stock_sat["n_dunes_decal"], stock_sat["n_plain_mains"]],
                 matches_crosscheck_422_212_56_154=(
                     stock_sat["n_body_topo16"] == 422 and stock_sat["n_grass_decal"] == 212
                     and stock_sat["n_dunes_decal"] == 56 and stock_sat["n_plain_mains"] == 154))

    out = dict(stock=stock_sat, rung_e=re_sat,
               saturation_gap_pct_points=gap, row0_ratio_rung_e_over_stock=row0_ratio,
               spine_stock=stock_spine, spine_rung_e=re_spine,
               mass3_recheck=m3, control_a=ca, control_b=ctrlB,
               n_staged_terrain_files=nfiles)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n== SUMMARY ==")
    print(f"stock  body={stock_sat['n_body_topo16']} grass_decal={stock_sat['n_grass_decal']} "
          f"dunes={stock_sat['n_dunes_decal']} plain={stock_sat['n_plain_mains']} "
          f"other={stock_sat['n_other']} foreign={stock_sat['n_mains_foreign']}")
    print(f"stock  sat_grass={stock_sat['saturation_grass_only']} sat_any={stock_sat['saturation_any_decal']} rows={stock_sat['row_frac']}")
    print(f"rungE  body={re_sat['n_body_topo16']} grass_decal={re_sat['n_grass_decal']} "
          f"plain={re_sat['n_plain_mains']} other={re_sat['n_other']} foreign={re_sat['n_mains_foreign']} dunes={re_sat['n_dunes_decal']}")
    print(f"rungE  sat_grass={re_sat['saturation_grass_only']} rows={re_sat['row_frac']}")
    print(f"gap={gap}pt  row0_ratio={row0_ratio}")
    print(f"spine zero-frac: stock={stock_spine['zero_fraction']} rungE={re_spine['zero_fraction']}")
    print(f"spine median/p90/mean: stock={stock_spine['median']}/{stock_spine['p90']}/{stock_spine['mean']} "
          f"rungE={re_spine['median']}/{re_spine['p90']}/{re_spine['mean']}")
    print(f"mass3: {m3['gd_boundary_edges']} gd-edges, {m3['gd_straddle_cells']} straddle cells")
    print(f"control_a: {ca['n_grass_decal_dressed']}/{ca['n_desert_tris']} desert dressed")
    print(f"control_b matches crosscheck: {ctrlB['matches_crosscheck_422_212_56_154']}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
