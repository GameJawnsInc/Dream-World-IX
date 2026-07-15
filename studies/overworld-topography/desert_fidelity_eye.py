"""THE DESERT FIDELITY EYE -- plan-view Moguri renders: the minted desert island vs stock.

The earmarked DESERT TILE FIDELITY CHECK names two mint approximations (see
desert_ground_anatomy.py + the study README): (1) locked grass-form tile windows vs
stock's FREE fractional slides (the COL-FREEDOM form at ground scale), and (2) the
grass relief field vs stock desert's rougher one (y std 2.44 vs 0.66-1.25). This is
the offline eye for both, before the playtest spends a round:

  row 1: the MINT  -- the deployed r52 fidelity island's interior (768,-1216)
  row 2: STOCK A   -- real block (12,4)  (377 topo-17 tris, no topo-38)
  row 3: STOCK B   -- real block (12,5)  (298 topo-17 tris, no topo-38)

  col 1: TEXTURE only (flat light)   -> isolates gap 1 (tile-window regularity)
  col 2: HILLSHADE only (no texture) -> isolates gap 2 (relief roughness)
  col 3: TEXTURE x HILLSHADE         -> the closest offline read to in-game

Also prints the relief stats measured on the minted bytes vs the study's stock figures.
Run from the repo root: py studies/overworld-topography/desert_fidelity_eye.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                        # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

BLOCK = 64.0
SC = 12                                                     # px per world unit
WIN = 64.0                                                  # window side in units
GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()

LDIR = (-0.45, 0.72, 0.45)                                  # oblique NW-ish, same everywhere
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)


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
    return aa, (acc[0], acc[1], acc[2])


def world_tris(bm, bx, by):
    V = np.asarray(bm.verts, dtype=np.float64)
    N = np.asarray(bm.normals, dtype=np.float64)
    U = np.asarray(bm.uvs, dtype=np.float64)
    for i in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in i]
        yield p3, [tuple(U[j][:2]) for j in i], [tuple(N[j][:3]) for j in i]


def mint_block(bx, by):
    p = (GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
         / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh")
    return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")


def render(blocks, cx, cz, reader):
    """One window -> (tex, shade, combined) images + the window's vertex y samples."""
    x0, x1 = cx - WIN / 2, cx + WIN / 2
    z0, z1 = cz - WIN / 2, cz + WIN / 2
    RW = RH = int(WIN * SC)
    tex = Image.new("RGB", (RW, RH), (150, 178, 210))
    sha = Image.new("RGB", (RW, RH), (150, 178, 210))
    com = Image.new("RGB", (RW, RH), (150, 178, 210))
    tp, sp, cp = tex.load(), sha.load(), com.load()
    tris, ys = [], {}
    for (bx, by) in blocks:
        bm = reader(bx, by)
        for p3, q3, n3 in world_tris(bm, bx, by):
            if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
                continue
            if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
                continue
            tris.append((max(p[1] for p in p3), p3, q3, n3))
            for p in p3:
                if x0 <= p[0] <= x1 and z0 <= p[2] <= z1:
                    ys[(round(p[0], 3), round(p[2], 3))] = p[1]
    for _, p3, q3, n3 in sorted(tris, key=lambda t: t[0]):    # low first, high paints over
        sx = [(p[0] - x0) * SC for p in p3]
        sy = [(z1 - p[2]) * SC for p in p3]                   # north (higher z) at the top
        bx0, bx1 = int(min(sx)), int(max(sx)) + 1
        by0, by1 = int(min(sy)), int(max(sy)) + 1
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        for pxx in range(max(0, bx0), min(RW, bx1)):
            for pyy in range(max(0, by0), min(RH, by1)):
                w0 = ((sy[1] - sy[2]) * (pxx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (pxx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                               w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
                if aa < 24:
                    continue
                nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                f = 0.45 + 0.55 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                tp[pxx, pyy] = tuple(min(255, int(c)) for c in rgb)
                g = min(255, int(235 * f))
                sp[pxx, pyy] = (g, g, g)
                cp[pxx, pyy] = tuple(min(255, int(c * f)) for c in rgb)
    return tex, sha, com, ys


def relief_stats(ys):
    dys = []
    for (x, z), y in ys.items():
        for n in ((round(x + 4.0, 3), z), (x, round(z + 4.0, 3))):
            if n in ys:
                dys.append(abs(ys[n] - y))
    ally = list(ys.values())
    return (float(np.std(ally)), float(np.median(dys)) if dys else 0.0,
            float(np.percentile(dys, 90)) if dys else 0.0)


ROWS = [
    ("MINT r52 island (768,-1216)", [(11, 18), (12, 18), (11, 19), (12, 19)],
     768.0, -1216.0, mint_block),
    ("STOCK block (12,4)", [(12, 4)], 800.0, -288.0,
     lambda bx, by: X.read_block(bx, by, disc=1, part="terrain")),
    ("STOCK block (12,5)", [(12, 5)], 800.0, -352.0,
     lambda bx, by: X.read_block(bx, by, disc=1, part="terrain")),
]

panels = []
for label, blocks, cx, cz, reader in ROWS:
    tex, sha, com, ys = render(blocks, cx, cz, reader)
    st = relief_stats(ys)
    print(f"{label}: verts {len(ys)}; relief y std {st[0]:.2f}, |dY| med {st[1]:.2f} "
          f"p90 {st[2]:.2f}")
    panels.append((label, tex, sha, com))
print("(study baselines -- stock desert: std 2.44 med 0.33 p90 1.04; "
      "grass: std 0.66-1.25 med ~0.2 p90 ~0.5-0.7)")

RW = RH = int(WIN * SC)
gap, head = 14, 26
sheet = Image.new("RGB", (RW * 3 + gap * 2, (RH + head) * len(panels) + gap * (len(panels) - 1)),
                  (10, 10, 10))
dr = ImageDraw.Draw(sheet)
for r, (label, tex, sha, com) in enumerate(panels):
    oy = r * (RH + head + gap)
    dr.text((4, oy + 6), f"{label}   |   TEXTURE / HILLSHADE / COMBINED", fill=(240, 240, 240))
    for c, img in enumerate((tex, sha, com)):
        sheet.paste(img, (c * (RW + gap), oy + head))
OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
sheet.save(OUT / "desert_fidelity_eye.png")
print(f"-> {OUT / 'desert_fidelity_eye.png'}")
