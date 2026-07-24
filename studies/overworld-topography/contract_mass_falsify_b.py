"""INDEPENDENT FALSIFIER for Lane B (saturation + spine ceilings).

Re-derives Lane B's gate-bound numbers WITHOUT importing the lane script or seam_null_recon's
classify_tri -- the UV classification is reimplemented here directly from grassland's byte-probed
constants (GROUNDS/STRIPS/FAM_REGION/STRIP_U/STRIPS_V). Reads raw stock bytes (X.read_block) at the
one real grass|desert site (13-15,11-12) and the staged Rung E Terrain meshes in out/rung_e/.

READ-ONLY. Zero writes to the game install, zero deploy. Only writes out/contract_mass/falsify_b.json.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import grassland as G        # noqa: E402
from ff9mapkit.world import mesh as M             # noqa: E402

OUT = HERE / "out" / "contract_mass" / "falsify_b.json"
RUNG_E_STAGE = HERE / "out" / "rung_e" / "FF9CustomMap-world"

CELL = 4.0

# ---- independent family table (topo -> family), grass/desert/dunes only (the pair we care about) --
FAM_OF = {}
for _t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[_t] = "grass"
for _t in (16, 17, 19, 20):
    FAM_OF[_t] = "desert"
FAM_OF[41] = "dunes"

# ---- independent UV classifier, built straight from the byte constants -----------------------------
EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125

STRIP_U0, STRIP_U1 = G.STRIP_U                        # (0.39355, 0.4541)
ROW0_V0 = G.STRIPS_V[0][0]                            # 0.36914
GD_DU, GD_DV = G.STRIPS[("grass", "desert")]["du"], G.STRIPS[("grass", "desert")]["dv"]
DD_DU, DD_DV = G.STRIPS[("desert", "dunes")]["du"], G.STRIPS[("desert", "dunes")]["dv"]

# desert mains rect = FAM_REGION["main"] translated by desert's mains du/dv
_m = G.FAM_REGION["main"]
_dg = G.GROUNDS["desert"]
DESERT_MAINS_RECT = (_m[0] + _dg["mains_du"], _m[1] + _dg["mains_dv"],
                     _m[2] + _dg["mains_du"], _m[3] + _dg["mains_dv"])
# grass mains rect (for the foreign-mains check; grass du/dv = 0)
GRASS_MAINS_RECT = _m
# dunes mains rect
_du = G.GROUNDS["dunes"]
DUNES_MAINS_RECT = (_m[0] + _du["mains_du"], _m[1] + _du["mains_dv"],
                    _m[2] + _du["mains_du"], _m[3] + _du["mains_dv"])


def in_rect(uv3, rect, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps
               for (u, v) in uv3)


def strip_row(uv3, du, dv):
    """Return row k (0..3) if all 3 corners' u sit in the strip column translated by du, and
    v_min aligns to a row pitch; else None. Independent reimplementation of the strip test."""
    u_lo, u_hi = STRIP_U0 + du - EPS, STRIP_U1 + du + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    base = ROW0_V0 + dv
    k = round((v_min - base) / ROW_PITCH)
    if k < 0 or k > 3 or abs((v_min - base) - k * ROW_PITCH) > TOL_V:
        return None
    return int(k)


def classify(uv3, fam):
    """Independent: returns ('gd_strip', k) | ('mains', fam_of_rect) | ('dd_strip', k) | ('other', None).
    Order matches the shared convention: strip(grass,desert) first, then own/foreign mains,
    then strip(desert,dunes)."""
    k = strip_row(uv3, GD_DU, GD_DV)
    if k is not None:
        return ("gd_strip", k)
    if in_rect(uv3, DESERT_MAINS_RECT):
        return ("mains", "desert")
    if in_rect(uv3, GRASS_MAINS_RECT):
        return ("mains", "grass")
    if in_rect(uv3, DUNES_MAINS_RECT):
        return ("mains", "dunes")
    k2 = strip_row(uv3, DD_DU, DD_DV)
    if k2 is not None:
        return ("dd_strip", k2)
    return ("other", None)


def load_terrain(bx, by, *, staged_root=None):
    """Return list of tri dicts (topo, fam, uv, world-verts, cell). staged_root -> read the
    override Terrain.ff9mesh there; else stock X.read_block."""
    if staged_root is not None:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = staged_root / rel
        if not path.exists():
            return None
        bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
    else:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            return None
    ox, oz = X.block_world_origin(bx, by)
    tris = []
    for tri in bm.tris:
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
        w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        cell = (math.floor(cx / CELL), math.floor(cz / CELL))
        tris.append(dict(topo=topo, fam=FAM_OF.get(topo), uv=uv, w=w, cell=cell))
    return tris


def analyze_body(all_tris, label):
    """all_tris across the site's blocks. Compute topo-16 body saturation + row distribution."""
    body = [t for t in all_tris if t["topo"] == 16]
    n_body = len(body)
    cls_counter = Counter()
    gd_rows = Counter()
    dd_rows = Counter()
    for t in body:
        c, k = classify(t["uv"], t["fam"])
        cls_counter[c] += 1
        if c == "gd_strip":
            gd_rows[k] += 1
        elif c == "dd_strip":
            dd_rows[k] += 1
    n_gd = cls_counter["gd_strip"]
    n_dd = cls_counter["dd_strip"]
    n_mains = cls_counter["mains"]
    n_other = cls_counter["other"]
    if not n_body:
        print(f"\n=== {label} === (no topo-16 body tris)")
        return dict(n_body=0, n_gd_strip=0, n_dd_strip=0, n_mains=0, n_other=0,
                    saturation_grass_only=None, saturation_any_decal=None,
                    gd_row_counts={}, gd_row_fractions={"0": 0, "1": 0, "2": 0, "3": 0},
                    dd_row_counts={})
    sat_grass = n_gd / n_body if n_body else None
    # diagnostic: v_min histogram of gd_strip tris (to explain any row-binning divergence)
    base = ROW0_V0 + GD_DV
    vmins = [min(v for (_u, v) in t["uv"]) - base for t in body
             if classify(t["uv"], t["fam"])[0] == "gd_strip"]
    sat_any = (n_gd + n_dd) / n_body if n_body else None
    total_gd = sum(gd_rows.values())
    row_frac = {k: (gd_rows.get(k, 0) / total_gd if total_gd else 0.0) for k in range(4)}
    print(f"\n=== {label} ===")
    print(f"  topo-16 body tris        : {n_body}")
    print(f"  gd_strip (grass decal)   : {n_gd}   -> saturation grass-only = {sat_grass:.4f}")
    print(f"  dd_strip (dunes decal)   : {n_dd}")
    print(f"  mains (plain)            : {n_mains}")
    print(f"  other/uncatalogued       : {n_other}")
    print(f"  saturation ANY decal     : {sat_any:.4f}  ({n_gd + n_dd}/{n_body})")
    print(f"  gd row tri counts (vmin) : {dict(sorted(gd_rows.items()))}")
    print(f"  gd row fractions (vmin)  : " + ", ".join(f"r{k}={row_frac[k]:.4f}" for k in range(4)))
    # alt binning: by v-CENTROID and by v-MAX, to see which the lane might be using
    def rowbin(vals, agg):
        c = Counter()
        for t in body:
            if classify(t["uv"], t["fam"])[0] != "gd_strip":
                continue
            vv = agg(v for (_u, v) in t["uv"])
            k = round((vv - base) / ROW_PITCH)
            c[max(0, min(3, k))] += 1
        return c
    cen = rowbin(None, lambda g: sum(g) / 3.0)
    vmx = rowbin(None, max)
    tc = sum(cen.values()) or 1
    tm = sum(vmx.values()) or 1
    print(f"  gd row (vCENTROID)       : {dict(sorted(cen.items()))}  frac=" +
          ",".join(f"{cen.get(k,0)/tc:.3f}" for k in range(4)))
    print(f"  gd row (vMAX)            : {dict(sorted(vmx.items()))}  frac=" +
          ",".join(f"{vmx.get(k,0)/tm:.3f}" for k in range(4)))
    return dict(n_body=n_body, n_gd_strip=n_gd, n_dd_strip=n_dd, n_mains=n_mains, n_other=n_other,
                saturation_grass_only=round(sat_grass, 4) if sat_grass is not None else None,
                saturation_any_decal=round(sat_any, 4) if sat_any is not None else None,
                gd_row_counts={str(k): gd_rows.get(k, 0) for k in range(4)},
                gd_row_fractions={str(k): round(row_frac[k], 4) for k in range(4)},
                dd_row_counts={str(k): dd_rows.get(k, 0) for k in range(4)})


def edge_key(p):
    return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def spine_band_analysis(all_tris, label):
    """Independent SPINE proxy via graph-BFS band depth (robust to jaggy boundaries, the lane's
    2nd convention). Seed BFS at boundary cells (cells owning a grass|desert world-space edge);
    march through DESERT-family cells; a cell is 'plain' if it holds a desert-mains tri and NO
    grass|desert strip tri. Report: band-1 plain rate, max desert band depth, and a per-boundary
    'plain run' spine (consecutive plain desert cells straight back from each boundary cell)."""
    # cell -> set of families, and per-cell classification (has strip? has mains?)
    cell_fam = defaultdict(set)
    cell_has_strip = defaultdict(bool)
    cell_has_mains = defaultdict(bool)
    for t in all_tris:
        if t["fam"] in ("grass", "desert"):
            cell_fam[t["cell"]].add(t["fam"])
        if t["topo"] == 16:
            c, _k = classify(t["uv"], t["fam"])
            if c == "gd_strip":
                cell_has_strip[t["cell"]] = True
            elif c == "mains":
                cell_has_mains[t["cell"]] = True

    # boundary cells: cells owning a world-space edge shared by a grass tri and a desert tri
    edge_owner = defaultdict(list)
    for t in all_tris:
        if t["fam"] not in ("grass", "desert"):
            continue
        ks = [edge_key(p) for p in t["w"]]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                edge_owner[e].append(t)
    boundary_cells = set()
    for e, owners in edge_owner.items():
        fams = {o["fam"] for o in owners}
        if fams == {"grass", "desert"}:
            for o in owners:
                boundary_cells.add(o["cell"])
    boundary_cells &= set(cell_fam)

    desert_cells = {c for c, f in cell_fam.items() if "desert" in f}
    # BFS band depth through desert cells from the boundary
    dist = {c: 0 for c in boundary_cells}
    q = deque(dist)
    max_depth = 0
    while q:
        c = q.popleft()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n in desert_cells and n not in dist:
                dist[n] = dist[c] + 1
                max_depth = max(max_depth, dist[n])
                q.append(n)
    band1 = [c for c, dd in dist.items() if dd == 1]
    band1_plain = sum(1 for c in band1 if cell_has_mains[c] and not cell_has_strip[c])
    band1_plain_rate = band1_plain / len(band1) if band1 else None

    # per-boundary spine: from each boundary cell, march the 4 cardinal directions into desert;
    # the spine = the longest straight plain-desert run before non-desert or a strip cell.
    spine_lengths = []
    n_unmeasured = 0
    for bc in boundary_cells:
        best = None
        measured = False
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            # only march the direction that goes AWAY from grass into desert
            step1 = (bc[0] + d[0], bc[1] + d[1])
            if step1 not in desert_cells:
                continue
            measured = True
            run = 0
            cur = step1
            while cur in desert_cells and cell_has_mains[cur] and not cell_has_strip[cur]:
                run += 1
                cur = (cur[0] + d[0], cur[1] + d[1])
            if best is None or run > best:
                best = run
        if not measured:
            n_unmeasured += 1
            continue
        spine_lengths.append(best if best is not None else 0)

    spine_lengths.sort()
    med = statistics.median(spine_lengths) if spine_lengths else None
    p90 = spine_lengths[min(len(spine_lengths) - 1, int(0.9 * len(spine_lengths)))] if spine_lengths else None
    mean = statistics.mean(spine_lengths) if spine_lengths else None
    zero_frac = (sum(1 for s in spine_lengths if s == 0) / len(spine_lengths)) if spine_lengths else None
    print(f"\n--- SPINE (graph proxy) {label} ---")
    print(f"  boundary cells           : {len(boundary_cells)}")
    print(f"  desert cells             : {len(desert_cells)}")
    print(f"  max desert band depth    : {max_depth}")
    print(f"  band-1 plain rate        : {band1_plain_rate}")
    print(f"  spine measured / unmeas  : {len(spine_lengths)} / {n_unmeasured}")
    print(f"  spine median / p90 / mean: {med} / {p90} / {mean}")
    print(f"  spine zero fraction      : {zero_frac}")
    return dict(n_boundary_cells=len(boundary_cells), n_desert_cells=len(desert_cells),
                max_band_depth=max_depth,
                band1_plain_rate=round(band1_plain_rate, 4) if band1_plain_rate is not None else None,
                spine_n_measured=len(spine_lengths), spine_n_unmeasured=n_unmeasured,
                spine_median=med, spine_p90=p90,
                spine_mean=round(mean, 4) if mean is not None else None,
                spine_zero_fraction=round(zero_frac, 4) if zero_frac is not None else None,
                spine_max=max(spine_lengths) if spine_lengths else None)


def find_staged_terrain_blocks():
    blocks = []
    for p in RUNG_E_STAGE.rglob("*Terrain.ff9mesh"):
        name = p.name
        if not name.startswith("Block["):
            continue
        # "Block[bx][by] Terrain.ff9mesh"
        inside = name[name.index("[") + 1:]
        bx = int(inside[:inside.index("]")])
        rest = inside[inside.index("]") + 1:]
        rest = rest[rest.index("[") + 1:]
        by = int(rest[:rest.index("]")])
        blocks.append((bx, by))
    return sorted(set(blocks))


def main():
    result = {}

    # ===== STOCK site (13-15, 11-12) =====
    stock_blocks = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
    stock_tris = []
    loaded = []
    for (bx, by) in stock_blocks:
        t = load_terrain(bx, by)
        if t is None:
            print(f"  WARN stock block ({bx},{by}) missing")
            continue
        loaded.append((bx, by))
        stock_tris.extend(t)
    print(f"STOCK blocks loaded: {loaded} ({len(stock_tris)} terrain tris)")
    stock_body = analyze_body(stock_tris, "STOCK site (13-15,11-12) topo-16 body")
    stock_spine = spine_band_analysis(stock_tris, "STOCK")

    # ===== RUNG E staged =====
    e_blocks = find_staged_terrain_blocks()
    print(f"\nRUNG E staged Terrain blocks: {e_blocks}")
    e_tris = []
    e_loaded = []
    for (bx, by) in e_blocks:
        t = load_terrain(bx, by, staged_root=RUNG_E_STAGE)
        if t is None:
            continue
        e_loaded.append((bx, by))
        e_tris.extend(t)
    print(f"RUNG E blocks loaded: {e_loaded} ({len(e_tris)} terrain tris)")
    e_body = analyze_body(e_tris, "RUNG E staged topo-16 body")
    e_spine = spine_band_analysis(e_tris, "RUNG E")

    # ===== separations =====
    sat_gap = round((e_body["saturation_grass_only"] - stock_body["saturation_grass_only"]) * 100, 2)
    row0_ratio = round(e_body["gd_row_fractions"]["0"] / stock_body["gd_row_fractions"]["0"], 3) \
        if stock_body["gd_row_fractions"]["0"] else None
    print("\n" + "=" * 70)
    print(f"SATURATION GAP (Rung E - stock, grass-only) = {sat_gap} pts")
    print(f"ROW0 ratio (Rung E / stock)                 = {row0_ratio}")

    result = dict(
        stock_blocks_loaded=[list(b) for b in loaded],
        stock=stock_body, stock_spine=stock_spine,
        rung_e_blocks_loaded=[list(b) for b in e_loaded],
        rung_e=e_body, rung_e_spine=e_spine,
        saturation_gap_pts=sat_gap, row0_ratio_rung_e_over_stock=row0_ratio,
        constants=dict(desert_mains_rect=DESERT_MAINS_RECT, gd_du=GD_DU, gd_dv=GD_DV,
                       dd_du=DD_DU, dd_dv=DD_DV, strip_u=[STRIP_U0, STRIP_U1], row0_v0=ROW0_V0),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
