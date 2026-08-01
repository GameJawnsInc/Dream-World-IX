"""THE GUTTER PREDICATE, APPLIED TO THE DEPLOYED MESH (completeness critic).

THE MOGURI-GUTTER LAW says any ground uv CROSSING a transparent atlas gutter smears
in game and that no offline sampler which skips transparent texels can see it. The
panel applied that predicate to the DONOR's own 97 re-row candidate triangles
(corpus_rerow_check.py) and to nothing else. It was never applied to the live mesh,
to the pristine bench, or to stock as a control -- so the arc has no idea whether
the live bench's ground crosses gutters at a rate stock does not.

Per triangle: does its uv bounding box straddle a grass-quadrant boundary (the u
split at 0.06445/0.06641 or the v split at 0.79883/0.79980), does any corner leave
FAM_REGION['main'] entirely, and how many distinct quadrant rects does it touch.

Read-only. Writes only out/critic_gutter_live.json.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb")
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import mesh as MESH  # noqa: E402
from ff9mapkit.world.grassland import GRASS_U_HALF, GRASS_V_HALF, FAM_REGION  # noqa: E402

OUT = ROOT / "studies" / "overworld-topography" / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
PRISTINE = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")

BENCH = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
DONOR = [(15, 14), (14, 14), (16, 14), (15, 13), (15, 15)]
CENTER = (416.0, -512.0)
GRASS = {0, 1, 2, 3, 42}
EPS = 1e-6

MAIN = FAM_REGION["main"]


def quad_of(u, v):
    """Which grass quadrant rect (if any) this uv point is inside. None = gutter/outside."""
    qu = qv = None
    for i, (a, b) in enumerate(GRASS_U_HALF):
        if a - EPS <= u <= b + EPS:
            qu = i
    for j, (a, b) in enumerate(GRASS_V_HALF):
        if a - EPS <= v <= b + EPS:
            qv = j
    if qu is None or qv is None:
        return None
    return (qu, qv)


def classify(U, tris, T, V, ox, oz):
    out = []
    for a, b, c in tris:
        try:
            topo = X.decode_id(int(round(T[a][0])))["topograph"]
        except Exception:
            continue
        if topo not in GRASS:
            continue
        us = [U[i][0] for i in (a, b, c)]
        vs = [U[i][1] for i in (a, b, c)]
        qs = {quad_of(u, v) for u, v in zip(us, vs)}
        outside = any(not (MAIN[0] - EPS <= u <= MAIN[2] + EPS
                           and MAIN[1] - EPS <= v <= MAIN[3] + EPS)
                      for u, v in zip(us, vs))
        # does the uv bbox straddle the internal split?
        u_lo, u_hi = min(us), max(us)
        v_lo, v_hi = min(vs), max(vs)
        cross_u = u_lo < GRASS_U_HALF[0][1] - EPS and u_hi > GRASS_U_HALF[1][0] + EPS
        cross_v = v_lo < GRASS_V_HALF[0][1] - EPS and v_hi > GRASS_V_HALF[1][0] + EPS
        p = [np.array([V[i][0] + ox, V[i][1], V[i][2] + oz]) for i in (a, b, c)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        a3 = 0.5 * float(np.linalg.norm(n))
        cx = float((p[0][0] + p[1][0] + p[2][0]) / 3.0)
        cz = float((p[0][2] + p[1][2] + p[2][2]) / 3.0)
        out.append(dict(cross_u=cross_u, cross_v=cross_v, outside=outside,
                        nq=len({q for q in qs if q is not None}),
                        any_gutter_corner=(None in qs), a3=a3,
                        r=math.hypot(cx - CENTER[0], cz - CENTER[1])))
    return out


def summ(recs, label):
    if not recs:
        return {"label": label, "n": 0}
    n = len(recs)
    A = sum(r["a3"] for r in recs) or 1.0
    def sh(pred):
        return round(sum(1 for r in recs if pred(r)) / n, 4)
    def sha(pred):
        return round(sum(r["a3"] for r in recs if pred(r)) / A, 4)
    return {
        "label": label, "n_grass_tris": n, "area3d_u2": round(A, 1),
        "share_crossing_a_gutter": sh(lambda r: r["cross_u"] or r["cross_v"]),
        "AREA_share_crossing_a_gutter": sha(lambda r: r["cross_u"] or r["cross_v"]),
        "share_cross_u": sh(lambda r: r["cross_u"]),
        "share_cross_v": sh(lambda r: r["cross_v"]),
        "share_corner_outside_main_region": sh(lambda r: r["outside"]),
        "AREA_share_corner_outside_main": sha(lambda r: r["outside"]),
        "share_corner_in_a_gutter": sh(lambda r: r["any_gutter_corner"]),
        "share_touching_2plus_quadrants": sh(lambda r: r["nq"] >= 2),
    }


def main():
    res = {"what": "THE MOGURI-GUTTER PREDICATE on the DEPLOYED mesh, with stock and the "
                   "pristine bench as controls -- never run on anything but the donor's "
                   "97 re-row candidates before now"}
    sets = {}

    live = []
    for bx, by in BENCH:
        p = LIVE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.exists():
            continue
        bm = MESH.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, part="terrain")
        tris = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
        live += classify(bm.chan_arrays[X.CH_UV], tris, bm.chan_arrays[X.CH_TAN],
                         bm.chan_arrays[X.CH_POS], 64.0 * bx, -64.0 * by)
    sets["live_bench"] = live

    pris = []
    for bx, by in BENCH:
        hits = list(PRISTINE.rglob(f"Block[[]{bx}[]][[]{by}[]] Terrain.ff9mesh"))
        if not hits:
            continue
        bm = MESH.blockmesh_from_ff9mesh(hits[0], disc=9, x=bx, y=by, part="terrain")
        tris = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
        pris += classify(bm.chan_arrays[X.CH_UV], tris, bm.chan_arrays[X.CH_TAN],
                         bm.chan_arrays[X.CH_POS], 64.0 * bx, -64.0 * by)
    sets["pristine_bench"] = pris

    stock = []
    for bx, by in DONOR:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:
            continue
        tris = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
        stock += classify(bm.chan_arrays[X.CH_UV], tris, bm.chan_arrays[X.CH_TAN],
                          bm.chan_arrays[X.CH_POS], 64.0 * bx, -64.0 * by)
    sets["stock_donor_nbhd"] = stock

    # a WIDE stock control: 40 deterministic disc-1 blocks
    wide = []
    blocks = X.list_blocks(disc=1)
    for i, (bx, by) in enumerate(blocks):
        if i % 6:
            continue
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:
            continue
        tris = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
        wide += classify(bm.chan_arrays[X.CH_UV], tris, bm.chan_arrays[X.CH_TAN],
                         bm.chan_arrays[X.CH_POS], 64.0 * bx, -64.0 * by)
    sets["stock_wide_every6th_block"] = wide

    for k, v in sets.items():
        res[k] = summ(v, k)

    # radial localisation of the crossing population on the live bench
    rad = []
    for lo, hi in [(0, 16), (16, 24), (24, 32), (32, 40), (40, 48), (48, 64)]:
        sel = [r for r in live if lo <= r["r"] < hi]
        if not sel:
            rad.append({"band": f"{lo}-{hi}", "n": 0})
            continue
        rad.append({"band": f"{lo}-{hi}", "n": len(sel),
                    "share_crossing": round(sum(1 for r in sel if r["cross_u"] or r["cross_v"]) / len(sel), 4),
                    "share_outside_region": round(sum(1 for r in sel if r["outside"]) / len(sel), 4)})
    res["live_radial"] = rad

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "critic_gutter_live.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
