"""THE DESERT SHORE -- retile the crag bench's coastal cliff wall to the DESERT band.

The desert ground retile left one grass remnant: the cliff wall band (topo 58) samples
the mint's grey-rock atlas band, whose TOP row is painted with a green grass lip. The
crag island's own coast measures a desert wall band of the SAME structure (u width
0.24805 = the grass band's 0.248; v span 0.03027 = one row; v runs base->top downward)
at its own atlas spot -- THE WALL TRANSLATION LAW, the shore sibling of the desert
mains translation:

    mint (grass) wall: ROCK_U (0.699, 0.947)     ROCK_V (0.923, 0.893)
    desert wall:       (0.42773, 0.67578)        (0.90234, 0.87207)
    translation:       du = -0.27127             dv = -0.02066

This script translates every topo-58 corner's UV on the crag bench IN PLACE (zero
geometry change; the topograph stays 58 -- the crag island's own coast is 58 too).
With the ground already deserted (desert_bench.py), this completes the bench: desert
ground + desert cliff shore + the native-ground crag.

Usage:  py studies/overworld-topography/desert_shore.py [deploy]
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import extract as X                   # noqa: E402
from ff9mapkit.world import interior as IN                 # noqa: E402
from ff9mapkit.world import mesh as M                      # noqa: E402

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BLOCKS = [(0, 18), (1, 18), (0, 19), (1, 19)]
DU, DV = -0.27127, -0.02066                                # THE WALL TRANSLATION LAW
REGION = (0.42773 - 0.004, 0.87207 - 0.004, 0.67578 + 0.004, 0.90234 + 0.004)

changed = {}
n_rw = 0
for (bx, by) in BLOCKS:
    p = MODW / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, lod="0_1", part="terrain")
    ts = bm.chan_arrays[X.CH_TAN]
    uv = [list(u) for u in bm.chan_arrays[X.CH_UV]]
    dirty = False
    for tri in bm.tris:
        if X.decode_id(int(round(ts[tri[0]][0])))["topograph"] != 58:
            continue
        for i in tri:
            uv[i] = [uv[i][0] + DU, uv[i][1] + DV]
            assert REGION[0] <= uv[i][0] <= REGION[2] and \
                REGION[1] <= uv[i][1] <= REGION[3], f"corner left the desert wall band {uv[i]}"
            n_rw += 1
            dirty = True
    if dirty:
        import dataclasses
        ca = dict(bm.chan_arrays)
        ca[X.CH_UV] = uv
        changed[(bx, by)] = dataclasses.replace(bm, chan_arrays=ca)
print(f"rewritten: {n_rw} wall corners -> the desert cliff band (geometry untouched)")
assert n_rw, "no topo-58 wall on the bench?"

# atlas alpha gate over the retiled wall tris
from PIL import Image                                       # noqa: E402
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
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
    ts = bm.chan_arrays[X.CH_TAN]
    us = bm.chan_arrays[X.CH_UV]
    for tri in bm.tris:
        if X.decode_id(int(round(ts[tri[0]][0])))["topograph"] != 58:
            continue
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
print(f"atlas gate over the retiled wall: blank samples = {blank} (want 0)")
assert blank == 0
IN.census_gate(changed, disc=1)

if len(sys.argv) > 1 and sys.argv[1] == "deploy":
    IN.deploy_changed(changed, mod_folder="FF9CustomMap-world", disc=1)
    print("DONE -- run world-mirror, then F6 world re-entry: the bench is now FULLY "
          "desert (ground + cliff shore + the native-ground crag).")
else:
    print("dry run only -- re-run with 'deploy' to write.")
