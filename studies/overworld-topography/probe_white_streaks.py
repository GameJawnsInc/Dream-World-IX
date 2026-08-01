"""WHITE-STREAK HUNT -- byte-locate the owner's photographed seam lines.

The owner's still at (375,-508) shows two thin BRIGHT WHITE line segments lying flat
on the lawn. Hypothesis (the last unexplained class): collapsed repair-pass slivers
whose smeared uv samples the atlas's white transparent GUTTERS -- the critic's
extreme-anisotropy tail, rendered. This scans every deployed grass tri for what its
uv actually SAMPLES (mean atlas color over the uv triangle) and flags bright/white
ones; the pristine bench is the zero-control.

Read-only. Regenerate: py -X utf8 probe_white_streaks.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
PRIS = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
GRASS_TOPO = {0, 1, 2, 3, 42}

atlas = np.asarray(Image.open(GAME / "MoguriMain" / "StreamingAssets" / "assets"
                              / "resources" / "worldmap" / "textures"
                              / "res(1_24)_terrain.png").convert("RGB"), dtype=float)
AH, AW = atlas.shape[:2]


def sample_tri(uv3, n=24):
    """Mean atlas RGB over the uv triangle (barycentric grid)."""
    acc = np.zeros(3)
    cnt = 0
    for i in range(n):
        for j in range(n - i):
            w1, w2 = (i + 0.5) / n, (j + 0.5) / n
            w3 = 1 - w1 - w2
            if w3 < 0:
                continue
            u = w1 * uv3[0][0] + w2 * uv3[1][0] + w3 * uv3[2][0]
            v = w1 * uv3[0][1] + w2 * uv3[1][1] + w3 * uv3[2][1]
            px = min(max(int((u % 1.0) * AW), 0), AW - 1)
            py = min(max(int((1.0 - v % 1.0) * AH), 0), AH - 1)
            acc += atlas[py, px]
            cnt += 1
    return acc / max(1, cnt)


def scan(name, src):
    hits = []
    for (bx, by) in CELLS:
        for p in (src / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh",
                  src / f"Block[{bx}][{by}] Terrain.ff9mesh"):
            if p.is_file():
                break
        else:
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, part="terrain")
        V = bm.chan_arrays[X.CH_POS]
        U = bm.chan_arrays[X.CH_UV]
        T = bm.chan_arrays[X.CH_TAN]
        ox, oz = 64.0 * bx, -64.0 * by
        for t in bm.tris:
            if X.decode_id(int(round(T[t[0]][0])))["topograph"] not in GRASS_TOPO:
                continue
            w = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in t]
            uv3 = [tuple(U[i]) for i in t]
            r, g, b = sample_tri(uv3)
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            sat = (max(r, g, b) - min(r, g, b)) / max(1.0, max(r, g, b))
            if lum > 120 and sat < 0.25:                    # bright + grey/white
                cx = sum(q[0] for q in w) / 3
                cz = sum(q[2] for q in w) / 3
                e = [math.dist(w[i], w[j]) for i, j in ((0, 1), (1, 2), (2, 0))]
                area = 0.5 * float(np.linalg.norm(np.cross(
                    np.array(w[1]) - np.array(w[0]), np.array(w[2]) - np.array(w[0]))))
                us = [q[0] for q in uv3]
                vs = [q[1] for q in uv3]
                hits.append((lum, sat, (round(cx, 1), round(cz, 1)), round(area, 3),
                             round(max(e), 2),
                             (round(min(us), 4), round(max(us), 4),
                              round(min(vs), 4), round(max(vs), 4))))
    hits.sort(reverse=True)
    print(f"\n{name}: {len(hits)} bright/white-sampling grass tris")
    for h in hits[:20]:
        print(f"   lum {h[0]:.0f} sat {h[1]:.2f}  at {h[2]}  area {h[3]}u2  "
              f"longest edge {h[4]}u  uv bbox {h[5]}")
    return hits


live_hits = scan("LIVE (deployed)", LIVE)
pris_hits = scan("PRISTINE", PRIS)
print(f"\nowner sightlines: line A near (368-380, -516..-504); "
      f"line B east of the inlet, roughly (405-435, -510..-498)")
