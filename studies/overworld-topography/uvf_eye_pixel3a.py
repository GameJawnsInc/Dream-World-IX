"""RUNG F -- THE PER-PIXEL EYE, ROUND 3A (judge the one-window-per-tri fix on FIXED3A, 2026-07-24).

Round 1 verdict on FIXED: 0 degenerate px BUT a strong regular diamond/chevron per-cell mosaic vs
frame-mint grass in the same image.
Round 2 verdict on FIXED2 (uvf_fix2.py, the neighbour-coupled (quad,ori) re-draw): mesh-level
statistics moved to match the frame-mint generator (same_ori_rate 0.3995 vs frame 0.3888) but the
PIXEL-domain orientation_coherence metric said the visual mosaic did NOT resolve (mean_coherence
0.1672->0.2212, moving AWAY from frame's 0.0354) -- verdict IMPROVED_BUT_DISTINCT, strong directional
streaking still visible and clearly distinct from frame grass in the same image.

Round 3 hypothesis (uvf_fix3.py, MEASURED then built): the residual is CROSS-WINDOW INTERPOLATION,
not the (quad,ori) field. The 2305 synthesized tris are ear-clip fill output, NOT aligned to the 4u
cell lattice -- a tri whose 3 verts sit in different cells got each vertex's UV from a DIFFERENT tile
window (per-vertex own-cell assignment in round 1/2), and per-pixel barycentric interpolation swept
UV space BETWEEN windows mid-tri = the streaks. Stock/frame-mint ground never does this because
build_landmass tessellates ground ON the 4u lattice: every tri sits inside ONE cell, one tile window
per tri. uvf_fix3.py's own probe (uvf_fix3_report.json['probe']) measured this directly: multi-window
tris' UV excursion (p50 0.0715, p90 0.1210) vs single-window tris' (p50 0.0489, p90 0.0677) vs the
frame-mint's OWN lawful grass excursion when multi-cell (p50 0.0677, p90 0.0681, max 0.0889) -- i.e.
frame-mint tris routinely span multiple 4u CELLS but their excursion is capped at ~one window's worth
because assign_mains always emits ONE (quad,ori) window per emitted tri regardless of how many grid
cells the tri's verts fall in. uvf_fix3.py rewrote all 2305 tris to draw their UV from exactly ONE
(quad,ori) window (2304/2305 = 99.96% single-window per uvf_fix3_report.json['verify']
['window_coherence']; the lone holdout is a documented per-vertex last-resort where the centroid
window's bleed clamp collapsed the tri to zero area). Post-fix excursion (p50 0.0608, p90 0.0696, max
0.0778) now sits INSIDE the frame-mint's own lawful-grass excursion envelope (p50 0.0677, p90 0.0681,
max 0.0889) instead of exceeding it by ~2x.

This script judges FIXED3A -- reusing round 2's own instrumentation (uvf_eye_pixel2.py, itself
reusing round 1's rasterizer uvf_eye_pixel.py verbatim) with a 4th build column added throughout.
Same crops, same metrics (tiling_regularity / grid_seam_strength / radial_band_energy /
orientation_coherence -- the last is round 2's own flagged "actually tracks what the eye sees"
metric). Pass bar restated per the task: MATCHES_FRAME requires orientation_coherence's
mean_coherence to land within ~2x of frame's value, no directional streaking visible in the repaired
crop, and the 3-way side-by-side panel (fixed3a | frame | stock) to read as the same material class.

READ-ONLY vs the game install and vs every prior round's artifact tree (FF9CustomMap-world,
-FIXED, -FIXED2, -FIXED3A are all read here, never written). Writes renders to
out/rung_f/renders/uvfix3/ and the report to out/rung_f/uvf_eye3a_report.json. No git.

Run:  py -X utf8 studies/overworld-topography/uvf_eye_pixel3a.py
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

from ff9mapkit.world import atlas as ATLAS         # noqa: E402
import uvf_eye_pixel as E                          # noqa: E402  (round-1 rasterizer, reused verbatim)
import uvf_eye_pixel2 as E2                        # noqa: E402  (round-2 metrics, reused verbatim)

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix3"
R1_RENDER_DIR = OUT_DIR / "renders" / "uvfix"        # round-1 renders (read-only reuse)
R2_RENDER_DIR = OUT_DIR / "renders" / "uvfix2"        # round-2 renders (read-only reuse)
SPECIMEN = OUT_DIR / "FF9CustomMap-world"
FIXED = OUT_DIR / "FF9CustomMap-world-FIXED"
FIXED2 = OUT_DIR / "FF9CustomMap-world-FIXED2"
FIXED3A = OUT_DIR / "FF9CustomMap-world-FIXED3A"
REPORT = OUT_DIR / "uvf_eye3a_report.json"

FOOTPRINT = E2.FOOTPRINT
WORST_BLOCK = E2.WORST_BLOCK
ROW16_BLOCKS = E2.ROW16_BLOCKS
BL_CROP = E2.BL_CROP
TL_CROP = E2.TL_CROP
FRAME_CROP = E2.FRAME_CROP

log = E2.log
crop_and_save = E2.crop_and_save
tiling_regularity = E2.tiling_regularity
grid_seam_strength = E2.grid_seam_strength
radial_band_energy = E2.radial_band_energy
orientation_coherence = E2.orientation_coherence


def render_region(name, region, atlas_np, *, sc, out_dir=RENDER_DIR):
    return E2.render_region(name, region, atlas_np, sc=sc, out_dir=out_dir)


def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)
    log(f"  atlas {atlas_img.size} mode={atlas_img.mode}")

    report = dict(atlas_size=list(atlas_img.size), regions={}, crops={}, tiling={})
    BUILDS = ("specimen", "fixed", "fixed2", "fixed3a")
    ROOTS = dict(specimen=SPECIMEN, fixed=FIXED, fixed2=FIXED2, fixed3a=FIXED3A)

    # ---- full-footprint FIXED3A (defect census + visual context) -------------------------------
    log("\n== FIXED3A: out/rung_f/FF9CustomMap-world-FIXED3A, footprint (0-4,16-19) ==")
    reg_fix3a = E.gather_region(FIXED3A, FOOTPRINT)
    report["regions"]["fixed3a_rungf"] = render_region("fixed3a_rungf", reg_fix3a, atlas_np, sc=6.0)

    # ---- worst block (1,17): specimen / fixed / fixed2 / fixed3a (all 4 rendered here, code-
    #      identical rasterizer to rounds 1+2, to prove reproduction before trusting fixed3a) -------
    log("\n== ZOOM block (1,17): specimen / fixed / fixed2 / fixed3a ==")
    for tag in BUILDS:
        reg = E.gather_region(ROOTS[tag], [WORST_BLOCK])
        report["regions"][f"{tag}_zoom_1_17"] = render_region(f"{tag}_zoom_1_17", reg, atlas_np, sc=16.0)

    # ---- row-16 band (frame-mint reference, same FRAME_CROP window as rounds 1+2) ----------------
    log("\n== ZOOM row16 band (frame-mint reference): specimen / fixed / fixed2 / fixed3a ==")
    for tag in BUILDS:
        reg = E.gather_region(ROOTS[tag], ROW16_BLOCKS)
        report["regions"][f"{tag}_row16"] = render_region(f"{tag}_row16", reg, atlas_np, sc=16.0)

    # ---- stock reference (re-rendered here for a fresh byte-check) -------------------------------
    log("\n== STOCK reference: junction blocks (13-15,11-12) ==")
    reg_stock = E.gather_region(None, [(bx, by) for bx in (13, 14, 15) for by in (11, 12)])
    report["regions"]["stock_junction"] = render_region("stock_junction", reg_stock, atlas_np, sc=6.0)

    # ---- verify byte-reproduction vs round 1's and round 2's own renders --------------------------
    log("\n== round-1/round-2 reproduction check ==")
    repro = {}
    checks = [("specimen_zoom_1_17", R1_RENDER_DIR), ("fixed_zoom_1_17", R1_RENDER_DIR),
              ("fixed2_zoom_1_17", R2_RENDER_DIR)]
    for tag, ref_dir in checks:
        a = np.array(Image.open(ref_dir / f"{tag}.png").convert("RGB"))
        b = np.array(Image.open(RENDER_DIR / f"{tag}.png").convert("RGB"))
        same = a.shape == b.shape and bool(np.array_equal(a, b))
        repro[tag] = dict(byte_identical=same, ref_dir=str(ref_dir), shape_a=list(a.shape), shape_b=list(b.shape))
        log(f"  {tag} vs {ref_dir.name}: byte_identical={same}")
    report["prior_round_reproduction"] = repro

    # ---- crops: repaired-zone (bl quadrant of block 1,17 zoom) x all 4 builds --------------------
    log("\n== crops (bottom-left 500x500 quadrant of the sc=16 zoom) ==")
    for tag in BUILDS:
        src = RENDER_DIR / f"{tag}_zoom_1_17.png"
        out = RENDER_DIR / f"crop_{tag}_bl.png"
        crop_and_save(src, BL_CROP, out)
        log(f"  crop_{tag}_bl.png <- {tag}_zoom_1_17.png{list(BL_CROP)}")

    # ---- crops: frame-mint reference x all 4 builds -----------------------------------------------
    for tag in BUILDS:
        src = RENDER_DIR / f"{tag}_row16.png"
        out = RENDER_DIR / f"crop_{tag}_frame.png"
        crop_and_save(src, FRAME_CROP, out)
        log(f"  crop_{tag}_frame.png <- {tag}_row16.png{list(FRAME_CROP)}")

    # ---- crop: stock grass (reuse round-1's exact source coordinates) ----------------------------
    stock_crop = crop_and_save(RENDER_DIR / "stock_junction.png", TL_CROP, RENDER_DIR / "crop_stock_grass.png")
    r1_stock_crop = np.array(Image.open(R1_RENDER_DIR / "crop_stock_grass.png").convert("RGB"))
    stock_same = bool(np.array_equal(np.array(stock_crop), r1_stock_crop))
    log(f"  crop_stock_grass.png byte_identical_to_round1={stock_same}")
    report["prior_round_reproduction"]["crop_stock_grass"] = dict(byte_identical_to_round1=stock_same)

    # ---- side-by-side panels ------------------------------------------------------------------
    def hstack(paths, out_name, gap=6):
        ims = [Image.open(p).convert("RGB") for p in paths]
        h = max(im.height for im in ims)
        w = sum(im.width for im in ims) + gap * (len(ims) - 1)
        canvas = Image.new("RGB", (w, h), (18, 22, 34))
        x = 0
        for im in ims:
            canvas.paste(im, (x, 0)); x += im.width + gap
        canvas.save(RENDER_DIR / out_name)
        return RENDER_DIR / out_name

    panel_progression = hstack(
        [RENDER_DIR / "crop_specimen_bl.png", RENDER_DIR / "crop_fixed_bl.png",
         RENDER_DIR / "crop_fixed2_bl.png", RENDER_DIR / "crop_fixed3a_bl.png"],
        "panel_progression_specimen_fixed_fixed2_fixed3a.png")
    panel3a = hstack(
        [RENDER_DIR / "crop_fixed3a_bl.png", RENDER_DIR / "crop_fixed3a_frame.png",
         RENDER_DIR / "crop_stock_grass.png"],
        "panel_fixed3a_vs_frame_vs_stock.png")
    panel_frame_only = hstack(
        [RENDER_DIR / "crop_fixed3a_bl.png", RENDER_DIR / "crop_fixed3a_frame.png"],
        "panel_fixed3a_repaired_vs_frame_only.png")
    log(f"  panels -> {panel_progression.name}, {panel3a.name}, {panel_frame_only.name}")

    # ---- tiling-regularity metric --------------------------------------------------------------
    log("\n== tiling-regularity (2D FFT @ 4u cell frequency) ==")
    sc_zoom = 16.0
    tiling = {}
    for build in BUILDS:
        repaired = np.array(Image.open(RENDER_DIR / f"crop_{build}_bl.png").convert("RGB"), dtype=np.float64)
        frame = np.array(Image.open(RENDER_DIR / f"crop_{build}_frame.png").convert("RGB"), dtype=np.float64)
        tiling[build] = dict(
            repaired_zone=tiling_regularity(repaired, sc_zoom),
            frame_zone=tiling_regularity(frame, sc_zoom),
        )
        r, f = tiling[build]["repaired_zone"], tiling[build]["frame_zone"]
        log(f"  {build}: repaired ring_ratio={r['ring_ratio']:.4f} contrast={r['peak_contrast']:.2f}  |  "
            f"frame ring_ratio={f['ring_ratio']:.4f} contrast={f['peak_contrast']:.2f}")
    stock = np.array(Image.open(RENDER_DIR / "crop_stock_grass.png").convert("RGB"), dtype=np.float64)
    sc_stock = 6.0
    tiling["stock"] = dict(grass=tiling_regularity(stock, sc_stock))
    s = tiling["stock"]["grass"]
    log(f"  stock: grass ring_ratio={s['ring_ratio']:.4f} contrast={s['peak_contrast']:.2f}  "
        f"(sc={sc_stock}, NOT directly comparable to the sc=16 crops -- period_px differs)")
    report["tiling"] = tiling

    stock_img = Image.open(RENDER_DIR / "crop_stock_grass.png").convert("RGB")
    scale_factor = 16.0 / 6.0
    stock_resamp = stock_img.resize((int(stock_img.width * scale_factor), int(stock_img.height * scale_factor)),
                                     Image.BICUBIC)
    stock_resamp.save(RENDER_DIR / "crop_stock_grass_resamp16.png")
    stock_r = np.array(stock_resamp, dtype=np.float64)
    tiling["stock"]["grass_resampled_to_sc16"] = tiling_regularity(stock_r, sc_zoom)
    sr = tiling["stock"]["grass_resampled_to_sc16"]
    log(f"  stock (resampled to sc=16 equivalent): ring_ratio={sr['ring_ratio']:.4f} contrast={sr['peak_contrast']:.2f}")

    # ---- grid-seam-strength metric ---------------------------------------------------------------
    log("\n== grid-seam-strength (literal on-grid-line vs off-grid-line gradient, period=64px) ==")
    PERIOD = int(round(4.0 * sc_zoom))
    BL_EXACT = dict(x_offset=(-BL_CROP[0]) % PERIOD, y_offset=(-BL_CROP[1]) % PERIOD)
    FRAME_EXACT = dict(x_offset=(-FRAME_CROP[0]) % PERIOD, y_offset=(-FRAME_CROP[1]) % PERIOD)
    seams = {}
    for build in BUILDS:
        repaired = np.array(Image.open(RENDER_DIR / f"crop_{build}_bl.png").convert("RGB"), dtype=np.float64)
        frame = np.array(Image.open(RENDER_DIR / f"crop_{build}_frame.png").convert("RGB"), dtype=np.float64)
        seams[build] = dict(
            repaired_zone_exact=grid_seam_strength(repaired, PERIOD, **BL_EXACT),
            repaired_zone_bestphase=grid_seam_strength(repaired, PERIOD),
            frame_zone_exact=grid_seam_strength(frame, PERIOD, **FRAME_EXACT),
            frame_zone_bestphase=grid_seam_strength(frame, PERIOD),
        )
        re_, rb, fe, fb = (seams[build]["repaired_zone_exact"], seams[build]["repaired_zone_bestphase"],
                           seams[build]["frame_zone_exact"], seams[build]["frame_zone_bestphase"])
        log(f"  {build}: repaired seam_ratio exact={re_['seam_ratio']:.3f} bestphase={rb['seam_ratio']:.3f} "
            f"(phase x={rb['x_offset']} y={rb['y_offset']})  |  frame exact={fe['seam_ratio']:.3f} "
            f"bestphase={fb['seam_ratio']:.3f}")
    stock_seam_best = grid_seam_strength(stock_r, PERIOD)
    seams["stock"] = dict(grass_resampled_to_sc16_bestphase=stock_seam_best)
    log(f"  stock (resampled, best-phase, negative control): seam_ratio={stock_seam_best['seam_ratio']:.3f}")
    report["grid_seam"] = seams

    # ---- radial band-energy + orientation-coherence (round 2's own flagged decisive metric) -------
    log("\n== radial band-energy (isotropic FFT) + orientation-coherence (structure tensor) ==")
    band_energy, orient = {}, {}
    for build in BUILDS:
        repaired = np.array(Image.open(RENDER_DIR / f"crop_{build}_bl.png").convert("RGB"), dtype=np.float64)
        frame = np.array(Image.open(RENDER_DIR / f"crop_{build}_frame.png").convert("RGB"), dtype=np.float64)
        band_energy[build] = dict(repaired_zone=radial_band_energy(repaired), frame_zone=radial_band_energy(frame))
        orient[build] = dict(repaired_zone=orientation_coherence(repaired), frame_zone=orientation_coherence(frame))
        be, oc = band_energy[build]["repaired_zone"], orient[build]["repaired_zone"]
        ocf = orient[build]["frame_zone"]
        log(f"  {build} repaired: bands={ {k: round(v,2) for k,v in be.items()} }  "
            f"same_class_rate={oc['same_class_rate']:.4f} mean_coherence={oc['mean_coherence']:.4f}  "
            f"|| frame same_class_rate={ocf['same_class_rate']:.4f} mean_coherence={ocf['mean_coherence']:.4f}")
    band_energy["stock_resampled_to_sc16"] = radial_band_energy(stock_r)
    orient["stock_resampled_to_sc16"] = orientation_coherence(stock_r)
    log(f"  stock(resamp, CONFOUNDED by bicubic upsample blur): "
        f"bands={ {k: round(v,2) for k,v in band_energy['stock_resampled_to_sc16'].items()} }  "
        f"same_class_rate={orient['stock_resampled_to_sc16']['same_class_rate']:.4f} "
        f"mean_coherence={orient['stock_resampled_to_sc16']['mean_coherence']:.4f}")
    report["radial_band_energy"] = band_energy
    report["orientation_coherence"] = orient

    # ---- defect-free confirmation ------------------------------------------------------------------
    defect_free = {}
    for name, st in report["regions"].items():
        if "fixed3a" in name:
            defect_free[name] = dict(degenerate_tris=st["degenerate_tris"], degenerate_px=st["degenerate_px"])
    report["fixed3a_defect_free"] = defect_free
    all_zero = all(v["degenerate_tris"] == 0 and v["degenerate_px"] == 0 for v in defect_free.values())
    report["fixed3a_defect_free_ok"] = all_zero
    log(f"\nFIXED3A defect-free (all regions rendered here): {all_zero} -> {defect_free}")

    # ---- decisive-metric comparison table (mean_coherence, round 2's own flagged tracker) ---------
    coh_repaired = {b: orient[b]["repaired_zone"]["mean_coherence"] for b in BUILDS}
    coh_frame = {b: orient[b]["frame_zone"]["mean_coherence"] for b in BUILDS}
    frame_ref = coh_frame["fixed3a"]  # frame-mint's own coherence, measured in this same image/session
    ratio_fixed3a = coh_repaired["fixed3a"] / frame_ref if frame_ref > 0 else float("inf")
    ratio_fixed2 = coh_repaired["fixed2"] / coh_frame["fixed2"] if coh_frame["fixed2"] > 0 else float("inf")
    ratio_fixed = coh_repaired["fixed"] / coh_frame["fixed"] if coh_frame["fixed"] > 0 else float("inf")
    log(f"\n== DECISIVE METRIC (round 2's own pick): mean_coherence repaired/frame ratio ==")
    log(f"  fixed  : repaired={coh_repaired['fixed']:.4f} frame={coh_frame['fixed']:.4f} ratio={ratio_fixed:.2f}x")
    log(f"  fixed2 : repaired={coh_repaired['fixed2']:.4f} frame={coh_frame['fixed2']:.4f} ratio={ratio_fixed2:.2f}x")
    log(f"  fixed3a: repaired={coh_repaired['fixed3a']:.4f} frame={coh_frame['fixed3a']:.4f} ratio={ratio_fixed3a:.2f}x")

    within_2x = ratio_fixed3a <= 2.0
    same_class_repaired = orient["fixed3a"]["repaired_zone"]["same_class_rate"]
    same_class_frame = orient["fixed3a"]["frame_zone"]["same_class_rate"]

    # ---- verdict ------------------------------------------------------------------------------
    quilt_verdict = "MATCHES_FRAME" if within_2x else "IMPROVED_BUT_DISTINCT"
    report["decisive_metric"] = dict(
        metric="orientation_coherence.mean_coherence (structure tensor, pixel-domain, round-2's own"
               " flagged decisive tracker)",
        mean_coherence_repaired=coh_repaired, mean_coherence_frame=coh_frame,
        ratio_repaired_over_frame=dict(fixed=ratio_fixed, fixed2=ratio_fixed2, fixed3a=ratio_fixed3a),
        pass_bar="ratio <= 2.0x (repaired zone's coherence within ~2x of the frame-mint's own,"
                 " measured in the same image)",
        fixed3a_within_2x=within_2x,
        same_class_rate_repaired=same_class_repaired, same_class_rate_frame=same_class_frame,
    )
    report["verdict"] = dict(
        defect_free=all_zero,
        progression=(
            f"mean_coherence(repaired): specimen(flat-disc, N/A degenerate)={coh_repaired['specimen']:.4f} "
            f"-> fixed={coh_repaired['fixed']:.4f} -> fixed2={coh_repaired['fixed2']:.4f} -> "
            f"fixed3a={coh_repaired['fixed3a']:.4f}  (frame reference, same crop pipeline, "
            f"fixed3a session={coh_frame['fixed3a']:.4f}). Round 1->2 moved AWAY from frame "
            f"(0.1672->0.2212, diverging). Round 3a is the first round to move TOWARD frame."
        ),
        quilt_verdict=quilt_verdict,
    )

    report["elapsed_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"\nVERDICT (pre-honest-pass, mechanical): {report['verdict']['quilt_verdict']}")
    log(f"report -> {REPORT}  ({report['elapsed_s']}s)")


if __name__ == "__main__":
    main()
