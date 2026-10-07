"""CAPACITY lane, step 9 -- THE GROUND-QUERY SCAN COST of stock blocks (the CPU side of "adding tris").

Source model (stock Memoria, cited in NOTES.md): a FULL SCAN (WMBlock.cs:185-200 -> WMPhysics.cs:13-46) walks
the block's Form-1 walk meshes in REGISTRATION order (WMWorld.cs:588-806: Object, Terrain, VolcanoCrater1,
VolcanoLava1, Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1..Sea6) and each mesh's tris in array order,
returning the FIRST hit. Per tri: a mapid skip test {4078,4088,2040} and the up-facing test ny>0.1 (CHEAP),
then 3x Transform.TransformPoint + intersect3D_RayTriangle (EXPENSIVE) only for tris that pass.
A miss (no hit anywhere) iterates every tri of every walk mesh.

For each disc-1 land block (block 219's early-return order is NOT modelled; it is 1 block) and a 16x16 grid of
plan points (cell centres), with the ray cast from the sky (so any surface below counts; the real ray starts
2.34375 above the actor and additionally rejects surfaces above it -- the from-sky count is the UPPER bound on
how deep the scan reaches before its first hit), count: tris ITERATED and tris EXPENSIVELY tested.

Calibration: a block's miss count must equal its total Form-1 walk-tri count; a plan point inside the stock
lawn must hit (stock = one up-facing sheet everywhere, WALK-QUERY-DECODE.md REGIME_STOCK) -> report the miss
rate, expected ~0 on land interiors.

Writes out/scan_cost.json.  Run:  py studies/terrain-malleability/capacity/scan_cost.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ff9mapkit.world import extract as X  # noqa: E402
from census import decode, PAT  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
ORDER = ["object", "terrain", "volcanocrater", "volcanolava", "beach1", "beach2", "stream", "river",
         "riverjoint", "falls", "sea1", "sea2", "sea3", "sea4", "sea5", "sea6"]
SKIP = {4078, 4088, 2040}


def block_soup(meshes, x, y):
    """Concatenated Form-1 walk tris in registration order: (A,B,C [m,3]), expensive_mask [m], part_of [m]."""
    As, Bs, Cs, ex, part = [], [], [], [], []
    for p in ORDER:
        o = meshes.get((x, y, p))
        if o is None:
            continue
        V, U, T, I, *_ = decode(o.read())
        tri = I.reshape(-1, 3)
        a, b, c = V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]]
        cr = np.cross(b - a, c - a)
        n = np.linalg.norm(cr, axis=1)
        ny = np.where(n > 0, cr[:, 1] / np.maximum(n, 1e-30), 0.0)
        mid = np.round(T[tri[:, 0], 0]).astype(np.int64)
        e = (~np.isin(mid, list(SKIP))) & (ny > 0.1)
        As.append(a); Bs.append(b); Cs.append(c); ex.append(e); part += [p] * len(tri)
    return np.concatenate(As), np.concatenate(Bs), np.concatenate(Cs), np.concatenate(ex), part


def first_hits(A, B, C, ex, pts):
    """For each plan point: index of the first EXPENSIVE-eligible tri whose XZ projection contains it."""
    # barycentric in XZ (vertical ray); degenerate XZ projections never contain the point (ray parallel)
    ax, az = A[:, 0][None], A[:, 2][None]
    v0x, v0z = (C[:, 0] - A[:, 0])[None], (C[:, 2] - A[:, 2])[None]
    v1x, v1z = (B[:, 0] - A[:, 0])[None], (B[:, 2] - A[:, 2])[None]
    px, pz = pts[:, 0][:, None] - ax, pts[:, 1][:, None] - az
    d00, d01, d11 = v0x * v0x + v0z * v0z, v0x * v1x + v0z * v1z, v1x * v1x + v1z * v1z
    d20, d21 = px * v0x + pz * v0z, px * v1x + pz * v1z
    den = d00 * d11 - d01 * d01
    with np.errstate(divide="ignore", invalid="ignore"):
        u = (d11 * d20 - d01 * d21) / den
        v = (d00 * d21 - d01 * d20) / den
    inside = (np.abs(den) > 1e-12) & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & ex[None]
    hit = inside.any(1)
    idx = np.where(hit, inside.argmax(1), len(A))
    return idx, hit


def main():
    env = X._worldmap_env(1)
    meshes = {}
    for c, o in X._mesh_index(env).items():
        m = PAT.search(c)
        if m and int(m.group(1)) == 1 and m.group(2) == "0_1":
            meshes[(int(m.group(4)), int(m.group(3)), m.group(6))] = o
    land = sorted({(x, y) for (x, y, p) in meshes if p == "terrain"})
    g = np.arange(16) * 4.0 + 2.0
    pts = np.array([(gx, -gz) for gz in g for gx in g])
    rows = []
    for (x, y) in land:
        A, B, C, ex, part = block_soup(meshes, x, y)
        idx, hit = first_hits(A, B, C, ex, pts)
        cum_ex = np.concatenate([[0], np.cumsum(ex)])
        iterated = np.minimum(idx + 1, len(A))
        expensive = np.where(hit, cum_ex[np.minimum(idx + 1, len(A))], cum_ex[-1])
        rows.append({"x": x, "y": y, "walk_tris": int(len(A)), "eligible": int(ex.sum()),
                     "miss_rate": round(float(1 - hit.mean()), 4),
                     "iter_mean": round(float(iterated.mean()), 1), "iter_max": int(iterated.max()),
                     "exp_mean": round(float(expensive.mean()), 1), "exp_max": int(expensive.max()),
                     "obj_tris": int(sum(1 for p in part if p == "object"))})
    W = np.array([r["walk_tris"] for r in rows])
    IM = np.array([r["iter_mean"] for r in rows])
    EM = np.array([r["exp_mean"] for r in rows])
    MR = np.array([r["miss_rate"] for r in rows])
    summ = {"blocks": len(rows), "walk_tris_per_block": {"med": int(np.median(W)), "max": int(W.max())},
            "full_scan_iterated_mean_over_blocks": {"med": float(np.median(IM)), "max": float(IM.max())},
            "full_scan_expensive_mean_over_blocks": {"med": float(np.median(EM)), "max": float(EM.max())},
            "iterated_frac_of_block": round(float(np.median(IM / W)), 3),
            "plan_miss_rate_median": float(np.median(MR)),
            "worst_blocks_by_expensive_mean": sorted(rows, key=lambda r: -r["exp_mean"])[:5]}
    (OUT / "scan_cost.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=0), encoding="utf-8")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
