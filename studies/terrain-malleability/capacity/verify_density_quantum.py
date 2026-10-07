"""VERIFIER for CAP-7 (READ-ONLY on the install; reuses census.py's decoder + cache).

Two adversarial checks:

 (1) NEGATIVE CALIBRATION of the 1/256-grid instrument. resolution.py's only calibration is Sea4f, which is
     on-grid by construction, so a "100% on the 1/256 grid" verdict could come from an instrument that cannot
     fail. Here the SAME grid_frac test is run on the kit-authored deployed Terrain overrides (float32, never
     snapped) -- if those also read ~100%, the stock 100% means nothing.

 (2) THE DENSITY UNIT. CAP-7 quotes "stock-like density ~0.08 tris/u^2". That number is tris / 4096 u^2
     (the whole 64x64 block, sea included). The density a builder must match is tris per COVERED plan area.
     This recomputes both from out/census_cache.json (per-block tris / areaxz_sum) and 1/median-tri-area.

Writes out/verify_density_quantum.json.  Run:  py studies/terrain-malleability/capacity/verify_density_quantum.py
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
ROOT = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"


def grid_frac(V, step):           # identical to resolution.py's test
    q = V / step
    return float(np.mean(np.all(np.abs(q - np.round(q)) < 1e-4, axis=1)))


def read_verts(p):
    b = p.read_bytes()
    assert b[:4] == b"F9WM"
    ver, vc, ic, flags = struct.unpack_from("<iiii", b, 4)
    return np.frombuffer(b, dtype="<f4", count=vc * 3, offset=20).reshape(vc, 3).astype(np.float64)


def main():
    res = {}
    # (1) negative calibration on deployed kit-authored terrain
    fr256, fr4, n = [], [], 0
    for p in sorted((ROOT / "Disc1").rglob("*Terrain.ff9mesh")):
        V = read_verts(p)
        if len(V) < 30:
            continue                      # skip the tiny divert/hidden stubs
        fr256.append(grid_frac(V, 1 / 256))
        fr4.append(grid_frac(V[:, [0, 2]], 4.0))
        n += 1
    res["deployed_disc1_terrain_files"] = n
    res["deployed_on_1_256_grid_median"] = round(float(np.median(fr256)), 4) if fr256 else None
    res["deployed_on_1_256_grid_min_max"] = [round(min(fr256), 4), round(max(fr256), 4)] if fr256 else None
    res["deployed_files_fully_on_1_256_grid"] = int(sum(f > 0.9999 for f in fr256))
    res["deployed_on_4u_lattice_median"] = round(float(np.median(fr4)), 4) if fr4 else None

    # (2) density units, stock disc1 terrain
    rows = json.loads((OUT / "census_cache.json").read_text(encoding="utf-8"))["rows"]
    ter = [r for r in rows if r["disc"] == 1 and r["dir"] == "0_1" and r["part"] == "terrain"]
    per_block = np.array([r["tris"] / 4096.0 for r in ter])
    per_cover = np.array([r["tris"] / r["areaxz_sum"] for r in ter if r["areaxz_sum"] > 1.0])
    dist = json.loads((OUT / "census_cache.json").read_text(encoding="utf-8"))["dist"]["disc1|0_1|terrain"]
    res["density_tris_per_block_area_median"] = round(float(np.median(per_block)), 4)
    res["density_tris_per_covered_xz_area_median"] = round(float(np.median(per_cover)), 4)
    res["density_tris_per_covered_xz_area_p5_p95"] = [round(float(np.percentile(per_cover, 5)), 4),
                                                       round(float(np.percentile(per_cover, 95)), 4)]
    res["one_over_median_tri_xz_area"] = round(1.0 / dist["areaxz"]["p50"], 4)
    res["one_over_median_tri_3d_area"] = round(1.0 / dist["area3d"]["p50"], 4)
    OUT.mkdir(exist_ok=True)
    (OUT / "verify_density_quantum.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
