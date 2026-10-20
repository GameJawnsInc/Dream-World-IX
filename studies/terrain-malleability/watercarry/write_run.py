"""Rung 3 runner: cluster C composed, its Sea4 cut, THE KNIT (W1), written to a scratch folder OUTSIDE the install
(out/river_mod, laid out as a mod folder), B1 read back from the bytes, then rendered with ``world-render --stock``
(the standard views) and four seam views (the knit seen from above, each join, the cove from outside).
Offline: the game is never touched.
RUN:  py studies/terrain-malleability/watercarry/write_run.py
      (writes out/river_mod/, out/write.json, out/river_render/*.png)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import render as RD, river as R  # noqa: E402

OUT = HERE / "out"
SCRATCH = OUT / "river_mod"
RENDER = OUT / "river_render"


def main():
    win = R.read_window(R.CLUSTER_C)
    f = R.build_fragment(win, R.CLUSTER_C)
    ol = R.outline(f)
    dbx, dby = R.open_ocean_offsets(sorted(R.mint(ol)["blocks"]))[0]
    comp = R.compose(f, offset=(64.0 * dbx, -64.0 * dby), window=win, ol=ol)
    own = Counter(t["blk"] for t in f.tris if t["part"] == "sea5")
    (bx0, bx1), (by0, by1) = R.CLUSTER_C.window
    donors = [b for b, _ in own.most_common()] + [(x, y) for x in range(bx0, bx1 + 1) for y in range(by0, by1 + 1)]
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    rep = R.write_composition(comp, SCRATCH, window=win, donors=donors)
    rep.pop("meshes")
    rep["compose_green"] = comp.report["green"]
    OUT.mkdir(exist_ok=True)
    (OUT / "write.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("files", "blocks", "sea_plan")}, indent=1, default=str))
    print("W1:", json.dumps({k: rep["W1"][k] for k in ("ok", "passes", "quads", "after", "home", "edges_introduced",
                                                       "edges_introduced_where", "wang", "unpaintable")}, default=str))
    print("B1:", json.dumps({k: rep["B1"][k] for k in ("ok", "fails", "cells")}))

    P = [p for t in comp.tris for p in t["P"]]
    cx = (min(p[0] for p in P) + max(p[0] for p in P)) / 2
    cz = (min(p[2] for p in P) + max(p[2] for p in P)) / 2
    if RENDER.exists():
        shutil.rmtree(RENDER)
    cmd = [sys.executable, "-m", "ff9mapkit", "world-render", "--mod-root", str(SCRATCH), "--around",
           f"{cx:.0f},{cz + 40:.0f}", "--radius", "150", "--disc", "1", "--stock", "--out", str(RENDER)]
    print("$", " ".join(cmd[2:]))
    subprocess.run(cmd, cwd=ROOT / "ff9mapkit", check=True)
    site = RD.RenderSite(cells=RD.cells_around(cx, cz + 40, radius=150.0), disc=1, mod_root=SCRATCH)
    batches = RD.load_batches(site, stock=True)
    dx, dz = comp.offset
    (_ce, be), (_cw, bw) = f.joins["E"], f.joins["W"]
    E, W = (be[0] + dx, be[2] + dz), (bw[0] + dx, bw[2] + dz)
    views = {
        "seam_top": dict(kind="ortho", x0=W[0] - 12, x1=E[0] + 20, z0=W[1] - 16, z1=E[1] + 16),
        "join_W": dict(kind="persp", eye=(W[0] + 22, 7.0, W[1] + 14), at=(W[0], 1.0, W[1] - 1), fov=55.0, reach=50.0),
        "join_E": dict(kind="persp", eye=(E[0] + 23, 10.0, E[1] - 18), at=(E[0], 1.5, E[1]), fov=50.0, reach=60.0),
        "mouth_in": dict(kind="persp", eye=(E[0] - 13, 6.0, W[1] - 35), at=(E[0] - 53, 1.0, E[1] - 17), fov=55.0,
                         reach=160.0),
    }
    for n, v in views.items():
        RD.raster(v, batches, n, site=site, out_dir=RENDER)


if __name__ == "__main__":
    main()
