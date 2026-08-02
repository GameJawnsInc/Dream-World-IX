"""THE RENDER GATE — offline textured software renderer over the bench block meshes.

Registration: RENDER-GATE.md. The look-axis instrument. Built ON the prior art
(feedback-own-prior-art-before-new-lanes):
  - atlas:    ff9mapkit.world.atlas.load_atlas (engine-resolved: Moguri loose PNG
              or p0data3 bundle) — extraction was already productized.
  - water:    per-name frame-0 caustic textures (THE PER-NAME MATERIAL LAW; the
              map is engine-verified in studies/overworld-topography/whole_island_eye.py).
  - cull:     THE GAME-EYE PASS convention from terrace_wall_strip.render_strip —
              cull when cross(b-a, c-a) . (toward-eye) <= 0; holes render as sky.
Engine-faithful choices (Memoria trace, 2026-08-02): UNLIT (WorldMap/Terrain binds
no normal), uv plain 0..1 over one 1024^2 terrain atlas, sea layers OPAQUE and
geometric (frame-swap anim -> frame 0 for stills), NEAREST sampling (vanilla),
alpha-0 texels render WHITE in-game (blank-tile law, world/atlas.py).

READ-ONLY over the install; renders to out/render_gate/.

Usage:
  py render_gate.py render <baseline|v1|v2|live>
  py render_gate.py calibrate            # P-A..P-E corpus run + diffs
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import atlas as A                      # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(config.find_game_path(None))
MOD = "FF9CustomMap-world"
DISC = 9
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
BLOCK = 64.0
OUTD = HERE / "out" / "render_gate"
BK = Path(r"C:\gd\Dream-World-IX\backups")
TEXDIR = GAME / "MoguriMain" / "StreamingAssets" / "Assets" / "Resources" / \
    "worldmap" / "textures"
WATER_TEX = {"Beach1": "11_0_128_0", "Sea1": "10_64_0_0", "Sea2": "10_128_0_0",
             "Sea3": "10_128_64_0", "Sea4": "10_128_128_0", "Sea5": "11_64_0_0"}
PARTS = ["Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5"]
SKY = (152, 178, 208)
BLANK_WHITE = (255, 255, 255)                               # alpha-0 sample -> white

RES = (960, 640)
# committed cameras — constants once calibration passes; every run comparable
VIEWS = {
    "sea_w": dict(kind="persp", eye=(348.0, 9.0, -524.0), at=(381.0, 2.0, -513.0),
                  fov=50.0, reach=90.0),
    "sea_sw": dict(kind="persp", eye=(356.0, 7.0, -540.0), at=(380.0, 2.0, -511.0),
                   fov=50.0, reach=90.0),
    "top": dict(kind="ortho", x0=362.0, x1=398.0, z0=-528.0, z1=-498.0),
    "island": dict(kind="persp", eye=(330.0, 40.0, -604.0), at=(414.0, 2.0, -510.0),
                   fov=55.0, reach=220.0),
}
CORNER_BBOX = (370.0, 390.0, -520.0, -505.0)                # P-D localization box


# ---------------------------------------------------------------- textures
_TEX = {}


def tex_for(part):
    """(H,W,4) uint8 RGBA or None. Terrain/Object via the kit's engine-resolved
    loader; water parts via the per-name frame-0 Moguri loose PNGs."""
    if part in _TEX:
        return _TEX[part]
    img = None
    if part in ("Terrain", "Object"):
        img = A.load_atlas(part.lower() if part != "Terrain" else "terrain",
                           game=GAME, source="engine")
    elif part in WATER_TEX:
        p = TEXDIR / f"{WATER_TEX[part]}.png"
        if p.is_file():
            img = Image.open(p)
    _TEX[part] = np.asarray(img.convert("RGBA")) if img is not None else None
    return _TEX[part]


def sample(tex, u, v):
    """NEAREST, Unity V bottom-up; wrap repeat; alpha-0 -> white (blank-tile law)."""
    h, w = tex.shape[:2]
    iu = np.floor((u % 1.0) * w).astype(np.int64) % w
    iv = np.floor((1.0 - (v % 1.0)) * h).astype(np.int64) % h
    rgba = tex[iv, iu].astype(np.float32)
    blank = rgba[:, 3] == 0
    rgb = rgba[:, :3]
    rgb[blank] = BLANK_WHITE
    return rgb


# ---------------------------------------------------------------- mesh loading
def live_path(bx, by, part):
    root = GAME / MOD / "FF9_Data" / "WorldMap" / f"Disc{DISC}" / "0_1"
    return root / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"


def load_batches(part_src=None):
    """[(part, verts Nx3 world, uvs Nx2, tris Mx3)]; part_src maps
    (bx,by,part)->Path overriding the live file (walk_sim convention)."""
    batches = []
    for (bx, by) in CELLS:
        ox, oz = BLOCK * bx, -BLOCK * by
        for part in PARTS:
            p = live_path(bx, by, part)
            if part_src is not None:
                p = part_src.get((bx, by, part), p)
            if not p.is_file():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=DISC, x=bx, y=by, part=part.lower())
            pos = np.asarray(bm.chan_arrays[X.CH_POS], dtype=np.float64)
            uvc = bm.chan_arrays.get(X.CH_UV)
            uv = np.asarray(uvc, dtype=np.float64)[:, :2] if uvc is not None \
                else np.zeros((len(pos), 2))
            tris = np.asarray(bm.tris, dtype=np.int64)
            w = pos.copy()
            w[:, 0] += ox
            w[:, 2] += oz
            batches.append((part, w, uv, tris))
    return batches


# ---------------------------------------------------------------- camera
def project(view, verts):
    """world Nx3 -> (sx, sy, depth); depth grows AWAY from the eye."""
    W, H = RES
    if view["kind"] == "ortho":
        x0, x1, z0, z1 = view["x0"], view["x1"], view["z0"], view["z1"]
        sx = (verts[:, 0] - x0) / (x1 - x0) * (W - 1)
        sy = (verts[:, 2] - z0) / (z1 - z0) * (H - 1)
        return sx, sy, -verts[:, 1]
    eye = np.array(view["eye"])
    at = np.array(view["at"])
    fwd = at - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = verts - eye
    cx, cy, cz = rel @ right, rel @ up, rel @ fwd
    f = (H / 2.0) / math.tan(math.radians(view["fov"]) / 2.0)
    czs = np.where(np.abs(cz) < 1e-6, 1e-6, cz)
    return W / 2.0 + f * cx / czs, H / 2.0 - f * cy / czs, cz


# ---------------------------------------------------------------- raster
def raster(view, batches, title, cull=True):
    W, H = RES
    color = np.zeros((H, W, 3), dtype=np.float32)
    color[:] = SKY
    zbuf = np.full((H, W), np.inf)
    eye = np.array(view.get("eye", (0.0, 1e6, 0.0)))        # ortho: eye at +inf y
    ncull = ntri = 0

    for part, verts, uvs, tris in batches:
        sx, sy, dep = project(view, verts)
        tex = tex_for(part)
        for t in tris:
            i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
            if view["kind"] == "persp":
                if dep[i0] <= 0.05 or dep[i1] <= 0.05 or dep[i2] <= 0.05:
                    continue
                if "reach" in view:
                    cx3 = (verts[i0] + verts[i1] + verts[i2]) / 3.0
                    if np.linalg.norm(cx3 - np.array(view["at"])) > view["reach"]:
                        continue
            ntri += 1
            if cull:
                # THE GAME-EYE PASS (terrace_wall_strip convention, calibrated):
                # cull when the geometric normal faces away from the eye.
                a3, b3, c3 = verts[i0], verts[i1], verts[i2]
                fn = np.cross(b3 - a3, c3 - a3)
                to_eye = eye - (a3 + b3 + c3) / 3.0
                if float(fn @ to_eye) <= 0.0:
                    ncull += 1
                    continue
            x0f = min(sx[i0], sx[i1], sx[i2]); x1f = max(sx[i0], sx[i1], sx[i2])
            y0f = min(sy[i0], sy[i1], sy[i2]); y1f = max(sy[i0], sy[i1], sy[i2])
            if x1f < 0 or y1f < 0 or x0f > W - 1 or y0f > H - 1:
                continue
            area = ((sx[i1] - sx[i0]) * (sy[i2] - sy[i0])
                    - (sx[i2] - sx[i0]) * (sy[i1] - sy[i0]))
            if abs(area) < 1e-9:
                continue
            xa = max(int(x0f), 0); xb = min(int(math.ceil(x1f)), W - 1)
            ya = max(int(y0f), 0); yb = min(int(math.ceil(y1f)), H - 1)
            gx, gy = np.meshgrid(np.arange(xa, xb + 1), np.arange(ya, yb + 1))
            b0 = ((sx[i1] - sx[i2]) * (gy - sy[i2]) - (sy[i1] - sy[i2]) * (gx - sx[i2])) / -area
            b1 = ((sx[i2] - sx[i0]) * (gy - sy[i0]) - (sy[i2] - sy[i0]) * (gx - sx[i0])) / -area
            b2 = 1.0 - b0 - b1
            m = (b0 >= -1e-9) & (b1 >= -1e-9) & (b2 >= -1e-9)
            if not m.any():
                continue
            if view["kind"] == "persp":                     # perspective-correct
                iz = np.array([1.0 / dep[i0], 1.0 / dep[i1], 1.0 / dep[i2]])
                izp = b0 * iz[0] + b1 * iz[1] + b2 * iz[2]
                d = 1.0 / np.maximum(izp, 1e-12)
                pu = (b0 * uvs[i0, 0] * iz[0] + b1 * uvs[i1, 0] * iz[1]
                      + b2 * uvs[i2, 0] * iz[2]) * d
                pv = (b0 * uvs[i0, 1] * iz[0] + b1 * uvs[i1, 1] * iz[1]
                      + b2 * uvs[i2, 1] * iz[2]) * d
            else:
                d = b0 * dep[i0] + b1 * dep[i1] + b2 * dep[i2]
                pu = b0 * uvs[i0, 0] + b1 * uvs[i1, 0] + b2 * uvs[i2, 0]
                pv = b0 * uvs[i0, 1] + b1 * uvs[i1, 1] + b2 * uvs[i2, 1]
            zt = zbuf[ya:yb + 1, xa:xb + 1]
            vis = m & (d < zt)
            if not vis.any():
                continue
            sub = color[ya:yb + 1, xa:xb + 1]
            if tex is not None:
                sub[vis] = sample(tex, pu[vis], pv[vis])
            else:
                sub[vis] = (200, 60, 200)                   # missing texture = magenta
            zt[vis] = d[vis]

    img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8))
    OUTD.mkdir(parents=True, exist_ok=True)
    out = OUTD / f"{title}.png"
    img.save(out)
    print(f"   render {out.name}  tris={ntri} culled={ncull}")
    return np.asarray(img)


# ---------------------------------------------------------------- states
def state_src(tag):
    park = HERE / "out" / "vcorner_park"
    if tag == "live":
        return {}
    if tag == "baseline":                                   # == live (parked); explicit
        return {
            (5, 7, "Terrain"): BK / "Block[5][7] Terrain.ff9mesh.r7.20260802-025232",
            (5, 8, "Terrain"): BK / "Block[5][8] Terrain.ff9mesh.r8.20260802-025232",
            (5, 7, "Sea4"): park / "Block[5][7] Sea4.ff9mesh",
            (5, 8, "Sea4"): park / "Block[5][8] Sea4.ff9mesh",
        }
    if tag == "v1":
        return {
            (5, 7, "Terrain"): BK / "Block[5][7] Terrain.ff9mesh.r7.20260802-032654",
            (5, 8, "Terrain"): BK / "Block[5][8] Terrain.ff9mesh.r8.20260802-032654",
            (5, 7, "Sea4"): park / "Block[5][7] Sea4.ff9mesh",
            (5, 8, "Sea4"): park / "Block[5][8] Sea4.ff9mesh",
        }
    if tag == "v2":
        return {
            (5, 7, "Terrain"): BK / "Block[5][7] Terrain.ff9mesh.park.20260802-033102",
            (5, 8, "Terrain"): BK / "Block[5][8] Terrain.ff9mesh.park.20260802-033102",
            (5, 7, "Sea4"): BK / "Block[5][7] Sea4.ff9mesh.park.20260802-033102",
            (5, 8, "Sea4"): BK / "Block[5][8] Sea4.ff9mesh.park.20260802-033102",
        }
    raise SystemExit(f"unknown state {tag}")


# ---------------------------------------------------------------- diff
def diff(a, b, title, thresh=18):
    d = np.abs(a.astype(np.int32) - b.astype(np.int32)).max(axis=2)
    mask = d > thresh
    n = int(mask.sum())
    ys, xs = np.nonzero(mask)
    box = None if n == 0 else (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    print(f"   diff {title}: {n} px changed  box={box}")
    if n:
        vis = (a // 3).astype(np.uint8)
        vis[mask] = (255, 40, 40)
        Image.fromarray(vis).save(OUTD / f"diff_{title}.png")
    return n, box


# ---------------------------------------------------------------- verbs
def cmd_render(tag):
    src = state_src(tag)
    for p in src.values():
        assert p.is_file(), f"missing corpus file: {p}"
    batches = load_batches(src)
    nt = sum(len(t) for _, _, _, t in batches)
    print(f"[{tag}] {len(batches)} part batches, {nt} tris total")
    return {vn: raster(v, batches, f"{tag}_{vn}") for vn, v in VIEWS.items()}


def cmd_calibrate():
    imgs = {t: cmd_render(t) for t in ("baseline", "v1", "v2")}
    print("\n=== P-E determinism (baseline re-render) ===")
    b = load_batches(state_src("baseline"))
    for vn, v in VIEWS.items():
        r2 = raster(v, b, f"baseline2_{vn}")
        diff(imgs["baseline"][vn], r2, f"PE_{vn}", thresh=0)
    print("\n=== P-B/P-C/P-D: candidate vs baseline ===")
    for tag in ("v1", "v2"):
        for vn in VIEWS:
            diff(imgs["baseline"][vn], imgs[tag][vn], f"{tag}_{vn}")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == "render":
        cmd_render(sys.argv[2] if len(sys.argv) > 2 else "live")
    elif sys.argv[1] == "calibrate":
        cmd_calibrate()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
