"""MASSIF FACE RENDER -- Moguri-textured ELEVATION render of the west wall, before/after
the tweak-1 probes (the offline eye for the tile experiments).

Orthographic, looking EAST (+x) like the player from the lowland teleport: screen x = north
to the LEFT (matching the in-game screenshot), screen y = height. Painter far-to-near by x.
Reads the DEPLOYED Block[1][16] Terrain.ff9mesh (probes live) and its newest .bak-* sibling
(pristine); draws both, plus a probe-outline overlay on the after image.

Run from the repo root: py studies/overworld-topography/massif_face_render.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import mesh as M                      # noqa: E402

CELL = (1, 16)
BLOCK = 64.0
# the west-face window (world frame): z north..south, y up
Z0, Z1 = -1092.0, -1046.0                                  # horizontal span (46u)
Y0, Y1 = 0.0, 34.0
SC = 22                                                    # px per unit
PROBES = [((94.2, 10.5, -1078.0), (255, 60, 60), "A col"),
          ((94.6, 10.0, -1058.2), (60, 140, 255), "B row")]

GP = Path(_cfg.find_game_path(None))
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
    acc = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
        r, g, b, a = APX[px_, py_]
        acc[0] += r * wg; acc[1] += g * wg; acc[2] += b * wg; aa += a * wg
    return aa, (int(acc[0]), int(acc[1]), int(acc[2]))


mesh_path = (GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
             / f"r{CELL[1]}" / f"Block[{CELL[0]}][{CELL[1]}] Terrain.ff9mesh")
baks = sorted(p for p in mesh_path.parent.iterdir()
              if p.name.startswith(mesh_path.name + ".bak-"))
if not baks:
    sys.exit("no .bak sibling -- run massif_tweak1.py --apply first")

RW, RH = int((Z1 - Z0) * SC), int((Y1 - Y0) * SC)
LDIR = (-0.55, 0.65, -0.25)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)


def render(path):
    bm = M.blockmesh_from_ff9mesh(path, disc=1, x=CELL[0], y=CELL[1], part="terrain")
    V = np.asarray(bm.verts, dtype=np.float64)
    N = np.asarray(bm.normals, dtype=np.float64)
    U = np.asarray(bm.uvs, dtype=np.float64)
    idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    img = Image.new("RGB", (RW, RH), (150, 178, 210))
    op = img.load()
    tris = []
    for i in idx:
        p3 = [(V[j][0] + BLOCK * CELL[0], V[j][1], V[j][2] - BLOCK * CELL[1]) for j in i]
        tris.append((max(p[0] for p in p3), p3, [tuple(U[j][:2]) for j in i],
                     [tuple(N[j][:3]) for j in i]))
    for _, p3, q3, n3 in sorted(tris, key=lambda t: -t[0]):   # far (east) first
        sx = [(Z1 - p[2]) * SC for p in p3]
        sy = [(Y1 - p[1]) * SC for p in p3]
        x0, x1 = int(min(sx)), int(max(sx)) + 1
        y0, y1 = int(min(sy)), int(max(sy)) + 1
        if x1 < 0 or x0 >= RW or y1 < 0 or y0 >= RH:
            continue
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        for pyx in range(max(0, x0), min(RW, x1)):
            for pyy in range(max(0, y0), min(RH, y1)):
                w0 = ((sy[1] - sy[2]) * (pyx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (pyx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                               w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
                if aa < 24:
                    continue
                nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                f = 0.55 + 0.45 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                op[pyx, pyy] = tuple(min(255, int(c * f)) for c in rgb[:3])
    return img


before = render(baks[-1])
after = render(mesh_path)
marked = after.copy()
dr = ImageDraw.Draw(marked)
for (wx, wy, wz), col, lab in PROBES:
    cx, cy = (Z1 - wz) * SC, (Y1 - wy) * SC
    r = 2.6 * SC
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=4)
    dr.text((cx - r, cy - r - 18), lab, fill=col)

OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
gap = 12
sheet = Image.new("RGB", (RW, RH * 3 + gap * 2), (10, 10, 10))
sheet.paste(before, (0, 0))
sheet.paste(after, (0, RH + gap))
sheet.paste(marked, (0, 2 * (RH + gap)))
sheet.save(OUT / "massif_face_probes.png")
print(f"-> {OUT / 'massif_face_probes.png'} (top: pristine, middle: probes live, "
      f"bottom: probes circled)")
