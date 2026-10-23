"""Rung A1's in-game check, the offline half: choose the landmarks, make each "click", register the predictions.

    py studies/overworld-editor/a1_prep.py          # -> studies/overworld-editor/out/a1_prep.json

For every navipos landmark (locate.landmarks, the engine's own marker table) on disc 1 it asks world.pointinfo at the
marker, and keeps a marker only where the 3D view draws what the game binds (no part hidden by another FolderNames
folder), the ground query is modelled, and the ground is walkable on foot. Three of them, spread across the map, are
the targets. For each target the CLICK is made exactly as the World tab makes it: the live scene the 3D page loads
(worldview3d.load_scene over FF9CustomMap-world, disc 1, all 480 blocks), an orbit camera centred on the marker, the
marker projected to its pixel, and worldview3d.pick at that pixel's centre. The picked point is what the button
sends; point_info at the picked point is the predicted standing height.

REGISTERED PREDICTIONS (written to the JSON before the game is opened; a1_run.py judges them):
  P1 each pick lands within 0.5u (x, z) of the marker it was aimed at;
  P2 the game's read-back world x, z equal the picked x, z within 0.05u (tools/world_teleport.py, the button's argv);
  P3 the game's read-back y equals point_info's stand_y at the picked point within 0.15u;
  P4 (a precondition, checked here) the view draws what the game binds at each target: owners.hidden is empty.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[1] / "ff9mapkit"
sys.path.insert(0, str(KIT))
import ff9mapkit                                                      # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT), ff9mapkit.__file__

from ff9mapkit import config                                          # noqa: E402
from ff9mapkit.world import locate as L, mesh as M, pointinfo as PI, render as R   # noqa: E402

OUT = HERE / "out" / "a1_prep.json"
RES = (1280, 720)
TOL_PICK, TOL_XZ, TOL_Y = 0.5, 0.05, 0.15


def main():
    import numpy as np
    from ff9mapkit.workspace import worldview3d as V
    game = Path(config.find_game_path(None))
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=cells, disc=1, game=game, mod_root=game / "FF9CustomMap-world")
    stack = PI.stack_folders(game)
    cands = []
    for lm in L.landmarks():
        x, z = lm["world"]
        info = PI.point_info(site, x, z, stack=stack, landmark=False)
        g = info["ground"]
        ok = (g["modelled"] and g["part"] != "MISS" and g.get("walkable") and not info["owners"]["hidden"]
              and info["owners"]["in_stack"])
        cands.append({"name": lm["name"], "loc": lm["loc"], "marker": (x, z), "ok": bool(ok),
                      "ground": {k: g.get(k) for k in ("y", "part", "topograph", "walkable", "canopy")},
                      "hidden": info["owners"]["hidden"]})
    good = [c for c in cands if c["ok"]]
    # three targets far apart: the first good one, then each next the farthest from those already taken
    targets = [good[0]]
    while len(targets) < 3 and len(targets) < len(good):
        targets.append(max((c for c in good if c not in targets),
                           key=lambda c: min(math.dist(c["marker"], t["marker"]) for t in targets)))
    t0 = time.perf_counter()
    packed, _tex = V.load_scene(site)
    load_s = time.perf_counter() - t0
    for t in targets:
        x, z = t["marker"]
        cam = V.OrbitCamera(target=(x, t["ground"]["y"], z), yaw=30.0, pitch=55.0, dist=160.0)
        view = cam.view()
        sx, sy, _ = R.project(view, np.array([[x, t["ground"]["y"], z]]), RES)
        t0 = time.perf_counter()
        hit = V.pick(packed, view, RES, float(sx[0]) + 0.5, float(sy[0]) + 0.5)
        t["pick_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        t["click_px"] = (round(float(sx[0]), 2), round(float(sy[0]), 2))
        t["pick"] = None if hit is None else {"xyz": hit[0], "part": hit[1]}
        if hit is not None:
            info = PI.point_info(site, hit[0][0], hit[0][2], stack=stack)
            t["pick_dist"] = math.dist((hit[0][0], hit[0][2]), (x, z))
            t["predict"] = {"x": hit[0][0], "z": hit[0][2], "stand_y": info["ground"].get("stand_y"),
                            "lines": PI.describe(info)}
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "stack": stack, "res": RES, "scene_tris": packed.tris,
           "scene_load_s": round(load_s, 2), "tolerances": {"pick": TOL_PICK, "xz": TOL_XZ, "y": TOL_Y},
           "candidates": cands, "targets": targets}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"{sum(c['ok'] for c in cands)}/{len(cands)} landmarks qualify; scene {packed.tris} tris in {load_s:.1f}s")
    for t in targets:
        p = t.get("predict") or {}
        print(f"  {t['name']:22s} marker {t['marker'][0]:.2f},{t['marker'][1]:.2f}  pick {t.get('pick_dist', -1):.3f}u "
              f"({t['pick_ms']} ms)  -> teleport {p.get('x', 0):.2f} {p.get('z', 0):.2f}, stand y {p.get('stand_y')}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
