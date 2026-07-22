"""THE RELIEF EYE -- does the resurrected world-coord rolling relief READ in-language?

The 2026-07-21 resurrection (grassland.relief, opt-in --relief) adds gentle inland undulation to
world-island mints. This is the offline eye that judges the AESTHETIC axis (the calibration numbers
already prove it lands in the measured band) before the one playtest:

  row 1: MINT RELIEF  -- the demo island interior (672,-608), --relief amp 1.3
  row 2: MINT FLAT    -- the SAME island, relief OFF (the A/B control: dead-flat renders every
                         tile border as a naked straight line at the oblique camera)
  row 3: STOCK grass (15,15) -- a calm interior plain, the calibration target (CALIBRATE FIRST)
  row 4: STOCK grass (18,12) -- a second stock plain

  col 1: TEXTURE only     col 2: HILLSHADE only (isolates the roll)     col 3: TEXTURE x HILLSHADE

Then a GRAZING oblique strip (the player-height camera pitch) of MINT-RELIEF vs MINT-FLAT vs STOCK,
where the roll is most visible. Run from repo root: py studies/overworld-topography/relief_eye.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                        # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import island as I                     # noqa: E402

BLOCK = 64.0
SC = 12
WIN = 56.0
GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()
LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR)); LDIR = tuple(q / _l for q in LDIR)


def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = [0.0, 0.0, 0.0]; aa = 0.0
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


def collect(blocks, reader):
    tris = []
    for (bx, by) in blocks:
        bm = reader(bx, by)
        for p3, q3, n3 in world_tris(bm, bx, by):
            tris.append((p3, q3, n3))
    return tris


def render_topdown(tris, cx, cz):
    x0, x1 = cx - WIN / 2, cx + WIN / 2
    z0, z1 = cz - WIN / 2, cz + WIN / 2
    RW = RH = int(WIN * SC)
    tex = Image.new("RGB", (RW, RH), (150, 178, 210))
    sha = Image.new("RGB", (RW, RH), (150, 178, 210))
    com = Image.new("RGB", (RW, RH), (150, 178, 210))
    tp, sp, cp = tex.load(), sha.load(), com.load()
    keep, ys = [], {}
    for p3, q3, n3 in tris:
        if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
            continue
        if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
            continue
        keep.append((max(p[1] for p in p3), p3, q3, n3))
        for p in p3:
            if x0 <= p[0] <= x1 and z0 <= p[2] <= z1:
                ys[(round(p[0], 3), round(p[2], 3))] = p[1]
    for _, p3, q3, n3 in sorted(keep, key=lambda t: t[0]):
        sx = [(p[0] - x0) * SC for p in p3]
        sy = [(z1 - p[2]) * SC for p in p3]
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        for pxx in range(max(0, int(min(sx))), min(RW, int(max(sx)) + 1)):
            for pyy in range(max(0, int(min(sy))), min(RH, int(max(sy)) + 1)):
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
                f = 0.42 + 0.58 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                tp[pxx, pyy] = tuple(min(255, int(c)) for c in rgb)
                g = min(255, int(235 * f)); sp[pxx, pyy] = (g, g, g)
                cp[pxx, pyy] = tuple(min(255, int(c * f)) for c in rgb)
    return tex, sha, com, ys


def render_graze(tris, cx, cz, W=560, H=300):
    """A low-pitch painter-sorted oblique render (the player-height game camera): stand south of the
    window, look north-down across the interior. The roll shows as silhouette + shading."""
    cam = np.array([cx, 34.0, cz + 46.0])                  # stand south (higher z), ~34u up
    look = np.array([cx, 2.5, cz - 8.0])
    fwd = look - cam; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 1.0, 0.0])); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    fov = math.radians(42.0); fpx = (H / 2) / math.tan(fov / 2)
    img = Image.new("RGB", (W, H), (150, 178, 210)); px = img.load()
    zbuf = [[1e18] * W for _ in range(H)]

    def proj(p):
        rel = np.array(p) - cam
        cxx = float(np.dot(rel, right)); cyy = float(np.dot(rel, up)); czz = float(np.dot(rel, fwd))
        if czz <= 0.1:
            return None
        return (W / 2 + fpx * cxx / czz, H / 2 - fpx * cyy / czz, czz)

    order = sorted(tris, key=lambda t: -max(np.hypot(p[0] - cam[0], p[2] - cam[2]) for p in t[0]))
    for p3, q3, n3 in order:
        pv = [proj(p) for p in p3]
        if any(v is None for v in pv):
            continue
        sx = [v[0] for v in pv]; sy = [v[1] for v in pv]; sz = [v[2] for v in pv]
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        nx = sum(n[0] for n in n3) / 3; ny = sum(n[1] for n in n3) / 3; nz = sum(n[2] for n in n3) / 3
        nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        sh = 0.42 + 0.58 * max(0.0, (nx*LDIR[0] + ny*LDIR[1] + nz*LDIR[2]) / nl)
        for pxx in range(max(0, int(min(sx))), min(W, int(max(sx)) + 1)):
            for pyy in range(max(0, int(min(sy))), min(H, int(max(sy)) + 1)):
                w0 = ((sy[1]-sy[2])*(pxx-sx[2]) + (sx[2]-sx[1])*(pyy-sy[2])) / d
                w1 = ((sy[2]-sy[0])*(pxx-sx[2]) + (sx[0]-sx[2])*(pyy-sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                zz = w0*sz[0] + w1*sz[1] + w2*sz[2]
                if zz >= zbuf[pyy][pxx]:
                    continue
                aa, rgb = at_b(w0*q3[0][0] + w1*q3[1][0] + w2*q3[2][0],
                               w0*q3[0][1] + w1*q3[1][1] + w2*q3[2][1])
                if aa < 24:
                    continue
                zbuf[pyy][pxx] = zz
                px[pxx, pyy] = tuple(min(255, int(c * sh)) for c in rgb)
    return img


def rstats(ys):
    dys = []
    for (x, z), y in ys.items():
        for n in ((round(x + 4.0, 3), z), (x, round(z + 4.0, 3))):
            if n in ys:
                dys.append(abs(ys[n] - y))
    ally = list(ys.values())
    return (float(np.std(ally)) if ally else 0, float(np.median(dys)) if dys else 0,
            float(np.percentile(dys, 90)) if dys else 0)


# ---- build the demo island (in-memory) relief + flat; stock readers -------------------------------
CX, CZ = 672.0, -608.0
built_r = I.build_landmass(center=(CX, CZ), base_radius=44.0, seed=788.0, lobes=1, relief_amp=1.3)
built_f = I.build_landmass(center=(CX, CZ), base_radius=44.0, seed=788.0, lobes=1, relief_amp=0.0)
rblk = {blk: bm for blk, bm in built_r["blocks"].items()}
fblk = {blk: bm for blk, bm in built_f["blocks"].items()}


def _stock(bx, by):
    return X.read_block(bx, by, disc=1, part="terrain")


ROWS = [
    ("MINT RELIEF (672,-608) amp1.3", collect(list(rblk), lambda bx, by: rblk[(bx, by)]), CX, CZ),
    ("MINT FLAT (relief off)", collect(list(fblk), lambda bx, by: fblk[(bx, by)]), CX, CZ),
    ("STOCK grass (15,15)", collect([(15, 15)], _stock), 992.0, -992.0),
    ("STOCK grass (18,12)", collect([(18, 12)], _stock), 1184.0, -800.0),
]

panels = []
print("CALIBRATE THE INSTRUMENT (same pipeline for mint + stock):")
for label, tris, cx, cz in ROWS:
    tex, sha, com, ys = render_topdown(tris, cx, cz)
    st = rstats(ys)
    print(f"  {label}: verts {len(ys)}  y-std {st[0]:.2f}  |dY| med {st[1]:.2f} p90 {st[2]:.2f}")
    panels.append((label, tex, sha, com))
print("  (stock calm-grass band: std ~0.46-1.07, |dY| med ~0.2 p90 ~0.5-0.7)")

RW = RH = int(WIN * SC)
gap, head = 14, 24
sheet = Image.new("RGB", (RW * 3 + gap * 2, (RH + head) * len(panels) + gap * (len(panels) - 1)),
                  (10, 10, 10))
dr = ImageDraw.Draw(sheet)
for r, (label, tex, sha, com) in enumerate(panels):
    oy = r * (RH + head + gap)
    dr.text((4, oy + 5), f"{label}   |   TEXTURE / HILLSHADE / COMBINED", fill=(240, 240, 240))
    for c, img in enumerate((tex, sha, com)):
        sheet.paste(img, (c * (RW + gap), oy + head))
OUT = Path(__file__).with_name("out"); OUT.mkdir(exist_ok=True)
sheet.save(OUT / "relief_eye_topdown.png")
print(f"-> {OUT / 'relief_eye_topdown.png'}")

# grazing strip
gz = [("MINT RELIEF", render_graze(ROWS[0][1], CX, CZ)),
      ("MINT FLAT", render_graze(ROWS[1][1], CX, CZ)),
      ("STOCK (15,15)", render_graze(ROWS[2][1], 992.0, -992.0))]
GW, GH = gz[0][1].size
strip = Image.new("RGB", (GW, (GH + head) * len(gz)), (10, 10, 10))
dr2 = ImageDraw.Draw(strip)
for r, (label, img) in enumerate(gz):
    oy = r * (GH + head)
    dr2.text((4, oy + 5), f"GRAZING (player pitch): {label}", fill=(240, 240, 240))
    strip.paste(img, (0, oy + head))
strip.save(OUT / "relief_eye_grazing.png")
print(f"-> {OUT / 'relief_eye_grazing.png'}")
