"""LATTICE-SWAP, part 2 -- the BOUNDARY of the donor's grass footprint, plus the two
bench baselines read through the correct API. Read-only; nothing written under the install.

Part 1 (lattice_swap_feasibility.py) established:
  - the donor's grass y is SINGLE-VALUED per 4u lattice corner (spread med 0.0, max 0.0)
  - the donor's grass tri plan area is 8.0u2 median, 2 tris / cell, max 4 -- and stock
    at large is identical (7.98u2, max 7 map-wide)
  - donor grass verts are only ~53% exactly on the 4u lattice, and STOCK IS THE SAME
    (0.489) -- so stock ground is a lattice QUAD GRAPH with jittered interior verts

The question this part settles: a cell-swap weld only touches the BOUNDARY of the
swapped footprint. Are the boundary verts of a stock ground patch on the lattice, so a
host generated on the same lattice can weld to them with zero inserted vertices?
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb")
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import mesh as MSH  # noqa: E402

OUT = ROOT / "studies/overworld-topography/out/lattice_swap_boundary.json"
CELL = 4.0
GRASS = {0, 1, 2, 3, 42}


def pct(a, q):
    return float(np.percentile(np.asarray(a, float), q)) if len(a) else None


def tris_of(bm):
    fi = bm.flat_index
    return [tuple(int(v) for v in fi[3 * t:3 * t + 3]) for t in range(len(fi) // 3)]


def topos_of(bm, tris):
    T = bm.chan_arrays[X.CH_TAN]
    return [X.decode_id(int(round(T[t[0]][0])))["topograph"] for t in tris]


def boundary_report(V, tris, topos, keep, ox, oz, label):
    """Boundary = edges of the kept set owned by exactly one kept tri."""
    sel = [i for i, tp in enumerate(topos) if tp in keep]
    if not sel:
        return None
    key = {}
    for v in {v for t in sel for v in tris[t]}:
        key[v] = (round(float(V[v][0]) + ox, 3), round(float(V[v][2]) + oz, 3))
    own = defaultdict(int)
    for t in sel:
        a, b, c = tris[t]
        for e in ((a, b), (b, c), (c, a)):
            own[tuple(sorted((key[e[0]], key[e[1]])))] += 1
    bnd = [e for e, n in own.items() if n == 1]
    bverts = {p for e in bnd for p in e}
    on = 0
    dev = []
    for (x, z) in bverts:
        ex = abs(x / CELL - round(x / CELL)) * CELL
        ez = abs(z / CELL - round(z / CELL)) * CELL
        d = max(ex, ez)
        dev.append(d)
        if d <= 1e-3:
            on += 1
    elen = [math.dist(e[0], e[1]) for e in bnd]
    return {
        "label": label,
        "n_boundary_edges": len(bnd),
        "boundary_len_u": round(sum(elen), 1),
        "edge_len_med": round(pct(elen, 50), 3),
        "edge_len_p10": round(pct(elen, 10), 3),
        "edge_len_sub_1u_share": round(sum(1 for L in elen if L < 1.0) / len(elen), 4),
        "n_boundary_verts": len(bverts),
        "boundary_on_lattice_share": round(on / len(bverts), 4),
        "boundary_off_lattice_med": round(pct(dev, 50), 4),
        "boundary_off_lattice_p90": round(pct(dev, 90), 4),
    }


res = {}

# --- the donor block's grass patch boundary ---
bm = X.read_block(15, 14, disc=1, part="terrain")
V = bm.chan_arrays[X.CH_POS]
tris = tris_of(bm)
tps = topos_of(bm, tris)
res["donor_15_14_grass_boundary"] = boundary_report(
    V, tris, tps, GRASS, 64.0 * 15, -64.0 * 14, "donor (15,14) grass patch")

# --- stock control: every 4th block's grass patch boundary ---
rows = []
for (sx, sy) in X.list_blocks(disc=1)[::4]:
    try:
        b = X.read_block(sx, sy, disc=1, part="terrain")
    except Exception:
        continue
    t = tris_of(b)
    p = topos_of(b, t)
    r = boundary_report(b.chan_arrays[X.CH_POS], t, p, GRASS,
                        64.0 * sx, -64.0 * sy, f"({sx},{sy})")
    if r and r["n_boundary_edges"] >= 8:
        rows.append(r)
res["stock_grass_boundaries"] = {
    "n_blocks": len(rows),
    "on_lattice_share_med": round(pct([r["boundary_on_lattice_share"] for r in rows], 50), 4),
    "on_lattice_share_p10": round(pct([r["boundary_on_lattice_share"] for r in rows], 10), 4),
    "edge_len_med_med": round(pct([r["edge_len_med"] for r in rows], 50), 3),
    "sub_1u_share_med": round(pct([r["edge_len_sub_1u_share"] for r in rows], 50), 4),
}

# --- the two bench baselines ---
BB = [(x, z) for x in (5, 6, 7) for z in (7, 8)]
SRC = {
    "live_round8": Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
                        r"\FF9CustomMap-world\FF9_Data\WorldMap\Disc9\0_1"),
    "pristine_prewall": Path(r"C:\gd\Dream-World-IX\backups"
                             r"\terrace-strip-prewall.20260731-220001"),
}
for label, root in SRC.items():
    agg = {"tris": 0, "areas": [], "percell": defaultdict(int), "bnd": []}
    got = 0
    for (cx, cz) in BB:
        for cand in (root / f"r{cz}" / f"Block[{cx}][{cz}] Terrain.ff9mesh",
                     root / f"Block[{cx}][{cz}] Terrain.ff9mesh"):
            if cand.exists():
                break
        else:
            continue
        b = MSH.blockmesh_from_ff9mesh(str(cand), disc=9, x=cx, y=cz)
        got += 1
        Vb = b.chan_arrays[X.CH_POS]
        tb = tris_of(b)
        pb = topos_of(b, tb)
        ox, oz = 64.0 * cx, -64.0 * cz
        for i, tp in enumerate(pb):
            if tp not in GRASS:
                continue
            P = [(float(Vb[v][0]) + ox, float(Vb[v][2]) + oz) for v in tb[i]]
            ar = abs((P[1][0] - P[0][0]) * (P[2][1] - P[0][1])
                     - (P[2][0] - P[0][0]) * (P[1][1] - P[0][1])) / 2
            agg["areas"].append(ar)
            agg["tris"] += 1
            cxx = math.floor((min(p[0] for p in P) + max(p[0] for p in P)) / 2 / CELL)
            czz = math.floor((min(p[1] for p in P) + max(p[1] for p in P)) / 2 / CELL)
            agg["percell"][(cxx, czz)] += 1
        r = boundary_report(Vb, tb, pb, GRASS, ox, oz, f"{label} ({cx},{cz})")
        if r:
            agg["bnd"].append(r)
    if not got:
        res[label] = {"error": "no blocks found", "root": str(root)}
        continue
    counts = sorted(agg["percell"].values())
    res[label] = {
        "blocks": got,
        "n_grass_tris": agg["tris"],
        "plan_area_med": round(pct(agg["areas"], 50), 4),
        "plan_area_p10": round(pct(agg["areas"], 10), 4),
        "share_under_4u2": round(sum(1 for a in agg["areas"] if a < 4.0) / len(agg["areas"]), 4),
        "cells": len(counts),
        "tris_per_cell_med": round(pct(counts, 50), 2),
        "tris_per_cell_max": int(max(counts)),
        "cells_over_7_tris_share": round(sum(1 for c in counts if c > 7) / len(counts), 4),
        "boundary_on_lattice_share_med": round(
            pct([r["boundary_on_lattice_share"] for r in agg["bnd"]], 50), 4),
        "boundary_sub_1u_edge_share_med": round(
            pct([r["edge_len_sub_1u_share"] for r in agg["bnd"]], 50), 4),
    }

OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
print("\nwrote", OUT)
