"""`world-forest --spread / --rot` offline: the real (15,15) canopy over a grid of spreads and angles.

Host: the lab island (out/lab/island, `world-island --center 1372,-84 --radius 58 --lobes 1 --patches 0
--seed 42`, blocks (20,0)-(22,2), open ocean). Each carve runs `carve_forest(near=...)` + the placement census --
every gate the kit runs -- and records:
  S1 every carve passes every gate (placement, hole, zip, step law, perimeter walk-in, census);
  S2 the canopy's plan texel density is the donor's / s^2 (UV area per plan area, the stretch the owner judges) and
     its anisotropy stays the donor's (rotation and a uniform plan scale add none);
  S3 at rot 0 a wider canopy never climbs worse at the rim than the verbatim carry (its slopes are gentler);
     at any angle the walk-in gate (S1) holds it under 2.30.
RUN:  py studies/terrain-malleability/canopyspread/sweep.py   (writes out/sweep.json; ~10 min on 4 workers)
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOST = HERE / "out" / "lab" / "island" / "FF9CustomMap-lab"
NEAR = (1372.0, -84.0)
SPREADS = (1.0, 1.1, 1.25, 1.5)
ROTS = (0, 15, 30, 45, 60, 75, 90, 120, 200, 315)


def _kit():
    sys.path.insert(0, str(ROOT / "ff9mapkit"))
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
    from ff9mapkit.world import interior as IN, extract as X
    return IN, X


def uv_stats(bm_list, X):
    """The canopy's walkable top (topo 37, ny > 0.1: not its curtains) over the changed blocks: total UV area /
    plan area, and the median singular-value ratio of the plan->UV Jacobian (1 = isotropic). Curtains are out: a
    near-vertical tri's plan area is ~0, and the two hairline curtains (closed by a mapped carve) would swing the
    ratio on their own."""
    import numpy as np
    a_uv = a_pl = 0.0
    anis = []
    for bm in bm_list:
        P, U, T = bm.chan_arrays[X.CH_POS], bm.chan_arrays[X.CH_UV], bm.chan_arrays[X.CH_TAN]
        for t in bm.tris:
            if X.decode_id(int(round(T[t[0]][0])))["topograph"] != 37:
                continue
            p = np.array([[P[i][0], P[i][2]] for i in t])
            u = np.array([U[i] for i in t])
            dp = np.array([p[1] - p[0], p[2] - p[0]]).T
            du = np.array([u[1] - u[0], u[2] - u[0]]).T
            p3 = np.array([P[i] for i in t])
            n = np.cross(p3[1] - p3[0], p3[2] - p3[0])
            if abs(n[1]) <= 0.1 * np.linalg.norm(n):
                continue                                    # a curtain
            ap, au = abs(np.linalg.det(dp)) / 2, abs(np.linalg.det(du)) / 2
            if ap < 1e-6 or au < 1e-12:
                continue
            a_pl += ap
            a_uv += au
            sv = np.linalg.svd(du @ np.linalg.inv(dp), compute_uv=False)
            anis.append(float(sv[0] / sv[1]))
    return a_uv / a_pl, float(np.median(anis)), len(anis)


def one(job):
    spread, rot = job
    IN, X = _kit()
    lines = []
    out = {"spread": spread, "rot": rot}
    try:
        blocks = IN.read_deployed_blocks(str(HOST), near=NEAR, reach=128.0, disc=1)
        soup = IN.soup_from_blocks(blocks)
        res = IN.carve_forest(soup, near=NEAR, spread=spread, rot_deg=rot, log=lines.append)
        IN.census_gate(res["changed"], disc=1, probe=(res["center"], 37), baseline=blocks, log=lines.append)
        dens, anis, n = uv_stats(list(res["changed"].values()), X)
        m = re.search(r"worst single-step climb ([0-9.]+)", " ".join(lines))
        out.update(ok=True, center=res["center"], report=res["report"], uv_per_plan=dens, anis_med=anis, uv_tris=n,
                   walk_in=float(m.group(1)) if m else None)
    except Exception as err:                                                    # noqa: BLE001
        out.update(ok=False, error=f"{type(err).__name__}: {err}"[:400])
    out["log"] = [str(x)[:200] for x in lines]
    return out


def main():
    jobs = [(s, r) for s in SPREADS for r in ROTS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(one, jobs))
    base = next(r for r in rows if r["spread"] == 1.0 and r["rot"] == 0)
    print(f"{'spread':>6} {'rot':>4}  ok  centre        walk-in  uv/plan(rel)  s^-2    anis   zip")
    for r in rows:
        if not r["ok"]:
            print(f"{r['spread']:>6} {r['rot']:>4}  FAIL {r['error'][:150]}")
            continue
        rel = r["uv_per_plan"] / base["uv_per_plan"]
        print(f"{r['spread']:>6} {r['rot']:>4}  ok  {str(r['center']):13s} {r['walk_in']:.2f}    {rel:.4f}      "
              f"{r['spread'] ** -2:.4f}  {r['anis_med']:.3f}  {r['report']['zip_tris']}")
    s1 = all(r["ok"] for r in rows)
    s2 = base["ok"] and all(abs(r["uv_per_plan"] / base["uv_per_plan"] * r["spread"] ** 2 - 1) < 0.01
             and abs(r["anis_med"] - base["anis_med"]) < 0.01 * base["anis_med"] for r in rows if r["ok"])
    s3 = base["ok"] and all(r["walk_in"] <= base["walk_in"] + 1e-9 for r in rows if r["ok"] and r["rot"] == 0)
    print(f"S1 every carve clean: {'PASS' if s1 else 'FAIL'} ({sum(r['ok'] for r in rows)}/{len(rows)})")
    print(f"S2 texel density / s^2, anisotropy kept: {'PASS' if s2 else 'FAIL'}")
    print(f"S3 at rot 0, walk-in never worse than the verbatim carry ({base.get('walk_in')}): {'PASS' if s3 else 'FAIL'}")
    (HERE / "out" / "sweep.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
