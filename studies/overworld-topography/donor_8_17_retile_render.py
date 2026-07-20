"""THE (8,17)+2x2 -> DESERT RETILE, OFFLINE CALIBRATED EYE -- the round-4 donor screen's top
new pick, driven end-to-end through the SAME shipped ``GroundRetile``/``transplant_region``
machinery the (7,17) and (10,17)+2x2 in-game-proven builds used, with ZERO writes (every
``ff9mapkit.world.mesh.deploy_override`` / ``deploy_donor_sidecar`` / ``discmirror.auto_mirror``
call is intercepted -- captured for inspection, never touches the real install).

Renders 3 panels at the SAME texel-accurate Moguri-atlas TEXTURE x HILLSHADE recipe as
``desert_fidelity_eye.py`` (the proven calibrated instrument -- real atlas texels, real per-vert
normals, one consistent light direction, no invented shading):

  row 1: OUR CARRY   -- the dry-built retile at target rect (19,17)+2x2, captured straight from
                        the in-memory BlockMesh objects the real deploy call would have written
                        (never touches disk)
  row 2: DONOR REAL   -- the SAME donor bytes before the retile: real stock grass island
                        (8,17)+2x2 (data blocks (8,17)/(9,17)/(9,18); (8,18) is open sea)
  row 3: STOCK DESERT -- a real stock desert beach island, block (13,3) (one of the 15 real
                        topo-32 desert-sand blocks map-wide), for the acceptance KIND question:
                        does OUR carry read as one of THESE, the same bar (10,17) passed.

Offline only -- no deploys, no mint, no install writes. Run from the repo root:
    py studies/overworld-topography/donor_8_17_retile_render.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import discmirror as DM                   # noqa: E402
from ff9mapkit.world import transplant as TR                   # noqa: E402

BLOCK = 64.0
SC = 8                                                          # px per world unit (matches the study default)
GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size
APX = atlas.load()

LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)

RENDER_PARTS = ("terrain", "beach1", "sea1", "sea2")           # land + beach + shore water only


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


def render(mesh_entries, cx, cz, winx, winz):
    """``mesh_entries`` = [(bx, by, bm), ...] (one entry per block x part already selected).
    Returns (tex, sha, com, ys)."""
    x0, x1 = cx - winx / 2, cx + winx / 2
    z0, z1 = cz - winz / 2, cz + winz / 2
    RW, RH = int(winx * SC), int(winz * SC)
    tex = Image.new("RGB", (RW, RH), (150, 178, 210))
    sha = Image.new("RGB", (RW, RH), (150, 178, 210))
    com = Image.new("RGB", (RW, RH), (150, 178, 210))
    tp, sp, cp = tex.load(), sha.load(), com.load()
    tris, ys = [], {}
    for (bx, by, bm) in mesh_entries:
        for p3, q3, n3 in world_tris(bm, bx, by):
            if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
                continue
            if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
                continue
            tris.append((max(p[1] for p in p3), p3, q3, n3))
            for p in p3:
                if x0 <= p[0] <= x1 and z0 <= p[2] <= z1:
                    ys[(round(p[0], 3), round(p[2], 3))] = p[1]
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


# ==== 1. dry-build OUR CARRY, capture the exact BlockMesh objects a real deploy would write ====
_captured: dict = {}


def _fake_deploy_override(bm, *, mod_folder, game=None, lod="0_1", part="Terrain"):
    _captured[(bm.x, bm.y, part.lower())] = bm
    return f"FAKE/{mod_folder}/Disc{bm.disc}/{lod}/r{bm.y}/Block[{bm.x}][{bm.y}] {part}.ff9mesh"


def _fake_sidecar(dx, dy, *, mod_folder, disc, x, y, lod="0_1", game=None):
    return f"FAKE/{mod_folder}/Disc{disc}/{lod}/r{y}/Block[{x}][{y}] Donor.txt"


def _fake_mirror(paths, *, mod_folder, skip_mirror=False, game=None):
    return None


M.deploy_override = _fake_deploy_override
M.deploy_donor_sidecar = _fake_sidecar
DM.auto_mirror = _fake_mirror

gt = TR.GroundRetile.for_donor((8, 17), "desert", size=(2, 2), strips="auto", extra=8.0, disc=1)
summary = TR.transplant_region(
    "FF9CustomMap-world", cell=(19, 17), donor=(8, 17), size=(2, 2), rot=0, shift=(0.0, 0.0),
    strips="auto", tweaks=[gt], extra=8.0, land_margin=0.0, disc=1, dry_run=False)
assert summary["clean"], f"the carry is not clean -- render would be misleading: {summary['gates']}"
print(f"dry-built OUR CARRY: clean={summary['clean']}, {len(_captured)} block/part meshes captured "
      f"(zero writes -- deploy_override/deploy_donor_sidecar/auto_mirror all intercepted)")

carry_entries = [(bx, by, bm) for (bx, by, part), bm in _captured.items() if part in RENDER_PARTS]

# ==== 2. DONOR REAL (pre-retile, real stock grass bytes) ========================================
donor_entries = []
for (bx, by) in [(8, 17), (9, 17), (9, 18)]:               # (8,18) carries no data -- open sea
    for part in RENDER_PARTS:
        try:
            bm = X.read_block(bx, by, disc=1, part=part)
        except ValueError:
            continue
        donor_entries.append((bx, by, bm))

# ==== 3. STOCK DESERT reference (real blocks (13,2)+(13,3), one of the 15 real topo-32 blocks --
#         (13,2) added purely to widen the window so the whole beach cove is in frame) ===========
stock_entries = []
for (bx, by) in [(13, 2), (13, 3)]:
    for part in RENDER_PARTS:
        try:
            bm = X.read_block(bx, by, disc=1, part=part)
        except ValueError:
            continue
        stock_entries.append((bx, by, bm))


def relief_stats(ys):
    dys = []
    for (x, z), y in ys.items():
        for n in ((round(x + 4.0, 3), z), (x, round(z + 4.0, 3))):
            if n in ys:
                dys.append(abs(ys[n] - y))
    ally = list(ys.values())
    return (float(np.std(ally)) if ally else 0.0,
           float(np.median(dys)) if dys else 0.0,
           float(np.percentile(dys, 90)) if dys else 0.0)


ROWS = [
    ("OUR CARRY -- (19,17)+2x2 desert (donor (8,17)+2x2)", carry_entries, 1280.0, -1152.0, 128.0, 128.0),
    ("DONOR REAL -- (8,17)+2x2 grass, PRE-retile", donor_entries, 576.0, -1152.0, 128.0, 128.0),
    ("STOCK DESERT -- real blocks (13,2)+(13,3)", stock_entries, 862.0, -204.0, 96.0, 128.0),
]

panels = []
for label, entries, cx, cz, winx, winz in ROWS:
    tex, sha, com, ys = render(entries, cx, cz, winx, winz)
    st = relief_stats(ys)
    print(f"{label}: {len(entries)} block/part meshes, {len(ys)} verts in window; "
          f"relief y std {st[0]:.2f}, |dY| med {st[1]:.2f} p90 {st[2]:.2f}")
    panels.append((label, tex, sha, com))

gap, head = 14, 26
maxw = max(t.size[0] for _, t, _, _ in panels)
sheet = Image.new("RGB", (maxw * 3 + gap * 2,
                          sum(c.size[1] + head for _, _, c, _ in panels) + gap * (len(panels) - 1)),
                  (10, 10, 10))
dr = ImageDraw.Draw(sheet)
oy = 0
for (label, tex, sha, com) in panels:
    dr.text((4, oy + 6), f"{label}   |   TEXTURE / HILLSHADE / COMBINED", fill=(240, 240, 240))
    for c, img in enumerate((tex, sha, com)):
        sheet.paste(img, (c * (maxw + gap), oy + head))
    oy += com.size[1] + head + gap
OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
sheet.save(OUT / "donor_8_17_retile_render.png")
print(f"-> {OUT / 'donor_8_17_retile_render.png'}")
