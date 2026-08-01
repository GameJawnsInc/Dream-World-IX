"""LATTICE-SWAP FEASIBILITY -- read-only. Context-first lens for the ground-junction synthesis.

The question no prior instrument asked: can the donor's ground be dropped into a
lattice host CELL-EXACTLY -- one 4u cell swapped for one 4u cell, zero inserted
vertices, zero conformance splits -- at the round-8 pose?

If yes, the whole subdivision cascade (refine_wall edge-lerps, conformance splits,
centroid fans, border stitch, T-sweep, hole capper, residue stitch) is unnecessary
machinery, and the measured 25x tessellation excess on the bench (S2-verify: bench
grass tri median 0.32u2 vs stock 8.00u2) is a self-inflicted wound rather than a
consequence of carrying.

Measures, read-only, against stock disc-1 + the pre-wall pristine bench backup +
the live deployed bench (opened read-only; nothing written under the install):
  L1  donor (15,14) vertex lattice residency (4u grid), by topograph class
  L2  donor triangle cell-containment (does a tri stay inside one 4u cell?)
  L3  the same two for stock at large (is L1/L2 a property of stock ground generally?)
  L4  the same two for the pristine bench and the live round-8 bench
  L5  the donor's ground as a HEIGHT FIELD sampled at 4u lattice corners:
      coverage, and the residual of reconstructing its tris from corner heights
  L6  border-cut pricing: rock/plateau/forest vertices ON the block frame, and
      the free-standing height they would expose in a 1x1 block carry
  L7  island geometry: margin available around a 64x64 footprint at the bench
      radius, and the radius needed for a given margin
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

OUT = ROOT / "studies/overworld-topography/out/lattice_swap_feasibility.json"
CELL = 4.0
GRASS = {0, 1, 2, 3, 42}
PLATEAU = {10, 11, 12}
ROCK = {49}
FOREST = {36, 37}


def pct(a, q):
    return float(np.percentile(np.asarray(a, float), q)) if len(a) else None


def tris_of(bm):
    fi = bm.flat_index
    return [tuple(int(x) for x in fi[3 * t:3 * t + 3]) for t in range(len(fi) // 3)]


def topo_of(bm, idx):
    T = bm.chan_arrays[X.CH_TAN]
    return X.decode_id(int(round(T[idx][0])))["topograph"]


def lattice_stats(V, tris, topos, keep, ox=0.0, oz=0.0):
    """vertex lattice residency + tri cell containment for tris whose topo is in keep."""
    sel = [i for i, tp in enumerate(topos) if tp in keep]
    if not sel:
        return None
    vids = sorted({v for t in sel for v in tris[t]})
    dx, dz, dmax = [], [], []
    for v in vids:
        x = float(V[v][0]) + ox
        z = float(V[v][2]) + oz
        ex = abs(x / CELL - round(x / CELL)) * CELL
        ez = abs(z / CELL - round(z / CELL)) * CELL
        dx.append(ex)
        dz.append(ez)
        dmax.append(max(ex, ez))
    on = sum(1 for d in dmax if d <= 1e-3)
    # tri containment: all 3 verts inside one closed 4u cell
    contained = 0
    areas = []
    percell = defaultdict(int)
    for t in sel:
        P = [(float(V[v][0]) + ox, float(V[v][2]) + oz) for v in tris[t]]
        xs = [p[0] for p in P]
        zs = [p[1] for p in P]
        cx = math.floor((min(xs) + max(xs)) / 2 / CELL)
        cz = math.floor((min(zs) + max(zs)) / 2 / CELL)
        percell[(cx, cz)] += 1
        span_ok = (max(xs) - min(xs) <= CELL + 1e-3) and (max(zs) - min(zs) <= CELL + 1e-3)
        # and inside the SAME cell (allowing closed boundary)
        ix = {math.floor(min(x / CELL + 1e-6, x / CELL) ) for x in xs}
        iz = {math.floor(z / CELL + 1e-6) for z in zs}
        cell_ok = span_ok and len(ix) <= 2 and len(iz) <= 2
        if cell_ok:
            # strict: every vert on the boundary of, or inside, one cell
            lo_x, lo_z = min(xs), min(zs)
            k = (math.floor(lo_x / CELL + 1e-6), math.floor(lo_z / CELL + 1e-6))
            ok = all(k[0] * CELL - 1e-3 <= x <= (k[0] + 1) * CELL + 1e-3 for x in xs) and all(
                k[1] * CELL - 1e-3 <= z <= (k[1] + 1) * CELL + 1e-3 for z in zs)
            if ok:
                contained += 1
        ar = abs((P[1][0] - P[0][0]) * (P[2][1] - P[0][1]) - (P[2][0] - P[0][0]) * (P[1][1] - P[0][1])) / 2
        areas.append(ar)
    counts = sorted(percell.values())
    return {
        "n_tris": len(sel),
        "n_verts": len(vids),
        "on_lattice_share": round(on / len(vids), 4),
        "off_lattice_med": round(pct(dmax, 50), 4),
        "off_lattice_p90": round(pct(dmax, 90), 4),
        "tri_cell_contained_share": round(contained / len(sel), 4),
        "plan_area_med": round(pct(areas, 50), 3),
        "plan_area_p10": round(pct(areas, 10), 3),
        "cells": len(percell),
        "tris_per_cell_med": round(pct(counts, 50), 2),
        "tris_per_cell_max": int(max(counts)),
    }


res = {}

# ---------------- L1/L2/L5/L6 : the donor block ----------------
bx, by = 15, 14
bm = X.read_block(bx, by, disc=1, part="terrain")
V = bm.chan_arrays[X.CH_POS]
tris = tris_of(bm)
topos = [topo_of(bm, t[0]) for t in tris]
ox, oz = 64.0 * bx, -64.0 * by
# round-8 pose: yaw 0, translate (-576, +416) applied to WORLD coords
POSE = (-576.0, 416.0)

res["donor_15_14"] = {
    "n_tris": len(tris),
    "class_counts": {str(k): sum(1 for t in topos if t == k) for k in sorted(set(topos))},
    "grass": lattice_stats(V, tris, topos, GRASS, ox, oz),
    "plateau": lattice_stats(V, tris, topos, PLATEAU, ox, oz),
    "rock": lattice_stats(V, tris, topos, ROCK, ox, oz),
    "forest": lattice_stats(V, tris, topos, FOREST, ox, oz),
}
# pose invariance check: the pose must not move the lattice phase
res["donor_15_14"]["grass_posed"] = lattice_stats(
    V, tris, topos, GRASS, ox + POSE[0], oz + POSE[1])
res["pose_lattice_phase"] = {
    "tx": POSE[0], "tz": POSE[1],
    "tx_mod_4": POSE[0] % 4.0, "tz_mod_4": POSE[1] % 4.0,
    "tx_mod_64": POSE[0] % 64.0, "tz_mod_64": POSE[1] % 64.0,
    "donor_block_origin_posed": (ox + POSE[0], oz + POSE[1]),
}

# L5: donor ground as a height field on lattice corners
gsel = [i for i, tp in enumerate(topos) if tp in GRASS]
corner_y = defaultdict(list)
for t in gsel:
    for v in tris[t]:
        x = float(V[v][0]) + ox
        z = float(V[v][2]) + oz
        y = float(V[v][1])
        kx, kz = x / CELL, z / CELL
        if abs(kx - round(kx)) <= 1e-3 and abs(kz - round(kz)) <= 1e-3:
            corner_y[(int(round(kx)), int(round(kz)))].append(y)
spread = [max(v) - min(v) for v in corner_y.values()]
res["donor_height_field"] = {
    "lattice_corners_with_grass": len(corner_y),
    "corner_y_spread_med": round(pct(spread, 50), 4),
    "corner_y_spread_max": round(max(spread), 4) if spread else None,
    "corner_y_min": round(min(min(v) for v in corner_y.values()), 3),
    "corner_y_max": round(max(max(v) for v in corner_y.values()), 3),
    "note": "spread ~0 => the donor's grass y is single-valued per lattice corner, "
            "i.e. it IS a height field a lattice host can carry exactly",
}

# L6: border-cut pricing -- non-grass verts sitting ON the block frame
frame_hits = defaultdict(list)
for t, tp in enumerate(topos):
    if tp in GRASS:
        continue
    for v in tris[t]:
        x = float(V[v][0])
        z = float(V[v][2])
        y = float(V[v][1])
        for name, on in (("W", abs(x) < 1e-3), ("E", abs(x - 64.0) < 1e-3),
                         ("N", abs(z) < 1e-3), ("S", abs(z + 64.0) < 1e-3)):
            if on:
                frame_hits[name].append((y, tp))
res["border_cut_price"] = {
    k: {
        "n_verts": len(v),
        "y_min": round(min(y for y, _ in v), 2),
        "y_max": round(max(y for y, _ in v), 2),
        "classes": sorted({int(tp) for _, tp in v}),
        "verts_above_y6": sum(1 for y, _ in v if y > 6.0),
    }
    for k, v in sorted(frame_hits.items())
}

# ---------------- L3 : stock at large ----------------
blocks = X.list_blocks(disc=1)
agg = {"grass": [], "rock": []}
n_read = 0
for (sx, sy) in blocks[::4]:
    try:
        b = X.read_block(sx, sy, disc=1, part="terrain")
    except Exception:
        continue
    n_read += 1
    Vs = b.chan_arrays[X.CH_POS]
    ts = tris_of(b)
    tps = [topo_of(b, t[0]) for t in ts]
    o = (64.0 * sx, -64.0 * sy)
    for key, keep in (("grass", GRASS), ("rock", ROCK)):
        s = lattice_stats(Vs, ts, tps, keep, o[0], o[1])
        if s:
            agg[key].append(s)
res["stock_sample"] = {"blocks_read": n_read, "blocks_listed": len(blocks)}
for key, rows in agg.items():
    if not rows:
        continue
    res["stock_sample"][key] = {
        "n_blocks": len(rows),
        "on_lattice_share_med": round(pct([r["on_lattice_share"] for r in rows], 50), 4),
        "tri_cell_contained_med": round(pct([r["tri_cell_contained_share"] for r in rows], 50), 4),
        "plan_area_med_med": round(pct([r["plan_area_med"] for r in rows], 50), 3),
        "tris_per_cell_max_max": int(max(r["tris_per_cell_max"] for r in rows)),
    }

# ---------------- L4 : pristine + live bench ----------------
def read_bench(root, blocks):
    out = []
    for (cx, cz) in blocks:
        rdir = root / f"r{cz}"
        f = rdir / f"Block[{cx}][{cz}] Terrain.ff9mesh"
        if not f.exists():
            continue
        b = MSH.blockmesh_from_ff9mesh(f.read_bytes())
        out.append(((cx, cz), b))
    return out


BENCH_BLOCKS = [(x, z) for x in (5, 6, 7) for z in (7, 8)]
live_root = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
                 r"\FF9CustomMap-world\FF9_Data\WorldMap\Disc9\0_1")
for label, root in (("live_round8", live_root),):
    rows = []
    try:
        got = read_bench(root, BENCH_BLOCKS)
    except Exception as e:  # pragma: no cover
        res[label] = {"error": repr(e)}
        continue
    for (cx, cz), b in got:
        Vb = b.chan_arrays[X.CH_POS]
        tb = tris_of(b)
        pb = [topo_of(b, t[0]) for t in tb]
        s = lattice_stats(Vb, tb, pb, GRASS, 64.0 * cx, -64.0 * cz)
        if s:
            rows.append(s)
    if rows:
        tot_t = sum(r["n_tris"] for r in rows)
        res[label] = {
            "blocks": len(rows),
            "n_grass_tris": tot_t,
            "on_lattice_share_med": round(pct([r["on_lattice_share"] for r in rows], 50), 4),
            "tri_cell_contained_med": round(pct([r["tri_cell_contained_share"] for r in rows], 50), 4),
            "plan_area_med_med": round(pct([r["plan_area_med"] for r in rows], 50), 4),
            "tris_per_cell_max_max": int(max(r["tris_per_cell_max"] for r in rows)),
            "per_block": rows,
        }

pri = ROOT.parent.parent.parent / "backups"  # placeholder, resolved below
prewall = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
if prewall.exists():
    rows = []
    for cand in [prewall / "0_1", prewall]:
        got = read_bench(cand, BENCH_BLOCKS)
        if got:
            break
    for (cx, cz), b in got:
        Vb = b.chan_arrays[X.CH_POS]
        tb = tris_of(b)
        pb = [topo_of(b, t[0]) for t in tb]
        s = lattice_stats(Vb, tb, pb, GRASS, 64.0 * cx, -64.0 * cz)
        if s:
            rows.append(s)
    if rows:
        res["pristine_bench"] = {
            "blocks": len(rows),
            "n_grass_tris": sum(r["n_tris"] for r in rows),
            "on_lattice_share_med": round(pct([r["on_lattice_share"] for r in rows], 50), 4),
            "tri_cell_contained_med": round(pct([r["tri_cell_contained_share"] for r in rows], 50), 4),
            "plan_area_med_med": round(pct([r["plan_area_med"] for r in rows], 50), 4),
            "tris_per_cell_max_max": int(max(r["tris_per_cell_max"] for r in rows)),
        }
    else:
        res["pristine_bench"] = {"error": "no Terrain.ff9mesh found under the backup"}
else:
    res["pristine_bench"] = {"error": "backup dir not present"}

# ---------------- L7 : island margin geometry ----------------
half = 32.0
halfdiag = math.hypot(half, half)
res["island_margin"] = {
    "footprint": "64x64u block, half-extent 32.0u, half-diagonal %.2fu" % halfdiag,
    "bench_grass_reach_u": 50.6,
    "margin_at_midedge_at_50p6": round(50.6 - half, 2),
    "margin_at_corner_at_50p6": round(50.6 - halfdiag, 2),
    "radius_for_16u_corner_margin": round(halfdiag + 16.0, 2),
    "area_at_that_radius": round(math.pi * (halfdiag + 16.0) ** 2, 0),
    "bench_area_measured_u2": 7488.0,
    "growth_factor": round(math.pi * (halfdiag + 16.0) ** 2 / 7488.0, 3),
}

OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
print("\nwrote", OUT)
