"""HOW MUCH does the area -> camera PLACE consumer move the camera? (w_cameraChangeUpdate, ff9.cs:3117, STOCK)

place = w_cameraArea2Place[area]; the chase camera's 'down' posstat = w_cameraElement[type_cam, place].down, blended
to 'up' by actor height: t = clamp((y*256+1000)*4096/4500, 0, 4096) (w_cameraGetHeightParam, ff9.cs:3181), i.e. the
area matters ONLY below y = 13.67 and fully below y = -3.9. Units after w_cameraSystemConstructor (ff9.cs:2586):
distance/256, height/-256, correct/-256, aim/-256 (pers unchanged).

For every stock WALKABLE land sample of the 1u atlas (out/stock_atlas.npz), at its real ground height y, it computes
the on-foot (type_cam 0) and chocobo (type_cam 1) camera under the sample's own place and under each other place,
so a restamp's framing delta is a measured number, not a guess. Also locates the atlas MISS samples.

Rerun:  py studies/terrain-malleability/gap_area_layer/camera_place_effect.py  (after stock_atlas.py)
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

FIELDS = ("cameraPers", "cameraDistance", "cameraHeight", "cameraCorrect", "aimHeight")
SCALE = {"cameraPers": 1.0, "cameraDistance": 1 / 256, "cameraHeight": -1 / 256, "cameraCorrect": -1 / 256,
         "aimHeight": -1 / 256}


def posstat_units(t):
    return [{f: p[f] * SCALE[f] for f in FIELDS} for p in t["w_cameraPosstat"]]


def cam(post, elem, tcam, place, y):
    e = elem[f"{tcam},{place}"]
    dn, up = post[e["down"]], post[e["up"]]
    t = np.clip(((y * 256 + 1000) * 4096 / 4500), 0, 4096) / 4096
    return {f: dn[f] + (up[f] - dn[f]) * t for f in FIELDS}


def main():
    t = A.tables()
    post = posstat_units(t)
    elem = t["w_cameraElement"]
    z = np.load(A.OUT / "stock_atlas.npz")
    place_lut = np.array(t["w_cameraArea2Place"])
    res = {"posstat_units": post, "discs": {}}
    walk_ok = np.array(sorted(P.WALK_OK))
    for d in (1, 4):
        area, topo, land, y = z[f"area_d{d}"], z[f"topo_d{d}"], z[f"land_d{d}"], z[f"y_d{d}"]
        m = land & (area >= 0) & np.isin(topo, walk_ok)
        ar, yy = area[m], y[m].astype(np.float64)
        pl = place_lut[ar]
        dd = {"walkable_land_samples": int(m.sum()),
              "frac_below_13.67": float((yy < 13.672).mean()), "frac_below_-3.9": float((yy < -3.906).mean()),
              "y_pct": [round(float(v), 2) for v in np.percentile(yy, [1, 25, 50, 75, 99])], "by_place": {}}
        for p in (0, 1, 2):
            sel = pl == p
            if not sel.any():
                continue
            ys = yy[sel]
            row = {"samples": int(sel.sum()), "frac_below_13.67": float((ys < 13.672).mean()),
                   "y_median": round(float(np.median(ys)), 2)}
            for tcam in (0, 1):
                own = cam(post, elem, tcam, p, ys)
                for q in (0, 1, 2):
                    if q == p:
                        continue
                    oth = cam(post, elem, tcam, q, ys)
                    row[f"tc{tcam}_as_place{q}"] = {f: {"median_delta": round(float(np.median(oth[f] - own[f])), 3),
                                                        "max_abs_delta": round(float(np.abs(oth[f] - own[f]).max()), 3)}
                                                    for f in FIELDS if np.abs(oth[f] - own[f]).max() > 1e-9}
                row[f"tc{tcam}_own_median"] = {f: round(float(np.median(own[f])), 3) for f in FIELDS}
            dd["by_place"][p] = row
        # stock PLACE boundaries: 4-neighbour pairs (toroidal) whose camera place differs
        plg = np.where(area >= 0, place_lut[np.clip(area, 0, 63)], -1)
        walk = land & (area >= 0) & np.isin(topo, walk_ok)
        pb = {"walk_walk": 0, "walk_any": 0, "examples": []}
        for ax in (0, 1):
            nb = np.roll(plg, -1, axis=ax)
            nw = np.roll(walk, -1, axis=ax)
            diff = (plg >= 0) & (nb >= 0) & (plg != nb)
            ww = diff & walk & nw
            pb["walk_walk"] += int(ww.sum())
            pb["walk_any"] += int((diff & (walk | nw)).sum())
            cc, rr = np.nonzero(ww)
            for c, r in list(zip(cc, rr))[:5]:
                pb["examples"].append({"col": int(c), "row": int(r), "block": [int(c) // 64, int(r) // 64],
                                       "areas": [int(area[c, r]), int(np.roll(area, -1, axis=ax)[c, r])]})
        dd["place_boundaries"] = pb
        miss = area < 0
        mc, mr = np.nonzero(miss)
        blocks = {}
        for c, r in zip(mc, mr):
            k = f"{c // 64},{r // 64}"
            blocks[k] = blocks.get(k, 0) + 1
        dd["miss_samples"] = int(miss.sum())
        dd["miss_by_block"] = dict(sorted(blocks.items(), key=lambda kv: -kv[1]))
        res["discs"][d] = dd
    (A.OUT / "camera_place_effect.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("posstats (units):")
    for i, p in enumerate(post):
        print(f"  {i}: " + ", ".join(f"{k}={v:.2f}" for k, v in p.items()))
    for d, dd in res["discs"].items():
        print(f"\nDISC {d}: walkable land {dd['walkable_land_samples']}  below13.67={dd['frac_below_13.67']:.3f} "
              f"below-3.9={dd['frac_below_-3.9']:.3f}  y pct={dd['y_pct']}  MISS={dd['miss_samples']} "
              f"top-miss-blocks={list(dd['miss_by_block'].items())[:4]}")
        print(f"  stock PLACE boundaries: walkable<->walkable pairs={dd['place_boundaries']['walk_walk']} "
              f"walkable<->any={dd['place_boundaries']['walk_any']}  examples={dd['place_boundaries']['examples'][:4]}")
        for p, row in dd["by_place"].items():
            print(f"  place {p}: n={row['samples']} below13.67={row['frac_below_13.67']:.3f} y_med={row['y_median']}")
            for k, v in row.items():
                if k.startswith("tc"):
                    print(f"     {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
