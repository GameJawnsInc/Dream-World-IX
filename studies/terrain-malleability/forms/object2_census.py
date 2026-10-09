"""WHAT REMOVING A STOCK BUILDING LEAVES (2026-10-09, story buildings, before any Object2 authoring).

For every stock cell whose form-1 walk list carries an Object, raster the sky ground query (0.5u pitch) twice: the
full walk list (the Object registers first, so it answers wherever it covers), and the list WITHOUT the Object (what a
blank Object2 leaves in form 2). Per cell, over the samples the Object answers:
  under_walk   the rest answers with a walkable topograph   -> removal leaves walkable ground there
  under_block  the rest answers with a blocked topograph    -> removal leaves an invisible wall (no building drawn)
  under_miss   nothing answers                              -> removal leaves a HOLE (no ground: the Object was a plug)
and obj_walk = the Object samples that are themselves walkable (where the player stood on the building).
Writes forms/out/object2_census.json.
Run:  py studies/terrain-malleability/forms/object2_census.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TM = HERE.parent
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(TM / "consumption"))
sys.path.insert(0, str(TM / "disc4"))
sys.path.insert(0, str(TM.parent.parent / "ff9mapkit"))
import arealib as A                                   # noqa: E402
from ff9mapkit.world.placement import WALK_OK         # noqa: E402

PITCH = 0.5
WALK = np.array(sorted(WALK_OK))


def topo(ids):
    return (ids & 0xFC) >> 2


def cell(d, x, y):
    walk = A.stock_walk_list(d, x, y)
    names = [n for n, _k in walk]
    if "Object" not in names:
        return None
    meshes = A.load_walk_arrays([(n, k, "stock") for n, k in walk])
    full_id, full_pi, full_y = A.raster(meshes, pitch=PITCH)
    rest = [m for m in meshes if m[0] != "Object"]
    rest_id, rest_pi, rest_y = A.raster(rest, pitch=PITCH)
    oi = names.index("Object")
    on = full_pi == oi
    n = int(on.sum())
    if n == 0:
        return {"parts": names, "obj": 0}
    hit = rest_id[on] >= 0
    walkable = np.isin(topo(rest_id[on]), WALK)
    return {
        "parts": names,
        "obj": n,
        "obj_walk": int(np.isin(topo(full_id[on]), WALK).sum()),
        "under_walk": int((hit & walkable).sum()),
        "under_block": int((hit & ~walkable).sum()),
        "under_miss": int((~hit).sum()),
        "rest_parts": sorted({rest[i][0] for i in set(rest_pi[on][hit].tolist())}),
        "dy_mean": round(float((full_y[on][hit] - rest_y[on][hit]).mean()), 3) if hit.any() else None,
    }


def main():
    out = {}
    for d in (1, 4):
        for y in range(20):
            for x in range(24):
                if A._engine().is_sea(d, x, y):
                    continue
                r = cell(d, x, y)
                if r:
                    out[f"d{d}/{x},{y}"] = r
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "object2_census.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for d in (1, 4):
        rows = {k: v for k, v in out.items() if k.startswith(f"d{d}/") and v["obj"]}
        miss = {k: v for k, v in rows.items() if v["under_miss"]}
        block = {k: v for k, v in rows.items() if v["under_block"]}
        clean = [k for k, v in rows.items() if not v["under_miss"] and not v["under_block"]]
        print(f"disc {d}: {len(rows)} cells with an Object; leaves a hole {len(miss)}, leaves blocked ground "
              f"{len(block)}, leaves only walkable ground {len(clean)}")
        tot = {k: sum(v[k] for v in rows.values()) for k in ("obj", "obj_walk", "under_walk", "under_block",
                                                             "under_miss")}
        print("   samples:", tot)
        for k, v in sorted(rows.items(), key=lambda kv: -kv[1]["under_miss"])[:12]:
            print(f"   {k:10s} obj {v['obj']:6d} walk {v['obj_walk']:6d} | under walk {v['under_walk']:6d} "
                  f"block {v['under_block']:6d} miss {v['under_miss']:6d}  dy {v['dy_mean']}  {v['rest_parts']}")


if __name__ == "__main__":
    main()
