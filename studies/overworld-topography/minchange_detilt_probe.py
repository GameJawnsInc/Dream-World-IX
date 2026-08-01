"""MINIMAL-CHANGE LENS PROBE -- is the (15,14) mesa's grass weld line DE-TILTABLE onto a FLAT bench?

Read-only. Reads stock disc-1 (p0data via ff9mapkit.world.extract), the DEPLOYED round-8 bench
(loose .ff9mesh under the install, opened read-only), and the pre-wall bench backup in the MAIN
repo's backups/. Writes only studies/overworld-topography/out/minchange_detilt.json (+ .png).
Nothing is built, nothing is deployed, nothing under the game install is written.

Four measurements, each answering one question the minimal-change design needs:

  A  THE DE-TILT BUDGET. Decompose the donor's GRASS-only ground-weld line into
     (i) a rigid PLANE component (a global affine the ROCK-RIGID LAW already permits:
     "de-tilt + DY") and (ii) a residual roughness. If the residual is inside stock's own
     ground roughness at a wall foot, a FLAT bench can weld to it with NO lift field at all.

  B  THE STOCK FOOT-ROUGHNESS ENVELOPE. What |dy| does stock itself carry between
     neighbouring positions along a wall's grass foot line? This is the tolerance the
     residual has to fit inside. Measured over every disc-1 block that has a 49|grass foot.

  C  THE DEPLOYED BENCH TESSELLATION, by radius. Reproduce the S2-verifier's ground-tri
     plan-area / tris-per-cell census on the live bytes so the design does not assert it,
     and localise it: how many tris and how much area would a deletion of the lift+repair
     machinery have to give back?

  D  THE PRE-WALL BASELINE. Same census on backups/terrace-strip-prewall.<ts> -- was the
     bench's own ground sheet lawful BEFORE the wall arc subdivided it?
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb")
MAIN = Path(r"C:\gd\Dream-World-IX")
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402

OUT = ROOT / "studies" / "overworld-topography" / "out"
OUT.mkdir(parents=True, exist_ok=True)

GRASS = {0, 1, 2, 3, 42}
PLATEAU = {10, 11, 12}
FOREST = {36, 37}
ROCK = {49}
CELL = 4.0
BLOCK = 64.0


def pct(a, q):
    a = np.asarray(a, dtype=float)
    return float(np.percentile(a, q)) if a.size else None


def stats(a, name=""):
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return {"n": 0}
    return {
        "n": int(a.size),
        "min": float(a.min()),
        "p10": pct(a, 10),
        "p25": pct(a, 25),
        "med": pct(a, 50),
        "p75": pct(a, 75),
        "p90": pct(a, 90),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "rms": float(np.sqrt((a ** 2).mean())),
    }


def read_tris(bx, by, disc=1):
    """-> (V world-space Nx3, tris list of (i,j,k), topo list per tri) or None."""
    try:
        bm = X.read_block(bx, by, disc=disc, part="terrain")
    except Exception:
        return None
    V = np.asarray(bm.chan_arrays[X.CH_POS], dtype=float)
    T = np.asarray(bm.chan_arrays[X.CH_TAN], dtype=float)
    U = np.asarray(bm.chan_arrays[X.CH_UV], dtype=float)
    fi = list(bm.flat_index)
    tris = [tuple(fi[3 * t:3 * t + 3]) for t in range(len(fi) // 3)]
    topo = [X.decode_id(int(round(T[t[0]][0])))["topograph"] for t in tris]
    ox, oz = BLOCK * bx, -BLOCK * by
    W = V.copy()
    W[:, 0] += ox
    W[:, 2] += oz
    return W, tris, topo, U


def read_loose(path, bx, by):
    bm = M.blockmesh_from_ff9mesh(path, disc=9, x=bx, y=by, part="terrain")
    V = np.asarray(bm.chan_arrays[X.CH_POS], dtype=float)
    T = np.asarray(bm.chan_arrays[X.CH_TAN], dtype=float)
    U = np.asarray(bm.chan_arrays[X.CH_UV], dtype=float)
    fi = list(bm.flat_index)
    tris = [tuple(fi[3 * t:3 * t + 3]) for t in range(len(fi) // 3)]
    topo = [X.decode_id(int(round(T[t[0]][0])))["topograph"] for t in tris]
    ox, oz = BLOCK * bx, -BLOCK * by
    W = V.copy()
    W[:, 0] += ox
    W[:, 2] += oz
    return W, tris, topo, U


# ---------------------------------------------------------------- A: the de-tilt budget
def foot_verts(blocks, disc=1, want=GRASS):
    """Positions (rounded 3dp keys) shared between a ROCK tri and a `want`-class tri."""
    rock_keys, want_keys, pos = {}, {}, {}
    for (bx, by) in blocks:
        r = read_tris(bx, by, disc=disc)
        if r is None:
            continue
        W, tris, topo, _ = r
        for t, tp in zip(tris, topo):
            for i in t:
                k = (round(W[i][0], 3), round(W[i][2], 3))
                pos.setdefault(k, []).append(W[i][1])
                if tp in ROCK:
                    rock_keys[k] = 1
                if tp in want:
                    want_keys[k] = 1
    shared = sorted(set(rock_keys) & set(want_keys))
    out = []
    for k in shared:
        out.append((k[0], float(np.median(pos[k])), k[1]))
    return out


def plane_fit(P):
    """P: Nx3 (x,y,z). LSQ y = a*x + b*z + c. -> (a,b,c, resid array, tilt_deg)."""
    P = np.asarray(P, dtype=float)
    A = np.column_stack([P[:, 0], P[:, 2], np.ones(len(P))])
    coef, *_ = np.linalg.lstsq(A, P[:, 1], rcond=None)
    a, b, c = [float(v) for v in coef]
    resid = P[:, 1] - (A @ coef)
    tilt = math.degrees(math.atan(math.hypot(a, b)))
    return a, b, c, resid, tilt


def chain_dy(P, max_step=6.0):
    """|dy| between each foot vertex and its nearest neighbours in plan (<=max_step)."""
    P = np.asarray(P, dtype=float)
    out = []
    for i in range(len(P)):
        d = np.hypot(P[:, 0] - P[i, 0], P[:, 2] - P[i, 2])
        d[i] = 1e9
        for j in np.where((d > 1e-6) & (d <= max_step))[0]:
            if j > i:
                out.append(abs(P[i, 1] - P[j, 1]))
    return out


def part_a():
    donor_blocks = [(15, 14)]
    nbr_blocks = [(14, 14), (15, 14), (16, 14), (15, 13), (15, 15)]
    res = {}
    for label, blocks in (("donor_block_only", donor_blocks), ("donor_plus_neighbours", nbr_blocks)):
        gr = foot_verts(blocks, want=GRASS)
        fo = foot_verts(blocks, want=FOREST)
        allw = foot_verts(blocks, want=GRASS | FOREST | PLATEAU)
        gr_only = [p for p in gr if (p[0], p[2]) not in {(q[0], q[2]) for q in fo}]
        entry = {}
        for nm, P in (("grass_and_forest", allw), ("grass_touching", gr), ("grass_only", gr_only), ("forest_touching", fo)):
            if not P:
                entry[nm] = {"n": 0}
                continue
            Pa = np.asarray(P, dtype=float)
            a, b, c, resid, tilt = plane_fit(Pa)
            xs, zs = Pa[:, 0], Pa[:, 2]
            span = math.hypot(xs.max() - xs.min(), zs.max() - zs.min())
            entry[nm] = {
                "n": len(P),
                "y_raw": stats(Pa[:, 1]),
                "raw_spread_maxmin": float(Pa[:, 1].max() - Pa[:, 1].min()),
                "raw_spread_p10_p90": float(pct(Pa[:, 1], 90) - pct(Pa[:, 1], 10)),
                "plane": {"a_dydx": a, "b_dydz": b, "c": c, "tilt_deg": tilt,
                          "plane_rise_across_footprint": float(abs(a) * (xs.max() - xs.min()) + abs(b) * (zs.max() - zs.min())),
                          "diag_span_u": span},
                "detilted_resid": stats(resid),
                "detilted_spread_maxmin": float(resid.max() - resid.min()),
                "detilted_spread_p10_p90": float(pct(resid, 90) - pct(resid, 10)),
                "neighbour_abs_dy": stats(chain_dy(Pa)),
            }
        res[label] = entry
    return res


# ------------------------------------------------- B: stock foot-line roughness envelope
def part_b(sample_every=1):
    blocks = X.list_blocks(disc=1)
    per_block, all_dy, all_resid, all_tilt = [], [], [], []
    n_read = 0
    for i, (bx, by) in enumerate(blocks):
        if i % sample_every:
            continue
        r = read_tris(bx, by)
        if r is None:
            continue
        n_read += 1
        W, tris, topo, _ = r
        rock_keys, grass_keys, pos = set(), set(), {}
        for t, tp in zip(tris, topo):
            for j in t:
                k = (round(W[j][0], 3), round(W[j][2], 3))
                pos.setdefault(k, []).append(W[j][1])
                if tp in ROCK:
                    rock_keys.add(k)
                elif tp in GRASS:
                    grass_keys.add(k)
        shared = sorted(rock_keys & grass_keys)
        if len(shared) < 8:
            continue
        P = np.array([[k[0], float(np.median(pos[k])), k[1]] for k in shared], dtype=float)
        dy = chain_dy(P)
        a, b, c, resid, tilt = plane_fit(P)
        all_dy.extend(dy)
        all_resid.extend(list(resid))
        all_tilt.append(tilt)
        per_block.append({
            "block": [bx, by], "n_foot": len(P),
            "raw_spread": float(P[:, 1].max() - P[:, 1].min()),
            "raw_p10_p90": float(pct(P[:, 1], 90) - pct(P[:, 1], 10)),
            "tilt_deg": tilt,
            "detilt_resid_rms": float(np.sqrt((resid ** 2).mean())),
            "detilt_spread": float(resid.max() - resid.min()),
            "detilt_p10_p90": float(pct(resid, 90) - pct(resid, 10)),
            "nbr_dy_med": pct(dy, 50) if dy else None,
            "nbr_dy_p90": pct(dy, 90) if dy else None,
        })
    comps = [b["raw_spread"] for b in per_block]
    return {
        "blocks_read": n_read, "blocks_with_grass_foot": len(per_block),
        "neighbour_abs_dy_all": stats(all_dy),
        "detilt_resid_all": stats(all_resid),
        "per_block_tilt_deg": stats(all_tilt),
        "per_block_raw_spread": stats(comps),
        "per_block_detilt_spread": stats([b["detilt_spread"] for b in per_block]),
        "per_block_detilt_p10_p90": stats([b["detilt_p10_p90"] for b in per_block]),
        "per_block_detilt_rms": stats([b["detilt_resid_rms"] for b in per_block]),
        "per_block": sorted(per_block, key=lambda d: -d["raw_spread"])[:25],
    }


# --------------------------------------------------- C/D: tessellation census on a sheet
def tessellate(W, tris, topo, classes, centre=None, radial=True):
    areas, cells = [], {}
    per_r = {}
    bands = [(0, 8), (8, 16), (16, 24), (24, 32), (32, 40), (40, 48), (48, 56), (56, 999)]
    for t, tp in zip(tris, topo):
        if tp not in classes:
            continue
        p = W[list(t)]
        ax = 0.5 * abs((p[1][0] - p[0][0]) * (p[2][2] - p[0][2]) - (p[2][0] - p[0][0]) * (p[1][2] - p[0][2]))
        areas.append(ax)
        cx, cz = p[:, 0].mean(), p[:, 2].mean()
        cells.setdefault((math.floor(cx / CELL), math.floor(cz / CELL)), []).append(ax)
        if radial and centre is not None:
            r = math.hypot(cx - centre[0], cz - centre[1])
            for lo, hi in bands:
                if lo <= r < hi:
                    per_r.setdefault((lo, hi), []).append(ax)
                    break
    dens = [len(v) for v in cells.values()]
    out = {
        "n_tris": len(areas),
        "plan_area": stats(areas),
        "share_under_4u2": float(np.mean(np.asarray(areas) < 4.0)) if areas else None,
        "share_under_0p05u2": float(np.mean(np.asarray(areas) < 0.05)) if areas else None,
        "n_cells": len(cells),
        "tris_per_cell": stats(dens),
        "cells_over_7": int(sum(1 for d in dens if d > 7)),
        "share_cells_over_7": float(np.mean(np.asarray(dens) > 7)) if dens else None,
    }
    if per_r:
        out["by_radius"] = {f"{lo}-{hi}": {"n": len(v), "area_med": pct(v, 50), "area_p10": pct(v, 10)}
                            for (lo, hi), v in sorted(per_r.items())}
    return out


def load_sheet(root: Path, blocks, tag):
    Ws, tris_all, topo_all = [], [], []
    base = 0
    for (bx, by) in blocks:
        cands = list(root.rglob(f"Block[[]{bx}[]][[]{by}[]] Terrain.ff9mesh"))
        if not cands:
            continue
        W, tris, topo, _ = read_loose(cands[0], bx, by)
        Ws.append(W)
        tris_all.extend([(a + base, b + base, c + base) for (a, b, c) in tris])
        topo_all.extend(topo)
        base += len(W)
    if not Ws:
        raise RuntimeError(f"no blocks found for {tag} under {root}")
    return np.vstack(Ws), tris_all, topo_all


def main():
    result = {"instrument": str(Path(__file__).resolve()), "readonly": True}

    print("A. donor de-tilt budget ...", flush=True)
    result["A_detilt_budget"] = part_a()

    print("B. stock foot-line roughness envelope ...", flush=True)
    result["B_stock_foot_envelope"] = part_b()

    bench_blocks = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
    centre = (416.0, -512.0)

    print("C. deployed bench tessellation ...", flush=True)
    live = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
    W, tris, topo = load_sheet(live, bench_blocks, "live")
    result["C_live_bench"] = {
        "source": str(live),
        "n_tris_total": len(tris),
        "ground": tessellate(W, tris, topo, GRASS, centre),
        "plateau_carried": tessellate(W, tris, topo, PLATEAU, centre, radial=False),
        "rock": tessellate(W, tris, topo, ROCK, centre, radial=False),
    }

    print("D. pre-wall baseline tessellation ...", flush=True)
    bks = sorted((MAIN / "backups").glob("terrace-strip-prewall.*"))
    if bks:
        W2, tris2, topo2 = load_sheet(bks[-1], bench_blocks, "prewall")
        result["D_prewall_bench"] = {
            "source": str(bks[-1]),
            "n_tris_total": len(tris2),
            "ground": tessellate(W2, tris2, topo2, GRASS, centre),
        }

    print("E. stock ground tessellation reference (donor + 4 neighbours) ...", flush=True)
    Ws, ts, tp = [], [], []
    base = 0
    for (bx, by) in [(15, 14), (14, 14), (16, 14), (15, 13), (15, 15)]:
        r = read_tris(bx, by)
        if r is None:
            continue
        Wd, td, tpd, _ = r
        Ws.append(Wd)
        ts.extend([(a + base, b + base, c + base) for (a, b, c) in td])
        tp.extend(tpd)
        base += len(Wd)
    Wd = np.vstack(Ws)
    result["E_stock_reference"] = {"ground": tessellate(Wd, ts, tp, GRASS, radial=False)}

    p = OUT / "minchange_detilt.json"
    p.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\nwrote {p}")

    # ---- console digest
    A = result["A_detilt_budget"]["donor_block_only"]
    for nm in ("grass_and_forest", "grass_touching", "grass_only"):
        e = A.get(nm, {})
        if not e.get("n"):
            continue
        print(f"  A {nm:18s} n={e['n']:3d} raw span {e['raw_spread_maxmin']:.2f}u "
              f"(p10-p90 {e['raw_spread_p10_p90']:.2f}) -> plane tilt {e['plane']['tilt_deg']:.2f}deg "
              f"rise {e['plane']['plane_rise_across_footprint']:.2f}u -> DETILTED span "
              f"{e['detilted_spread_maxmin']:.2f}u (p10-p90 {e['detilted_spread_p10_p90']:.2f}, "
              f"rms {e['detilted_resid']['rms']:.2f})")
    B = result["B_stock_foot_envelope"]
    print(f"  B stock feet: {B['blocks_with_grass_foot']} blocks; neighbour |dy| med "
          f"{B['neighbour_abs_dy_all']['med']:.2f} p90 {B['neighbour_abs_dy_all']['p90']:.2f}; "
          f"per-block detilt p10-p90 med {B['per_block_detilt_p10_p90']['med']:.2f} "
          f"p90 {B['per_block_detilt_p10_p90']['p90']:.2f}; tilt med {B['per_block_tilt_deg']['med']:.2f}deg")
    C = result["C_live_bench"]["ground"]
    print(f"  C live ground: {C['n_tris']} tris, area med {C['plan_area']['med']:.2f}u2, "
          f"tris/cell med {C['tris_per_cell']['med']:.1f} max {C['tris_per_cell']['max']:.0f}, "
          f"cells>7 {C['share_cells_over_7']*100:.1f}%")
    if "D_prewall_bench" in result:
        D = result["D_prewall_bench"]["ground"]
        print(f"  D prewall ground: {D['n_tris']} tris, area med {D['plan_area']['med']:.2f}u2, "
              f"tris/cell med {D['tris_per_cell']['med']:.1f} max {D['tris_per_cell']['max']:.0f}")
    E = result["E_stock_reference"]["ground"]
    print(f"  E stock ground: {E['n_tris']} tris, area med {E['plan_area']['med']:.2f}u2, "
          f"tris/cell med {E['tris_per_cell']['med']:.1f} max {E['tris_per_cell']['max']:.0f}")
    if "by_radius" in C:
        print("  C by radius:", {k: round(v["area_med"], 2) for k, v in C["by_radius"].items()})


if __name__ == "__main__":
    main()
