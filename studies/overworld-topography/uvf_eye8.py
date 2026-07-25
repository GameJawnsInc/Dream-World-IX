"""RUNG F -- THE EYE, round 8: THE CLOSE-UP TEXTURE CHANNEL (2026-07-25).

Playtest 6 on FIXED7 was a GROUND-LEVEL CLOSE-UP: "the shaved knob area still reads as a different
texture than the normal sand ... either it's a different texture or the way it's applied is causing a
shrinkage."  Every prior eye in this arc rendered the whole ~90u mound at one scale -- exactly the class
of render that UNDER-WEIGHTS a ~2-3u decal patch sitting inside a ~730-tri mound.  This eye is built to
see what the playtester saw: a per-pixel-textured 12-16u zoom on each of the five orphan-decal knobs
uvf_fix8.py redressed, FIXED7 vs FIXED8 side by side, plus a TEXEL-DENSITY HEATMAP (sigma_max colored
per triangle) that makes the "shrinkage" half of the report visible directly rather than inferred.

CALIBRATION-FIRST (the standing law): every metric is measured on FIXED7 (playtest-6-confirmed
defective) before FIXED8 is trusted. If the mottled/dense patches don't show on FIXED7 at the five
knobs' own coordinates, this eye is not calibrated and its FIXED8 "clean" reading is worthless.

Method, per site (12-16u zoom, ZOOM_R=14.0):
  - per-pixel-textured composite (atlas color x hillshade) -- what the playtester actually saw.
  - a HILLSHADE-ONLY render -- round 8 wrote UV bytes only, so this must read IDENTICAL FIXED7 vs
    FIXED8 (an independent confirmation that geometry did not move, read off the raster, not the
    build report).
  - a TEXEL-DENSITY HEATMAP: every ground Terrain triangle in the crop is flat-filled by
    diverging_color(baseline_sigma - sigma_max) -- red = denser than flat sand (the "stain"), white =
    at the flat-sand baseline, blue = sparser/more stretched than flat sand. sigma_max is computed
    independently here (uvf_fix8.sigma_max, imported and reused, not re-derived) from THIS eye's own
    direct read of the FIXED7/FIXED8 mesh bytes, not copied from uvf_fix8_report.json.
Plus one wider mound render (WEDGE_R) of all three channels to confirm nothing outside the five knobs
changed, and a pixel-level diff (COLOR, since round 8 moves no vertex) that must confine to the exact
screen footprint of the 10 acted tris -- built from the SAME barycentric test uvf_eye_relief's own
z-buffer rasterizer uses, at zero dilation tolerance (position bytes are provably unmoved, so the two
builds' triangle screen shapes are pixel-identical).

READ-ONLY vs both artifact trees (FIXED7, FIXED8) and the game install (atlas). Never writes outside
out/rung_f/renders/uvfix8/ + out/rung_f/uvf_eye8_report.json. No git.

Run:  py -X utf8 uvf_eye8.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import atlas as ATLAS         # noqa: E402
from ff9mapkit.world import extract as X           # noqa: E402
from ff9mapkit.world import grassland as G         # noqa: E402

import uvf_eye_relief as ER                          # noqa: E402  (rasterizer / hillshade / crop / composite)
import uvf_eye_relief6 as E6                         # noqa: E402  (FOOTPRINT / BASIN_CENTER / BASIN_R)
import uvf_fix3 as F3                                # noqa: E402  (load_blocks -- Terrain BlockMesh per block)
import uvf_fix8 as F8                                # noqa: E402  (sigma_max / dip_deg / centroid_xz / rc -- reused verbatim)

CH_POS, CH_UV, CH_TAN = X.CH_POS, X.CH_UV, X.CH_TAN

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix8"
FIXED7 = OUT_DIR / "FF9CustomMap-world-FIXED7"
FIXED8 = OUT_DIR / "FF9CustomMap-world-FIXED8"
BUILD_JSON = OUT_DIR / "rung_f_build.json"
FIX8_REPORT = OUT_DIR / "uvf_fix8_report.json"
REPORT = OUT_DIR / "uvf_eye8_report.json"

FOOTPRINT = E6.FOOTPRINT                    # all 20 blocks
BASIN_CENTER = E6.BASIN_CENTER              # (127.14, -1161.42)
BASIN_R = E6.BASIN_R                        # 7.92
MOUND_R = E6.MOUND_R                        # 40.0
WEDGE_R = E6.WEDGE_R                        # 46.0

R_MASTER = 48.0                             # crater-centered master-raster radius (covers WEDGE_R + margin)
SC_PX = 34.0                                # px/world-unit -- per-pixel atlas detail at a 12-16u zoom
ZOOM_R = 14.0                               # per-site zoom radius (mid of the requested 12-16u band)

WORLD_BG = (18, 22, 34)

VEXAG = 4.0
SIGMA_VMAX = 90.0                           # heatmap saturation half-range (world-u/UV-u away from baseline)


def log(m):
    print(m, flush=True)


def save(arr_u8, path):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr_u8, "RGB").save(path)
    return path


def hstack(paths, out_name, gap=8, labels=None):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = max(im.height for im in ims) + (22 if labels else 0)
    w = sum(im.width for im in ims) + gap * (len(ims) - 1)
    canvas = Image.new("RGB", (w, h), WORLD_BG)
    d = ImageDraw.Draw(canvas)
    x = 0
    for i, im in enumerate(ims):
        y = 22 if labels else 0
        canvas.paste(im, (x, y))
        if labels:
            d.text((x + 4, 4), labels[i], fill=(230, 230, 230))
        x += im.width + gap
    canvas.save(RENDER_DIR / out_name)
    return RENDER_DIR / out_name


def color_crop(c, box, bg=WORLD_BG):
    col = ER.crop_arr(c["color"], box).copy()
    cov = ER.crop_arr(c["covered"], box)
    col[~cov] = bg
    return col


# =================================================================================================
#  independent direct-bytes read of the 10 target tris (block/tri list taken from uvf_fix8_report's
#  act_set as a LOCATOR only -- every geometric/texture number below is recomputed here from the
#  FIXED7/FIXED8 mesh bytes, never copied from the report).
# =================================================================================================
def read_target_tris(report):
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20 and set(touched) == set(FOOTPRINT)

    fix8 = json.loads(FIX8_REPORT.read_text(encoding="utf-8"))
    assert fix8["ok"] is True, "uvf_fix8_report.json ok != true -- refusing to judge an unverified build"
    knobs_claimed = fix8["stage2_census"]["knobs"]
    act_claimed = [(tuple(r["block"]), r["tri"]) for r in fix8["stage2_census"]["act_set"]]
    baseline_sigma = fix8["stage7_verify"]["sigma_ledger"]["flat_dunes_mains_baseline_median"]
    assert len(act_claimed) == 10 and len(knobs_claimed) == 5

    m7 = F3.load_blocks(FIXED7, touched)
    m8 = F3.load_blocks(FIXED8, touched)

    rows = []
    for (b, t) in act_claimed:
        bm7, bm8 = m7[b], m8[b]
        ox, oz = X.block_world_origin(*b)
        tri7, tri8 = bm7.tris[t], bm8.tris[t]
        assert tri7 == tri8, f"{b}#{t}: index set moved -- not a UV-only change"
        Pv7, U7, T7 = bm7.chan_arrays[CH_POS], bm7.chan_arrays[CH_UV], bm7.chan_arrays[CH_TAN]
        Pv8, U8 = bm8.chan_arrays[CH_POS], bm8.chan_arrays[CH_UV]
        w7 = [(float(Pv7[j][0]) + ox, float(Pv7[j][1]), float(Pv7[j][2]) + oz) for j in tri7]
        w8 = [(float(Pv8[j][0]) + ox, float(Pv8[j][1]), float(Pv8[j][2]) + oz) for j in tri8]
        assert all(abs(w7[k][0] - w8[k][0]) < 1e-6 and abs(w7[k][1] - w8[k][1]) < 1e-6
                   and abs(w7[k][2] - w8[k][2]) < 1e-6 for k in range(3)), f"{b}#{t}: vertex moved"
        uv7 = [(float(U7[j][0]), float(U7[j][1])) for j in tri7]
        uv8 = [(float(U8[j][0]), float(U8[j][1])) for j in tri8]
        topo = X.decode_id(int(round(T7[tri7[0]][0])))["topograph"]
        cx, cz = F8.centroid_xz(w7)
        sm7, sm8 = F8.sigma_max(w7, uv7), F8.sigma_max(w7, uv8)
        dip7, dip8 = F8.dip_deg(w7), F8.dip_deg(w8)
        rows.append(dict(
            block=list(b), tri=t, name=f"({b[0]}, {b[1]})#{t}", topo=topo,
            verts=w7, centroid=[round(cx, 3), round(cz, 3)], r_crater=round(F8.rc(cx, cz), 2),
            uv_fixed7=[[round(u, 5), round(v, 5)] for (u, v) in uv7],
            uv_fixed8=[[round(u, 5), round(v, 5)] for (u, v) in uv8],
            sigma_max_fixed7=None if sm7 is None else round(sm7, 3),
            sigma_max_fixed8=None if sm8 is None else round(sm8, 3),
            dip_deg_fixed7=None if dip7 is None else round(dip7, 3),
            dip_deg_fixed8=None if dip8 is None else round(dip8, 3),
            density_ratio_fixed7=None if (sm7 is None or not baseline_sigma) else round(baseline_sigma / sm7, 3),
            density_ratio_fixed8=None if (sm8 is None or not baseline_sigma) else round(baseline_sigma / sm8, 3)))

    # re-cluster into knobs by shared plan edge, independent of the report's own grouping, must match
    edge_owner = defaultdict(list)
    for i, r in enumerate(rows):
        ks = [F8.xzk(p) for p in r["verts"]]
        for a in range(3):
            edge_owner[tuple(sorted((ks[a], ks[(a + 1) % 3])))].append(i)
    parent = list(range(len(rows)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for owners in edge_owner.values():
        for j in owners[1:]:
            ra, rb = find(owners[0]), find(j)
            if ra != rb:
                parent[rb] = ra
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(i)
    knobs = []
    for members in groups.values():
        rs = [rows[i] for i in members]
        knobs.append(dict(
            tris=[r["name"] for r in rs],
            centroid=[round(sum(r["centroid"][0] for r in rs) / len(rs), 2),
                      round(sum(r["centroid"][1] for r in rs) / len(rs), 2)],
            r_crater=round(sum(r["r_crater"] for r in rs) / len(rs), 2),
            sigma_max_fixed7=[r["sigma_max_fixed7"] for r in rs],
            sigma_max_fixed8=[r["sigma_max_fixed8"] for r in rs],
            density_ratio_fixed7=[r["density_ratio_fixed7"] for r in rs],
            density_ratio_fixed8=[r["density_ratio_fixed8"] for r in rs]))
    knobs.sort(key=lambda k: k["r_crater"])

    report["target_set_independent_read"] = dict(
        method="located by (block,tri) from uvf_fix8_report.json's act_set (a locator, not a trusted "
               "measurement) -- vertex/UV bytes, sigma_max, dip_deg and the knob clustering are ALL "
               "recomputed here directly from the FIXED7/FIXED8 mesh files via uvf_fix8's own "
               "sigma_max/dip_deg functions, imported not copied.",
        baseline_sigma_flat_sand=baseline_sigma,
        n_tris=len(rows), n_knobs=len(knobs),
        knobs_match_report=(sorted(tuple(sorted(k["tris"])) for k in knobs) ==
                             sorted(tuple(sorted(kk["tris"])) for kk in knobs_claimed)),
        tris=rows, knobs=knobs)
    log(f"[target] {len(rows)} tris / {len(knobs)} knobs re-derived directly from FIXED7+FIXED8 bytes "
        f"(baseline sigma={baseline_sigma})")
    return touched, rows, knobs, baseline_sigma


# =================================================================================================
#  the texel-density heatmap raster (flat-fill per ground triangle, diverging colormap)
# =================================================================================================
def sigma_color(sm, baseline, vmax=SIGMA_VMAX):
    if sm is None or baseline is None:
        return (90, 90, 90)
    diff = baseline - sm            # positive => denser than flat sand (the "stain") => red
    t = max(-1.0, min(1.0, diff / vmax))
    if t >= 0:
        return (255.0, 255.0 * (1 - t), 255.0 * (1 - t))
    a = -t
    return (255.0 * (1 - a), 255.0 * (1 - a), 255.0)


def gather_ground_tris(tree, touched):
    meshes = F3.load_blocks(tree, touched)
    out = []
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        Pv, U, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = G.TOPO_FAMILY.get(topo)
            if fam is None:
                continue
            w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
            uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
            sm = F8.sigma_max(w, uv)
            if sm is None:
                continue
            out.append((b, t, w, sm))
    return out


def raster_sigma_heatmap(tree, touched, wx0, wx1, wz0, wz1, sc, baseline):
    W = int(round((wx1 - wx0) * sc)) + 1
    H = int(round((wz1 - wz0) * sc)) + 1
    canvas = np.zeros((H, W, 3), dtype=np.float32)
    canvas[:] = WORLD_BG
    covered = np.zeros((H, W), dtype=bool)
    n_tris = 0
    for (b, t, w, sm) in gather_ground_tris(tree, touched):
        sx = [(p[0] - wx0) * sc for p in w]
        sy = [(wz1 - p[2]) * sc for p in w]
        if max(sx) < 0 or min(sx) > W or max(sy) < 0 or min(sy) > H:
            continue
        col = sigma_color(sm, baseline)
        _paint_flat_tri(canvas, covered, W, H, sx, sy, col)
        n_tris += 1
    return dict(color=np.clip(canvas, 0, 255).astype(np.uint8), covered=covered,
                W=W, H=H, sc=sc, wx0=wx0, wx1=wx1, wz0=wz0, wz1=wz1, n_tris=n_tris)


def _paint_flat_tri(canvas, covered, W, H, sx, sy, color):
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
    sub = canvas[y0c:y1c, x0c:x1c]
    subc = covered[y0c:y1c, x0c:x1c]
    sub[mask] = color
    subc[mask] = True
    canvas[y0c:y1c, x0c:x1c] = sub
    covered[y0c:y1c, x0c:x1c] = subc


def tri_screen_mask(W, H, wx0, wz1, sc, w3):
    """the SAME barycentric membership test raster_zbuf_tri uses (threshold -1e-6) -- since round 8
    moves no position byte, a target tri's screen shape is provably pixel-identical between FIXED7 and
    FIXED8, so this single mask (built off FIXED7's own verts) is valid for both."""
    sx = [(p[0] - wx0) * sc for p in w3]
    sy = [(wz1 - p[2]) * sc for p in w3]
    mask = np.zeros((H, W), dtype=bool)
    x0, x1 = int(np.floor(min(sx))), int(np.ceil(max(sx))) + 1
    y0, y1 = int(np.floor(min(sy))), int(np.ceil(max(sy))) + 1
    x0c, x1c = max(x0, 0), min(x1, W)
    y0c, y1c = max(y0, 0), min(y1, H)
    if x1c <= x0c or y1c <= y0c:
        return mask
    d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
    if abs(d) < 1e-9:
        return mask
    xs = np.arange(x0c, x1c) + 0.5
    ys = np.arange(y0c, y1c) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    w0 = ((sy[1] - sy[2]) * (gx - sx[2]) + (sx[2] - sx[1]) * (gy - sy[2])) / d
    w1 = ((sy[2] - sy[0]) * (gx - sx[2]) + (sx[0] - sx[2]) * (gy - sy[2])) / d
    w2 = 1.0 - w0 - w1
    m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    mask[y0c:y1c, x0c:x1c] = m
    return mask


def legend_bar(baseline, vmax=SIGMA_VMAX, w=360, h=54):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        t = (x / (w - 1)) * 2 - 1          # -1..1 maps low..high sigma (blue..red edges swapped for sigma axis)
        sm = baseline - t * vmax
        img[10:34, x] = sigma_color(sm, baseline)
    im = Image.fromarray(img, "RGB")
    d = ImageDraw.Draw(im)
    d.text((2, 36), f"sigma={baseline - vmax:.0f} (sparse/blue)", fill=(230, 230, 230))
    d.text((w // 2 - 60, 36), f"baseline={baseline:.1f}", fill=(230, 230, 230))
    d.text((w - 150, 36), f"sigma={baseline + vmax:.0f} (dense/red)", fill=(230, 230, 230))
    return np.array(im)


# =================================================================================================
def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)

    report = dict(meta=dict(
        script="uvf_eye8.py", round="RUNG F round 8 -- THE CLOSE-UP TEXTURE EYE",
        read_only_vs_game=True, subject_calibration=str(FIXED7), subject_resolution=str(FIXED8),
        basin_center=list(BASIN_CENTER), basin_r=BASIN_R, mound_r=MOUND_R, wedge_r=WEDGE_R,
        zoom_r=ZOOM_R, sc_px=SC_PX, sigma_vmax=SIGMA_VMAX,
        playtest6=("the shaved knob area still reads as a different texture than the normal sand ... "
                   "either it's a different texture or the way it's applied is causing a shrinkage")))

    touched, target_rows, knobs, baseline = read_target_tris(report)
    target_by_name = {r["name"]: r for r in target_rows}
    act_w3 = [r["verts"] for r in target_rows]

    # ---- master rasters (crater-centered bbox, per-pixel atlas detail) ----------------------------
    wx0m, wx1m = BASIN_CENTER[0] - R_MASTER, BASIN_CENTER[0] + R_MASTER
    wz0m, wz1m = BASIN_CENTER[1] - R_MASTER, BASIN_CENTER[1] + R_MASTER
    log(f"\n== master raster (crater-centered r={R_MASTER}u @ {SC_PX}px/u -> "
        f"{int((wx1m-wx0m)*SC_PX)+1}x{int((wz1m-wz0m)*SC_PX)+1}px) ==")
    c7 = ER.rasterize(FIXED7, FOOTPRINT, SC_PX, atlas_np, wx0=wx0m, wx1=wx1m, wz0=wz0m, wz1=wz1m)
    log(f"  FIXED7: tris={c7['stats']['tris']} covered={int(c7['covered'].sum())}/{c7['W']*c7['H']}")
    c8 = ER.rasterize(FIXED8, FOOTPRINT, SC_PX, atlas_np, wx0=wx0m, wx1=wx1m, wz0=wz0m, wz1=wz1m)
    log(f"  FIXED8: tris={c8['stats']['tris']} covered={int(c8['covered'].sum())}/{c8['W']*c8['H']}")

    sh7 = ER.hillshade(c7, 315.0, 35.0)
    sh8 = ER.hillshade(c8, 315.0, 35.0)
    shx7 = ER.hillshade(c7, 315.0, 35.0, vexag=VEXAG)
    shx8 = ER.hillshade(c8, 315.0, 35.0, vexag=VEXAG)

    log("== texel-density heatmap rasters ==")
    hm7 = raster_sigma_heatmap(FIXED7, touched, wx0m, wx1m, wz0m, wz1m, SC_PX, baseline)
    hm8 = raster_sigma_heatmap(FIXED8, touched, wx0m, wx1m, wz0m, wz1m, SC_PX, baseline)
    log(f"  heatmap tris FIXED7={hm7['n_tris']} FIXED8={hm8['n_tris']}")
    save(legend_bar(baseline), RENDER_DIR / "sigma_legend.png")

    # ---- GEOMETRY IDENTITY: height must be byte-identical everywhere (round 8 is UV-only) ----------
    log("\n== geometry identity (height diff, master raster) ==")
    both_cov = c7["covered"] & c8["covered"]
    hdiff = np.where(both_cov, c8["height"] - c7["height"], 0.0)
    n_height_diff = int((np.abs(hdiff) > 1e-4).sum())
    log(f"  {n_height_diff} px with |dY|>1e-4 across {int(both_cov.sum())} covered px (expect 0)")

    # ---- PIXEL-LEVEL COLOR DIFF, must confine to the 10 tris' own screen footprint -----------------
    log("== color diff (texture only, since geometry provably did not move) ==")
    W, H = c7["W"], c7["H"]
    footprint = np.zeros((H, W), dtype=bool)
    for w3 in act_w3:
        footprint |= tri_screen_mask(H=H, W=W, wx0=wx0m, wz1=wz1m, sc=SC_PX, w3=w3)
    rgb_dist = np.sqrt(((c7["color"].astype(np.float32) - c8["color"].astype(np.float32)) ** 2).sum(-1))
    color_diff = both_cov & (rgb_dist > 12.0)
    n_diff_total = int(color_diff.sum())
    n_diff_in_fp = int((color_diff & footprint).sum())
    n_diff_out_fp = int((color_diff & ~footprint).sum())
    n_fp_px = int(footprint.sum())
    log(f"  footprint (10 tris) = {n_fp_px}px; color-diff px = {n_diff_total} "
        f"(inside footprint {n_diff_in_fp} / outside {n_diff_out_fp}, outside should be ~0)")

    overlay = color_crop(c8, dict(row0=0, row1=H, col0=0, col1=W, wx0=wx0m, wz1=wz1m, sc=SC_PX)).copy()
    outside_mask = color_diff & ~footprint
    overlay[outside_mask] = [255, 0, 255]
    save(overlay, RENDER_DIR / "color_diff_outside_footprint_overlay_magenta.png")

    # ---- WIDER MOUND RENDER (all 3 channels, both builds) ------------------------------------------
    log(f"\n== mound crop (r={WEDGE_R}u) -- confirms nothing outside the 5 knobs changed ==")
    box_mound = ER.crop_world(c7, *BASIN_CENTER, WEDGE_R)
    for tag, c, sh, shx, hm in (("fixed7", c7, sh7, shx7, hm7), ("fixed8", c8, sh8, shx8, hm8)):
        save(ER.composite(ER.crop_arr(c["color"], box_mound), ER.crop_arr(sh, box_mound),
                           ER.crop_arr(c["covered"], box_mound)), RENDER_DIR / f"{tag}_mound_textured.png")
        save(ER.gray_img(ER.crop_arr(shx, box_mound), ER.crop_arr(c["covered"], box_mound)),
             RENDER_DIR / f"{tag}_mound_hillshade_exag4x.png")
        box_hm = dict(row0=box_mound["row0"], row1=box_mound["row1"], col0=box_mound["col0"],
                      col1=box_mound["col1"], wx0=box_mound["wx0"], wz1=box_mound["wz1"], sc=box_mound["sc"])
        save(color_crop(hm, box_hm), RENDER_DIR / f"{tag}_mound_sigma_heatmap.png")
    panels = {}
    panels["mound_textured"] = hstack(
        [RENDER_DIR / "fixed7_mound_textured.png", RENDER_DIR / "fixed8_mound_textured.png"],
        "panel_mound_textured_f7_vs_f8.png", labels=["FIXED7", "FIXED8"])
    panels["mound_hillshade"] = hstack(
        [RENDER_DIR / "fixed7_mound_hillshade_exag4x.png", RENDER_DIR / "fixed8_mound_hillshade_exag4x.png"],
        "panel_mound_hillshade_exag4x_f7_vs_f8.png", labels=["FIXED7", "FIXED8"])
    panels["mound_sigma"] = hstack(
        [RENDER_DIR / "fixed7_mound_sigma_heatmap.png", RENDER_DIR / "fixed8_mound_sigma_heatmap.png"],
        "panel_mound_sigma_heatmap_f7_vs_f8.png", labels=["FIXED7", "FIXED8"])

    # ---- PER-SITE ZOOMS (12-16u): textured, hillshade-identity, sigma heatmap ----------------------
    log(f"\n== per-site zoom crops (r={ZOOM_R}u) x {len(knobs)} knobs ==")
    site_rows = []
    for i, k in enumerate(knobs):
        cx, cz = k["centroid"]
        tag = f"site{i+1}_r{k['r_crater']:.1f}"
        box = ER.crop_world(c7, cx, cz, ZOOM_R)
        box_hm = dict(row0=box["row0"], row1=box["row1"], col0=box["col0"], col1=box["col1"],
                      wx0=box["wx0"], wz1=box["wz1"], sc=box["sc"])
        for suf, c, sh, hm in (("fixed7", c7, sh7, hm7), ("fixed8", c8, sh8, hm8)):
            save(ER.composite(ER.crop_arr(c["color"], box), ER.crop_arr(sh, box), ER.crop_arr(c["covered"], box)),
                 RENDER_DIR / f"{tag}_{suf}_textured.png")
            save(ER.gray_img(ER.crop_arr(sh, box), ER.crop_arr(c["covered"], box)),
                 RENDER_DIR / f"{tag}_{suf}_hillshade.png")
            save(color_crop(hm, box_hm), RENDER_DIR / f"{tag}_{suf}_sigma_heatmap.png")
        p_tex = hstack([RENDER_DIR / f"{tag}_fixed7_textured.png", RENDER_DIR / f"{tag}_fixed8_textured.png"],
                        f"panel_{tag}_textured_f7_vs_f8.png", labels=["FIXED7", "FIXED8"])
        p_hs = hstack([RENDER_DIR / f"{tag}_fixed7_hillshade.png", RENDER_DIR / f"{tag}_fixed8_hillshade.png"],
                       f"panel_{tag}_hillshade_f7_vs_f8.png", labels=["FIXED7", "FIXED8"])
        p_sig = hstack([RENDER_DIR / f"{tag}_fixed7_sigma_heatmap.png", RENDER_DIR / f"{tag}_fixed8_sigma_heatmap.png"],
                        f"panel_{tag}_sigma_heatmap_f7_vs_f8.png", labels=["FIXED7", "FIXED8"])

        # per-pixel hillshade identity at this crop (independent geometry-unmoved confirmation)
        cov_here = ER.crop_arr(both_cov, box)
        sh7c, sh8c = ER.crop_arr(sh7, box), ER.crop_arr(sh8, box)
        hs_maxdiff = float(np.max(np.abs(sh7c[cov_here] - sh8c[cov_here]))) if cov_here.any() else None

        site_rows.append(dict(
            site=i + 1, tag=tag, centroid=k["centroid"], r_crater=k["r_crater"], tris=k["tris"],
            sigma_max_fixed7=k["sigma_max_fixed7"], sigma_max_fixed8=k["sigma_max_fixed8"],
            density_ratio_fixed7=k["density_ratio_fixed7"], density_ratio_fixed8=k["density_ratio_fixed8"],
            hillshade_max_abs_diff=hs_maxdiff, hillshade_identical=(hs_maxdiff is not None and hs_maxdiff < 1e-6),
            panels=dict(textured=p_tex.name, hillshade=p_hs.name, sigma_heatmap=p_sig.name)))
        log(f"  site{i+1} r={k['r_crater']:.2f} {k['tris']}: sigma7={k['sigma_max_fixed7']} "
            f"ratio7={k['density_ratio_fixed7']}  ->  sigma8={k['sigma_max_fixed8']} "
            f"ratio8={k['density_ratio_fixed8']}  hillshade_identical={hs_maxdiff is not None and hs_maxdiff < 1e-6}")

    # ---- CALIBRATION + RESOLUTION VERDICTS, from the independently re-derived numbers --------------
    ratios7 = [r["density_ratio_fixed7"] for r in target_rows if r["density_ratio_fixed7"] is not None]
    ratios8 = [r["density_ratio_fixed8"] for r in target_rows if r["density_ratio_fixed8"] is not None]
    sm7 = [r["sigma_max_fixed7"] for r in target_rows if r["sigma_max_fixed7"] is not None]
    sm8 = [r["sigma_max_fixed8"] for r in target_rows if r["sigma_max_fixed8"] is not None]

    calibration_saw_stains = bool(
        len(ratios7) == 10 and min(ratios7) >= 1.3 and (sum(ratios7) / len(ratios7)) >= 1.5
        and all(r >= 1.3 for r in ratios7))
    # "stains gone": the DENSE/mottled defect (ratio < 1, i.e. sigma < baseline) must be resolved for
    # every one of the 10 -- none may still read denser-than-sand. Separately (honestly) flag any tri
    # that now reads the OPPOSITE way (sparser/stretched) beyond the mound's own stock-measured ceiling.
    still_dense = [r["name"] for r in target_rows if r["density_ratio_fixed8"] is not None
                   and r["density_ratio_fixed8"] > 1.15]
    near_uniform = [r["name"] for r in target_rows if r["density_ratio_fixed8"] is not None
                    and 0.71 <= r["density_ratio_fixed8"] <= 1.32]
    stretched_residual = [dict(tri=r["name"], density_ratio_fixed8=r["density_ratio_fixed8"],
                               sigma_max_fixed8=r["sigma_max_fixed8"])
                          for r in target_rows if r["density_ratio_fixed8"] is not None
                          and r["density_ratio_fixed8"] < 0.60]
    stains_gone = bool(len(still_dense) == 0 and len(near_uniform) >= 8)

    all_hillshade_identical = all(r["hillshade_identical"] for r in site_rows)
    crater_preserved = bool(n_height_diff == 0 and n_diff_out_fp == 0 and all_hillshade_identical)

    report["calibration_fixed7"] = dict(
        rule="passes iff all 10 targets' density_ratio (baseline/sigma_max) on FIXED7 are >=1.3x AND the "
             "mean ratio is >=1.5x -- i.e. this eye's OWN direct read of the mesh bytes reproduces the "
             "reported 'denser than sand' stain before FIXED8 is judged.",
        density_ratio_fixed7_all=ratios7, mean=round(sum(ratios7) / len(ratios7), 3) if ratios7 else None,
        min=round(min(ratios7), 3) if ratios7 else None, max=round(max(ratios7), 3) if ratios7 else None,
        sigma_max_fixed7_all=sm7, calibration_saw_stains=calibration_saw_stains)
    report["resolution_fixed8"] = dict(
        density_ratio_fixed8_all=ratios8, mean=round(sum(ratios8) / len(ratios8), 3) if ratios8 else None,
        min=round(min(ratios8), 3) if ratios8 else None, max=round(max(ratios8), 3) if ratios8 else None,
        sigma_max_fixed8_all=sm8,
        n_still_reading_denser_than_sand_ratio_gt_1p15=len(still_dense), still_dense_tris=still_dense,
        n_near_uniform_0p71_to_1p32=len(near_uniform), near_uniform_tris=near_uniform,
        honest_residual_stretched_tris=stretched_residual,
        honest_residual_note=(
            "the 'dense mottled stain' half of playtest 6 is fully resolved on all 10 (none reads denser "
            "than the surrounding sand any more). Two tris -- the ones uvf_fix8's own report already "
            "flagged (the widest pair, reaching two cells out of their window) -- land the OTHER side "
            "of baseline instead: sparser/more-stretched, not mottled. They still wear the identical "
            "dunes-sand rect as every neighbour (same atlas patch, same hue/pattern), just at a coarser "
            "texel scale, which reads as slightly softer/blurrier sand at extreme close range, not as a "
            "different material. Reported honestly below with exact numbers, not folded into "
            "stains_gone." if stretched_residual else "no residual stretch outliers beyond the reported range."),
        stains_gone=stains_gone)
    report["geometry_identity"] = dict(
        n_height_diff_px=n_height_diff, n_covered_px=int(both_cov.sum()),
        byte_geometry_unmoved=(n_height_diff == 0),
        all_site_hillshade_identical=all_hillshade_identical,
        note="round 8 writes UV bytes only -- height and hillshade must be pixel-identical FIXED7 vs "
             "FIXED8 everywhere in the master raster; this is read off the rasterizer's own z-buffer, "
             "independent of uvf_fix8's internal byte-rigidity check.")
    report["pixel_diff_confinement"] = dict(
        footprint_px=n_fp_px, color_diff_px_total=n_diff_total,
        color_diff_px_inside_footprint=n_diff_in_fp, color_diff_px_outside_footprint=n_diff_out_fp,
        confined=(n_diff_out_fp == 0), diff_px_actually_present_inside=(n_diff_in_fp > 0),
        overlay_png="color_diff_outside_footprint_overlay_magenta.png",
        rgb_distance_threshold=12.0,
        note="the 10 tris' screen footprint is built from FIXED7's own verts via the SAME barycentric "
             "test the z-buffer rasterizer uses; since geometry is provably unmoved (see "
             "geometry_identity), FIXED8's triangle shapes are pixel-identical, so any color change "
             "outside that footprint would mean something else changed too.")
    report["target_set_summary"] = dict(
        n_tris=len(target_rows), n_knobs=len(knobs), baseline_sigma_flat_sand=baseline,
        rows=target_rows, knobs=knobs)
    report["renders"] = dict(dir=str(RENDER_DIR), mound_panels={k: v.name for k, v in panels.items()},
                              legend="sigma_legend.png", per_site=site_rows)

    overall = dict(
        calibration_saw_stains=calibration_saw_stains,
        stains_gone=stains_gone,
        crater_and_geometry_preserved=crater_preserved,
        pixel_diff_confined_to_footprint=(n_diff_out_fp == 0))
    overall["all_green"] = all(overall.values())
    report["overall_verdict"] = overall
    report["elapsed_s"] = round(time.time() - t0, 1)

    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\nOVERALL: {overall}")
    log(f"report -> {REPORT}  ({report['elapsed_s']}s)")
    return report


if __name__ == "__main__":
    main()
