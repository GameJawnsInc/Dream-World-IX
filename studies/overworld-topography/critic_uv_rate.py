"""THE UV-RATE INSTRUMENT (completeness critic, 2026-07-31).

The one quantity the whole eight-round STRETCH class is about -- texels per world
unit, i.e. duv/ds -- and the one quantity no gate in any of the four builders and no
instrument in the S1-S6 panel ever computed. The synthesis asserts a mechanism
("a cell that fine cannot wear one tile -- it wears a smear of one") without it.

Measured three ways, on three meshes, through ONE code path:
  A. per-triangle uv RATE: singular values of the 2x2 Jacobian d(uv_in_texels)/d(s)
     on an isometrically unfolded triangle (so slope is folded out, not ignored)
  B. per-triangle uv EXTENT in tiles vs its own 3D area -- the direct test of
     "does a 0.3u2 triangle wear a whole tile (magnification) or a sub-portion of
     one (affine inheritance, cosmetically inert)?"
  C. per-4u-cell uv extent and window count, for reference

Meshes: the LIVE deployed round-8 bench (read-only off the install), the PRISTINE
pre-wall bench backup, and the stock donor neighbourhood (disc 1).

Read-only. Writes only out/critic_uv_rate.json + .png.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb")
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import mesh as MESH  # noqa: E402

OUT = ROOT / "studies" / "overworld-topography" / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
PRISTINE = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")

BENCH_BLOCKS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
DONOR_BLOCKS = [(15, 14), (14, 14), (16, 14), (15, 13), (15, 15)]
CENTER = (416.0, -512.0)

ATLAS_W, ATLAS_H = 2048.0, 4096.0
TILE_U, TILE_V = 0.0625, 0.03125
GRASS = {0, 1, 2, 3, 42}


def pct(a, ps=(1, 10, 25, 50, 75, 90, 99)):
    if len(a) == 0:
        return {}
    a = np.asarray(a, dtype=float)
    return {f"p{p}": round(float(np.percentile(a, p)), 4) for p in ps} | {
        "n": int(len(a)), "min": round(float(a.min()), 4), "max": round(float(a.max()), 4),
        "mean": round(float(a.mean()), 4)}


def tri_records(V, U, T, tris, ox, oz, want_ground=True):
    """Per-triangle: uv rate singular values (atlas px per world unit), uv extent in
    tiles, 3D area, plan area, slope, world centroid, topograph."""
    recs = []
    for a, b, c in tris:
        p0 = np.array([V[a][0] + ox, V[a][1], V[a][2] + oz])
        p1 = np.array([V[b][0] + ox, V[b][1], V[b][2] + oz])
        p2 = np.array([V[c][0] + ox, V[c][1], V[c][2] + oz])
        e1, e2 = p1 - p0, p2 - p0
        n = np.cross(e1, e2)
        a3 = 0.5 * float(np.linalg.norm(n))
        if a3 <= 0.0:
            continue
        try:
            topo = X.decode_id(int(round(T[a][0])))["topograph"]
        except Exception:
            continue
        if want_ground and topo not in GRASS:
            continue
        aplan = 0.5 * abs(float(e1[0] * e2[2] - e1[2] * e2[0]))
        slope = math.degrees(math.acos(min(1.0, abs(float(n[1])) / (2.0 * a3))))
        # isometric unfold: 2D coords of the triangle in its own plane
        L1 = float(np.linalg.norm(e1))
        if L1 <= 1e-9:
            continue
        ex = e1 / L1
        ey = e2 - ex * float(np.dot(e2, ex))
        Ly = float(np.linalg.norm(ey))
        if Ly <= 1e-9:
            continue
        ey = ey / Ly
        s1 = np.array([L1, 0.0])
        s2 = np.array([float(np.dot(e2, ex)), Ly])
        # uv in ATLAS PIXELS
        q0 = np.array([U[a][0] * ATLAS_W, U[a][1] * ATLAS_H])
        d1 = np.array([U[b][0] * ATLAS_W, U[b][1] * ATLAS_H]) - q0
        d2 = np.array([U[c][0] * ATLAS_W, U[c][1] * ATLAS_H]) - q0
        S = np.array([s1, s2]).T          # 2x2 surface basis
        D = np.array([d1, d2]).T          # 2x2 uv deltas
        det = float(np.linalg.det(S))
        if abs(det) < 1e-12:
            continue
        J = D @ np.linalg.inv(S)          # px per world unit
        sv = np.linalg.svd(J, compute_uv=False)
        # uv extent of this tri, in tiles
        us = [U[a][0], U[b][0], U[c][0]]
        vs = [U[a][1], U[b][1], U[c][1]]
        eu = (max(us) - min(us)) / TILE_U
        ev = (max(vs) - min(vs)) / TILE_V
        cx = (p0[0] + p1[0] + p2[0]) / 3.0
        cz = (p0[2] + p1[2] + p2[2]) / 3.0
        recs.append(dict(sv_hi=float(sv[0]), sv_lo=float(sv[1]), a3=a3, aplan=aplan,
                         slope=slope, ext_u=eu, ext_v=ev,
                         ext_max=max(eu, ev), cx=float(cx), cz=float(cz), topo=topo))
    return recs


def read_live(bx, by):
    p = LIVE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    if not p.exists():
        return None
    return MESH.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, part="terrain")


def read_pristine(bx, by):
    # backup layout mirrors the deploy tree; find the file by name
    hits = list(PRISTINE.rglob(f"Block[[]{bx}[]][[]{by}[]] Terrain.ff9mesh"))
    if not hits:
        return None
    return MESH.blockmesh_from_ff9mesh(hits[0], disc=9, x=bx, y=by, part="terrain")


def harvest(reader, blocks, disc_stock=False):
    recs = []
    got = []
    for (bx, by) in blocks:
        try:
            bm = reader(bx, by)
        except Exception as e:  # noqa: BLE001
            print(f"  skip ({bx},{by}): {e}")
            continue
        if bm is None:
            continue
        V = bm.chan_arrays[X.CH_POS]
        U = bm.chan_arrays[X.CH_UV]
        T = bm.chan_arrays[X.CH_TAN]
        tris = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
        ox, oz = 64.0 * bx, -64.0 * by
        recs += tri_records(V, U, T, tris, ox, oz)
        got.append((bx, by))
    return recs, got


def summarize(recs, label):
    if not recs:
        return {"label": label, "n": 0}
    a3 = np.array([r["a3"] for r in recs])
    hi = np.array([r["sv_hi"] for r in recs])
    lo = np.array([r["sv_lo"] for r in recs])
    aniso = np.array([r["sv_hi"] / max(r["sv_lo"], 1e-9) for r in recs])
    extm = np.array([r["ext_max"] for r in recs])
    slope = np.array([r["slope"] for r in recs])
    # the magnification test: tile-extent per triangle SIZE
    lin = np.sqrt(np.maximum(a3, 1e-12))          # linear size proxy, world units
    tiles_per_u = extm / np.maximum(lin, 1e-9)    # tiles of atlas per world unit of tri
    return {
        "label": label,
        "n_tris": len(recs),
        "area3d_u2": pct(a3),
        "uv_rate_px_per_u_hi": pct(hi),
        "uv_rate_px_per_u_lo": pct(lo),
        "uv_anisotropy_hi_over_lo": pct(aniso),
        "tri_uv_extent_tiles": pct(extm),
        "tri_uv_extent_over_linear_size": pct(tiles_per_u),
        "slope_deg": pct(slope),
        "share_tris_under_1u2": round(float((a3 < 1.0).mean()), 4),
        "share_rate_hi_over_2x_median": None,
    }


def main():
    print("reading LIVE bench ...")
    live, live_got = harvest(read_live, BENCH_BLOCKS)
    print(f"  {len(live)} ground tris over {len(live_got)} blocks")
    print("reading PRISTINE bench backup ...")
    pris, pris_got = harvest(read_pristine, BENCH_BLOCKS)
    print(f"  {len(pris)} ground tris over {len(pris_got)} blocks")
    print("reading STOCK donor neighbourhood ...")
    stock = []
    stock_got = []
    for (bx, by) in DONOR_BLOCKS:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception as e:  # noqa: BLE001
            print(f"  skip ({bx},{by}): {e}")
            continue
        V = bm.chan_arrays[X.CH_POS]
        U = bm.chan_arrays[X.CH_UV]
        T = bm.chan_arrays[X.CH_TAN]
        tris = [bm.flat_index[3 * t:3 * t + 3] for t in range(len(bm.flat_index) // 3)]
        stock += tri_records(V, U, T, tris, 64.0 * bx, -64.0 * by)
        stock_got.append((bx, by))
    print(f"  {len(stock)} ground tris over {len(stock_got)} blocks")

    res = {
        "what": "uv RATE (atlas px per world unit) and per-tri uv EXTENT -- the duv/ds "
                "axis the synthesis names as ungated and then does not measure",
        "blocks": {"live": live_got, "pristine": pris_got, "stock_donor": stock_got},
        "stock_donor": summarize(stock, "stock donor neighbourhood (disc1)"),
        "pristine_bench": summarize(pris, "pristine pre-wall bench"),
        "live_bench": summarize(live, "live round-8 bench"),
    }

    # THE DECISIVE COMPARISON: is the fine live tessellation's uv rate stock-lawful?
    def rate_band(recs):
        hi = np.array([r["sv_hi"] for r in recs]) if recs else np.array([])
        return hi
    s_hi = rate_band(stock)
    l_hi = rate_band(live)
    p_hi = rate_band(pris)
    if len(s_hi) and len(l_hi):
        s_lo_b, s_hi_b = np.percentile(s_hi, 1), np.percentile(s_hi, 99)
        res["decisive"] = {
            "stock_rate_p1_p99_px_per_u": [round(float(s_lo_b), 3), round(float(s_hi_b), 3)],
            "live_share_inside_stock_p1_p99": round(float(((l_hi >= s_lo_b) & (l_hi <= s_hi_b)).mean()), 4),
            "pristine_share_inside_stock_p1_p99": (
                round(float(((p_hi >= s_lo_b) & (p_hi <= s_hi_b)).mean()), 4) if len(p_hi) else None),
            "live_share_over_2x_stock_median": round(float((l_hi > 2.0 * np.median(s_hi)).mean()), 4),
            "live_share_under_half_stock_median": round(float((l_hi < 0.5 * np.median(s_hi)).mean()), 4),
        }

    # radial breakdown on the live bench (the ring the owner points at)
    bands = [(0, 8), (8, 16), (16, 24), (24, 32), (32, 40), (40, 48), (48, 56)]
    radial = []
    for lo_r, hi_r in bands:
        sel = [r for r in live
               if lo_r <= math.hypot(r["cx"] - CENTER[0], r["cz"] - CENTER[1]) < hi_r]
        if not sel:
            radial.append({"band": f"{lo_r}-{hi_r}", "n": 0})
            continue
        hi = np.array([r["sv_hi"] for r in sel])
        an = np.array([r["sv_hi"] / max(r["sv_lo"], 1e-9) for r in sel])
        a3 = np.array([r["a3"] for r in sel])
        ex = np.array([r["ext_max"] for r in sel])
        radial.append({
            "band": f"{lo_r}-{hi_r}", "n": len(sel),
            "area3d_med": round(float(np.median(a3)), 3),
            "rate_hi_med": round(float(np.median(hi)), 2),
            "rate_hi_p99": round(float(np.percentile(hi, 99)), 2),
            "aniso_med": round(float(np.median(an)), 3),
            "aniso_p99": round(float(np.percentile(an, 99)), 3),
            "tri_uv_extent_tiles_med": round(float(np.median(ex)), 4),
            "share_extent_over_half_tile": round(float((ex > 0.5).mean()), 4),
        })
    res["live_radial"] = radial

    # stock reference for the same two shape statistics
    for name, recs in (("stock_donor", stock), ("pristine_bench", pris)):
        if not recs:
            continue
        an = np.array([r["sv_hi"] / max(r["sv_lo"], 1e-9) for r in recs])
        ex = np.array([r["ext_max"] for r in recs])
        res[name]["share_extent_over_half_tile"] = round(float((ex > 0.5).mean()), 4)
        res[name]["aniso_p99"] = round(float(np.percentile(an, 99)), 3)
    if live:
        an = np.array([r["sv_hi"] / max(r["sv_lo"], 1e-9) for r in live])
        ex = np.array([r["ext_max"] for r in live])
        res["live_bench"]["share_extent_over_half_tile"] = round(float((ex > 0.5).mean()), 4)
        res["live_bench"]["aniso_p99"] = round(float(np.percentile(an, 99)), 3)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "critic_uv_rate.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "live_radial"}, indent=1)[:4000])
    print("RADIAL:", json.dumps(res["live_radial"], indent=1))
    print("\nwrote", OUT / "critic_uv_rate.json")


if __name__ == "__main__":
    main()
