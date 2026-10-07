"""THE LAND-DONOR WATER FREE-RIDE -- what a sidecar-less reclaimed cell really registers under its Terrain.

Source: a reclaimed sea cell with a 'Terrain.ff9mesh' override and NO 'Donor.txt' loads the LandDonorPrefab
Block[12][10] of the current disc (WMWorld.cs:1210-1211 + ResolveReclaimDonor :556-557, both s34 PATCH lines),
and LoadBlock registers EVERY child slot that prefab carries (WMWorld.cs:778-807, STOCK) as a Form1+Form2
walkmesh + renderer. The s34 comment at WMWorld.cs:1207-1209 calls 12,10 "a Terrain child, no town Object,
no beach/sea" -- the census (census.py -> out/consumption_census.json) says 12,10 also carries Sea1/Sea3/Sea4/Sea5.

This script measures what that water IS, by a plan-view raster of the engine's own hit rule
(first mesh in registration order with a hit, Sea1 -> Sea3 -> Sea4 -> Sea5; topograph = tangent.x of the
hit tri's first corner, WMBlock.cs:210 / WMPhysics.cs:15):
  * coverage of the 64x64 cell by the free-riding water union,
  * the boat-legal share (boat mask {0x02600000, 0} -> topographs 53/54/57, memory project-ff9-overworld-
    terrain-authoring "OCEAN IS BOAT-WALKABLE"),
  * where the islet hole is.

CALIBRATION (asserted): the same raster on Block[12][0]:
  * sea4f (SeaBlockPrefab's mesh) must cover 100.000% of the cell,
  * sea4 (the cell's own) must miss exactly one 4x4 quad (16 u^2 = 0.390625%),
  * and Block[12][0]'s Sea6 (2 tris) must cover exactly that missing quad (hypothesis under test).

Rerun:  py studies/terrain-malleability/consumption/landdonor_water.py
Writes  out/landdonor_water.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                    # noqa: E402
from ff9mapkit.world import extract as X              # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
STEP = 0.125
BOAT_TOPO = {53, 54, 57}


def raster_first_hit(meshes, step=STEP):
    """meshes: [(name, BlockMesh)] in registration order. Returns (owner_index_grid, topo_grid) over the cell's
    local plan x in [0,64), z in (-64,0], sampled at cell centres. -1 = no hit (a MISS = invisible vehicle wall)."""
    xs = np.arange(step / 2, 64, step)
    zs = -np.arange(step / 2, 64, step)
    X_, Z_ = np.meshgrid(xs, zs)
    owner = np.full(X_.shape, -1, dtype=np.int32)
    topo = np.full(X_.shape, -1, dtype=np.int32)
    for mi, (_name, bm) in enumerate(meshes):
        V = np.asarray(bm.verts, dtype=np.float64)
        T = np.asarray(bm.tangents, dtype=np.float64)
        tris = np.asarray(bm.tris, dtype=np.int64)
        todo = owner < 0
        if not todo.any():
            break
        # first TRI in buffer order wins inside a mesh: paint in REVERSE so earlier tris overwrite later ones
        paint_o = np.full(X_.shape, -1, dtype=np.int32)
        paint_t = np.full(X_.shape, -1, dtype=np.int32)
        for ti in range(len(tris) - 1, -1, -1):
            a, b, c = V[tris[ti, 0]], V[tris[ti, 1]], V[tris[ti, 2]]
            n = np.cross(b - a, c - a)
            if n[1] <= 0.1 * np.linalg.norm(n):      # up-facing filter (WMPhysics.cs:22): ny > 0.1
                continue
            x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
            z0, z1 = min(a[2], b[2], c[2]), max(a[2], b[2], c[2])
            i0, i1 = np.searchsorted(-zs, -z1), np.searchsorted(-zs, -z0, side="right")
            j0, j1 = np.searchsorted(xs, x0), np.searchsorted(xs, x1, side="right")
            if i0 >= i1 or j0 >= j1:
                continue
            px, pz = X_[i0:i1, j0:j1], Z_[i0:i1, j0:j1]
            # barycentric in plan (x,z)
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / d
            l2 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / d
            l3 = 1 - l1 - l2
            inside = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
            sub_o, sub_t = paint_o[i0:i1, j0:j1], paint_t[i0:i1, j0:j1]
            sub_o[inside] = mi
            sub_t[inside] = (int(T[tris[ti, 0], 0]) & 0xFC) >> 2
        take = todo & (paint_o >= 0)
        owner[take] = paint_o[take]
        topo[take] = paint_t[take]
    return owner, topo


def frac(mask):
    return float(mask.mean())


def main():
    OUT.mkdir(exist_ok=True)
    res = {}
    # ---- calibration on Block[12][0] -----------------------------------------------------------------------
    s4f = X.read_block(12, 0, part="sea4f")
    s4 = X.read_block(12, 0, part="sea4")
    s6 = X.read_block(12, 0, part="sea6")
    o_f, _ = raster_first_hit([("sea4f", s4f)])
    o_4, _ = raster_first_hit([("sea4", s4)])
    o_6, _ = raster_first_hit([("sea6", s6)])
    cov_f = frac(o_f >= 0)
    miss_4 = frac(o_4 < 0)
    hole = (o_4 < 0)
    six = (o_6 >= 0)
    hole_eq_six = bool(np.array_equal(hole, six))
    c1 = abs(cov_f - 1.0) < 1e-9
    c2 = abs(miss_4 - 16 / 4096) < 1e-9
    print(f"CALIB 12,0 sea4f coverage = {cov_f:.6f} (want 1.0): {'OK' if c1 else 'FAIL'}")
    print(f"CALIB 12,0 sea4 miss = {miss_4 * 4096:.3f} u^2 (want 16): {'OK' if c2 else 'FAIL'}")
    print(f"TEST  12,0 Sea6 footprint == Sea4 hole: {hole_eq_six}  (sea6 area {frac(six) * 4096:.3f} u^2)")
    res["calibration"] = {"sea4f_cov": cov_f, "sea4_miss_u2": miss_4 * 4096, "sea6_fills_sea4_hole": hole_eq_six,
                          "ok": bool(c1 and c2)}
    # ---- the land donor 12,10 ------------------------------------------------------------------------------
    for disc in (1, 4):
        parts = []
        for p in ("sea1", "sea2", "sea3", "sea4", "sea5", "sea6"):
            try:
                parts.append((p, X.read_block(12, 10, disc=disc, part=p)))
            except ValueError:
                pass
        terr = X.read_block(12, 10, disc=disc, part="terrain")
        o, t = raster_first_hit(parts)
        ot, _ = raster_first_hit([("terrain", terr)])
        cov = frac(o >= 0)
        boat = frac(np.isin(t, list(BOAT_TOPO)))
        topo_hist = {int(k): int(v) for k, v in zip(*np.unique(t[t >= 0], return_counts=True))}
        owner_hist = {parts[int(k)][0]: int(v) for k, v in zip(*np.unique(o[o >= 0], return_counts=True))}
        hole = o < 0
        ys, xs = np.nonzero(hole)
        hole_bbox = None
        if len(xs):
            hole_bbox = [float(xs.min() * STEP), float(xs.max() * STEP + STEP), float(-(ys.min() * STEP)),
                         float(-(ys.max() * STEP + STEP))]
        r = {"parts": [p for p, _ in parts], "water_coverage": cov, "boat_legal_fraction": boat,
             "topo_hist_samples": topo_hist, "first_hit_owner_samples": owner_hist,
             "hole_fraction": frac(hole), "hole_bbox_local_x0x1_z0z1": hole_bbox,
             "terrain_tris": len(terr.tris), "terrain_footprint_fraction": frac(ot >= 0),
             "terrain_y_range": [float(min(v[1] for v in terr.verts)), float(max(v[1] for v in terr.verts))],
             "hole_inside_stock_islet": float(((ot >= 0) & hole).sum() / max(hole.sum(), 1))}
        res[f"disc{disc}_12_10"] = r
        print(f"disc {disc} Block[12][10]: parts={r['parts']} water covers {cov * 100:.2f}% of the cell, "
              f"boat-legal first hit {boat * 100:.2f}%, topo samples {topo_hist}, hole {r['hole_fraction'] * 100:.2f}% "
              f"bbox {hole_bbox}; stock islet terrain {r['terrain_tris']} tris covering "
              f"{r['terrain_footprint_fraction'] * 100:.2f}%, y {r['terrain_y_range']}; "
              f"hole-inside-islet {r['hole_inside_stock_islet'] * 100:.1f}%")
    (OUT / "landdonor_water.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote {OUT / 'landdonor_water.json'}")
    return 0 if res["calibration"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
