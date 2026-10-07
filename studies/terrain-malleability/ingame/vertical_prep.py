"""PREP for in-game experiment 5 (the zero-edit vertical session): pick test points OFFLINE from the LIVE mesh.

  canopy  -- a forest sample (topo 36/37) and a nearby lawn sample (topo 0), each with >= 3u clearance, on the
             disc-1 forest at block (15,15). Prediction (vertical V3, ff9.cs canopy sink): on forest the published
             height = ground - 1.171875; on lawn = ground.
  basin   -- the deepest on-foot sample of the (2,7)/(3,7) sub-zero basin. Prediction (V10): y ~ -5.77, no water.

The engine's SKY ground query (gap_area_layer/arealib.raster, first registered mesh with a passing hit, first tri in
buffer order) over the LIVE FolderNames stack -- a live override, where one exists, is what the game walks on.

Rerun:  py studies/terrain-malleability/ingame/vertical_prep.py   -> ingame/out/vertical_prep.json
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
DISC = 1


def cell_grid(bx, by):
    cells = A.live_cells()
    cf = cells.get((DISC, bx, by), {})
    if cf:
        pk, why, walk = A.live_walk_list(DISC, bx, by, cf)
    else:
        walk = [(n, k, "stock") for n, k in A.stock_walk_list(DISC, bx, by)]
        pk, why = f"d{DISC}/{bx},{by}", "stock (no live override)"
    meshes = A.load_walk_arrays(walk)
    ids, pi, ys = A.raster(meshes, pitch=PITCH)
    px, pz, n = A.sample_grid(PITCH)
    return {"pk": pk, "why": why, "walk": [[w[0], w[2]] for w in walk], "n": n,
            "X": px.reshape(n, n) + bx * 64.0, "Z": pz.reshape(n, n) - by * 64.0, "Y": ys.reshape(n, n),
            "id": ids.reshape(n, n), "part": pi.reshape(n, n),
            "topo": np.where(ids >= 0, (ids & 0xFC) >> 2, -1).reshape(n, n)}


def clearance(G, mask):
    out = np.zeros(mask.shape)
    fx, fz = G["X"][~mask], G["Z"][~mask]
    for i, j in zip(*np.nonzero(mask)):
        out[i, j] = np.min(np.hypot(fx - G["X"][i, j], fz - G["Z"][i, j])) if fx.size else 99.0
    return out


def pt(G, ij, c):
    i, j = ij
    return {"world": [round(float(G["X"][i, j]), 2), round(float(G["Z"][i, j]), 2)], "ground_y": round(float(G["Y"][i, j]), 3),
            "topo": int(G["topo"][i, j]), "id": int(G["id"][i, j]), "clearance": round(float(c[i, j]), 2)}


def main():
    res = {}
    # ---- canopy: block (15,15)
    G = cell_grid(15, 15)
    forest = np.isin(G["topo"], [36, 37])
    lawn = (G["topo"] == 0)
    cf, cl = clearance(G, forest), clearance(G, lawn)
    fi = np.unravel_index(np.argmax(cf), cf.shape)
    cand = np.argwhere(lawn & (cl >= 3.0))
    d = np.hypot(G["X"][tuple(cand.T)] - G["X"][fi], G["Z"][tuple(cand.T)] - G["Z"][fi])
    li = tuple(cand[np.argmin(d)])
    res["canopy"] = {"cell": [15, 15], "prefab": G["pk"], "why": G["why"], "walk": G["walk"],
                     "forest": pt(G, fi, cf), "lawn": pt(G, li, cl),
                     "topo_hist": {int(t): int((G["topo"] == t).sum()) for t in np.unique(G["topo"])}}
    # ---- basin: blocks (2,7) and (3,7)
    best = None
    for bx in (2, 3):
        H = cell_grid(bx, 7)
        ok = np.isin(H["topo"], sorted(WALK_OK)) & (H["id"] >= 0)
        Ym = np.where(ok, H["Y"], np.inf)
        ij = np.unravel_index(np.argmin(Ym), Ym.shape)
        c = clearance(H, ok & (H["Y"] < -3.0))
        row = {"cell": [bx, 7], "prefab": H["pk"], "why": H["why"], "walk": H["walk"], "lowest": pt(H, ij, c),
               "subzero_walkable_samples": int((ok & (H["Y"] < 0)).sum()),
               "subzero_parts": sorted({H["walk"][int(p)][0] for p in np.unique(H["part"][ok & (H["Y"] < 0)])})}
        # a sub-zero sample with clearance to leave room for a teleport + a short re-grounding walk
        cand = np.argwhere(ok & (H["Y"] < -3.0) & (c >= 2.0))
        if cand.size:
            k = tuple(cand[np.argmin(H["Y"][tuple(cand.T)])])
            row["teleport"] = pt(H, k, c)
        res[f"basin_{bx}_7"] = row
        if best is None or row["lowest"]["ground_y"] < best["lowest"]["ground_y"]:
            best = row
    res["basin_best"] = best["cell"]
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "vertical_prep.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
