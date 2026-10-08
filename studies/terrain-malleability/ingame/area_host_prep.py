"""PREP for the host-area session (defects 15-17 fixed on the live Southern Ring, ring REVERT.md section 32).

Reads the LIVE disc-1 mesh after the stamp (read-only) with the calibrated sky ground query
(gap_area_layer/arealib.raster) and fixes the session's points and registered predictions:

  P12 / P14  round 1's points at (19,18) (out/area_prep.json): P12 sat on the carried Cleyra tiles (area 12) and must
             now read area 14; P14 is the unchanged area-14 control.
  BEACH      the Sandreach (12,18) sample whose FIRST hit is Beach1 with the most clearance from any other part:
             it read area 49 before the stamp and must now read 14.
  QUAY       Ashvale's trigger point (48, -1168): an event-1 tile, now area 14.
  CONTROL    a STOCK area-12 point ("Vube Desert") deep in the Cleyra region, on a cell no live folder overrides:
             the title must read it BETWEEN the fixed points, or a title that never updates would pass every check.

Rerun:  py studies/terrain-malleability/ingame/area_host_prep.py      -> ingame/out/area_host_prep.json
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world.placement import WALK_OK        # noqa: E402

PITCH = 0.5
ROUND1 = json.loads((HERE / "out" / "area_prep.json").read_text(encoding="utf-8"))
QUAY_AT = (48.0, -1168.0)                             # mint_quay_beacon.SITES["ashvale"].trigger_at
QUAY_ARRIVE = (60.0, -1168.0)                         # its arrive point: walkable in both query modes (quay probe b)


def decode(i):
    return {"event": (i & 0xC000) >> 14, "area": (i & 0x3F00) >> 8, "topo": (i & 0xFC) >> 2}


def cell_raster(bx, by):
    cells = A.live_cells()
    pk, why, walk = A.live_walk_list(1, bx, by, cells.get((1, bx, by), {}))
    ids, pi, ys = A.raster(A.load_walk_arrays(walk), pitch=PITCH)
    px, pz, n = A.sample_grid(PITCH)
    return {"walk": walk, "ids": ids.reshape(n, n), "pi": pi.reshape(n, n), "y": ys.reshape(n, n),
            "X": px.reshape(n, n) + bx * 64.0, "Z": pz.reshape(n, n) - by * 64.0, "prefab": pk}


def at(r, wx, wz):
    d = np.hypot(r["X"] - wx, r["Z"] - wz)
    i = np.unravel_index(np.argmin(d), d.shape)
    idv = int(r["ids"][i])
    return {"world": [round(float(r["X"][i]), 2), round(float(r["Z"][i]), 2)], "id": idv, **decode(idv),
            "part": r["walk"][int(r["pi"][i])][0] if r["pi"][i] >= 0 else None, "y": round(float(r["y"][i]), 3)}


def main():
    names = A.location_names()
    res = {"location_text": {a: names.get(a) for a in (0, 12, 14, 49)}}
    r1918 = cell_raster(19, 18)
    res["P12"] = at(r1918, *ROUND1["P12"]["world"])
    res["P14"] = at(r1918, *ROUND1["P14"]["world"])
    res["bearing_14_to_12"], res["distance_14_to_12"] = ROUND1["bearing_14_to_12"], ROUND1["distance_14_to_12"]
    a1918 = np.where(r1918["ids"] >= 0, (r1918["ids"] & 0x3F00) >> 8, -1)
    res["cell_19_18_areas"] = {int(a): int((a1918 == a).sum()) for a in np.unique(a1918)}

    r = cell_raster(12, 18)
    parts = [w[0] for w in r["walk"]]
    bi = parts.index("Beach1")
    topo = np.where(r["ids"] >= 0, (r["ids"] & 0xFC) >> 2, -1)
    beach = (r["pi"] == bi) & np.isin(topo, sorted(WALK_OK))
    if not beach.any():
        raise SystemExit("no walkable first-hit Beach1 sample at (12,18) -- re-plan")
    fx, fz = r["X"][~beach], r["Z"][~beach]
    clear = np.zeros(beach.shape)
    for i, j in zip(*np.nonzero(beach)):
        clear[i, j] = np.min(np.hypot(fx - r["X"][i, j], fz - r["Z"][i, j]))
    ib = np.unravel_index(np.argmax(clear), clear.shape)
    res["BEACH"] = at(r, float(r["X"][ib]), float(r["Z"][ib])) | {"clearance": round(float(clear[ib]), 2)}

    rq = cell_raster(0, 18)
    res["QUAY"] = at(rq, *QUAY_AT)
    res["QUAY_ARRIVE"] = at(rq, *QUAY_ARRIVE)

    # CONTROL: the stock atlas (1u, [x, -z]) sample most surrounded by walkable non-event area 12, then re-read live
    z = np.load(HERE.parent / "gap_area_layer" / "out" / "stock_atlas.npz")
    a, t, e = z["area_d1"], z["topo_d1"], z["event_d1"]
    m = (a == 12) & (e == 0) & np.isin(t, sorted(WALK_OK))
    xs, rs = np.nonzero(m)
    best = max(((float(m[max(0, x - 12):x + 13, max(0, r - 12):r + 13].mean()), int(x), int(r))
                for x, r in zip(xs[::37], rs[::37])))
    cx, cz = best[1] + 0.5, -(best[2] + 0.5)
    cb = (int(cx // 64), int(-cz // 64))
    live = [k for k in A.live_cells() if k[0] == 1 and k[1:] == cb]   # the session runs on disc 1
    rc = cell_raster(*cb)
    res["CONTROL"] = at(rc, cx, cz) | {"window_frac_area12": round(best[0], 3), "live_overrides": live}

    ok = (res["P12"]["area"] == 14 and res["P12"]["event"] == 1 and res["P14"]["area"] == 14
          and res["CONTROL"]["area"] == 12 and not live
          and res["BEACH"]["area"] == 14 and res["BEACH"]["part"] == "Beach1"
          and res["QUAY"]["area"] == 14 and res["QUAY"]["event"] == 1 and 12 not in res["cell_19_18_areas"])
    res["prep_ok"] = ok
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "area_host_prep.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("P12", "P14", "BEACH", "QUAY", "QUAY_ARRIVE", "CONTROL"):
        print(k, res[k])
    print("(19,18) areas:", res["cell_19_18_areas"], "| names:", res["location_text"], "| prep_ok:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
