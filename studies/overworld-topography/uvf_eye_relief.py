"""RUNG F -- THE SHADED-RELIEF EYE (round 5 judgement, uvf_fix5.py, 2026-07-24).

Playtest 3 verdict on FIXED4: the family re-clothe worked ("they almost look gone") but the GEOMETRY
still betrays the dropped Cleyra roots -- radiating channel/cleft depressions, a raised terminal
face/nub at each channel's crater end, and local "dig spot" pits. All prior eyes (uvf_eye_pixel*.py)
are TOP-DOWN FLAT-LIT rasterizers: they answer "is the TEXTURE right" and are structurally blind to
"is the SHAPE right" -- a relief defect with correct color renders identically to lawful ground. This
script is the shape eye: it rasterizes the actual Terrain top-surface HEIGHT field (not just color) at
per-pixel resolution and renders it as oblique-lit hillshade + an orientation-independent slope-
magnitude map + a Laplacian roughness map, so a channel/nub/pit shows up as a bright streak regardless
of which way the light points.

CALIBRATION-FIRST (the standing law): every metric and every visual is measured on FIXED4 (playtest-
confirmed defective) BEFORE it is trusted on FIXED5. If the defect doesn't show on FIXED4, the eye is
not calibrated and FIXED5's "clean" reading is worthless.

Method:
  - one z-buffered raster pass over Terrain (top surface = MAX Y at each pixel, matching the DEM
    convention already used by uvf_relief_probe.py's _basin_dem) produces, per build, a HxW float32
    height field (NaN where uncovered) AND a per-pixel bilinear-sampled atlas color field (identical
    sampler to uvf_eye_pixel.sample_atlas_vec, reused verbatim for continuity with prior rounds).
  - hillshade: normal = normalize((-dh/dx, 1, -dh/dz)) from central-difference slopes in WORLD units
    (dh/dx = d(height)/d(col) * sc ; dh/dz = -d(height)/d(row) * sc, screen row grows south); shaded
    two ways -- a single oblique light (az=315 "NW", el=35) and a 4-azimuth MAX-hillshade (N/E/S/W)
    that cannot miss a channel just because it runs parallel to one light.
  - slope magnitude sqrt(dh/dx^2+dh/dz^2) and a discrete Laplacian |lap| are both ORIENTATION-
    INDEPENDENT relief metrics (no azimuth to dodge).
  - textured-and-shaded composite = atlas color * hillshade, the "what it actually looks like in the
    low sun" render.
  - height DIFF (FIXED5 - FIXED4), diverging colormap, checked against an AUTHORITATIVE changed-tri
    footprint mask (direct per-vertex Y diff of the two on-disk trees, rasterized independently of any
    prior report -- same method as uvf_eye_pixel4.py's footprint_diff) -- diff must be a subset.

READ-ONLY vs both artifact trees (FIXED4, FIXED5) and the game install (atlas + stock dunes reference).
Never writes outside out/rung_f/renders/uvfix5/. No git.

Run:  py -X utf8 studies/overworld-topography/uvf_eye_relief.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import atlas as ATLAS         # noqa: E402

import uvf_eye_pixel as E                          # noqa: E402  (block_part_mesh, sample_atlas_vec, raster_flat_tri)
import uvf_relief_probe as RP                       # noqa: E402  (reused verbatim: the kept-ground reference-plane fit)

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix5"
FIXED4 = OUT_DIR / "FF9CustomMap-world-FIXED4"
FIXED5 = OUT_DIR / "FF9CustomMap-world-FIXED5"
PROBE_JSON = OUT_DIR / "uvf_relief_probe.json"
REPORT = OUT_DIR / "uvf_eye_relief_report.json"

FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
UNTOUCHED_BLOCKS = [(0, 16), (1, 16), (4, 16), (0, 19), (4, 19)]          # fix5 report: 0 moved verts
STOCK_DUNES = [(18, 3), (18, 4), (19, 3), (19, 4), (20, 3)]               # real 273-cell dunes mass

CRATER_WORLD = (134.0, -1166.0)
BASIN_CENTER = (127.14, -1161.42)
BASIN_R = 7.92

SC = 10.0            # px / world unit for the master raster
CLOSE_R = 30.0        # crater-close crop radius (bowl + rim silhouette)
WEDGE_R = 145.0       # wedge-field crop radius (covers every clustered anomaly, farthest r_crater=122.8)

WORLD_BG = (18, 22, 34)
SEA_PARTS = E.SEA_PARTS
SEA_COLOR = E.SEA_COLOR
SEA_ALPHA = E.SEA_ALPHA


def log(m):
    print(m, flush=True)


# =================================================================================================
#  mesh -> xyz+uv triangles (adds Y to uvf_eye_pixel's xz-only block_tris)
# =================================================================================================
def block_tris_xyz(bm, bx, by):
    from ff9mapkit.world import extract as X
    ox, oz = X.block_world_origin(bx, by)
    verts, uvs = bm.verts, bm.uvs
    out = []
    for tri in bm.tris:
        w = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
        uv = [(float(uvs[j][0]), float(uvs[j][1])) for j in tri] if uvs else [(0.0, 0.0)] * 3
        out.append((w, uv))
    return out


def gather_xyz(root, blocks):
    terrain, sea, misses = [], [], []
    for (bx, by) in blocks:
        bm, src = E.block_part_mesh(root, bx, by, "Terrain")
        if bm is None:
            misses.append((bx, by, "Terrain"))
        else:
            terrain.append((bx, by, src, block_tris_xyz(bm, bx, by)))
        for part in SEA_PARTS:
            sbm, ssrc = E.block_part_mesh(root, bx, by, part)
            if sbm is None:
                continue
            sea.append((part, bx, by, ssrc, block_tris_xyz(sbm, bx, by)))
    return dict(terrain=terrain, sea=sea, misses=misses)


# =================================================================================================
#  z-buffered raster: color canvas + height field, top surface = MAX Y at each pixel
# =================================================================================================
def raster_zbuf_tri(canvas_color, canvas_h, covered, W, H, sx, sy, ys, uv, atlas_np, stats=None):
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
    ys_ = np.arange(y0c, y1c) + 0.5
    gx, gy = np.meshgrid(xs, ys_)
    w0 = ((sy[1] - sy[2]) * (gx - sx[2]) + (sx[2] - sx[1]) * (gy - sy[2])) / d
    w1 = ((sy[2] - sy[0]) * (gx - sx[2]) + (sx[0] - sx[2]) * (gy - sy[2])) / d
    w2 = 1.0 - w0 - w1
    mask = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not mask.any():
        return
    yfull = w0 * ys[0] + w1 * ys[1] + w2 * ys[2]
    ufull = w0 * uv[0][0] + w1 * uv[1][0] + w2 * uv[2][0]
    vfull = w0 * uv[0][1] + w1 * uv[1][1] + w2 * uv[2][1]

    sub_h = canvas_h[y0c:y1c, x0c:x1c]
    sub_cov = covered[y0c:y1c, x0c:x1c]
    win = mask & (~sub_cov | (yfull > sub_h))
    if not win.any():
        if stats is not None:
            stats["tris"] += 1
        return
    col = E.sample_atlas_vec(atlas_np, ufull[win], vfull[win])
    sub_h[win] = yfull[win]
    sub_cov[win] = True
    canvas_h[y0c:y1c, x0c:x1c] = sub_h
    covered[y0c:y1c, x0c:x1c] = sub_cov
    sub_c = canvas_color[y0c:y1c, x0c:x1c]
    subm = sub_c[win]
    subm[:, :3] = col[:, :3]
    sub_c[win] = subm
    canvas_color[y0c:y1c, x0c:x1c] = sub_c
    if stats is not None:
        stats["tris"] += 1
        stats["px"] += int(win.sum())


def rasterize(root, blocks, sc, atlas_np, *, wx0=None, wx1=None, wz0=None, wz1=None):
    """z-buffered top-surface height + color for `blocks`. Fixed bbox (wx0..wz1) lets two builds over
    the SAME block set share an identical pixel grid for a byte-comparable diff."""
    if wx0 is None:
        bxs = [b[0] for b in blocks]; bys = [b[1] for b in blocks]
        wx0, wx1 = min(bxs) * 64.0, (max(bxs) + 1) * 64.0
        wz0, wz1 = -(max(bys) + 1) * 64.0, -min(bys) * 64.0
    W = int(round((wx1 - wx0) * sc)) + 1
    H = int(round((wz1 - wz0) * sc)) + 1
    canvas_color = np.zeros((H, W, 3), dtype=np.float32)
    canvas_color[:] = WORLD_BG
    canvas_h = np.full((H, W), -1e9, dtype=np.float64)
    covered = np.zeros((H, W), dtype=bool)

    region = gather_xyz(root, blocks)

    def to_screen(w):
        return [(p[0] - wx0) * sc for p in w], [(wz1 - p[2]) * sc for p in w]

    for part, bx, by, src, tris in region["sea"]:
        col, al = SEA_COLOR[part], SEA_ALPHA[part]
        for (w, uv) in tris:
            sx, sy = to_screen(w)
            E.raster_flat_tri(canvas_color, W, H, sx, sy, col, al)

    stats = dict(tris=0, px=0)
    for bx, by, src, tris in region["terrain"]:
        for (w, uv) in tris:
            sx, sy = to_screen(w)
            ys = [w[0][1], w[1][1], w[2][1]]
            raster_zbuf_tri(canvas_color, canvas_h, covered, W, H, sx, sy, ys, uv, atlas_np, stats=stats)

    canvas_h[~covered] = np.nan
    return dict(color=np.clip(canvas_color, 0, 255).astype(np.uint8), height=canvas_h, covered=covered,
                W=W, H=H, sc=sc, wx0=wx0, wx1=wx1, wz0=wz0, wz1=wz1, stats=stats, misses=region["misses"])


# =================================================================================================
#  relief math -- hillshade / slope magnitude / Laplacian roughness (all orientation-robust variants)
# =================================================================================================
def _filled_height(canvas):
    h, cov = canvas["height"], canvas["covered"]
    if cov.all():
        return h.copy()
    fill_val = float(np.nanmean(h)) if cov.any() else 0.0
    out = np.where(cov, h, fill_val)
    return out


def slopes(canvas, vexag=1.0):
    """(slope_x, slope_z) = d(height)/d(world_x), d(height)/d(world_z), central differences.
    vexag>1 vertically exaggerates the height field before differencing -- standard relief-mapping
    practice for revealing sub-unit ripples a physically-true 1x hillshade underplays."""
    hf = _filled_height(canvas) * vexag
    sc = canvas["sc"]
    dh_dcol = np.gradient(hf, axis=1)
    dh_drow = np.gradient(hf, axis=0)
    slope_x = dh_dcol * sc                # d(world_x)/d(col) = 1/sc -> dh/dwx = dh/dcol * sc
    slope_z = -dh_drow * sc               # screen row grows as world_z SHRINKS -> extra minus sign
    return slope_x, slope_z


def hillshade(canvas, az_deg, el_deg, ambient=0.20, vexag=1.0):
    slope_x, slope_z = slopes(canvas, vexag=vexag)
    az = math.radians(az_deg); el = math.radians(el_deg)
    Lx, Ly, Lz = math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)
    nlen = np.sqrt(slope_x ** 2 + 1.0 + slope_z ** 2)
    dot = (-slope_x * Lx + 1.0 * Ly + -slope_z * Lz) / nlen
    shade = np.clip(dot, 0.0, 1.0)
    return np.clip(ambient + (1.0 - ambient) * shade, 0.0, 1.0)


def hillshade_multi(canvas, el_deg=35.0, azimuths=(0, 90, 180, 270), vexag=1.0):
    """MAX over several azimuths -- a channel cannot hide by running parallel to a single light."""
    acc = None
    for az in azimuths:
        s = hillshade(canvas, az, el_deg, ambient=0.0, vexag=vexag)
        acc = s if acc is None else np.maximum(acc, s)
    return np.clip(0.20 + 0.80 * acc, 0.0, 1.0)


def slope_magnitude(canvas):
    slope_x, slope_z = slopes(canvas)
    return np.sqrt(slope_x ** 2 + slope_z ** 2)


def laplacian_roughness(canvas):
    hf = _filled_height(canvas)
    pad = np.pad(hf, 1, mode="edge")
    lap = (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:] - 4.0 * pad[1:-1, 1:-1])
    return np.abs(lap) * (canvas["sc"] ** 2)          # scale-independent-ish, world-unit curvature


# =================================================================================================
#  colorize / compose / save
# =================================================================================================
def gray_img(field01, covered, bg=WORLD_BG):
    g = np.clip(field01, 0, 1)
    out = np.empty(g.shape + (3,), dtype=np.uint8)
    v = (g * 255).astype(np.uint8)
    out[..., 0] = v; out[..., 1] = v; out[..., 2] = v
    out[~covered] = bg
    return out


def diverging_img(diff, covered, vmax, bg=WORLD_BG):
    """blue(negative) - white(0) - red(positive), clamped to +-vmax."""
    t = np.clip(diff / vmax, -1.0, 1.0)
    out = np.empty(diff.shape + (3,), dtype=np.float32)
    neg = t < 0
    pos = ~neg
    # negative: white(1,1,1) -> blue(20,60,200)
    a = np.abs(t)
    out[..., 0] = np.where(neg, 255 + a * (20 - 255), 255 + a * (210 - 255))
    out[..., 1] = np.where(neg, 255 + a * (60 - 255), 255 + a * (40 - 255))
    out[..., 2] = np.where(neg, 255 + a * (200 - 255), 255 + a * (30 - 255))
    out = np.clip(out, 0, 255).astype(np.uint8)
    out[~covered] = bg
    return out


def composite(color_u8, shade01, covered, bg=WORLD_BG):
    out = (color_u8.astype(np.float32) * shade01[..., None]).clip(0, 255).astype(np.uint8)
    out[~covered] = bg
    return out


def save(arr_u8, path):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr_u8, "RGB").save(path)
    return path


def crop_world(canvas, cx, cz, R):
    wx0, wz1, sc = canvas["wx0"], canvas["wz1"], canvas["sc"]
    col0 = int(round((cx - R - canvas["wx0"]) * sc)); col1 = int(round((cx + R - canvas["wx0"]) * sc))
    row0 = int(round((wz1 - (cz + R)) * sc)); row1 = int(round((wz1 - (cz - R)) * sc))
    col0c, col1c = max(0, col0), min(canvas["W"], col1)
    row0c, row1c = max(0, row0), min(canvas["H"], row1)
    return dict(col0=col0c, col1=col1c, row0=row0c, row1=row1c,
                wx0=wx0 + col0c / sc, wz1=wz1 - row0c / sc, sc=sc)


def crop_arr(arr, box):
    return arr[box["row0"]:box["row1"], box["col0"]:box["col1"]]


# =================================================================================================
#  quantitative sampling
# =================================================================================================
def sample_stats(field, covered, canvas, x, z, R):
    box = crop_world(canvas, x, z, R)
    sub = crop_arr(field, box)
    subc = crop_arr(covered, box)
    v = sub[subc]
    if v.size == 0:
        return dict(n=0)
    return dict(n=int(v.size), mean=round(float(np.mean(v)), 4), max=round(float(np.max(v)), 4),
                p90=round(float(np.percentile(v, 90)), 4), p99=round(float(np.percentile(v, 99)), 4),
                std=round(float(np.std(v)), 4))


def height_stats(canvas, x, z, R):
    box = crop_world(canvas, x, z, R)
    sub = crop_arr(canvas["height"], box)
    subc = crop_arr(canvas["covered"], box)
    v = sub[subc]
    if v.size == 0:
        return dict(n=0)
    return dict(n=int(v.size), mean=round(float(np.mean(v)), 4), min=round(float(np.min(v)), 4),
                max=round(float(np.max(v)), 4), std=round(float(np.std(v)), 4))


def height_at(canvas, x, z):
    """Nearest-pixel lookup into a rasterized top-surface height field -- an INDEPENDENT sample of the
    same mesh the probe read vertex-exact, via this eye's own z-buffer rasterizer."""
    col = int(round((x - canvas["wx0"]) * canvas["sc"]))
    row = int(round((canvas["wz1"] - z) * canvas["sc"]))
    col = min(max(col, 0), canvas["W"] - 1)
    row = min(max(row, 0), canvas["H"] - 1)
    if not canvas["covered"][row, col]:
        return None
    return float(canvas["height"][row, col])


# =================================================================================================
#  authoritative changed-tri footprint (independent of the fix5 build report; direct mesh re-diff)
# =================================================================================================
def changed_footprint_mask(canvas_shape_hw, wx0, wz1, sc, blocks):
    H, W = canvas_shape_hw
    mask = np.zeros((H, W), dtype=bool)
    reg_a = gather_xyz(FIXED4, blocks)
    reg_b = gather_xyz(FIXED5, blocks)
    ta = {(bx, by): tris for bx, by, src, tris in reg_a["terrain"]}
    tb = {(bx, by): tris for bx, by, src, tris in reg_b["terrain"]}
    n_changed = 0
    max_abs_dy = 0.0
    for k in ta:
        for (wa, uva), (wb, uvb) in zip(ta[k], tb[k]):
            ya = [p[1] for p in wa]; yb = [p[1] for p in wb]
            if any(abs(ya[i] - yb[i]) > 1e-6 for i in range(3)):
                n_changed += 1
                max_abs_dy = max(max_abs_dy, max(abs(ya[i] - yb[i]) for i in range(3)))
                sx = [(p[0] - wx0) * sc for p in wa]
                sy = [(wz1 - p[2]) * sc for p in wa]
                x0, x1 = int(np.floor(min(sx))) - 2, int(np.ceil(max(sx))) + 2
                y0, y1 = int(np.floor(min(sy))) - 2, int(np.ceil(max(sy))) + 2
                x0c, x1c = max(x0, 0), min(x1, W)
                y0c, y1c = max(y0, 0), min(y1, H)
                if x1c <= x0c or y1c <= y0c:
                    continue
                d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
                if abs(d) < 1e-9:
                    continue
                xs = np.arange(x0c, x1c) + 0.5
                ys_ = np.arange(y0c, y1c) + 0.5
                gx, gy = np.meshgrid(xs, ys_)
                w0 = ((sy[1] - sy[2]) * (gx - sx[2]) + (sx[2] - sx[1]) * (gy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (gx - sx[2]) + (sx[0] - sx[2]) * (gy - sy[2])) / d
                w2 = 1.0 - w0 - w1
                m = (w0 >= -0.08) & (w1 >= -0.08) & (w2 >= -0.08)
                sub = mask[y0c:y1c, x0c:x1c]; sub[m] = True; mask[y0c:y1c, x0c:x1c] = sub
    return mask, n_changed, max_abs_dy


# =================================================================================================
def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)
    log(f"  atlas {atlas_img.size} mode={atlas_img.mode}")

    probe = json.loads(PROBE_JSON.read_text(encoding="utf-8"))
    clusters = probe["stage4_mechanism"]["clusters"]
    wedge_clusters = [c for c in clusters if c["verdict"] != "BASIN(keep)"]
    basin_clusters = [c for c in clusters if c["verdict"] == "BASIN(keep)"]
    log(f"probe: {len(clusters)} clusters ({len(wedge_clusters)} wedge/channel/dig-spot, "
        f"{len(basin_clusters)} basin)")

    report = dict(meta=dict(script="uvf_eye_relief.py", crater_world=list(CRATER_WORLD),
                             basin_center=list(BASIN_CENTER), basin_r=BASIN_R, sc=SC,
                             n_wedge_clusters=len(wedge_clusters), n_basin_clusters=len(basin_clusters)))

    # ---- master rasters over the SAME fixed footprint bbox (byte-comparable pixel grid) -----------
    bxs = [b[0] for b in FOOTPRINT]; bys = [b[1] for b in FOOTPRINT]
    wx0f, wx1f = min(bxs) * 64.0, (max(bxs) + 1) * 64.0
    wz0f, wz1f = -(max(bys) + 1) * 64.0, -min(bys) * 64.0
    log(f"footprint bbox world x[{wx0f},{wx1f}] z[{wz0f},{wz1f}] @ sc={SC} -> "
        f"{int((wx1f-wx0f)*SC)+1}x{int((wz1f-wz0f)*SC)+1}px")

    log("\n== rasterizing FIXED4 footprint (Terrain z-buffer: color + height) ==")
    c4 = rasterize(FIXED4, FOOTPRINT, SC, atlas_np, wx0=wx0f, wx1=wx1f, wz0=wz0f, wz1=wz1f)
    log(f"  tris={c4['stats']['tris']} px={c4['stats']['px']} covered={int(c4['covered'].sum())}/"
        f"{c4['W']*c4['H']} misses={c4['misses']}")

    log("\n== rasterizing FIXED5 footprint ==")
    c5 = rasterize(FIXED5, FOOTPRINT, SC, atlas_np, wx0=wx0f, wx1=wx1f, wz0=wz0f, wz1=wz1f)
    log(f"  tris={c5['stats']['tris']} px={c5['stats']['px']} covered={int(c5['covered'].sum())}/"
        f"{c5['W']*c5['H']} misses={c5['misses']}")

    log("\n== rasterizing STOCK dunes reference (18,3)(18,4)(19,3)(19,4)(20,3) ==")
    cst = rasterize(None, STOCK_DUNES, SC, atlas_np)
    log(f"  tris={cst['stats']['tris']} covered={int(cst['covered'].sum())}/{cst['W']*cst['H']}")

    # ---- hillshades + relief metrics per build ------------------------------------------------
    VEXAG = 4.0     # standard relief-mapping vertical exaggeration -- reveals sub-unit ripples a
                    # physically-true 1x render underplays; used ONLY as a diagnostic overlay, never
                    # for the quantitative residual metric (which works in true world units).
    shades = {}
    for tag, c in (("fixed4", c4), ("fixed5", c5), ("stock_dunes", cst)):
        sh_nw = hillshade(c, 315.0, 35.0)
        sh_multi = hillshade_multi(c)
        sh_nw_ex = hillshade(c, 315.0, 35.0, vexag=VEXAG)
        sh_multi_ex = hillshade_multi(c, vexag=VEXAG)
        sm = slope_magnitude(c)
        lap = laplacian_roughness(c)
        shades[tag] = dict(nw=sh_nw, multi=sh_multi, nw_ex=sh_nw_ex, multi_ex=sh_multi_ex, slope=sm, lap=lap)

    # ---- FULL FOOTPRINT renders (fixed4, fixed5) -----------------------------------------------
    log("\n== full-footprint renders ==")
    for tag, c in (("fixed4", c4), ("fixed5", c5)):
        sh = shades[tag]
        save(gray_img(sh["nw"], c["covered"]), RENDER_DIR / f"{tag}_footprint_hillshade_nw.png")
        save(gray_img(sh["multi"], c["covered"]), RENDER_DIR / f"{tag}_footprint_hillshade_multi.png")
        smn = np.clip(sh["slope"] / 1.5, 0, 1)
        save(gray_img(smn, c["covered"]), RENDER_DIR / f"{tag}_footprint_slope_mag.png")
        save(composite(c["color"], sh["nw"], c["covered"]), RENDER_DIR / f"{tag}_footprint_textured_shaded.png")
    save(gray_img(np.clip(shades["stock_dunes"]["slope"] / 1.5, 0, 1), cst["covered"]),
         RENDER_DIR / "stock_dunes_slope_mag.png")
    save(gray_img(shades["stock_dunes"]["multi"], cst["covered"]), RENDER_DIR / "stock_dunes_hillshade_multi.png")
    save(composite(cst["color"], shades["stock_dunes"]["nw"], cst["covered"]), RENDER_DIR / "stock_dunes_textured_shaded.png")

    # ---- CRATER-CLOSE crops (bowl/rim silhouette identity) -------------------------------------
    log("\n== crater-close crops (r=%su around %s) ==" % (CLOSE_R, BASIN_CENTER))
    box_close = crop_world(c4, *BASIN_CENTER, CLOSE_R)
    for tag, c in (("fixed4", c4), ("fixed5", c5)):
        sh = shades[tag]
        save(gray_img(crop_arr(sh["multi"], box_close), crop_arr(c["covered"], box_close)),
             RENDER_DIR / f"{tag}_crater_close_hillshade_multi.png")
        save(gray_img(crop_arr(sh["multi_ex"], box_close), crop_arr(c["covered"], box_close)),
             RENDER_DIR / f"{tag}_crater_close_hillshade_multi_exag4x.png")
        save(composite(crop_arr(c["color"], box_close), crop_arr(sh["nw"], box_close),
                        crop_arr(c["covered"], box_close)),
             RENDER_DIR / f"{tag}_crater_close_textured_shaded.png")

    # ---- WEDGE-FIELD crops (the whole donut, defect visibility) --------------------------------
    log("== wedge-field crops (r=%su) ==" % WEDGE_R)
    box_wedge = crop_world(c4, *CRATER_WORLD, WEDGE_R)
    for tag, c in (("fixed4", c4), ("fixed5", c5)):
        sh = shades[tag]
        save(gray_img(crop_arr(sh["multi"], box_wedge), crop_arr(c["covered"], box_wedge)),
             RENDER_DIR / f"{tag}_wedge_field_hillshade_multi.png")
        save(gray_img(crop_arr(sh["multi_ex"], box_wedge), crop_arr(c["covered"], box_wedge)),
             RENDER_DIR / f"{tag}_wedge_field_hillshade_multi_exag4x.png")
        save(gray_img(crop_arr(np.clip(sh["slope"] / 1.5, 0, 1), box_wedge), crop_arr(c["covered"], box_wedge)),
             RENDER_DIR / f"{tag}_wedge_field_slope_mag.png")
        save(composite(crop_arr(c["color"], box_wedge), crop_arr(sh["nw"], box_wedge),
                        crop_arr(c["covered"], box_wedge)),
             RENDER_DIR / f"{tag}_wedge_field_textured_shaded.png")

    # ---- side-by-side panels --------------------------------------------------------------------
    def hstack(paths, out_name, gap=8):
        ims = [Image.open(p).convert("RGB") for p in paths]
        h = max(im.height for im in ims)
        w = sum(im.width for im in ims) + gap * (len(ims) - 1)
        canvas = Image.new("RGB", (w, h), (18, 22, 34))
        x = 0
        for im in ims:
            canvas.paste(im, (x, 0)); x += im.width + gap
        canvas.save(RENDER_DIR / out_name)
        return RENDER_DIR / out_name

    panel_wedge_hillshade = hstack(
        [RENDER_DIR / "fixed4_wedge_field_hillshade_multi.png", RENDER_DIR / "fixed5_wedge_field_hillshade_multi.png"],
        "panel_wedge_hillshade_fixed4_vs_fixed5.png")
    panel_wedge_slope = hstack(
        [RENDER_DIR / "fixed4_wedge_field_slope_mag.png", RENDER_DIR / "fixed5_wedge_field_slope_mag.png"],
        "panel_wedge_slope_fixed4_vs_fixed5.png")
    panel_wedge_textured = hstack(
        [RENDER_DIR / "fixed4_wedge_field_textured_shaded.png", RENDER_DIR / "fixed5_wedge_field_textured_shaded.png"],
        "panel_wedge_textured_fixed4_vs_fixed5.png")
    panel_close = hstack(
        [RENDER_DIR / "fixed4_crater_close_hillshade_multi.png", RENDER_DIR / "fixed5_crater_close_hillshade_multi.png"],
        "panel_crater_close_hillshade_fixed4_vs_fixed5.png")
    panel_close_tex = hstack(
        [RENDER_DIR / "fixed4_crater_close_textured_shaded.png", RENDER_DIR / "fixed5_crater_close_textured_shaded.png"],
        "panel_crater_close_textured_fixed4_vs_fixed5.png")
    panel_ref = hstack(
        [RENDER_DIR / "fixed5_wedge_field_hillshade_multi.png", RENDER_DIR / "stock_dunes_hillshade_multi.png"],
        "panel_fixed5_vs_stock_dunes_hillshade.png")
    log(f"panels -> {panel_wedge_hillshade.name}, {panel_wedge_slope.name}, {panel_wedge_textured.name}, "
        f"{panel_close.name}, {panel_close_tex.name}, {panel_ref.name}")

    # ---- HEIGHT DIFF (fixed5 - fixed4) + authoritative changed-tri footprint subset check -------
    log("\n== height diff FIXED5 - FIXED4 (footprint grid) ==")
    both_cov = c4["covered"] & c5["covered"]
    diff = np.where(both_cov, c5["height"] - c4["height"], 0.0)
    diff_img = diverging_img(diff, both_cov, vmax=2.6)
    save(diff_img, RENDER_DIR / "footprint_height_diff_fixed5_minus_fixed4.png")

    changed_mask, n_changed_tris, max_abs_dy_meas = changed_footprint_mask(
        (c4["H"], c4["W"]), wx0f, wz1f, SC, FOOTPRINT)
    diff_nonzero = both_cov & (np.abs(diff) > 0.01)
    n_diff_px = int(diff_nonzero.sum())
    n_outside = int((diff_nonzero & ~changed_mask).sum())
    n_footprint_px = int(changed_mask.sum())
    log(f"  changed tris (direct mesh re-diff, independent of fix5 report): {n_changed_tris}, "
        f"max|dY| measured here = {max_abs_dy_meas:.4f}")
    log(f"  diff px (|dY|>0.01): {n_diff_px}  changed-tri footprint px: {n_footprint_px}  "
        f"OUTSIDE the footprint: {n_outside}")

    # overlay: diff outside the footprint highlighted in magenta on the fixed5 hillshade (should be
    # visually empty if n_outside==0)
    overlay = gray_img(shades["fixed5"]["multi"], c5["covered"]).copy()
    outside_mask = diff_nonzero & ~changed_mask
    overlay[outside_mask] = [255, 0, 255]
    save(overlay, RENDER_DIR / "diff_outside_footprint_overlay_magenta.png")

    # crater-exclusion check: diff inside the basin disc (+ its own 25u 59-decal-footprint halo is NOT
    # re-derived here -- the plain disc is the strict, cheap, honest bound the eye can check itself)
    yy, xx = np.mgrid[0:c4["H"], 0:c4["W"]]
    all_wx = wx0f + xx / SC
    all_wz = wz1f - yy / SC
    in_basin_disc = ((all_wx - BASIN_CENTER[0]) ** 2 + (all_wz - BASIN_CENTER[1]) ** 2) <= BASIN_R ** 2
    diff_in_basin = diff_nonzero & in_basin_disc
    n_basin_diff = int(diff_in_basin.sum())
    n_basin_px = int((in_basin_disc & both_cov).sum())
    log(f"  basin disc (r={BASIN_R}u around {BASIN_CENTER}): {n_basin_px} covered px, "
        f"{n_basin_diff} differ -- should be 0")

    report["height_diff"] = dict(
        vmax_colormap=2.6, n_diff_px_gt_0p01=n_diff_px,
        n_changed_tris_direct_mesh_diff=n_changed_tris, max_abs_dY_measured_here=round(max_abs_dy_meas, 4),
        n_changed_tri_footprint_px=n_footprint_px, n_diff_px_outside_footprint=n_outside,
        diff_localizes_to_changed_tris=(n_outside == 0),
        n_basin_disc_covered_px=n_basin_px, n_basin_disc_diff_px=n_basin_diff,
        basin_disc_untouched=(n_basin_diff == 0),
        overlay="diff_outside_footprint_overlay_magenta.png", diff_png="footprint_height_diff_fixed5_minus_fixed4.png",
        method="diff pixel-mask required to be a subset of an INDEPENDENT per-vertex-Y-diff mesh re-raster "
               "(not the fix5 build report), same zero-tolerance-subset method as uvf_eye_pixel4.py.")

    # ---- CALIBRATION-FIRST: reference-plane residual at each cluster site, an INDEPENDENT re-derivation
    #      of the probe's own anomaly definition (kept-ground plane fit) sampled through THIS eye's own
    #      z-buffer rasterizer instead of the probe's vertex-exact reader. A small-window local-slope
    #      metric was tried first and FAILED to calibrate (936/937 movable positions sit on a dead-FLAT
    #      land_height=3.0 sheet pre-fix -- zero *internal* slope; the defect is a STEP relative to the
    #      surrounding kept ground, not a ripple inside the fill itself, so only a reference-relative
    #      residual sees it). Kept in the report as `local_slope_window_probe_FAILED_see_note` for the
    #      record of what doesn't work.
    log("\n== reference-plane residuals at cluster sites (reusing uvf_relief_probe's own kept-ground fit) ==")
    rp_scratch = {}
    rp_touched, rp_f4_meshes, rp_defective, rp_synth_key, rp_prov_of, rp_pos_entries, rp_pinned, rp_movable = \
        RP.stage1(rp_scratch)
    _rp_ground_pos, rp_ghash, rp_samples = RP.stage2(rp_scratch, rp_touched, rp_f4_meshes, rp_synth_key)

    def ref_h(x, z):
        yhat, _diag = RP.ref_at(rp_ghash, rp_samples, x, z)
        return yhat

    cluster_rows = []
    for c in wedge_clusters:
        px, pz = c["peak_world"][0], c["peak_world"][2]
        cx, cz = c["centroid_world"][0], c["centroid_world"][1]
        yhat_peak = ref_h(px, pz)
        yhat_cent = ref_h(cx, cz)
        h4_peak, h5_peak = height_at(c4, px, pz), height_at(c5, px, pz)
        h4_cent, h5_cent = height_at(c4, cx, cz), height_at(c5, cx, cz)
        res4 = (h4_peak - yhat_peak) if (h4_peak is not None and yhat_peak is not None) else None
        res5 = (h5_peak - yhat_peak) if (h5_peak is not None and yhat_peak is not None) else None
        res4c = (h4_cent - yhat_cent) if (h4_cent is not None and yhat_cent is not None) else None
        res5c = (h5_cent - yhat_cent) if (h5_cent is not None and yhat_cent is not None) else None
        R = max(6.0, c.get("extent_major_u", 6.0) / 2.0 + 5.0)
        s4 = sample_stats(shades["fixed4"]["slope"], c4["covered"], c4, px, pz, R)
        s5 = sample_stats(shades["fixed5"]["slope"], c5["covered"], c5, px, pz, R)
        cluster_rows.append(dict(
            verdict=c["verdict"], sign=c["sign"], peak_world=[px, pz], r_crater=c["r_crater_min"],
            peak_residual_probe=c["peak_residual"], window_R_u=round(R, 2),
            residual_peak_fixed4_this_eye=round(res4, 3) if res4 is not None else None,
            residual_peak_fixed5_this_eye=round(res5, 3) if res5 is not None else None,
            residual_centroid_fixed4_this_eye=round(res4c, 3) if res4c is not None else None,
            residual_centroid_fixed5_this_eye=round(res5c, 3) if res5c is not None else None,
            slope_max_in_window_fixed4=s4.get("max"), slope_max_in_window_fixed5=s5.get("max"),
            slope_p90_in_window_fixed4=s4.get("p90"), slope_p90_in_window_fixed5=s5.get("p90")))

    # basin cluster (must stay ~unchanged -- the crater is kept, not relaxed)
    basin_rows = []
    for c in basin_clusters:
        px, pz = c["peak_world"][0], c["peak_world"][2]
        yhat = ref_h(px, pz)
        h4, h5 = height_at(c4, px, pz), height_at(c5, px, pz)
        basin_rows.append(dict(peak_world=[px, pz],
                                residual_fixed4_this_eye=round(h4 - yhat, 3) if (h4 is not None and yhat is not None) else None,
                                residual_fixed5_this_eye=round(h5 - yhat, 3) if (h5 is not None and yhat is not None) else None,
                                height_fixed4=h4, height_fixed5=h5))

    # untouched-block control ("quiet sand", 0 moved verts per the fix5 report) -- residual should be
    # small on BOTH builds (it is genuinely lawful kept ground, not fill). A single block-CENTER sample
    # is unreliable -- 4/5 of these are coastal corner blocks whose exact center is open sea (uncovered).
    # Sample a 7x7 grid across each block's interior instead and average over whatever land it hits.
    control_rows = []
    for (bx, by) in UNTOUCHED_BLOCKS:
        bcx, bcz = bx * 64.0 + 32.0, -(by * 64.0 + 32.0)
        pts_res = []
        for gi in range(7):
            for gj in range(7):
                gx = bx * 64.0 + 6.0 + gi * (52.0 / 6.0)
                gz = -(by * 64.0 + 6.0 + gj * (52.0 / 6.0))
                h4g = height_at(c4, gx, gz)
                if h4g is None:
                    continue
                yhg = ref_h(gx, gz)
                if yhg is None:
                    continue
                pts_res.append(h4g - yhg)
        control_rows.append(dict(block=[bx, by], center=[bcx, bcz], n_land_samples=len(pts_res),
                                  residual_fixed4_mean=round(float(np.mean(pts_res)), 4) if pts_res else None,
                                  residual_fixed4_abs_mean=round(float(np.mean(np.abs(pts_res))), 4) if pts_res else None))

    res4_all = [r["residual_peak_fixed4_this_eye"] for r in cluster_rows if r["residual_peak_fixed4_this_eye"] is not None]
    res5_all = [r["residual_peak_fixed5_this_eye"] for r in cluster_rows if r["residual_peak_fixed5_this_eye"] is not None]
    control_res_all = []
    for r in control_rows:
        if r["n_land_samples"]:
            control_res_all.append(r["residual_fixed4_abs_mean"])
    control_abs_mean = float(np.mean(control_res_all)) if control_res_all else None
    wedge_abs4 = float(np.mean(np.abs(res4_all))) if res4_all else None
    wedge_abs5 = float(np.mean(np.abs(res5_all))) if res5_all else None
    n_probe_match = sum(1 for c, r in zip(wedge_clusters, cluster_rows)
                         if r["residual_peak_fixed4_this_eye"] is not None
                         and abs(r["residual_peak_fixed4_this_eye"] - c["peak_residual"]) < 0.35)
    calibration_ok = (wedge_abs4 is not None and control_abs_mean is not None
                       and wedge_abs4 > 3.0 * control_abs_mean and wedge_abs4 > 0.8)
    n_dropped_to_lt_half = sum(1 for r in cluster_rows
                                if r["residual_peak_fixed4_this_eye"] is not None
                                and r["residual_peak_fixed5_this_eye"] is not None
                                and abs(r["residual_peak_fixed5_this_eye"]) < 0.5 * abs(r["residual_peak_fixed4_this_eye"]))

    report["calibration"] = dict(
        method="residual = THIS EYE's own rasterized top-surface height minus the SAME kept-ground "
               "reference-plane fit uvf_relief_probe.py uses (RP.stage2/ref_at, imported and called "
               "verbatim -- not re-implemented), sampled at each cluster's peak/centroid world position "
               "through an independent z-buffer rasterizer. This is the exact quantity 'anomalous' was "
               "originally defined by, cross-checked through different code.",
        n_clusters_where_this_eyes_fixed4_residual_matches_probe_within_0p35=f"{n_probe_match}/{len(wedge_clusters)}",
        control_untouched_blocks_residual=control_rows,
        control_abs_residual_mean=round(control_abs_mean, 4) if control_abs_mean else None,
        wedge_cluster_abs_residual_mean_fixed4=round(wedge_abs4, 4) if wedge_abs4 else None,
        wedge_cluster_abs_residual_mean_fixed5=round(wedge_abs5, 4) if wedge_abs5 else None,
        calibration_saw_fixed4_relief=calibration_ok,
        n_wedge_clusters_residual_dropped_below_half_on_fixed5=n_dropped_to_lt_half,
        n_wedge_clusters_total=len(cluster_rows),
        rule="calibration passes iff mean(|residual| at wedge-cluster peaks, FIXED4) exceeds both 3x the "
             "untouched-block control baseline AND an absolute 0.8u floor -- i.e. this eye's OWN "
             "rasterization, through an independently-fit reference, actually reproduces the reported "
             "defect before FIXED5 is judged.",
        local_slope_window_probe_FAILED_see_note=(
            "an earlier version of this calibration used mean/max slope-magnitude in a small window "
            "around each cluster peak; it measured FIXED4 wedge-site slope 0.173 vs an untouched-block "
            "control of 0.150 (FAILED to calibrate) because most fill vertices sit mid-plateau on a "
            "perfectly flat land_height=3.0 sheet -- locally zero slope even though the sheet as a whole "
            "sits well off the smooth reference. Superseded by the reference-plane residual above."))
    report["cluster_rows"] = cluster_rows
    report["basin_rows"] = basin_rows
    log(f"  probe cross-match (this eye's FIXED4 residual vs probe's peak_residual, tol 0.35u): "
        f"{n_probe_match}/{len(wedge_clusters)}")
    log(f"  control |residual| mean (5 untouched blocks): {control_abs_mean:.4f}" if control_abs_mean else "")
    log(f"  wedge-cluster |residual| mean FIXED4={wedge_abs4:.4f} -> FIXED5={wedge_abs5:.4f}"
        if wedge_abs4 and wedge_abs5 else "")
    log(f"  CALIBRATION {'PASSED' if calibration_ok else 'FAILED'}")
    log(f"  clusters whose |residual| dropped below half on fixed5: {n_dropped_to_lt_half}/{len(cluster_rows)}")

    # ---- rim/bowl silhouette identity -- NOT a guessed concentric ring (an earlier version centered a
    #      ring on CRATER_WORLD (134,-1166), 8.25u off the actual basin centroid (127.14,-1161.42), and
    #      it crossed genuine wedge fill -> a false "rim changed" reading of 1.39u). The honest test:
    #      KEPT terrain (outside the independently-measured changed-tri footprint) near the crater must
    #      be BYTE-IDENTICAL between builds -- no ring geometry to get wrong.
    NEAR_R = 25.0
    near_crater = (((all_wx - BASIN_CENTER[0]) ** 2 + (all_wz - BASIN_CENTER[1]) ** 2) <= NEAR_R ** 2)
    kept_near_crater = near_crater & both_cov & ~changed_mask
    bowl_mask = in_basin_disc & both_cov
    kept_delta = (c5["height"][kept_near_crater] - c4["height"][kept_near_crater]) if kept_near_crater.any() else np.array([])
    report["rim_bowl_identity"] = dict(
        method="kept (non-changed-tri) terrain within 25u of the basin centroid must be BYTE-IDENTICAL "
               "between FIXED4 and FIXED5 -- this IS the rim/bowl silhouette (the crater walls and floor "
               "the eye/owner see are either PINNED kept content or the pinned basin-floor fill; the ring-"
               "guess approach used here in an earlier draft mis-centered on CRATER_WORLD instead of the "
               "actual basin and produced a false 1.39u 'rim changed' reading -- retracted, replaced).",
        n_kept_px_within_25u_of_basin=int(kept_near_crater.sum()),
        max_abs_delta_kept_near_crater=round(float(np.max(np.abs(kept_delta))), 6) if kept_delta.size else None,
        kept_near_crater_untouched=bool(kept_delta.size == 0 or np.max(np.abs(kept_delta)) < 1e-4),
        bowl_height_fixed4=dict(mean=round(float(np.mean(c4["height"][bowl_mask])), 4)) if bowl_mask.any() else None,
        bowl_height_fixed5=dict(mean=round(float(np.mean(c5["height"][bowl_mask])), 4)) if bowl_mask.any() else None,
        bowl_max_abs_height_delta=round(float(np.max(np.abs(c5["height"][bowl_mask] - c4["height"][bowl_mask]))), 6)
        if bowl_mask.any() else None)
    log(f"  rim/bowl identity: {kept_near_crater.sum()} kept px within 25u of basin, max|delta|="
        f"{report['rim_bowl_identity']['max_abs_delta_kept_near_crater']}")

    # ---- residual bump/flat-spot honesty pass (per-cluster, using the reference-plane residual) -----
    still_anom = [r for r in cluster_rows if r["residual_peak_fixed5_this_eye"] is not None
                  and abs(r["residual_peak_fixed5_this_eye"]) > max(3.0 * (control_abs_mean or 0.0), 0.6)]
    report["residual_honesty"] = dict(
        threshold_u=round(max(3.0 * (control_abs_mean or 0.0), 0.6), 4),
        n_wedge_clusters_still_anomalous_on_fixed5=len(still_anom),
        still_anomalous_clusters=still_anom,
        note="probe's own prediction (uvf_relief_probe stage6_solve_dryrun.unfixable_residual): 12 "
             "non-basin positions are fully-pinned (whole 1-ring kept content) and cannot move under "
             "ANY fill-only relax -- if any cluster above is one of those, that is carried relief, not "
             "a fix5 regression. See also stage4b_jutting_faces.fully_pinned_steep_faces in the probe.")
    log(f"  residual clusters still anomalous on fixed5 (|res|>{report['residual_honesty']['threshold_u']}u): "
        f"{len(still_anom)}/{len(cluster_rows)}")

    overall_verdict = dict(
        anomalies_gone=(n_dropped_to_lt_half == len(cluster_rows) and len(still_anom) == 0),
        crater_preserved=(report["rim_bowl_identity"]["kept_near_crater_untouched"] and
                           report["rim_bowl_identity"]["bowl_max_abs_height_delta"] is not None and
                           report["rim_bowl_identity"]["bowl_max_abs_height_delta"] < 1e-4),
        diff_localizes=report["height_diff"]["diff_localizes_to_changed_tris"],
        basin_disc_untouched=report["height_diff"]["basin_disc_untouched"],
        calibration_saw_fixed4_relief=calibration_ok)
    overall_verdict["all_green"] = all(overall_verdict.values())
    report["overall_verdict"] = overall_verdict
    log(f"\nOVERALL: {overall_verdict}")

    panel_wedge_hillshade_ex = hstack(
        [RENDER_DIR / "fixed4_wedge_field_hillshade_multi_exag4x.png",
         RENDER_DIR / "fixed5_wedge_field_hillshade_multi_exag4x.png"],
        "panel_wedge_hillshade_exag4x_fixed4_vs_fixed5.png")
    panel_close_ex = hstack(
        [RENDER_DIR / "fixed4_crater_close_hillshade_multi_exag4x.png",
         RENDER_DIR / "fixed5_crater_close_hillshade_multi_exag4x.png"],
        "panel_crater_close_hillshade_exag4x_fixed4_vs_fixed5.png")

    report["renders"] = dict(dir=str(RENDER_DIR),
                              panels=[panel_wedge_hillshade.name, panel_wedge_slope.name, panel_wedge_textured.name,
                                      panel_close.name, panel_close_tex.name, panel_ref.name,
                                      panel_wedge_hillshade_ex.name, panel_close_ex.name])
    report["elapsed_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\nreport -> {REPORT}  ({report['elapsed_s']}s)")


if __name__ == "__main__":
    main()
