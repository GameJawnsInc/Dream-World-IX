"""PREP for in-game experiment 1 (the area session): pick the test points OFFLINE from the LIVE mesh.

Reads the live FolderNames stack (read-only) for disc-1 cell (19,18) -- the Southern Ring block that carries stock
Cleyra's 45 area-12 entrance tris (README section 6 defect 15) -- runs the engine's SKY ground query over a 0.5u
grid (gap_area_layer/arealib.raster, calibrated against world/placement.place), and picks:

  P12  the area-12 sample with the most clearance to any non-area-12 sample (the camera-lock / label spot)
  P14  the nearest on-foot-walkable area-14 sample with >= 3u clearance (the control spot)
  + a straight line P14 -> P12 with the area read every 0.5u, so the in-game crossing can be scored

and prints every engine consequence of both areas (zone, camera place, lock, weather, location text).

Rerun:  py studies/terrain-malleability/ingame/area_prep.py      -> ingame/out/area_prep.json
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world.placement import WALK_OK        # noqa: E402

DISC, BX, BY = 1, 19, 18
OX, OZ = BX * 64.0, -BY * 64.0                       # block origin in world units (z negated)
PITCH = 0.5


def decode(i):
    return {"event": (i & 0xC000) >> 14, "area": (i & 0x3F00) >> 8, "topo": (i & 0xFC) >> 2}


def main():
    cells = A.live_cells()
    cf = cells.get((DISC, BX, BY), {})
    pk, why, walk = A.live_walk_list(DISC, BX, BY, cf)
    print(f"cell ({BX},{BY}) disc {DISC}: effective prefab {pk} ({why})")
    for n, src, kind in walk:
        print(f"   {n:12s} {kind:8s} {src}")
    meshes = A.load_walk_arrays(walk)
    ids, pi, ys = A.raster(meshes, pitch=PITCH)
    px, pz, n = A.sample_grid(PITCH)
    area = np.where(ids >= 0, (ids & 0x3F00) >> 8, -1).reshape(n, n)
    topo = np.where(ids >= 0, (ids & 0xFC) >> 2, -1).reshape(n, n)
    walk_ok = np.isin(topo, sorted(WALK_OK))
    X, Z, Y = px.reshape(n, n), pz.reshape(n, n), ys.reshape(n, n)

    def clearance(mask):
        """distance (u) from each True sample to the nearest False sample (brute force on the small grid)."""
        out = np.zeros(mask.shape)
        fx, fz = X[~mask], Z[~mask]
        for i, j in zip(*np.nonzero(mask)):
            out[i, j] = np.min(np.hypot(fx - X[i, j], fz - Z[i, j])) if fx.size else 99.0
        return out

    m12 = (area == 12) & walk_ok
    m14 = (area == 14) & walk_ok
    print(f"samples: area12 walkable {int(m12.sum())}, area14 walkable {int(m14.sum())}")
    if not m12.any() or not m14.any():
        raise SystemExit("no area-12 or area-14 walkable ground here -- the live content changed; re-plan")
    c12, c14 = clearance(m12), clearance(m14)
    i12 = np.unravel_index(np.argmax(c12), c12.shape)
    cand = np.argwhere(m14 & (c14 >= 3.0))
    d = np.hypot(X[tuple(cand.T)] - X[i12], Z[tuple(cand.T)] - Z[i12])
    i14 = tuple(cand[np.argmin(d)])
    p12 = (OX + float(X[i12]), OZ + float(Z[i12]))
    p14 = (OX + float(X[i14]), OZ + float(Z[i14]))

    # the line P14 -> P12, area read every 0.5u (nearest grid sample)
    L = math.hypot(p12[0] - p14[0], p12[1] - p14[1])
    line = []
    for k in range(int(L / 0.5) + 1):
        t = min(1.0, k * 0.5 / L)
        wx, wz = p14[0] + t * (p12[0] - p14[0]), p14[1] + t * (p12[1] - p14[1])
        i = int(round((wx - OX) / PITCH - 0.37))
        j = int(round(-(wz - OZ) / PITCH - 0.61))
        if 0 <= i < n and 0 <= j < n:
            line.append({"t": round(t, 3), "x": round(wx, 2), "z": round(wz, 2), "area": int(area[i, j]),
                         "topo": int(topo[i, j]), "y": round(float(Y[i, j]), 3)})
    names = A.location_names()
    res = {
        "cell": [BX, BY], "disc": DISC, "prefab": pk, "why": why,
        "walk": [[n_, kind] for n_, _, kind in walk],
        "P12": {"world": [round(p12[0], 2), round(p12[1], 2)], "clearance": round(float(c12[i12]), 2),
                "y": round(float(Y[i12]), 3), "topo": int(topo[i12]), "id": int(ids.reshape(n, n)[i12])},
        "P14": {"world": [round(p14[0], 2), round(p14[1], 2)], "clearance": round(float(c14[i14]), 2),
                "y": round(float(Y[i14]), 3), "topo": int(topo[i14]), "id": int(ids.reshape(n, n)[i14])},
        "bearing_14_to_12": round(math.degrees(math.atan2(p12[1] - p14[1], p12[0] - p14[0])), 2),
        "distance_14_to_12": round(L, 2),
        "line": line,
        "consequence": {12: A.consequence(12), 14: A.consequence(14)},
        "location_text": {12: names.get(12), 14: names.get(14)},
        "area_hist": {int(a): int((area == a).sum()) for a in np.unique(area)},
    }
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "area_prep.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("P12", "P14"):
        print(k, res[k], decode(res[k]["id"]))
    print("bearing P14->P12", res["bearing_14_to_12"], "distance", res["distance_14_to_12"])
    print("areas along the line:", [r["area"] for r in line])
    print("consequence:", res["consequence"])
    print("location text:", res["location_text"])
    print("area histogram (0.5u samples):", res["area_hist"])


if __name__ == "__main__":
    main()
