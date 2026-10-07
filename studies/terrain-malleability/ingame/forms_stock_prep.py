"""PREP for in-game experiment 2, NO-DEPLOY form: the STOCK form switch, read through heights.

The stock place conditions (WorldConfiguration.cs:165-193) can be driven by the harness without writing a file:
the scenario counter (`warp ... scenario`) flips Cleyra (SC >= 4990), Lindblum (SC >= 5598) and the Water Shrine
(10600 <= SC < 10700); a gEventGlobal poke (`byte 101`) flips Mognet Central (0x80) and Chocobo's Paradise (0x40).

For each GEO cell (forms F10) this finds sample points that are on-foot walkable in BOTH forms, far from any event
tile in either form, where the two forms' ground heights differ the most -- a published height there says which
form the engine loaded. Walk lists follow WMWorld.LoadBlock's registration flags exactly:
  form 1 = Object, Terrain, VolcanoCrater1, VolcanoLava1, Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1-6
  form 2 = Object2, Terrain2, VolcanoCrater2, VolcanoLava2, Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1-6
  (block 219 = the Water Shrine is the hard-coded exception, :600-636 -- handled in forms_prep.py)
Refuses a cell that carries a live override (the read would then be of OUR content, not stock).

Rerun:  py studies/terrain-malleability/ingame/forms_stock_prep.py   -> ingame/out/forms_stock_prep.json
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from scipy.spatial import cKDTree                    # noqa: E402
from ff9mapkit.world.placement import WALK_OK        # noqa: E402

WATER = ["Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]
FORM1 = ["Object", "Terrain", "VolcanoCrater1", "VolcanoLava1"] + WATER
FORM2 = ["Object2", "Terrain2", "VolcanoCrater2", "VolcanoLava2"] + WATER
CELLS = {"Cleyra": [(13, 12), (14, 12)], "Lindblum": [(14, 16), (14, 17)], "MognetCentral": [(16, 1)],
         "ChocoboParadise": [(0, 0)], "Alexandria": [(20, 10)]}
PITCH = 0.5


def grid(bx, by, names):
    ch = {c["go"]: c["mesh_key"] for c in A.census()["prefabs"][f"d1/{bx},{by}"]["children"]}
    walk = [(n, ch[n], "stock") for n in names if n in ch]
    ids, pi, ys = A.raster(A.load_walk_arrays(walk), pitch=PITCH)
    px, pz, n = A.sample_grid(PITCH)
    return ({"id": ids.reshape(n, n), "y": ys.reshape(n, n), "part": pi.reshape(n, n), "walk": [w[0] for w in walk]},
            px.reshape(n, n) + bx * 64.0, pz.reshape(n, n) - by * 64.0)


def main():
    live = A.live_cells()
    res = {}
    for place, cells in CELLS.items():
        for (bx, by) in cells:
            key = f"{place} ({bx},{by})"
            if (1, bx, by) in live:
                res[key] = {"refused": "the cell carries a live override"}
                print(key, "REFUSED: live override")
                continue
            g1, X, Z = grid(bx, by, FORM1)
            g2, _, _ = grid(bx, by, FORM2)
            t1 = np.where(g1["id"] >= 0, (g1["id"] & 0xFC) >> 2, -1)
            t2 = np.where(g2["id"] >= 0, (g2["id"] & 0xFC) >> 2, -1)
            e1 = np.where(g1["id"] >= 0, (g1["id"] & 0xC000) >> 14, 0)
            e2 = np.where(g2["id"] >= 0, (g2["id"] & 0xC000) >> 14, 0)
            ok = np.isin(t1, sorted(WALK_OK)) & np.isin(t2, sorted(WALK_OK))
            ev = (e1 > 0) | (e2 > 0)
            if ev.any():
                clr = cKDTree(np.c_[X[ev], Z[ev]]).query(np.c_[X.ravel(), Z.ravel()])[0].reshape(X.shape)
            else:
                clr = np.full(X.shape, 99.0)
            nw = ~ok
            wclr = (cKDTree(np.c_[X[nw], Z[nw]]).query(np.c_[X.ravel(), Z.ravel()])[0].reshape(X.shape)
                    if nw.any() else np.full(X.shape, 99.0))
            dy = g2["y"] - g1["y"]
            m = ok & (clr >= 10.0) & (wclr >= 1.5) & (np.abs(dy) >= 0.3)
            picks = []
            if m.any():
                k = np.argwhere(m)
                for q in np.argsort(-np.abs(dy[tuple(k.T)])):
                    i, j = k[q]
                    if all(np.hypot(X[i, j] - p["world"][0], Z[i, j] - p["world"][1]) > 4 for p in picks):
                        picks.append({"world": [round(float(X[i, j]), 2), round(float(Z[i, j]), 2)],
                                      "y_form1": round(float(g1["y"][i, j]), 3), "y_form2": round(float(g2["y"][i, j]), 3),
                                      "dy": round(float(dy[i, j]), 3), "topo1": int(t1[i, j]), "topo2": int(t2[i, j]),
                                      "part1": g1["walk"][int(g1["part"][i, j])],
                                      "part2": g2["walk"][int(g2["part"][i, j])],
                                      "event_clearance": round(float(clr[i, j]), 1),
                                      "wall_clearance": round(float(wclr[i, j]), 1)})
                    if len(picks) >= 3:
                        break
            res[key] = {"form1_walk": g1["walk"], "form2_walk": g2["walk"],
                        "walk_differs": int((ok & (np.abs(dy) >= 0.05)).sum()), "picks": picks}
            print(key, "walkable-both & |dy|>=0.3 & clear:", int(m.sum()), "picks", picks[:2])
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "forms_stock_prep.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
