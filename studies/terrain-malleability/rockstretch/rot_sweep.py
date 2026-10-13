"""`world-mountain --rot`: the real donors carved at every 15 degrees, offline, on a flat bench.

Uaho, the crag and comp20 (the rock-only qualified massifs), each at 0..345 deg in 15-deg steps, rigid and at
--rock-height 1.5, exact --center on the test suite's flat 2x2-block mains bench (interior seat). Records, per
carve, pass or the gate that refused, plus the gate numbers (rigidity drift, zip rise, zip winding, apron slope,
dropped and zip tris), and checks:
  R1 rotation is rigid: the rigidity drift at every angle equals the 0-deg carry's (to 0.001);
  R2 a quarter angle through rot_deg takes the exact quarter-turn path (the int swap the scan uses);
  R3 the texture rides unchanged: the rock's area-weighted texel density and anisotropy (p10/p50/p90) and its
     total UV area equal the 0-deg carry's within 1%. (Not the UV multiset: a carry across a block border splits
     rock tris there, minting lerped UVs where the border cuts, and the lawn-line snap retouches fringe corners;
     both depend on placement, so they differ between angles -- and between quarter turns on the old path.)
Writes out/rot_sweep.json.  Rerun: py studies/terrain-malleability/rockstretch/rot_sweep.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "ff9mapkit" / "tests"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import interior as IN, extract as X  # noqa: E402
import test_world_interior as TW  # noqa: E402  (the suite's mains-grid bench)

DONORS = {"uaho": [(0, 0)], "crag": [(10, 5), (10, 6)], "comp20": [(12, 16), (12, 17)]}
ANGLES = list(range(0, 360, 15))
HEIGHTS = (1.0, 1.5)
CENTER = (256.0, -256.0)


def bench():
    return IN.soup_from_blocks({(bx, by): TW._grid_block(bx, by) for bx in (2, 3, 4, 5) for by in (2, 3, 4, 5)})


def rock_texture(res):
    """Area-weighted texel density / anisotropy quantiles and total UV area (px^2) of the carried rock."""
    P, T = [], []
    for bm in res["changed"].values():
        pos, uv, tan = bm.chan_arrays[X.CH_POS], bm.chan_arrays[X.CH_UV], bm.chan_arrays[X.CH_TAN]
        for t in bm.tris:
            if X.decode_id(int(round(tan[t[0]][0])))["topograph"] in IN.MOUNTAIN_ROCK_TOPOS:
                P.append([pos[i] for i in t])
                T.append([(uv[i][0] * 2048.0, uv[i][1] * 4096.0) for i in t])
    P, T = np.array(P, float), np.array(T, float)
    e1, e2 = P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]
    D = np.stack([T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]], axis=2)
    sv = np.linalg.svd(D @ np.linalg.pinv(np.stack([e1, e2], axis=2)), compute_uv=False)
    area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
    ok = area > 1e-4
    dens, ani, w = np.sqrt(sv[ok, 0] * sv[ok, 1]), sv[ok, 0] / np.maximum(sv[ok, 1], 1e-9), area[ok]

    def q(a, f):
        o = np.argsort(a)
        return float(a[o][np.searchsorted(np.cumsum(w[o]) / w.sum(), f)])
    uv_area = 0.5 * np.abs(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])).sum()
    return {"dens": [q(dens, f) for f in (0.1, 0.5, 0.9)], "aniso": [q(ani, f) for f in (0.1, 0.5, 0.9)],
            "uv_area": float(uv_area)}


def same_texture(a, b, tol=0.01):
    return (all(abs(x / y - 1) <= tol for x, y in zip(a["dens"] + a["aniso"], b["dens"] + b["aniso"]))
            and abs(a["uv_area"] / b["uv_area"] - 1) <= tol)


def main():
    rows, fails = [], []
    for name, blocks in DONORS.items():
        base = {}
        for h in HEIGHTS:
            for a in ANGLES:
                t0 = time.time()
                row = {"donor": name, "deg": a, "height": h}
                try:
                    res = IN.carve_mountain(bench(), center=CENTER, donor=blocks, rot_deg=a, rock_height=h,
                                            alcove="auto", log=lambda *x: None)
                    r = res["report"]
                    row.update(ok=True, rigid=r["rock_rigid"], zip_rise=r["zip_rise"], apron=r["apron_slope"],
                               dropped=r["dropped"], zip_tris=r["zip_tris"], peak=r["peak_y"],
                               blocks=len(r["blocks"]))
                    tex = rock_texture(res)
                    row["texture"] = {k: [round(v, 3) for v in x] if isinstance(x, list) else round(x, 1)
                                      for k, x in tex.items()}
                    if a == 0:
                        base[h] = (r["rock_rigid"], tex)
                    elif h in base:
                        if abs(r["rock_rigid"] - base[h][0]) > 1e-3:
                            fails.append(f"R1 {name} {a}deg x{h}: drift {r['rock_rigid']} vs 0deg {base[h][0]}")
                        if not same_texture(tex, base[h][1]):
                            fails.append(f"R3 {name} {a}deg x{h}: texture {row['texture']} vs 0deg {base[h][1]}")
                    if a % 90 == 0:                # R2: a quarter angle takes the exact int swap
                        row["quarter_path"] = isinstance(res["rot"], int) and res["rot"] == a // 90
                        if not row["quarter_path"]:
                            fails.append(f"R2 {name} {a}deg: not the exact quarter path (rot={res['rot']!r})")
                except ValueError as err:
                    row.update(ok=False, why=str(err)[:200])
                row["s"] = round(time.time() - t0, 1)
                rows.append(row)
                print(f"{name:7s} {a:3d}deg x{h}: " + ("PASS  drift {rigid:.4f} zipRise {zip_rise} apron {apron} "
                                                       "zip {zip_tris} dropped {dropped}".format(**row)
                                                       if row["ok"] else "REFUSED  " + row["why"]), flush=True)
    summary = {}
    for name in DONORS:
        for h in HEIGHTS:
            rs = [r for r in rows if r["donor"] == name and r["height"] == h]
            summary[f"{name} x{h}"] = {"pass": sum(r["ok"] for r in rs), "of": len(rs),
                                       "refused": {r["deg"]: r["why"][:80] for r in rs if not r["ok"]}}
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "rot_sweep.json").write_text(json.dumps({"rows": rows, "summary": summary, "fails": fails},
                                                            indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("R1-R3:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  ", f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
