"""THE COARSENING A/B NULL TEST -- does the shattered ring tessellation reach the eye?

The ground-junction synthesis (studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md)
measured the minted ring at 4,181 grass tris / median 0.32u2 (pristine: 858 / 8.00u2)
and INFERRED that this is what the owner reads as "meadowy corner tiles" and "seams" --
an inference its own critic half-falsified (the fine tris carry stock-lawful uv rate).
This instrument decides the bet OFFLINE, before any ninth build spends a playtest on it.

Three in-memory meshes, never written to the install:
  A = the DEPLOYED bench, byte-faithful (6 Disc9 blocks).
  B = A with every ring grass tri (centroid r 10-58u from CENTER) replaced by ONE quad
      per 4u cell -- corner heights sampled from A's own surface, uv = the pristine
      bench's own L3 (quad,ori) decode via G.ground_uv. This is the cell-granular
      proposal's TEXTURE OUTPUT synthesized from the deployed bytes. Boundary cracks at
      the rock rim are expected (render-only mock) and excluded from judgment.
  C = the PRISTINE backup (terrace-strip-prewall.20260731-220001) -- the null baseline.

Rendering is UNLIT (texture only): the S3 law measured WorldMap/Terrain deriving vertex
colour from constants with no N.L, so an offline lambert term would fake seams the game
never draws (round 8's normal field is render-inert in-engine). Geometry reaches the
image the way it reaches the game: through texture density and silhouette.

Cameras: the six standard game-eye bearings plus three CLOSE views matched to the
owner's own screenshot vantages (west base, SE base, north base).

EYE CALIBRATION, binding: A must REPRODUCE the owner's named artifact classes
(patchwork/meadowy tiles on the ring, seam lines) before B-vs-A can falsify anything.
The verdict is read from the PNGs, not asserted here.

Read-only. Regenerate: py -X utf8 critic_coarsen_ab.py   -> out/coarsen_ab/*.png
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "path-d-new-world"))

from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402
import uvf_fix2 as UF                                       # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
PRIS = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
CENTER = (416.0, -512.0)
LOWLAND = 3.2
GRASS_TOPO = {0, 1, 2, 3, 42}
RING = (10.0, 58.0)
CELL = 4.0
OUT = HERE / "out" / "coarsen_ab"
OUT.mkdir(parents=True, exist_ok=True)


def load(src):
    tris = []
    for (bx, by) in CELLS:
        p = (src / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh") if src is LIVE \
            else (src / f"Block[{bx}][{by}] Terrain.ff9mesh")
        bm = M.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, part="terrain")
        V = bm.chan_arrays[X.CH_POS]
        U = bm.chan_arrays[X.CH_UV]
        T = bm.chan_arrays[X.CH_TAN]
        ox, oz = 64.0 * bx, -64.0 * by
        for t in bm.tris:
            w = [(V[i][0] + ox, V[i][1], V[i][2] + oz) for i in t]
            tris.append(dict(
                w=w, uv=[tuple(U[i]) for i in t],
                topo=X.decode_id(int(round(T[t[0]][0])))["topograph"],
                cen=(sum(p[0] for p in w) / 3, sum(p[1] for p in w) / 3,
                     sum(p[2] for p in w) / 3)))
    return tris


def in_ring(t):
    r = math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
    return t["topo"] in GRASS_TOPO and RING[0] <= r <= RING[1]


A = load(LIVE)
C = load(PRIS)
print(f"A (deployed): {len(A)} tris, ring grass {sum(1 for t in A if in_ring(t))}")
print(f"C (pristine): {len(C)} tris, ring grass {sum(1 for t in C if in_ring(t))}")

# ---- the pristine L3 decode (the cell chart the proposal would emit) ------------------------
pre_quad, pre_ori = {}, {}
for t in C:
    if t["topo"] not in GRASS_TOPO:
        continue
    cc = (math.floor(t["cen"][0] / CELL), math.floor(t["cen"][2] / CELL))
    if cc in pre_quad:
        continue
    qo = UF.decode_quad_ori(cc, t["w"], [tuple(u) for u in t["uv"]])
    if qo is not None:
        pre_quad[cc], pre_ori[cc] = qo

# ---- mesh B: A with the ring coarsened to one quad per 4u cell ------------------------------
ring = [t for t in A if in_ring(t)]
keep = [t for t in A if not in_ring(t)]
cells = sorted({(math.floor(t["cen"][0] / CELL), math.floor(t["cen"][2] / CELL))
                for t in ring})
q2, o2 = UF.assign_mains_seeded([c for c in cells if c not in pre_quad],
                                dict(pre_quad), dict(pre_ori), seed=0x51AB)
cell_qo = {c: (pre_quad[c], pre_ori[c]) for c in cells if c in pre_quad}
cell_qo.update({c: (q2[c], o2[c]) for c in q2 if c in set(cells)})
print(f"B: {len(cells)} ring cells ({sum(1 for c in cells if c in pre_quad)} pristine-"
      f"decoded, {len(q2)} policy-resolved)")

# corner heights from A's own ring surface (containing-tri barycentric, else nearest vert)
rv = [(p[0], p[1], p[2]) for t in ring for p in t["w"]]
rv_arr = np.array([[p[0], p[2]] for p in rv])
rv_y = np.array([p[1] for p in rv])


def surf_y(x, z):
    for t in ring:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t["w"]
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-12:
            continue
        w2 = ((x - x1) * (z3 - z1) - (x3 - x1) * (z - z1)) / det
        w3 = ((x2 - x1) * (z - z1) - (x - x1) * (z2 - z1)) / det
        if w2 >= -1e-6 and w3 >= -1e-6 and w2 + w3 <= 1 + 1e-6:
            return (1 - w2 - w3) * y1 + w2 * y2 + w3 * y3
    i = int(np.argmin(np.hypot(rv_arr[:, 0] - x, rv_arr[:, 1] - z)))
    return float(rv_y[i])


ycache = {}


def corner_y(x, z):
    k = (round(x, 3), round(z, 3))
    if k not in ycache:
        ycache[k] = surf_y(x, z)
    return ycache[k]


B = list(keep)
for c in cells:
    quad, ori = cell_qo[c]
    x0, z0 = c[0] * CELL, c[1] * CELL
    P = [(x0, z0), (x0 + CELL, z0), (x0 + CELL, z0 + CELL), (x0, z0 + CELL)]
    P3 = [(x, corner_y(x, z), z) for (x, z) in P]
    for tri in ((P3[0], P3[1], P3[2]), (P3[0], P3[2], P3[3])):
        uvt = [G.ground_uv(p[0], p[2], c, quad, ori) for p in tri]
        cx = sum(p[0] for p in tri) / 3
        cz = sum(p[2] for p in tri) / 3
        B.append(dict(w=list(tri), uv=uvt, topo=0,
                      cen=(cx, sum(p[1] for p in tri) / 3, cz)))
print(f"B: {len(B)} tris ({len(keep)} kept + {2 * len(cells)} coarse quads)")

# ---- the unlit textured renderer (terrace_wall_strip's rasterizer, lam = 1) -----------------
atlas = Image.open(GAME / "MoguriMain" / "StreamingAssets" / "assets" / "resources"
                   / "worldmap" / "textures" / "res(1_24)_terrain.png").convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()


def at_b(u2, v2):
    fx = (u2 % 1.0) * AW - 0.5
    fy = (1.0 - v2 % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    a4 = [0.0, 0.0, 0.0]
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
        r, g2, b2, _ = APX[px_, py_]
        a4[0] += r * wg
        a4[1] += g2 * wg
        a4[2] += b2 * wg
    return tuple(int(v) for v in a4)


def render(tris, path, center, bearing, HW=44.0, HH=23.0, SC=12, elev=0.30):
    RW, RH = int(2 * HW * SC), int(HH * SC)
    img = Image.new("RGB", (RW, RH), (152, 178, 208))
    zbuf = np.full((RW, RH), -1e9)
    cb, sb = math.cos(bearing), math.sin(bearing)
    cph, sph = math.cos(elev), math.sin(elev)
    for t in tris:
        tri, uvt = t["w"], t["uv"]
        a3, b3, c3 = (np.array(p) for p in tri)
        fn3 = np.cross(b3 - a3, c3 - a3)
        if fn3[0] * cb * cph + fn3[1] * sph + fn3[2] * sb * cph <= 0:
            continue                                        # the game-eye backface cull
        pts = []
        for p, u2 in zip(tri, uvt):
            rx, ry, rz = p[0] - center[0], p[1] - LOWLAND, p[2] - center[1]
            s2 = -rx * sb + rz * cb
            h2 = -rx * cb * sph + ry * cph - rz * sb * sph
            d2 = rx * cb * cph + ry * sph + rz * sb * cph
            pts.append((s2, h2 + LOWLAND, d2, u2))
        if all(p[2] < 0 for p in pts):
            continue
        xs = [int((p[0] + HW) * SC) for p in pts]
        ys = [int((HH - p[1]) * SC) for p in pts]
        if max(xs) < 0 or min(xs) >= RW or max(ys) < 0 or min(ys) >= RH:
            continue
        a2, b2, c2 = (np.array((pts[k][0], pts[k][1])) for k in range(3))
        det = float(np.cross(b2 - a2, c2 - a2))
        if abs(det) < 1e-9:
            continue
        for px_ in range(max(0, min(xs)), min(RW - 1, max(xs)) + 1):
            for py_ in range(max(0, min(ys)), min(RH - 1, max(ys)) + 1):
                sx = px_ / SC - HW
                sy = HH - py_ / SC
                pv2 = np.array((sx, sy))
                w1 = float(np.cross(b2 - pv2, c2 - pv2)) / det
                w2 = float(np.cross(c2 - pv2, a2 - pv2)) / det
                w3 = 1 - w1 - w2
                if w1 < -1e-6 or w2 < -1e-6 or w3 < -1e-6:
                    continue
                dep = w1 * pts[0][2] + w2 * pts[1][2] + w3 * pts[2][2]
                if dep <= zbuf[px_, py_]:
                    continue
                zbuf[px_, py_] = dep
                uu = w1 * pts[0][3][0] + w2 * pts[1][3][0] + w3 * pts[2][3][0]
                vv = w1 * pts[0][3][1] + w2 * pts[1][3][1] + w3 * pts[2][3][1]
                img.putpixel((px_, py_), at_b(uu, vv))      # UNLIT: engine-faithful
    img.save(path)


VIEWS = [
    ("wide_S", CENTER, -math.pi / 2, 44.0, 23.0, 12, 0.30),
    ("wide_SW", CENTER, -3 * math.pi / 4, 44.0, 23.0, 12, 0.30),
    ("wide_NE", CENTER, math.pi / 4, 44.0, 23.0, 12, 0.30),
    # the owner's own vantages (playtest screenshots): west base, SE base, north base
    ("close_Wbase", (400.0, -511.0), 0.0, 24.0, 14.0, 20, 0.14),
    ("close_SEbase", (436.0, -514.0), 3 * math.pi / 4, 24.0, 14.0, 20, 0.14),
    ("close_Nbase", (419.0, -498.0), -math.pi / 2, 24.0, 14.0, 20, 0.14),
]
for name, cen, br, hw, hh, sc, el in VIEWS:
    for tag, mesh in (("A_deployed", A), ("B_coarse", B), ("C_pristine", C)):
        render(mesh, OUT / f"{name}__{tag}.png", cen, br, HW=hw, HH=hh, SC=sc, elev=el)
        print(f"   {name}__{tag}.png")
print(f"renders -> {OUT}")
