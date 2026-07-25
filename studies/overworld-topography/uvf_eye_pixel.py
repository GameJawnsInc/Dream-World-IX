"""RUNG F -- THE PER-PIXEL EYE (UV-FIX calibration round, 2026-07-24).

The old offline eye (massif_face_render.py / rung_f_eye_panel.py) shades a triangle by ONE
aggregate/average color -- structurally blind to a UV-channel defect (a degenerate 3-vert UV still
has a perfectly normal average color). This eye instead rasterizes every Terrain/Sea triangle with
PER-PIXEL barycentric UV interpolation and BILINEAR atlas sampling, so a collapsed-UV tri renders as
one smeared texel (the flat-green-sheet defect) instead of disappearing into an average.

Renders three top-down plan views at the same world-unit scale:
  1. STOCK reference   -- the real junction blocks (13-15,11-12) (disc-1, from the install, read-only)
  2. SPECIMEN          -- out/rung_f/FF9CustomMap-world (the defective build; must SHOW the defect --
                           the calibration requirement)
  3. FIXED             -- out/rung_f/FF9CustomMap-world-FIXED (must NOT show it)
Plus one zoomed crop (block (1,17), 332/332 degenerate tris pre-fix) of specimen vs fixed for a close
inspection of the worst-hit block.

READ-ONLY vs the game install (atlas texture load + the stock reference blocks' own mesh bytes --
X.read_block is how every other script in this arc, incl. rung_f_falsify.py, reads a stock fallback).
NEVER touches the FF9CustomMap-world / FF9CustomMap-world-FIXED trees (read-only), never writes
outside out/rung_f/renders/uvfix/. No git.

Run:  py -X utf8 studies/overworld-topography/uvf_eye_pixel.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import mesh as M              # noqa: E402
from ff9mapkit.world import atlas as ATLAS         # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix"
SPECIMEN = OUT_DIR / "FF9CustomMap-world"
FIXED = OUT_DIR / "FF9CustomMap-world-FIXED"
REPORT = OUT_DIR / "uvf_eye_pixel_report.json"

SEA_PARTS = ("Sea4", "Sea1", "Sea2", "Sea3", "Sea5")   # draw order: deep-first, land-adjacent last
SEA_COLOR = {"Sea4": (24, 60, 130), "Sea1": (60, 130, 190), "Sea2": (60, 130, 190),
             "Sea3": (90, 160, 200), "Sea5": (90, 160, 200)}
SEA_ALPHA = {"Sea4": 235, "Sea1": 170, "Sea2": 170, "Sea3": 140, "Sea5": 140}

WORLD_BG = (18, 22, 34)   # off-map / uncovered canvas fill (dark slate, never confusable with grass/sea)


def log(m):
    print(m, flush=True)


# ----------------------------------------------------------------------------------------------
# mesh loaders
# ----------------------------------------------------------------------------------------------
def block_part_mesh(root, bx, by, part):
    """``root=None`` -> stock disc-1 (install, read-only). Else: the tree's own override if the file
    exists, falling back to stock disc-1 for any part the tree doesn't carry (exactly the fallback
    ``load_block_terr`` in rung_f_falsify.py uses for staged-vs-stock)."""
    if root is not None:
        p = root / M.override_relpath(1, bx, by, "0_1", part)
        if p.exists():
            try:
                return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=part.lower()), "override"
            except Exception as e:                        # noqa: BLE001
                log(f"  ! {p}: {e}")
                return None, None
    try:
        return X.read_block(bx, by, disc=1, part=part.lower()), "stock"
    except (ValueError, FileNotFoundError):
        return None, None


def block_tris(bm, bx, by):
    """[(world_x0,world_z0, world_x1,world_z1, world_x2,world_z2, uv0,uv1,uv2), ...] -- x/z only (top-down)."""
    ox, oz = X.block_world_origin(bx, by)
    verts, uvs = bm.verts, bm.uvs
    out = []
    for tri in bm.tris:
        w = [(verts[j][0] + ox, verts[j][2] + oz) for j in tri]
        uv = [(float(uvs[j][0]), float(uvs[j][1])) for j in tri] if uvs else [(0.0, 0.0)] * 3
        out.append((w, uv))
    return out


def gather_region(root, blocks):
    """{'terrain': [...], 'sea': [(part, [(w,uv), ...])]} for the block set, honest about misses."""
    terrain, sea, misses = [], [], []
    for (bx, by) in blocks:
        bm, src = block_part_mesh(root, bx, by, "Terrain")
        if bm is None:
            misses.append((bx, by, "Terrain"))
        else:
            terrain.append((bx, by, src, block_tris(bm, bx, by)))
        for part in SEA_PARTS:
            sbm, ssrc = block_part_mesh(root, bx, by, part)
            if sbm is None:
                continue
            sea.append((part, bx, by, ssrc, block_tris(sbm, bx, by)))
    return dict(terrain=terrain, sea=sea, misses=misses)


# ----------------------------------------------------------------------------------------------
# per-pixel rasterizer
# ----------------------------------------------------------------------------------------------
def sample_atlas_vec(atlas_np, u, v):
    """Bilinear atlas sample at vectorized UV arrays -> (N,4) float RGBA, U wraps, V flipped (Unity
    bottom-up -> array top-down), exactly massif_face_render.py's ``at_b`` vectorized."""
    AH, AW = atlas_np.shape[0], atlas_np.shape[1]
    fx = (u % 1.0) * AW - 0.5
    fy = (1.0 - (v % 1.0)) * AH - 0.5
    x0 = np.floor(fx).astype(np.int64)
    y0 = np.floor(fy).astype(np.int64)
    tx = (fx - x0).astype(np.float32)
    ty = (fy - y0).astype(np.float32)
    x0c = np.clip(x0, 0, AW - 1); x1c = np.clip(x0 + 1, 0, AW - 1)
    y0c = np.clip(y0, 0, AH - 1); y1c = np.clip(y0 + 1, 0, AH - 1)
    c00 = atlas_np[y0c, x0c].astype(np.float32)
    c10 = atlas_np[y0c, x1c].astype(np.float32)
    c01 = atlas_np[y1c, x0c].astype(np.float32)
    c11 = atlas_np[y1c, x1c].astype(np.float32)
    w00 = ((1 - tx) * (1 - ty))[:, None]
    w10 = (tx * (1 - ty))[:, None]
    w01 = ((1 - tx) * ty)[:, None]
    w11 = (tx * ty)[:, None]
    return c00 * w00 + c10 * w10 + c01 * w01 + c11 * w11


def raster_textured_tri(canvas, W, H, sx, sy, uv, atlas_np, stats=None):
    x0, x1 = int(np.floor(min(sx))), int(np.ceil(max(sx))) + 1
    y0, y1 = int(np.floor(min(sy))), int(np.ceil(max(sy))) + 1
    x0c, x1c = max(x0, 0), min(x1, W)
    y0c, y1c = max(y0, 0), min(y1, H)
    if x1c <= x0c or y1c <= y0c:
        return
    d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
    if abs(d) < 1e-9:
        return
    xs = np.arange(x0c, x1c) + 0.5
    ys = np.arange(y0c, y1c) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    w0 = ((sy[1] - sy[2]) * (gx - sx[2]) + (sx[2] - sx[1]) * (gy - sy[2])) / d
    w1 = ((sy[2] - sy[0]) * (gx - sx[2]) + (sx[0] - sx[2]) * (gy - sy[2])) / d
    w2 = 1.0 - w0 - w1
    mask = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not mask.any():
        return
    u = w0[mask] * uv[0][0] + w1[mask] * uv[1][0] + w2[mask] * uv[2][0]
    v = w0[mask] * uv[0][1] + w1[mask] * uv[1][1] + w2[mask] * uv[2][1]
    col = sample_atlas_vec(atlas_np, u, v)
    alpha = (col[:, 3:4] / 255.0)
    sub = canvas[y0c:y1c, x0c:x1c]
    subm = sub[mask]
    subm[:, :3] = subm[:, :3] * (1 - alpha) + col[:, :3] * alpha
    sub[mask] = subm
    canvas[y0c:y1c, x0c:x1c] = sub
    if stats is not None:
        stats["px"] += int(mask.sum())
        # degenerate-UV signature: all 3 verts' UV within 1e-6 of each other -> every sampled pixel
        # in this tri is the SAME texel (u,v constant across the tri) -- the flat-sheet defect.
        du = max(abs(uv[0][0] - uv[1][0]), abs(uv[1][0] - uv[2][0]), abs(uv[0][0] - uv[2][0]))
        dv = max(abs(uv[0][1] - uv[1][1]), abs(uv[1][1] - uv[2][1]), abs(uv[0][1] - uv[2][1]))
        if du < 1e-6 and dv < 1e-6:
            stats["degenerate_px"] += int(mask.sum())
            stats["degenerate_tris"] += 1
        stats["tris"] += 1


def raster_flat_tri(canvas, W, H, sx, sy, color, alpha255):
    x0, x1 = int(np.floor(min(sx))), int(np.ceil(max(sx))) + 1
    y0, y1 = int(np.floor(min(sy))), int(np.ceil(max(sy))) + 1
    x0c, x1c = max(x0, 0), min(x1, W)
    y0c, y1c = max(y0, 0), min(y1, H)
    if x1c <= x0c or y1c <= y0c:
        return
    d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
    if abs(d) < 1e-9:
        return
    xs = np.arange(x0c, x1c) + 0.5
    ys = np.arange(y0c, y1c) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    w0 = ((sy[1] - sy[2]) * (gx - sx[2]) + (sx[2] - sx[1]) * (gy - sy[2])) / d
    w1 = ((sy[2] - sy[0]) * (gx - sx[2]) + (sx[0] - sx[2]) * (gy - sy[2])) / d
    w2 = 1.0 - w0 - w1
    mask = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not mask.any():
        return
    a = alpha255 / 255.0
    sub = canvas[y0c:y1c, x0c:x1c]
    subm = sub[mask]
    subm[:, :3] = subm[:, :3] * (1 - a) + np.array(color, dtype=np.float32) * a
    sub[mask] = subm
    canvas[y0c:y1c, x0c:x1c] = sub


# ----------------------------------------------------------------------------------------------
# region render
# ----------------------------------------------------------------------------------------------
def render_region(name, region, atlas_np, *, sc, pad=2.0):
    blocks = sorted({(bx, by) for (bx, by, *_r) in region["terrain"]}
                     | {(bx, by) for (_p, bx, by, *_r) in region["sea"]})
    bxs = [b[0] for b in blocks]; bys = [b[1] for b in blocks]
    wx0, wx1 = min(bxs) * 64.0, (max(bxs) + 1) * 64.0
    wz0, wz1 = -(max(bys) + 1) * 64.0, -min(bys) * 64.0     # z0=south(most-negative) .. z1=north
    W = int((wx1 - wx0) * sc) + 1
    H = int((wz1 - wz0) * sc) + 1
    canvas = np.empty((H, W, 3), dtype=np.float32)
    canvas[:] = WORLD_BG

    def to_screen(w):
        return [(p[0] - wx0) * sc for p in w], [(wz1 - p[1]) * sc for p in w]

    for part, bx, by, src, tris in region["sea"]:
        col, al = SEA_COLOR[part], SEA_ALPHA[part]
        for (w, uv) in tris:
            sx, sy = to_screen(w)
            raster_flat_tri(canvas, W, H, sx, sy, col, al)

    stats = dict(tris=0, px=0, degenerate_tris=0, degenerate_px=0)
    for bx, by, src, tris in region["terrain"]:
        for (w, uv) in tris:
            sx, sy = to_screen(w)
            raster_textured_tri(canvas, W, H, sx, sy, uv, atlas_np, stats=stats)

    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RENDER_DIR / f"{name}.png"
    img.save(out_path)
    stats.update(name=name, blocks=blocks, W=W, H=H, sc=sc,
                 world_bbox=[wx0, wx1, wz0, wz1], out=str(out_path),
                 misses=region["misses"])
    log(f"  -> {out_path}  {W}x{H}px  tris={stats['tris']} degenerate_tris={stats['degenerate_tris']} "
        f"degenerate_px={stats['degenerate_px']} ({100.0*stats['degenerate_px']/max(1,stats['px']):.2f}% of drawn px)")
    return stats


def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)
    log(f"  atlas {atlas_img.size} mode={atlas_img.mode}")

    report = dict(atlas_size=list(atlas_img.size), regions={})

    JUNCTION = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
    FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]

    log("\n== STOCK reference: junction blocks (13-15,11-12) ==")
    reg_stock = gather_region(None, JUNCTION)
    report["regions"]["stock_junction"] = render_region("stock_junction", reg_stock, atlas_np, sc=6.0)

    log("\n== SPECIMEN: out/rung_f/FF9CustomMap-world, footprint (0-4,16-19) ==")
    reg_spec = gather_region(SPECIMEN, FOOTPRINT)
    report["regions"]["specimen_rungf"] = render_region("specimen_rungf", reg_spec, atlas_np, sc=6.0)

    log("\n== FIXED: out/rung_f/FF9CustomMap-world-FIXED, footprint (0-4,16-19) ==")
    reg_fix = gather_region(FIXED, FOOTPRINT)
    report["regions"]["fixed_rungf"] = render_region("fixed_rungf", reg_fix, atlas_np, sc=6.0)

    log("\n== ZOOM: block (1,17), specimen vs fixed (worst block, 332/332 degenerate pre-fix) ==")
    reg_spec_z = gather_region(SPECIMEN, [(1, 17)])
    report["regions"]["specimen_zoom_1_17"] = render_region("specimen_zoom_1_17", reg_spec_z, atlas_np, sc=16.0)
    reg_fix_z = gather_region(FIXED, [(1, 17)])
    report["regions"]["fixed_zoom_1_17"] = render_region("fixed_zoom_1_17", reg_fix_z, atlas_np, sc=16.0)

    report["elapsed_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"\nreport -> {REPORT}  ({report['elapsed_s']}s)")


if __name__ == "__main__":
    main()
