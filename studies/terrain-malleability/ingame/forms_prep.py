"""PREP for in-game experiment 2 (the FORM SWITCH): where do the Water Shrine's Form-1 and Form-2 grounds differ?

Block (3,9) = engine block 219, the Water Shrine. Its registration is the hard-coded exception (WMWorld.cs:600-636):
Form 1 walks [Object, Terrain, Sea3, Sea4, Sea5]; Form 2 walks [Object2, Terrain2, Sea3_2, Sea4_2, Sea5_2]
(RegisterBlockComponent(..., form1, form2) flags; WMBlock.ActiveWalkMeshes picks the list by Form).
The stock condition for Form 2 is disc 1 && 10600 <= scenario < 10700 (WorldConfiguration.cs:187).

Picks sample points (clear of every event-tagged tile in EITHER form, so a probe can never fire the shrine's
entrance) where both forms give foot-walkable ground and the heights differ the most -- the in-game reading at such a
point says which form loaded. Also a control point where both forms agree.

Rerun:  py studies/terrain-malleability/ingame/forms_prep.py   -> ingame/out/forms_prep.json
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

BX, BY = 3, 9
PITCH = 0.5
FORM1 = ["Object", "Terrain", "Sea3", "Sea4", "Sea5"]
FORM2 = ["Object2", "Terrain2", "Sea3_2", "Sea4_2", "Sea5_2"]


def grid(names):
    ch = {c["go"]: c["mesh_key"] for c in A.census()["prefabs"][f"d1/{BX},{BY}"]["children"]}
    walk = [(n, ch[n], "stock") for n in names if n in ch]
    ids, pi, ys = A.raster(A.load_walk_arrays(walk), pitch=PITCH)
    px, pz, n = A.sample_grid(PITCH)
    return {"walk": [w[0] for w in walk], "id": ids.reshape(n, n), "y": ys.reshape(n, n),
            "part": pi.reshape(n, n), "X": px.reshape(n, n) + BX * 64.0, "Z": pz.reshape(n, n) - BY * 64.0}


def main():
    g1, g2 = grid(FORM1), grid(FORM2)
    topo = lambda g: np.where(g["id"] >= 0, (g["id"] & 0xFC) >> 2, -1)
    event = lambda g: np.where(g["id"] >= 0, (g["id"] & 0xC000) >> 14, 0)
    ok1 = np.isin(topo(g1), sorted(WALK_OK))
    ok2 = np.isin(topo(g2), sorted(WALK_OK))
    ev = (event(g1) > 0) | (event(g2) > 0)
    X, Z = g1["X"], g1["Z"]
    # clearance from any event tile in either form
    ex, ez = X[ev], Z[ev]
    clr = np.full(X.shape, 99.0)
    if ex.size:
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                clr[i, j] = np.min(np.hypot(ex - X[i, j], ez - Z[i, j]))
    dy = g2["y"] - g1["y"]
    both = ok1 & ok2 & (clr >= 12.0)
    cand = np.argwhere(both)
    order = np.argsort(-np.abs(dy[tuple(cand.T)]))
    picks = []
    for k in order:
        i, j = cand[k]
        if all(np.hypot(X[i, j] - p["world"][0], Z[i, j] - p["world"][1]) > 6.0 for p in picks):
            picks.append({"world": [round(float(X[i, j]), 2), round(float(Z[i, j]), 2)],
                          "y_form1": round(float(g1["y"][i, j]), 3), "y_form2": round(float(g2["y"][i, j]), 3),
                          "dy": round(float(dy[i, j]), 3), "topo1": int(topo(g1)[i, j]), "topo2": int(topo(g2)[i, j]),
                          "part1": g1["walk"][int(g1["part"][i, j])], "part2": g2["walk"][int(g2["part"][i, j])],
                          "event_clearance": round(float(clr[i, j]), 2)})
        if len(picks) >= 4:
            break
    same = np.argwhere(both & (np.abs(dy) < 0.01))
    ctl = None
    if same.size:
        i, j = same[len(same) // 2]
        ctl = {"world": [round(float(X[i, j]), 2), round(float(Z[i, j]), 2)], "y": round(float(g1["y"][i, j]), 3),
               "topo": int(topo(g1)[i, j]), "event_clearance": round(float(clr[i, j]), 2)}
    res = {"cell": [BX, BY], "form1_walk": g1["walk"], "form2_walk": g2["walk"],
           "event_tiles": {"form1": int((event(g1) > 0).sum()), "form2": int((event(g2) > 0).sum())},
           "differ_samples": int((np.abs(dy) > 0.05).sum()), "picks": picks, "control": ctl}
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "forms_prep.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
