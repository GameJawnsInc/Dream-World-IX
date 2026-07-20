"""Targeted high-SC re-render of the artifact window at (19,17)+2x2 (OLD site) using the SAME
texture recipe as donor_8_17_retile_render.py, PLUS a bucket-labeled overlay (mains=green outline,
wall=red, sand=blue, recovered=yellow, foam=magenta) so the hatch can be attributed to a bucket by
eye, not guessed."""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import discmirror as DM                   # noqa: E402
from ff9mapkit.world import transplant as TR                   # noqa: E402

BLOCK = 64.0
SC = 24
GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()
LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)
RENDER_PARTS = ("terrain", "beach1", "sea1", "sea2")


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


def render(mesh_entries, cx, cz, winx, winz, alpha_gate=24):
    x0, x1 = cx - winx / 2, cx + winx / 2
    z0, z1 = cz - winz / 2, cz + winz / 2
    RW, RH = int(winx * SC), int(winz * SC)
    tex = Image.new("RGB", (RW, RH), (150, 178, 210))
    tp = tex.load()
    tris = []
    for (bx, by, bm) in mesh_entries:
        for p3, q3, n3 in world_tris(bm, bx, by):
            if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
                continue
            if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
                continue
            tris.append((max(p[1] for p in p3), p3, q3, n3))
    for _, p3, q3, n3 in sorted(tris, key=lambda t: t[0]):
        sx = [(p[0] - x0) * SC for p in p3]
        sy = [(z1 - p[2]) * SC for p in p3]
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
                if aa < alpha_gate:
                    continue
                nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                f = 0.45 + 0.55 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                tp[pxx, pyy] = tuple(min(255, int(c * f)) for c in rgb)
    return tex


_captured: dict = {}


def _fake_deploy_override(bm, *, mod_folder, game=None, lod="0_1", part="Terrain"):
    _captured[(bm.x, bm.y, part.lower())] = bm
    return "FAKE"


def _fake_sidecar(dx, dy, *, mod_folder, disc, x, y, lod="0_1", game=None):
    return "FAKE"


def _fake_mirror(paths, *, mod_folder, skip_mirror=False, game=None):
    return None


M.deploy_override = _fake_deploy_override
M.deploy_donor_sidecar = _fake_sidecar
DM.auto_mirror = _fake_mirror

gt = TR.GroundRetile.for_donor((8, 17), "desert", size=(2, 2), strips="auto", extra=8.0, disc=1)
summary = TR.transplant_region(
    "FF9CustomMap-world", cell=(19, 17), donor=(8, 17), size=(2, 2), rot=0, shift=(0.0, 0.0),
    strips="auto", tweaks=[gt], extra=8.0, land_margin=0.0, disc=1, dry_run=False)
assert summary["clean"]

carry_entries = [(bx, by, bm) for (bx, by, part), bm in _captured.items() if part in RENDER_PARTS]

# zoom tight on the artifact: TARGET-frame world x~[1305,1325] z~[-1145,-1120]
tex = render(carry_entries, 1315.0, -1132.0, 40.0, 40.0)
OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
tex.save(OUT / "artifact_zoom_carry.png")
print("->", OUT / "artifact_zoom_carry.png")

# same window rendered from the DONOR's raw pre-retile bytes (grass), for comparison
import ff9mapkit.world.extract as X  # noqa: E402
donor_entries = []
for (bx, by) in [(8, 17), (9, 17), (9, 18)]:
    for part in RENDER_PARTS:
        try:
            bm = X.read_block(bx, by, disc=1, part=part)
        except ValueError:
            continue
        donor_entries.append((bx, by, bm))
tex2 = render(donor_entries, 1315.0 - 704.0, -1132.0, 40.0, 40.0)
tex2.save(OUT / "artifact_zoom_donor.png")
print("->", OUT / "artifact_zoom_donor.png")
