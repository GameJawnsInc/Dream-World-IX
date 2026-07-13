"""V4 DONOR RENDER -- Moguri-textured, lit, top-down render of the (5-7,15-16) window.

Terrain samples the Moguri HD atlas per pixel (bilinear) with the v3 study's lambert
shade; river/falls/riverjoint tint blue over their footprint; objects light grey; sea
parts as banded blues (sea3 shallow -> sea4 deep). Paint order = global min-y so higher
geometry overpaints lower. Run from the repo root; writes out/v4_donor_render.png.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import extract as X                   # noqa: E402

BLOCKS = [(5, 15), (6, 15), (7, 15), (5, 16), (6, 16), (7, 16)]
X0, Y0 = 5, 15
SC = 10                                                    # px per unit
GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
img = Image.open(MOG).convert("RGBA")
W_, H_ = img.size
PX = img.load()


def at_b(u_, v_):
    fx = (u_ % 1.0) * W_ - 0.5
    fy = (1.0 - v_ % 1.0) * H_ - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc_ = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx2, dy2, wgt) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                            (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx2, 0), W_ - 1), min(max(y0 + dy2, 0), H_ - 1)
        r, gg, b, a = PX[px_, py_]
        acc_[0] += r * wgt; acc_[1] += gg * wgt; acc_[2] += b * wgt; aa += a * wgt
    return aa, (int(acc_[0]), int(acc_[1]), int(acc_[2]))


FLAT = {"sea4": (24, 40, 72), "sea5": (30, 52, 92), "sea3": (40, 70, 118),
        "river": (80, 150, 235), "falls": (170, 215, 255), "riverjoint": (95, 160, 240),
        "object": (185, 180, 175)}
tris = []                                                  # (min_y, pts, kind, uv/None, nrm)
for (bx, by) in BLOCKS:
    ox, oz = (bx - X0) * 64.0, -(by - Y0) * 64.0
    for part in ("sea4", "sea5", "sea3", "terrain", "river", "riverjoint", "falls", "object"):
        try:
            pm = X.read_block(bx, by, disc=1, part=part)
        except Exception:
            continue
        V = np.asarray(pm.verts, dtype=np.float64)
        N = np.asarray(pm.normals, dtype=np.float64)
        U = np.asarray(pm.uvs, dtype=np.float64)
        idx = np.asarray(pm.flat_index, dtype=np.int64).reshape(-1, 3)
        for i in idx:
            p3 = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in i]
            my = min(p[1] for p in p3)
            if part == "terrain":
                tris.append((my, p3, "tex", [tuple(U[j][:2]) for j in i],
                             [tuple(N[j][:3]) for j in i]))
            else:
                tris.append((my + (0.01 if part != "object" else 0.02), p3, part, None,
                             [tuple(N[j][:3]) for j in i]))

W = 3 * 64
H = 2 * 64
RW, RH = W * SC, H * SC
out = Image.new("RGB", (RW, RH), (24, 40, 72))
op = out.load()
LDIR = (-0.45, 0.8, -0.35)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)

for my, p3, kind, q3, n3 in sorted(tris, key=lambda t: t[0]):
    xs_ = [pp[0] * SC for pp in p3]
    zs_ = [-pp[2] * SC for pp in p3]                       # window z 0..-128 -> raster 0..RH
    x0, x1 = int(min(xs_)), int(max(xs_)) + 1
    z0, z1 = int(min(zs_)), int(max(zs_)) + 1
    d = (zs_[1] - zs_[2]) * (xs_[0] - xs_[2]) + (xs_[2] - xs_[1]) * (zs_[0] - zs_[2])
    if abs(d) < 1e-9:
        continue
    for pyx in range(max(0, x0), min(RW, x1)):
        for pyz in range(max(0, z0), min(RH, z1)):
            w0 = ((zs_[1] - zs_[2]) * (pyx - xs_[2]) + (xs_[2] - xs_[1]) * (pyz - zs_[2])) / d
            w1 = ((zs_[2] - zs_[0]) * (pyx - xs_[2]) + (xs_[0] - xs_[2]) * (pyz - zs_[2])) / d
            w2 = 1 - w0 - w1
            if w0 < 0 or w1 < 0 or w2 < 0:
                continue
            if kind == "tex":
                aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                               w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
                if aa < 24:
                    continue
            else:
                rgb = FLAT[kind]
            nx = sum(w * n3[k2][0] for k2, w in enumerate((w0, w1, w2)))
            ny = sum(w * n3[k2][1] for k2, w in enumerate((w0, w1, w2)))
            nz = sum(w * n3[k2][2] for k2, w in enumerate((w0, w1, w2)))
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f = 0.55 + 0.45 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
            if kind in ("sea4", "sea5", "sea3"):
                f = 1.0
            op[pyx, pyz] = tuple(min(255, int(cc * f)) for cc in rgb[:3])

p = Path(__file__).parent / "out" / "v4_donor_render.png"
out.save(p)
print(f"render -> {p}")
