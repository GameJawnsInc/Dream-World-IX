"""THE DESERT BENCH -- retile the deployed crag bench's grass to DESERT ground in place.

The desert anatomy minted THE DESERT TRANSLATION LAW: the topo-17 desert mains region is
the GRASS mains structure translated by exactly (+0.65332, -0.09863) in the atlas --
same 2x2 quadrant rects, same widths (0.06054/0.03028), same gutters (0.00196/0.00097),
same linear-in-XZ map, same 4 rotations and handedness, byte-exact at 5dp:

    grass U [(0.00391,0.06445),(0.06641,0.12695)]  V [(0.76855,0.79883),(0.7998,0.83008)]
    desert U [(0.65723,0.71777),(0.71973,0.78027)]  V [(0.66992,0.70020),(0.70117,0.73145)]

(Real desert cells additionally use FREE fractional windows spanning the painted-over
internal gutter -- THE COL-FREEDOM LAW at ground scale -- but the locked grass-form
window is itself a common real form and every sample stays inside painted art, so the
mint uses it.) Desert ground topo = 17.

This script rewrites the crag bench (blocks (0-1,18-19), the multi-block carry proven
2026-07-15) IN PLACE: every plain-grass mains tri (topo 0, u in the grass region --
incl. the carve's zip annulus) gets desert mains UVs (fresh per-cell assignment under
the real neighbour policy) + topograph 17. ZERO geometry change (positions/normals
untouched -- no weld/crack risk); the carried crag rock is untouched. The crag's own
foot fringe was painted against exactly this ground -- THE TEST the grass bench could
not run.

Usage:  py studies/overworld-topography/desert_bench.py [deploy]
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import extract as X                   # noqa: E402
from ff9mapkit.world import grassland as G                 # noqa: E402
from ff9mapkit.world import interior as IN                 # noqa: E402
from ff9mapkit.world import mesh as M                      # noqa: E402

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BLOCKS = [(0, 18), (1, 18), (0, 19), (1, 19)]
BLOCK = 64.0
DU, DV = 0.65332, -0.09863                                 # THE DESERT TRANSLATION LAW
DESERT_TOPO = 17
SEED = 0xD17
REGION = (0.65723 - 0.0002, 0.66992 - 0.0002, 0.78027 + 0.0002, 0.73145 + 0.0002)

# ---- load the deployed bench ------------------------------------------------------------------
blocks = {}
for (bx, by) in BLOCKS:
    p = MODW / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    blocks[(bx, by)] = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, lod="0_1",
                                                part="terrain")
lo_u, hi_u = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
plain_cells = set()
per_block = {}
for blk, bm in blocks.items():
    bx, by = blk
    us = bm.chan_arrays[X.CH_UV]
    ts = bm.chan_arrays[X.CH_TAN]
    ps = bm.chan_arrays[X.CH_POS]
    plain = []
    for tdx, tri in enumerate(bm.tris):
        topo = X.decode_id(int(round(ts[tri[0]][0])))["topograph"]
        if topo == 0 and all(lo_u - 0.02 <= us[i][0] <= hi_u + 0.02 for i in tri):
            plain.append(tdx)
            cx = sum(ps[i][0] + BLOCK * bx for i in tri) / 3
            cz = sum(ps[i][2] - BLOCK * (by + 1) + BLOCK for i in tri) / 3
            plain_cells.add((math.floor(cx / 4.0), math.floor(cz / 4.0)))
    per_block[blk] = plain
n_plain = sum(len(v) for v in per_block.values())
print(f"bench: {sum(len(b.tris) for b in blocks.values())} tris, "
      f"{n_plain} plain-grass mains across {len(plain_cells)} cells")
assert n_plain, "no plain grass on the bench -- wrong blocks?"

# ---- per-cell desert assignment under the real neighbour policy --------------------------------
cell_quad, cell_ori = G.assign_mains(plain_cells, seed=SEED)

# ---- rewrite: UV -> desert mains, idall -> topo 17 ----------------------------------------------
ID17 = float(X.encode_id(topograph=DESERT_TOPO))
changed = {}
n_rw = 0
for blk, bm in sorted(blocks.items()):
    bx, by = blk
    ps = bm.chan_arrays[X.CH_POS]
    uv = [list(u) for u in bm.chan_arrays[X.CH_UV]]
    tan = [list(t) for t in bm.chan_arrays[X.CH_TAN]]
    for tdx in per_block[blk]:
        tri = bm.tris[tdx]
        cx = sum(ps[i][0] + BLOCK * bx for i in tri) / 3
        cz = sum(ps[i][2] - BLOCK * (by + 1) + BLOCK for i in tri) / 3
        cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        q, o = cell_quad[cell], cell_ori[cell]
        for i in tri:
            wx = ps[i][0] + BLOCK * bx
            wz = ps[i][2] - BLOCK * (by + 1) + BLOCK
            gu, gv = G.mains_uv(wx, wz, cell, q, o)
            uv[i] = [gu + DU, gv + DV]
            tan[i] = [ID17, 0.0, 0.0, 1.0]
            n_rw += 1
            assert REGION[0] <= uv[i][0] <= REGION[2] and \
                REGION[1] <= uv[i][1] <= REGION[3], f"corner left the desert region {uv[i]}"
    import dataclasses
    ca = dict(bm.chan_arrays)
    ca[X.CH_UV] = uv
    ca[X.CH_TAN] = tan
    changed[blk] = dataclasses.replace(bm, chan_arrays=ca)
print(f"rewritten: {n_rw} corners -> desert mains + topo {DESERT_TOPO} "
      f"(geometry untouched)")

# ---- gates --------------------------------------------------------------------------------------
# atlas alpha over the rewritten tris (transparent AND dark = gutter garbage)
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
from PIL import Image                                       # noqa: E402
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()


def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    a4 = [0.0] * 4
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
        r, g2, b2, al = APX[px_, py_]
        a4[0] += r * wg; a4[1] += g2 * wg; a4[2] += b2 * wg; a4[3] += al * wg
    return a4[3], (int(a4[0]), int(a4[1]), int(a4[2]))


blank = 0
for blk, bm in changed.items():
    us = bm.chan_arrays[X.CH_UV]
    for tdx in per_block[blk]:
        tri = bm.tris[tdx]
        for ii in range(6):
            for jj in range(6 - ii):
                w0, w1 = ii / 5.0, jj / 5.0
                w2 = 1 - w0 - w1
                if w2 < -1e-9:
                    continue
                u_ = w0 * us[tri[0]][0] + w1 * us[tri[1]][0] + w2 * us[tri[2]][0]
                v_ = w0 * us[tri[0]][1] + w1 * us[tri[1]][1] + w2 * us[tri[2]][1]
                aa, rgb = at_b(u_, v_)
                if aa < 24 and sum(rgb) < 90:
                    blank += 1
print(f"atlas gate over the retiled tris: blank samples = {blank} (want 0)")
assert blank == 0
IN.census_gate(changed, disc=1)

# ---- deploy -------------------------------------------------------------------------------------
if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    outp = IN.deploy_changed(changed, mod_folder="FF9CustomMap-world", disc=1)
    print("DONE -- run world-mirror, then F6 world re-entry; teleport (30.5, -1217.5) "
          "face east: the crag now stands on its NATIVE desert ground. Judge the foot "
          "fringe (mist OFF).")
else:
    print("dry run only -- re-run with 'deploy' to write.")
