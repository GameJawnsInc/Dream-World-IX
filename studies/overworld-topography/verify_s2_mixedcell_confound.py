"""PASS 3 -- is the bench's 25.9% MIXED-quadrant-cell rate real, or a subdivision artifact?

Pass 2 found: MIXED-quadrant 4u cells = stock disc-1 2.3%, donor block (15,14) 1.0%,
LIVE round-8 bench 25.9%. But the bench also carries ~13 grass tris per 4u cell against
stock's ~1.8, so more tris per cell means more chances to disagree. This pass separates
the two:

  C1 TRIS PER 4u CELL, stock vs donor vs bench -- is the SUBDIVISION itself off-language?
  C2 MIXED rate CONDITIONED on tri count per cell -- at matched tri count, does the bench
     still mix more than stock? (If stock has no cells at the bench's tri counts, say so:
     that is an instrument limit, and it is itself the finding.)
  C3 WHERE are the bench's mixed cells -- radius from the island centre (416,-512), and
     their height band, to tell "the whole retile" from "the collar / falloff ring".
  C4 The same three statistics on the donor's own carried footprint inside the bench, so
     the carry can be told from the mint.

Read-only. Artifact -> out/verify_s2_mixedcell_confound.json
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit import config                                   # noqa: E402
from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402
from ff9mapkit.world import mesh as MSH                        # noqa: E402

OUT = Path(__file__).with_name("out") / "verify_s2_mixedcell_confound.json"
GU, GV = G.GRASS_U_HALF, G.GRASS_V_HALF
MAIN = G.FAM_REGION["main"]
GRASS_TOPO = {0, 1, 2, 3, 10, 11, 12, 13, 42, 59}
CENTRE = (416.0, -512.0)


def quad_of(u, v):
    qu = 0 if GU[0][0] <= u <= GU[0][1] else 1 if GU[1][0] <= u <= GU[1][1] else None
    qv = 0 if GV[0][0] <= v <= GV[0][1] else 1 if GV[1][0] <= v <= GV[1][1] else None
    return "gutter" if (qu is None or qv is None) else f"q{qu}{qv}"


def cells(blocks, reader, label):
    """4u cell -> list of (quad, y, area)."""
    c = defaultdict(list)
    for (bx, by) in blocks:
        try:
            bm = reader(bx, by)
        except Exception:                                          # noqa: BLE001
            continue
        if bm is None:
            continue
        V, U, T, fi = bm.verts, bm.uvs, bm.tangents, bm.flat_index
        ox, oz = 64.0 * bx, -64.0 * by
        for t in range(len(fi) // 3):
            idx = fi[3 * t:3 * t + 3]
            if X.decode_id(int(round(T[idx[0]][0])))["topograph"] not in GRASS_TOPO:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in idx]
            u = sum(q[0] for q in uv) / 3.0
            v = sum(q[1] for q in uv) / 3.0
            if not (MAIN[0] <= u <= MAIN[2] and MAIN[1] <= v <= MAIN[3]):
                continue
            w = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in idx]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cy = sum(p[1] for p in w) / 3.0
            ar = 0.5 * abs((w[1][0] - w[0][0]) * (w[2][2] - w[0][2]) -
                           (w[2][0] - w[0][0]) * (w[1][2] - w[0][2]))
            c[(int(cx // 4), int(cz // 4))].append((quad_of(u, v), cy, ar, cx, cz))
    return c


def stats(c, label, out):
    n = max(1, len(c))
    tc = Counter(len(v) for v in c.values())
    ntris = sum(len(v) for v in c.values())
    mixed = {k: 0 for k in tc}
    for v in c.values():
        if len({q for q, *_ in v}) > 1:
            mixed[len(v)] += 1
    tot_mixed = sum(mixed.values())
    ar = [a for v in c.values() for (_, _, a, _, _) in v]
    print(f"\n[{label}] 4u cells {n}; grass.main tris {ntris}; tris/cell mean "
          f"{ntris / n:.2f} med {int(np.median([len(v) for v in c.values()]))} "
          f"max {max(len(v) for v in c.values())}")
    print(f"   tri AREA (plan u^2): med {np.median(ar):.2f} p10 {np.percentile(ar, 10):.2f} "
          f"p90 {np.percentile(ar, 90):.2f}   (a stock 4u cell = 2 tris of 8.00)")
    print(f"   MIXED-quadrant cells {tot_mixed} = {tot_mixed / n:.1%}")
    print("   per tri-count bucket:  n_cells / mixed / rate")
    rows = {}
    for k in sorted(tc):
        print(f"      {k:3d} tris/cell: {tc[k]:6d} cells  {mixed[k]:6d} mixed  "
              f"{mixed[k] / tc[k]:6.1%}")
        rows[str(k)] = dict(cells=tc[k], mixed=mixed[k], rate=round(mixed[k] / tc[k], 4))
    out[label] = dict(cells=n, tris=ntris, tris_per_cell_mean=round(ntris / n, 2),
                      tris_per_cell_max=max(len(v) for v in c.values()),
                      tri_area_med=round(float(np.median(ar)), 2),
                      mixed_cells=tot_mixed, mixed_share=round(tot_mixed / n, 4),
                      by_tricount=rows)
    return tc, mixed


t0 = time.time()
RES = {}
GAME = config.find_game_path(None)


def bench_reader(bx, by):
    p = GAME / "FF9CustomMap-world" / MSH.override_relpath(9, bx, by, "0_1", "Terrain")
    return (MSH.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, lod="0_1", part="terrain")
            if p.is_file() else None)


cs = cells(X.list_blocks(disc=1), lambda a, b: X.read_block(a, b, disc=1), "stock")
tcs, mxs = stats(cs, "STOCK disc1", RES)
cd = cells([(15, 14)], lambda a, b: X.read_block(a, b, disc=1), "donor")
stats(cd, "DONOR (15,14)", RES)
cb = cells([(x, y) for x in (5, 6, 7) for y in (7, 8)], bench_reader, "bench")
tcb, mxb = stats(cb, "BENCH round8", RES)

# ---- C2 matched-tri-count comparison -------------------------------------------------------
print("\n== C2 MATCHED tri-count comparison (only buckets both populations have) ==")
shared = sorted(set(tcs) & set(tcb))
sm = sum(mxs[k] for k in shared)
sn = sum(tcs[k] for k in shared)
bm_ = sum(mxb[k] for k in shared)
bn = sum(tcb[k] for k in shared)
print(f"   shared buckets {shared}")
print(f"   stock: {sm}/{sn} = {sm / max(1, sn):.1%} mixed   |   bench: {bm_}/{bn} = "
      f"{bm_ / max(1, bn):.1%} mixed")
# direct-standardised: apply stock's per-bucket rate to the bench's bucket mix
exp = sum(tcb[k] * (mxs[k] / tcs[k]) for k in shared)
print(f"   bench cells in shared buckets {bn}; EXPECTED mixed at stock's per-bucket rates "
      f"{exp:.1f} ({exp / max(1, bn):.1%}) vs OBSERVED {bm_} ({bm_ / max(1, bn):.1%})  "
      f"-> excess x{bm_ / max(1e-9, exp):.1f}")
only_bench = sorted(set(tcb) - set(tcs))
ob_cells = sum(tcb[k] for k in only_bench)
print(f"   bench-ONLY tri-count buckets {only_bench}: {ob_cells} cells "
      f"({ob_cells / max(1, len(cb)):.1%}) -- stock has NO cell at these densities, so no "
      f"matched comparison exists there (declared instrument limit)")
RES["C2"] = dict(shared_buckets=shared, stock_mixed=sm, stock_cells=sn,
                 bench_mixed=bm_, bench_cells=bn,
                 stock_rate=round(sm / max(1, sn), 4), bench_rate=round(bm_ / max(1, bn), 4),
                 expected_at_stock_rates=round(exp, 1),
                 excess_factor=round(bm_ / max(1e-9, exp), 2),
                 bench_only_buckets=only_bench, bench_only_cells=ob_cells)

# ---- C3 WHERE ------------------------------------------------------------------------------
print("\n== C3 WHERE the bench's mixed cells sit (radius from island centre 416,-512) ==")
band = defaultdict(lambda: [0, 0])
ys = defaultdict(list)
for (cx, cz), v in cb.items():
    mx = len({q for q, *_ in v}) > 1
    r = math.hypot((cx * 4 + 2) - CENTRE[0], (cz * 4 + 2) - CENTRE[1])
    b = int(r // 8) * 8
    band[b][0] += 1
    band[b][1] += 1 if mx else 0
    ys[b] += [y for (_, y, _, _, _) in v]
for b in sorted(band):
    n, m = band[b]
    print(f"   r {b:3d}-{b + 8:3d}u: cells {n:4d}  mixed {m:4d} = {m / n:5.1%}   "
          f"y med {np.median(ys[b]):5.2f}")
RES["C3_radius"] = {str(b): dict(cells=band[b][0], mixed=band[b][1],
                                 rate=round(band[b][1] / band[b][0], 4),
                                 y_med=round(float(np.median(ys[b])), 2)) for b in sorted(band)}
gut = sum(1 for v in cb.values() for (q, *_) in v if q == "gutter")
gut_s = sum(1 for v in cs.values() for (q, *_) in v if q == "gutter")
print(f"\n   GUTTER-centroid tris (uv centroid in grass.main's internal bleed gutter): "
      f"bench {gut}/{sum(len(v) for v in cb.values())} "
      f"({gut / max(1, sum(len(v) for v in cb.values())):.2%})  vs stock {gut_s}/"
      f"{sum(len(v) for v in cs.values())} ({gut_s / max(1, sum(len(v) for v in cs.values())):.2%})")
RES["gutter"] = dict(bench=gut, bench_tris=sum(len(v) for v in cb.values()),
                     stock=gut_s, stock_tris=sum(len(v) for v in cs.values()))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(RES, indent=0, default=str))
print(f"\nartifact -> {OUT}\ntotal {time.time() - t0:.0f}s")
