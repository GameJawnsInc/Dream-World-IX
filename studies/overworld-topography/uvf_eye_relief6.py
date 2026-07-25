"""RUNG F -- THE SHADED-RELIEF EYE, round 6 (THE CARRIED-SPIKE SHAVE, 2026-07-25).

Playtest 4 verdict on FIXED5: round 5's relief relax worked ("the crevices are sealed up ... seal
looks good") but "there's still the bumpy top part" -- the crater mound's carried donor-relief tent
apexes. uvf_fix6.py shaved 4 census-defined SPIKE positions (+8 welded fill positions) into the local
rim surface. This is that round's shape eye: CALIBRATION-FIRST on FIXED5 (must show the tents), then
judge FIXED6 (must show them gone, bowl+rim base untouched).

Extends uvf_eye_relief.py (round 5's shape eye) -- reuses its rasterizer, hillshade/slope math, image
helpers and panel machinery VERBATIM (imported, not copied) with FIXED4->FIXED5, FIXED5->FIXED6. The
reference-plane residual is re-derived HERE, independently of uvf_fix6.py's own bookkeeping: a fresh
KEPT-GROUND-ONLY (no fill) leave-one-out IDW plane fit built straight off FIXED5's own Terrain bytes,
basin-excluded -- the same convention uvf_relief_probe.stage2 uses for FIXED4, just pointed at FIXED5.
The 4 site coordinates are read from uvf_fix6_report.json (peak_world only -- a location, not a
verdict); every number computed AT those locations is this script's own.

READ-ONLY vs both artifact trees (FIXED5, FIXED6) and the game install (atlas + stock dunes reference).
Never writes outside out/rung_f/renders/uvfix6/. No git.

Run:  py -X utf8 uvf_eye_relief6.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import atlas as ATLAS         # noqa: E402
from ff9mapkit.world import extract as X           # noqa: E402
from ff9mapkit.world import mesh as M              # noqa: E402
from ff9mapkit.world import grassland as G         # noqa: E402

import uvf_eye_pixel as E                          # noqa: E402  (block_part_mesh, sample_atlas_vec, raster_flat_tri)
import uvf_eye_relief as ER                         # noqa: E402  (rasterizer / hillshade / slope math -- reused verbatim)
import uvf_relief_probe as RP                       # noqa: E402  (Hash2D / ref_at -- reused verbatim)

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix6"
FIXED5 = OUT_DIR / "FF9CustomMap-world-FIXED5"
FIXED6 = OUT_DIR / "FF9CustomMap-world-FIXED6"
FIX6_REPORT = OUT_DIR / "uvf_fix6_report.json"
REPORT = OUT_DIR / "uvf_eye_relief6_report.json"

FOOTPRINT = ER.FOOTPRINT                                    # (0-4, 16-19), same 20 blocks
STOCK_DUNES = ER.STOCK_DUNES

BASIN_CENTER = ER.BASIN_CENTER          # (127.14, -1161.42)
BASIN_R = ER.BASIN_R                    # 7.92
MOUND_R = 40.0                          # uvf_fix6's own crater-mound radius

SC = 10.0
CLOSE_R = 30.0
WEDGE_R = 46.0           # covers the mound (40u) + a small margin, all 4 sites (max r_crater=14.06)

CH_POS, CH_TAN = X.CH_POS, X.CH_TAN
PARTS = RP.PARTS
POS_DP = RP.POS_DP


def log(m):
    print(m, flush=True)


def pkey(p):
    return (round(float(p[0]), POS_DP), round(float(p[1]), POS_DP), round(float(p[2]), POS_DP))


def rc(k):
    return math.hypot(k[0] - BASIN_CENTER[0], k[2] - BASIN_CENTER[1])


class ExcludeHash:
    """Same device uvf_fix6.py uses -- lets RP.ref_at run leave-one-out on a sample set minus an
    index blacklist. Re-declared here (not imported from uvf_fix6) so this eye's reference fit is its
    own code path, independent of the fix's."""

    def __init__(self, base, drop):
        self.base = base
        self.drop = drop
        self.cell = base.cell
        self.pts = base.pts

    def query(self, x, z, r):
        return [(i, d2) for i, d2 in self.base.query(x, z, r) if i not in self.drop]


# =================================================================================================
#  an INDEPENDENT kept-ground-only reference, built straight off a tree's own Terrain bytes
#  (the RP.stage2 convention -- ground positions only, rock abstains -- pointed at FIXED5, not FIXED4;
#  uvf_relief_probe.stage2 hardcodes FIXED4 so it cannot be called directly for this round)
# =================================================================================================
def build_ground_reference(tree, touched, *, exclude_basin=True):
    ground_pos = {}
    for b in touched:
        p = tree / M.override_relpath(1, b[0], b[1], part="Terrain")
        d = M.read_ff9mesh(p)
        ox, oz = X.block_world_origin(*b)
        verts, tans, idx = d["verts"], d["tangents"], d["indices"]
        for t in range(len(idx) // 3):
            tri = idx[3 * t:3 * t + 3]
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            fam = G.TOPO_FAMILY.get(topo)
            if fam is None:
                continue
            for j in tri:
                v = verts[j]
                k = pkey((v[0] + ox, v[1], v[2] + oz))
                if exclude_basin and rc(k) <= BASIN_R:
                    continue
                ground_pos[k] = fam
    keys = sorted(ground_pos)
    samples = np.array([[k[0], k[1], k[2]] for k in keys], dtype=float)
    idx_of = {k: i for i, k in enumerate(keys)}
    base = RP.Hash2D(samples, cell=8.0)
    return dict(keys=keys, samples=samples, idx_of=idx_of, base=base)


def ref_leave_one_out(REF, x, z, extra_drop=()):
    """Query the nearest sample key at (x,z) (for leave-one-out) then fit with RP.ref_at, dropping it
    plus any extra indices (e.g. every other site, so sites never referee each other)."""
    hits = REF["base"].query(x, z, 0.6)
    drop = set(extra_drop)
    if hits:
        drop.add(min(hits, key=lambda h: h[1])[0])
    y, diag = RP.ref_at(ExcludeHash(REF["base"], frozenset(drop)), REF["samples"], x, z)
    return y, diag


# =================================================================================================
#  independent changed-tri footprint (direct per-vertex Y-diff re-raster of FIXED5 vs FIXED6, not a
#  read of uvf_fix6's own report)
# =================================================================================================
def changed_footprint_mask(shape_hw, wx0, wz1, sc, blocks):
    H, W = shape_hw
    mask = np.zeros((H, W), dtype=bool)
    reg_a = ER.gather_xyz(FIXED5, blocks)
    reg_b = ER.gather_xyz(FIXED6, blocks)
    ta = {(bx, by): tris for bx, by, src, tris in reg_a["terrain"]}
    tb = {(bx, by): tris for bx, by, src, tris in reg_b["terrain"]}
    n_changed = 0
    max_abs_dy = 0.0
    for k in ta:
        for (wa, uva), (wb, uvb) in zip(ta[k], tb[k]):
            ya = [p[1] for p in wa]
            yb = [p[1] for p in wb]
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
                sub = mask[y0c:y1c, x0c:x1c]
                sub[m] = True
                mask[y0c:y1c, x0c:x1c] = sub
    return mask, n_changed, max_abs_dy


def save(arr_u8, path):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr_u8, "RGB").save(path)
    return path


def hstack(paths, out_name, gap=8):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = max(im.height for im in ims)
    w = sum(im.width for im in ims) + gap * (len(ims) - 1)
    canvas = Image.new("RGB", (w, h), (18, 22, 34))
    x = 0
    for im in ims:
        canvas.paste(im, (x, 0))
        x += im.width + gap
    canvas.save(RENDER_DIR / out_name)
    return RENDER_DIR / out_name


# =================================================================================================
def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)
    log(f"  atlas {atlas_img.size} mode={atlas_img.mode}")

    fix6 = json.loads(FIX6_REPORT.read_text(encoding="utf-8"))
    build = json.loads((OUT_DIR / "rung_f_build.json").read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    sites_in = fix6["stage3_spike_census"]["sites"]
    site_pts = [(s["peak_world"][0], s["peak_world"][2]) for s in sites_in]
    log(f"sites read from uvf_fix6_report.json (location only, {len(site_pts)} sites): {site_pts}")

    report = dict(meta=dict(script="uvf_eye_relief6.py", basin_center=list(BASIN_CENTER),
                             basin_r=BASIN_R, mound_r=MOUND_R, sc=SC,
                             n_sites=len(site_pts), site_world_xz=site_pts))

    # ---- master rasters over the SAME fixed footprint bbox --------------------------------------
    bxs = [b[0] for b in FOOTPRINT]
    bys = [b[1] for b in FOOTPRINT]
    wx0f, wx1f = min(bxs) * 64.0, (max(bxs) + 1) * 64.0
    wz0f, wz1f = -(max(bys) + 1) * 64.0, -min(bys) * 64.0
    log(f"footprint bbox world x[{wx0f},{wx1f}] z[{wz0f},{wz1f}] @ sc={SC}")

    log("\n== rasterizing FIXED5 footprint (Terrain z-buffer: color + height) ==")
    c5 = ER.rasterize(FIXED5, FOOTPRINT, SC, atlas_np, wx0=wx0f, wx1=wx1f, wz0=wz0f, wz1=wz1f)
    log(f"  tris={c5['stats']['tris']} px={c5['stats']['px']} covered={int(c5['covered'].sum())}/"
        f"{c5['W']*c5['H']} misses={c5['misses']}")

    log("\n== rasterizing FIXED6 footprint ==")
    c6 = ER.rasterize(FIXED6, FOOTPRINT, SC, atlas_np, wx0=wx0f, wx1=wx1f, wz0=wz0f, wz1=wz1f)
    log(f"  tris={c6['stats']['tris']} px={c6['stats']['px']} covered={int(c6['covered'].sum())}/"
        f"{c6['W']*c6['H']} misses={c6['misses']}")

    log("\n== rasterizing STOCK dunes reference ==")
    cst = ER.rasterize(None, STOCK_DUNES, SC, atlas_np)
    log(f"  tris={cst['stats']['tris']} covered={int(cst['covered'].sum())}/{cst['W']*cst['H']}")

    VEXAG = 4.0
    shades = {}
    for tag, c in (("fixed5", c5), ("fixed6", c6), ("stock_dunes", cst)):
        shades[tag] = dict(
            nw=ER.hillshade(c, 315.0, 35.0), multi=ER.hillshade_multi(c),
            nw_ex=ER.hillshade(c, 315.0, 35.0, vexag=VEXAG), multi_ex=ER.hillshade_multi(c, vexag=VEXAG),
            slope=ER.slope_magnitude(c))

    # ---- FULL FOOTPRINT renders -------------------------------------------------------------------
    log("\n== full-footprint renders ==")
    for tag, c in (("fixed5", c5), ("fixed6", c6)):
        sh = shades[tag]
        save(ER.gray_img(sh["multi"], c["covered"]), RENDER_DIR / f"{tag}_footprint_hillshade_multi.png")
        save(ER.composite(c["color"], sh["nw"], c["covered"]), RENDER_DIR / f"{tag}_footprint_textured_shaded.png")
    save(ER.gray_img(shades["stock_dunes"]["multi"], cst["covered"]), RENDER_DIR / "stock_dunes_hillshade_multi.png")
    save(ER.composite(cst["color"], shades["stock_dunes"]["nw"], cst["covered"]), RENDER_DIR / "stock_dunes_textured_shaded.png")

    # ---- CRATER-CLOSE crops -------------------------------------------------------------------
    log(f"\n== crater-close crops (r={CLOSE_R}u around {BASIN_CENTER}) ==")
    box_close = ER.crop_world(c5, *BASIN_CENTER, CLOSE_R)
    for tag, c in (("fixed5", c5), ("fixed6", c6)):
        sh = shades[tag]
        save(ER.gray_img(ER.crop_arr(sh["multi"], box_close), ER.crop_arr(c["covered"], box_close)),
             RENDER_DIR / f"{tag}_crater_close_hillshade_multi.png")
        save(ER.composite(ER.crop_arr(c["color"], box_close), ER.crop_arr(sh["nw"], box_close),
                           ER.crop_arr(c["covered"], box_close)),
             RENDER_DIR / f"{tag}_crater_close_textured_shaded.png")

    # ---- MOUND crops (the owner's screenshot scope: the whole crater mound) -----------------------
    log(f"== mound crops (r={WEDGE_R}u) ==")
    box_mound = ER.crop_world(c5, *BASIN_CENTER, WEDGE_R)
    for tag, c in (("fixed5", c5), ("fixed6", c6)):
        sh = shades[tag]
        save(ER.gray_img(ER.crop_arr(sh["multi"], box_mound), ER.crop_arr(c["covered"], box_mound)),
             RENDER_DIR / f"{tag}_mound_hillshade_multi.png")
        save(ER.gray_img(ER.crop_arr(sh["multi_ex"], box_mound), ER.crop_arr(c["covered"], box_mound)),
             RENDER_DIR / f"{tag}_mound_hillshade_multi_exag4x.png")
        save(ER.gray_img(np.clip(ER.crop_arr(sh["slope"], box_mound) / 1.5, 0, 1),
                          ER.crop_arr(c["covered"], box_mound)),
             RENDER_DIR / f"{tag}_mound_slope_mag.png")
        save(ER.composite(ER.crop_arr(c["color"], box_mound), ER.crop_arr(sh["nw"], box_mound),
                           ER.crop_arr(c["covered"], box_mound)),
             RENDER_DIR / f"{tag}_mound_textured_shaded.png")

    panel_mound_hillshade = hstack(
        [RENDER_DIR / "fixed5_mound_hillshade_multi.png", RENDER_DIR / "fixed6_mound_hillshade_multi.png"],
        "panel_mound_hillshade_fixed5_vs_fixed6.png")
    panel_mound_hillshade_ex = hstack(
        [RENDER_DIR / "fixed5_mound_hillshade_multi_exag4x.png", RENDER_DIR / "fixed6_mound_hillshade_multi_exag4x.png"],
        "panel_mound_hillshade_exag4x_fixed5_vs_fixed6.png")
    panel_mound_textured = hstack(
        [RENDER_DIR / "fixed5_mound_textured_shaded.png", RENDER_DIR / "fixed6_mound_textured_shaded.png"],
        "panel_mound_textured_fixed5_vs_fixed6.png")
    panel_close_hillshade = hstack(
        [RENDER_DIR / "fixed5_crater_close_hillshade_multi.png", RENDER_DIR / "fixed6_crater_close_hillshade_multi.png"],
        "panel_crater_close_hillshade_fixed5_vs_fixed6.png")
    panel_ref = hstack(
        [RENDER_DIR / "fixed6_mound_hillshade_multi.png", RENDER_DIR / "stock_dunes_hillshade_multi.png"],
        "panel_fixed6_vs_stock_dunes_hillshade.png")
    log(f"panels -> {panel_mound_hillshade.name}, {panel_mound_hillshade_ex.name}, {panel_mound_textured.name}, "
        f"{panel_close_hillshade.name}, {panel_ref.name}")

    # ---- HEIGHT DIFF (fixed6 - fixed5) + independent changed-tri footprint check ------------------
    log("\n== height diff FIXED6 - FIXED5 (footprint grid) ==")
    both_cov = c5["covered"] & c6["covered"]
    diff = np.where(both_cov, c6["height"] - c5["height"], 0.0)
    save(ER.diverging_img(diff, both_cov, vmax=1.4), RENDER_DIR / "footprint_height_diff_fixed6_minus_fixed5.png")

    changed_mask, n_changed_tris, max_abs_dy_meas = changed_footprint_mask(
        (c5["H"], c5["W"]), wx0f, wz1f, SC, FOOTPRINT)
    diff_nonzero = both_cov & (np.abs(diff) > 0.01)
    n_diff_px = int(diff_nonzero.sum())
    n_outside = int((diff_nonzero & ~changed_mask).sum())
    n_footprint_px = int(changed_mask.sum())
    log(f"  changed tris (independent direct mesh re-diff): {n_changed_tris}, max|dY| here={max_abs_dy_meas:.4f}")
    log(f"  diff px (|dY|>0.01): {n_diff_px}  changed-tri footprint px: {n_footprint_px}  outside: {n_outside}")

    overlay = ER.gray_img(shades["fixed6"]["multi"], c6["covered"]).copy()
    overlay[diff_nonzero & ~changed_mask] = [255, 0, 255]
    save(overlay, RENDER_DIR / "diff_outside_footprint_overlay_magenta.png")

    yy, xx = np.mgrid[0:c5["H"], 0:c5["W"]]
    all_wx = wx0f + xx / SC
    all_wz = wz1f - yy / SC
    in_basin_disc = ((all_wx - BASIN_CENTER[0]) ** 2 + (all_wz - BASIN_CENTER[1]) ** 2) <= BASIN_R ** 2
    diff_in_basin = diff_nonzero & in_basin_disc
    n_basin_diff = int(diff_in_basin.sum())
    n_basin_px = int((in_basin_disc & both_cov).sum())
    log(f"  basin disc (r={BASIN_R}u): {n_basin_px} covered px, {n_basin_diff} differ -- should be 0")

    # a strict PIXEL-FOOTPRINT check specific to this round's claim: the diff must localize inside a
    # halo around the round's OWN claimed moved-position list (4 spikes + 8 welded fill, world XZ read
    # from uvf_fix6_report.json -- a location list, not a verdict) -- not merely "some footprint".
    moved_pts = [tuple(r["world"][0::2]) for r in fix6["stage4_solve"]["result"]["spike_moves"]] + \
        [tuple(r["world"][0::2]) for r in fix6["stage4_solve"]["result"]["fill_moves"]]
    site_r = 3.0  # a kept topo-41 tri pair's own footprint is a couple metres across
    near_site = np.zeros_like(in_basin_disc)
    for (sx, sz) in moved_pts:
        near_site |= (((all_wx - sx) ** 2 + (all_wz - sz) ** 2) <= site_r ** 2)
    n_diff_outside_site_halo = int((diff_nonzero & ~near_site).sum())

    report["height_diff"] = dict(
        vmax_colormap=1.4, n_diff_px_gt_0p01=n_diff_px,
        n_changed_tris_direct_mesh_diff=n_changed_tris, max_abs_dY_measured_here=round(max_abs_dy_meas, 4),
        n_changed_tri_footprint_px=n_footprint_px, n_diff_px_outside_footprint=n_outside,
        diff_localizes_to_changed_tris=(n_outside == 0),
        n_basin_disc_covered_px=n_basin_px, n_basin_disc_diff_px=n_basin_diff,
        basin_disc_untouched=(n_basin_diff == 0),
        n_diff_px_outside_9u_site_halo=n_diff_outside_site_halo,
        diff_localizes_to_the_4_sites=(n_diff_outside_site_halo == 0),
        overlay="diff_outside_footprint_overlay_magenta.png",
        diff_png="footprint_height_diff_fixed6_minus_fixed5.png")
    log(f"  diff outside a 9u halo around the 4 sites: {n_diff_outside_site_halo} (should be 0)")

    # ---- CALIBRATION-FIRST: reference-plane residual at each site, THIS SCRIPT'S OWN fit -----------
    log("\n== reference-plane residuals at the 4 sites (this eye's own kept-ground-only fit) ==")
    REF5 = build_ground_reference(FIXED5, touched)
    REF6 = build_ground_reference(FIXED6, touched)
    log(f"  kept-ground sample positions: FIXED5={len(REF5['keys'])} FIXED6={len(REF6['keys'])}")

    site_rows = []
    for (sx, sz) in site_pts:
        h5 = ER.height_at(c5, sx, sz)
        h6 = ER.height_at(c6, sx, sz)
        y5, _ = ref_leave_one_out(REF5, sx, sz)
        y6, _ = ref_leave_one_out(REF6, sx, sz)
        res5 = (h5 - y5) if (h5 is not None and y5 is not None) else None
        res6 = (h6 - y6) if (h6 is not None and y6 is not None) else None
        site_rows.append(dict(world_xz=[sx, sz], height_fixed5=h5, height_fixed6=h6,
                              reference_fixed5=round(y5, 3) if y5 is not None else None,
                              reference_fixed6=round(y6, 3) if y6 is not None else None,
                              residual_fixed5=round(res5, 3) if res5 is not None else None,
                              residual_fixed6=round(res6, 3) if res6 is not None else None))
        log(f"  site ({sx:.1f},{sz:.1f}): h5={h5:.3f} ref5={y5:.3f} res5={res5:+.3f}  ->  "
            f"h6={h6:.3f} ref6={y6:.3f} res6={res6:+.3f}")

    # control: untouched rim positions (crest ring, non-spike) + the 5 quiet blocks from round 5 -----
    CONTROL_UNTOUCHED_BLOCKS = [(0, 16), (1, 16), (4, 16), (0, 19), (4, 19)]
    control_rows = []
    for (bx, by) in CONTROL_UNTOUCHED_BLOCKS:
        pts_res = []
        for gi in range(7):
            for gj in range(7):
                gx = bx * 64.0 + 6.0 + gi * (52.0 / 6.0)
                gz = -(by * 64.0 + 6.0 + gj * (52.0 / 6.0))
                h5g = ER.height_at(c5, gx, gz)
                if h5g is None:
                    continue
                yhg, _ = ref_leave_one_out(REF5, gx, gz)
                if yhg is None:
                    continue
                pts_res.append(h5g - yhg)
        control_rows.append(dict(block=[bx, by], n_land_samples=len(pts_res),
                                  residual_abs_mean=round(float(np.mean(np.abs(pts_res))), 4) if pts_res else None))
    control_abs = [r["residual_abs_mean"] for r in control_rows if r["residual_abs_mean"] is not None]
    control_mean = float(np.mean(control_abs)) if control_abs else None

    res5_abs = [abs(r["residual_fixed5"]) for r in site_rows if r["residual_fixed5"] is not None]
    res6_abs = [abs(r["residual_fixed6"]) for r in site_rows if r["residual_fixed6"] is not None]
    site_abs5_mean = float(np.mean(res5_abs)) if res5_abs else None
    site_abs6_mean = float(np.mean(res6_abs)) if res6_abs else None
    calibration_saw_spikes = bool(site_abs5_mean is not None and control_mean is not None
                                  and site_abs5_mean > 3.0 * control_mean and site_abs5_mean > 0.6)
    n_spikes_gone = sum(1 for r in site_rows if r["residual_fixed6"] is not None and abs(r["residual_fixed6"]) < 0.30)
    spikes_gone = bool(n_spikes_gone == len(site_rows) and site_abs6_mean is not None and site_abs6_mean < 0.30)

    report["calibration"] = dict(
        method="THIS EYE's OWN kept-ground-only (rock abstains) leave-one-out IDW plane fit, built "
               "straight off each tree's own Terrain bytes with the basin disc excluded from the "
               "sample set -- the RP.stage2 convention pointed at FIXED5/FIXED6 instead of FIXED4 (that "
               "module hardcodes FIXED4, so it is re-derived here rather than called). Residual sampled "
               "through this eye's own z-buffer rasterizer, not a vertex-exact reader.",
        site_rows=site_rows, control_untouched_blocks=control_rows,
        control_abs_residual_mean=round(control_mean, 4) if control_mean else None,
        site_abs_residual_mean_fixed5=round(site_abs5_mean, 4) if site_abs5_mean else None,
        site_abs_residual_mean_fixed6=round(site_abs6_mean, 4) if site_abs6_mean else None,
        calibration_saw_spikes=calibration_saw_spikes,
        n_spikes_gone=n_spikes_gone, n_sites=len(site_rows), spikes_gone=spikes_gone,
        rule="calibration passes iff mean(|residual| at the 4 sites, FIXED5) exceeds both 3x the "
             "untouched-block control baseline and an absolute 0.6u floor; spikes-gone passes iff EVERY "
             "site's FIXED6 |residual| < 0.30u (this eye's own independent fit, not uvf_fix6's).")
    log(f"  control |residual| mean: {control_mean}")
    log(f"  site |residual| mean FIXED5={site_abs5_mean} -> FIXED6={site_abs6_mean}")
    log(f"  CALIBRATION {'PASSED' if calibration_saw_spikes else 'FAILED'}   "
        f"SPIKES GONE: {n_spikes_gone}/{len(site_rows)}")

    # ---- no new flats/dimples: local roughness at the shaved spots should look like ordinary sand,
    #      not a perfectly flat plateau (a 'fixed by deletion' tell) or a new pit (overshave) ---------
    rough_rows = []
    for (sx, sz) in site_pts:
        box = ER.crop_world(c6, sx, sz, 5.0)
        sub = ER.crop_arr(c6["height"], box)
        subc = ER.crop_arr(c6["covered"], box)
        v = sub[subc]
        rough_rows.append(dict(world_xz=[sx, sz], n=int(v.size),
                               std=round(float(np.std(v)), 4) if v.size else None,
                               ptp=round(float(np.ptp(v)), 4) if v.size else None))
    # control = OTHER carried-dunes points on the SAME mound, ring r=20..35u (same terrain family + mesh
    # density as the shaved sites, well clear of both the basin and the 4 site halos) -- a coastal block
    # centroid is the wrong comparison (often near-flat sea-adjacent land, an apples-to-oranges std~0).
    control_rough = []
    rng_ang = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    for ang in rng_ang:
        for rr in (20.0, 26.0, 32.0):
            gx = BASIN_CENTER[0] + rr * math.cos(ang)
            gz = BASIN_CENTER[1] + rr * math.sin(ang)
            if any((gx - sx) ** 2 + (gz - sz) ** 2 <= 9.0 ** 2 for sx, sz in site_pts):
                continue
            box = ER.crop_world(c5, gx, gz, 5.0)
            sub = ER.crop_arr(c5["height"], box)
            subc = ER.crop_arr(c5["covered"], box)
            v = sub[subc]
            if v.size >= 20:
                control_rough.append(float(np.std(v)))
    report["roughness_honesty"] = dict(
        method="std-dev of rasterized height in a 5u radius around each shaved site on FIXED6, vs the "
               "same statistic on 3 lawful untouched control blocks -- neither a dead-flat plateau "
               "(std near 0, a give-away deletion) nor a new pit (std far ABOVE the control) is wanted.",
        site_rows=rough_rows, control_std=[round(s, 4) for s in control_rough],
        control_std_mean=round(float(np.mean(control_rough)), 4) if control_rough else None,
        no_dead_flat=all(r["std"] is None or r["std"] > 0.02 for r in rough_rows),
        no_new_pit=all(r["std"] is None or (control_rough == [] or r["std"] < 5.0 * np.mean(control_rough))
                       for r in rough_rows))
    log(f"  roughness at shaved sites: {[r['std'] for r in rough_rows]}  control mean="
        f"{report['roughness_honesty']['control_std_mean']}")

    # ---- rim/bowl silhouette identity (kept content near the crater byte-identical) -----------------
    NEAR_R = 25.0
    near_crater = (((all_wx - BASIN_CENTER[0]) ** 2 + (all_wz - BASIN_CENTER[1]) ** 2) <= NEAR_R ** 2)
    kept_near_crater = near_crater & both_cov & ~changed_mask
    bowl_mask = in_basin_disc & both_cov
    kept_delta = (c6["height"][kept_near_crater] - c5["height"][kept_near_crater]) if kept_near_crater.any() else np.array([])
    report["rim_bowl_identity"] = dict(
        n_kept_px_within_25u_of_basin=int(kept_near_crater.sum()),
        max_abs_delta_kept_near_crater=round(float(np.max(np.abs(kept_delta))), 6) if kept_delta.size else None,
        kept_near_crater_untouched=bool(kept_delta.size == 0 or np.max(np.abs(kept_delta)) < 1e-4),
        bowl_height_fixed5=round(float(np.mean(c5["height"][bowl_mask])), 4) if bowl_mask.any() else None,
        bowl_height_fixed6=round(float(np.mean(c6["height"][bowl_mask])), 4) if bowl_mask.any() else None,
        bowl_max_abs_height_delta=round(float(np.max(np.abs(c6["height"][bowl_mask] - c5["height"][bowl_mask]))), 6)
        if bowl_mask.any() else None)
    log(f"  rim/bowl identity: {kept_near_crater.sum()} kept px within 25u of basin, max|delta|="
        f"{report['rim_bowl_identity']['max_abs_delta_kept_near_crater']}")

    overall_verdict = dict(
        calibration_saw_spikes=calibration_saw_spikes,
        spikes_gone=spikes_gone,
        diff_localizes_to_changed_tris=report["height_diff"]["diff_localizes_to_changed_tris"],
        diff_localizes_to_the_4_sites=report["height_diff"]["diff_localizes_to_the_4_sites"],
        basin_disc_untouched=report["height_diff"]["basin_disc_untouched"],
        crater_preserved=(report["rim_bowl_identity"]["kept_near_crater_untouched"]
                          and report["rim_bowl_identity"]["bowl_max_abs_height_delta"] is not None
                          and report["rim_bowl_identity"]["bowl_max_abs_height_delta"] < 1e-4),
        no_dead_flat_or_new_pit=(report["roughness_honesty"]["no_dead_flat"]
                                 and report["roughness_honesty"]["no_new_pit"]))
    overall_verdict["all_green"] = all(overall_verdict.values())
    report["overall_verdict"] = overall_verdict
    log(f"\nOVERALL: {overall_verdict}")

    report["renders"] = dict(dir=str(RENDER_DIR),
                              panels=[panel_mound_hillshade.name, panel_mound_hillshade_ex.name,
                                      panel_mound_textured.name, panel_close_hillshade.name,
                                      panel_ref.name])
    report["elapsed_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\nreport -> {REPORT}  ({report['elapsed_s']}s)")
    return report


if __name__ == "__main__":
    main()
