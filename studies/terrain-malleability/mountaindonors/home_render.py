"""A massif at HOME, rendered from the stock bytes: what the carry is meant to look like.

`world-render` reads only a mod folder's deployed overrides (`render.load_batches`), so stock land renders as sky.
This feeds it the stock parts instead (`part_src`): every part of every block round the massif is written to a
temp .ff9mesh from `extract.read_block` and rendered by the kit's own rasterizer, with four oblique cameras
round the massif and one from above, framed to its size.
RUN:  py studies/terrain-malleability/mountaindonors/home_render.py comp23   (-> out/home_<name>/)
"""
from __future__ import annotations

import math
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, mesh as M, render as R  # noqa: E402

# name: (world centre, rim radius, peak y) -- from census.py / _mountain_blob
SITES = {
    "comp23": ((1252.6, -229.4), 26.1, 16.3),
    "uaho": ((40.0, -32.0), 20.0, 12.1),
}


def views_for(cx, cz, r, peak):
    d, up = 2.6 * r + 20.0, 0.9 * r + 14.0
    at = (cx, 0.45 * peak, cz)
    v = {"top": dict(kind="ortho", x0=cx - 1.6 * r, x1=cx + 1.6 * r, z0=cz - 1.07 * r, z1=cz + 1.07 * r)}
    for name, ang in (("n", 90), ("e", 0), ("s", 270), ("w", 180)):
        a = math.radians(ang + 25)
        v[f"oblique_{name}"] = dict(kind="persp", eye=(cx + d * math.cos(a), up, cz + d * math.sin(a)),
                                    at=at, fov=50.0, reach=4.0 * d)
    return v


def main(name):
    (cx, cz), r, peak = SITES[name]
    cells = R.cells_around(cx, cz, radius=r + 64.0)
    tmp = Path(tempfile.mkdtemp(prefix="ff9_home_"))
    src = {}
    try:
        for bx, by in cells:
            for part in R.PARTS:
                try:
                    bm = X.read_block(bx, by, disc=1, part=part.lower())
                except Exception:                           # noqa: BLE001 -- the block has no such part
                    continue
                if not bm.tris:
                    continue
                src[(bx, by, part)] = M.write_ff9mesh(bm, tmp / f"{bx}_{by}_{part}.ff9mesh")
        site = R.RenderSite(cells=cells, disc=1)
        out = HERE / "out" / f"home_{name}"
        out.mkdir(parents=True, exist_ok=True)
        R.render_blocks(site, views_for(cx, cz, r, peak), out_dir=out, part_src=src, prefix="")
        print(f"-> {out}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "comp23")
