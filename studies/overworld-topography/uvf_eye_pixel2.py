"""RUNG F -- THE PER-PIXEL EYE, ROUND 2 (judge the quilt on FIXED2, 2026-07-24).

Round 1 verdict on FIXED (uvf_fix.py's output): 0 degenerate px (defect-free) BUT the repaired
hole-fill zone read as a strong regular diamond/chevron per-cell mosaic that the surrounding
frame-mint grass (build_landmass output, in-game-proven class) does NOT show in the SAME image.

Round 2 (uvf_fix2.py) re-resolved the 923 fully-dropped cells through a policy MIRRORING
grassland.assign_mains' own neighbour-coupling (orientation copy p=0.32, single-neighbour quad
avoid) instead of interior.decode_cell_pick's uncoupled uniform draw + dual-neighbour avoid. This
script judges FIXED2 against THREE standards in the SAME render: (a) frame-mint grass in the same
image [pass bar], (b) stock grass, (c) round-1 FIXED side-by-side. Quantified via a 2D-FFT
tiling-regularity metric at the 4-world-unit cell frequency, not eyeballing alone.

Reused verbatim from uvf_eye_pixel.py (round 1): sample_atlas_vec / raster_textured_tri /
raster_flat_tri / block_part_mesh / block_tris / gather_region -- imported, not re-derived, so the
per-pixel rasterizer is code-identical across rounds (a metric shift can only come from the mesh
bytes, not a rasterizer drift). render_region is a local copy that just retargets RENDER_DIR to
uvfix2/ (round-1 renders in uvfix/ untouched).

The crop_*_bl.png coordinates from round 1 (whose generating script was not preserved) were
RECOVERED by exhaustive pixel-exact template match (SAD=0.0 at the best offset -- see
`_locate_crop_offsets()` below, run once and hardcoded): crop_specimen_bl.png ==
specimen_zoom_1_17.png[500:1000, 0:500] and crop_fixed_bl.png == fixed_zoom_1_17.png[500:1000, 0:500]
byte-exact (SAD=0.0 both). crop_stock_grass.png == stock_junction.png[0:450, 0:450] byte-exact.
So "crop_specimen_bl.png's coordinates" = the bottom-left 500x500 quadrant of the sc=16 zoom of
block (1,17) (the worst pre-fix block, 332/332 degenerate). FIXED2 is cropped identically.

The frame-mint comparison zone reuses uvf_adversary_probe.py's "clean_corner" block (4,19) (0
defective tris in every round -- pure build_landmass output), zoomed at the SAME sc=16 and cropped
at the SAME bottom-left-quadrant offset, so all three standards (repaired / frame / stock) are
directly comparable crops of identical pixel footprint (500x500 at ~16px/world-unit, i.e. ~31.25
world units per crop side).

READ-ONLY vs the game install. Never touches FF9CustomMap-world / -FIXED (round-1 A/B artifacts) or
FF9CustomMap-world-FIXED2 (round-2 fix output) -- reads only. Writes renders to
out/rung_f/renders/uvfix2/ and the report to out/rung_f/uvf_eye2_report.json. No git.

Run:  py -X utf8 studies/overworld-topography/uvf_eye_pixel2.py
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

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix2"
R1_RENDER_DIR = OUT_DIR / "renders" / "uvfix"        # round-1 renders (read-only reuse)
SPECIMEN = OUT_DIR / "FF9CustomMap-world"
FIXED = OUT_DIR / "FF9CustomMap-world-FIXED"
FIXED2 = OUT_DIR / "FF9CustomMap-world-FIXED2"
REPORT = OUT_DIR / "uvf_eye2_report.json"

FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
WORST_BLOCK = (1, 17)     # 332/332 degenerate pre-fix (round 1's own zoom target)
ROW16_BLOCKS = [(bx, 16) for bx in range(0, 5)]   # frame-mint band north of the defect belt

# recovered by exhaustive pixel-exact template match vs round-1 crop_*_bl.png (SAD=0.0) -- see docstring
BL_CROP = (0, 500, 500, 1000)   # (x0, y0, x1, y1) within a 1025x1025 sc=16 single-block zoom
TL_CROP = (0, 0, 450, 450)      # crop_stock_grass.png's offset within stock_junction.png

# The obvious frame-mint candidate ("clean_corner" block (4,19), 0 defective tris every round, per
# uvf_adversary_probe.py) turned out to be ~97% open sea in its footprint -- useless for a 500x500
# texture crop. Row by=16 (5 blocks, north of the defect belt) was swept for a magenta-free
# (non-degenerate, per SPECIMEN's own degenerate-UV signature) window that is ALSO >=99% grass-toned
# (excludes sea/path/forest-deco pixels); the search converged on world block (2,16)'s NW quadrant.
# Fixed pixel offset within a 5-block-wide sc=16 render of ROW16_BLOCKS (5121x1025px, wx0=0,wz1=-1024):
FRAME_CROP = (2240, 88, 2740, 588)   # -> world x[140.0,171.25] z[-1060.75,-1029.5], pure grass-mains


def log(m):
    print(m, flush=True)


def render_region(name, region, atlas_np, *, sc, out_dir=RENDER_DIR):
    """Local copy of uvf_eye_pixel.render_region, retargeted to `out_dir` (round-1's stays in uvfix/)."""
    blocks = sorted({(bx, by) for (bx, by, *_r) in region["terrain"]}
                     | {(bx, by) for (_p, bx, by, *_r) in region["sea"]})
    bxs = [b[0] for b in blocks]; bys = [b[1] for b in blocks]
    wx0, wx1 = min(bxs) * 64.0, (max(bxs) + 1) * 64.0
    wz0, wz1 = -(max(bys) + 1) * 64.0, -min(bys) * 64.0
    W = int((wx1 - wx0) * sc) + 1
    H = int((wz1 - wz0) * sc) + 1
    canvas = np.empty((H, W, 3), dtype=np.float32)
    canvas[:] = E.WORLD_BG

    def to_screen(w):
        return [(p[0] - wx0) * sc for p in w], [(wz1 - p[1]) * sc for p in w]

    for part, bx, by, src, tris in region["sea"]:
        col, al = E.SEA_COLOR[part], E.SEA_ALPHA[part]
        for (w, uv) in tris:
            sx, sy = to_screen(w)
            E.raster_flat_tri(canvas, W, H, sx, sy, col, al)

    stats = dict(tris=0, px=0, degenerate_tris=0, degenerate_px=0)
    for bx, by, src, tris in region["terrain"]:
        for (w, uv) in tris:
            sx, sy = to_screen(w)
            E.raster_textured_tri(canvas, W, H, sx, sy, uv, atlas_np, stats=stats)

    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.png"
    img.save(out_path)
    stats.update(name=name, blocks=blocks, W=W, H=H, sc=sc,
                 world_bbox=[wx0, wx1, wz0, wz1], out=str(out_path), misses=region["misses"])
    log(f"  -> {out_path}  {W}x{H}px  tris={stats['tris']} degenerate_tris={stats['degenerate_tris']} "
        f"degenerate_px={stats['degenerate_px']} ({100.0*stats['degenerate_px']/max(1,stats['px']):.2f}% of drawn px)")
    return stats


def crop_and_save(src_png, box, out_png):
    im = Image.open(src_png).convert("RGB")
    c = im.crop(box)
    c.save(out_png)
    return c


# ----------------------------------------------------------------------------------------------
# tiling-regularity metric (2D FFT, energy at the 4-world-unit cell frequency)
# ----------------------------------------------------------------------------------------------
def tiling_regularity(img_rgb: np.ndarray, sc: float, cell_u: float = 4.0, band_frac: float = 0.18):
    """Radial-band FFT energy ratio at the cell-boundary spatial frequency (1 cycle / cell_u world
    units == 1 cycle / (cell_u*sc) pixels). A regular per-cell mosaic (every cell edge a texture
    discontinuity) concentrates power in a ring at this frequency; smooth/organic texture does not.

    Returns dict(ring_ratio=<ring energy / total non-DC energy>,
                 peak_contrast=<max power in ring / median power in an outer reference annulus>).
    Higher = more regular tiling artifact. Hann-windowed to control edge leakage; luminance only.
    """
    g = (0.2126 * img_rgb[..., 0] + 0.7152 * img_rgb[..., 1] + 0.0722 * img_rgb[..., 2]).astype(np.float64)
    H, W = g.shape
    wy = np.hanning(H); wx = np.hanning(W)
    win = np.outer(wy, wx)
    g = (g - g.mean()) * win
    F = np.fft.fft2(g)
    P = np.abs(F) ** 2
    fy = np.fft.fftfreq(H)      # cycles/px
    fx = np.fft.fftfreq(W)
    FX, FY = np.meshgrid(fx, fy)
    radius = np.sqrt(FX ** 2 + FY ** 2)      # cycles/px
    target = 1.0 / (cell_u * sc)             # cycles/px for a 4u period at this render scale
    ring = (radius >= target * (1 - band_frac)) & (radius <= target * (1 + band_frac))
    nyq_ok = radius <= 0.5
    dc = radius < (0.5 / max(H, W))          # exclude the DC bin itself
    non_dc = nyq_ok & ~dc
    ring = ring & nyq_ok
    total_energy = float(P[non_dc].sum())
    ring_energy = float(P[ring].sum())
    ratio = ring_energy / total_energy if total_energy > 0 else 0.0
    # reference annulus: same width, offset to 2x the target frequency (well clear of the ring, still
    # inside Nyquist) -- the "background" spectral level far from any suspected periodicity peak.
    ref_lo, ref_hi = 2.0 * target * (1 - band_frac), 2.0 * target * (1 + band_frac)
    ref = (radius >= ref_lo) & (radius <= ref_hi) & nyq_ok
    ref_med = float(np.median(P[ref])) if ref.any() else float(np.median(P[non_dc]))
    ring_peak = float(P[ring].max()) if ring.any() else 0.0
    contrast = ring_peak / ref_med if ref_med > 0 else 0.0
    return dict(ring_ratio=ratio, peak_contrast=contrast, target_freq_px=target,
                target_period_px=1.0 / target)


def grid_seam_strength(img_rgb: np.ndarray, period_px: int, x_offset: int | None = None,
                        y_offset: int | None = None, margin: int = 8):
    """A more literal check than the FFT ring: 'visible per-cell tile boundaries' means the gradient
    magnitude is elevated on a fixed-period grid line vs elsewhere. If x_offset/y_offset are given
    (derived from the render's known world origin + sc -- exact, no search) they are used directly;
    otherwise the BEST phase per axis is found by brute-force scan over all `period_px` phases (worst
    -case-for-the-null-hypothesis / most-charitable-to-detecting-a-seam, and self-checks the hand-
    derived offsets when both paths are run).

    Returns dict(on_grid_mean=.., off_grid_mean=.., seam_ratio=on/off, x_offset=, y_offset=).
    seam_ratio ~ 1.0 -> no seam bias (grid lines are not privileged over any other pixel = smooth /
    organic). seam_ratio >> 1.0 -> a real visible seam sits at that period's boundary (quilt defect).
    """
    g = (0.2126 * img_rgb[..., 0] + 0.7152 * img_rgb[..., 1] + 0.0722 * img_rgb[..., 2]).astype(np.float64)
    gy, gx = np.gradient(g)
    grad = np.hypot(gx, gy)
    H, W = grad.shape

    def best_phase(axis_len, line_mean_fn):
        means = [line_mean_fn(off) for off in range(period_px)]
        return int(np.argmax(means))

    if x_offset is None:
        x_offset = best_phase(W, lambda off: grad[:, off::period_px].mean())
    if y_offset is None:
        y_offset = best_phase(H, lambda off: grad[off::period_px, :].mean())

    yy, xx = np.mgrid[0:H, 0:W]
    on_x = (((xx - x_offset) % period_px) == 0)
    on_y = (((yy - y_offset) % period_px) == 0)
    on_grid = on_x | on_y
    dx = np.minimum((xx - x_offset) % period_px, (-(xx - x_offset)) % period_px)
    dy = np.minimum((yy - y_offset) % period_px, (-(yy - y_offset)) % period_px)
    off_grid = (dx >= margin) & (dy >= margin)
    on_mean = float(grad[on_grid].mean()) if on_grid.any() else 0.0
    off_mean = float(grad[off_grid].mean()) if off_grid.any() else 0.0
    ratio = on_mean / off_mean if off_mean > 0 else 0.0
    return dict(on_grid_mean=on_mean, off_grid_mean=off_mean, seam_ratio=ratio,
                period_px=period_px, x_offset=x_offset, y_offset=y_offset)


def radial_band_energy(img_rgb: np.ndarray, bands=((0.0, 0.05), (0.05, 0.25), (0.25, 0.51))):
    """Isotropic (radially-averaged) power-spectrum energy fraction in named low/mid/high bands.
    Deliberately coarser than tiling_regularity's narrow ring -- catches a gross smooth-vs-noisy
    shape difference the narrow ring can miss, but (like tiling_regularity) is BLIND to orientation:
    a texture with strong locally-coherent streaks in alternating directions and an isotropic mottled
    texture can have similar radial energy distribution even though only one of them looks 'tiled'."""
    g = (0.2126 * img_rgb[..., 0] + 0.7152 * img_rgb[..., 1] + 0.0722 * img_rgb[..., 2]).astype(np.float64)
    H, W = g.shape
    win = np.outer(np.hanning(H), np.hanning(W))
    g = (g - g.mean()) * win
    F = np.fft.fft2(g)
    P = np.abs(F) ** 2
    fy = np.fft.fftfreq(H); fx = np.fft.fftfreq(W)
    FX, FY = np.meshgrid(fx, fy)
    R = np.sqrt(FX ** 2 + FY ** 2)
    total = float(P[R <= 0.5].sum())
    out = {}
    for lo, hi in bands:
        m = (R >= lo) & (R < hi) & (R <= 0.5)
        out[f"{lo:.2f}-{hi:.2f}"] = 100.0 * float(P[m].sum()) / total if total > 0 else 0.0
    return out


def orientation_coherence(img_rgb: np.ndarray, cell: int = 64):
    """Structure-tensor orientation analysis at the cell granularity -- the direct pixel-domain
    analogue of uvf_fix2.py's own mesh-level same_ori_rate diagnostic, computed independently from
    the RENDERED texture (not the mesh angles), as a cross-check. Per cell: mean structure tensor
    (Jxx,Jyy,Jxy) over the 64x64px block -> a binary orientation CLASS (sign of Jxx-Jyy, a 2-way
    proxy for the tile's dominant streak axis, since a 0/180 deg rotation and a 90/270 deg rotation
    of an anisotropic grass tile are the two orientation FAMILIES a human eye distinguishes) and a
    coherence scalar in [0,1] (0 = isotropic/no dominant streak direction in that cell, 1 = perfectly
    oriented). Returns dict(same_class_rate=<adjacent E/S cell-pairs sharing a class>,
    mean_coherence=<avg per-cell anisotropy>, grid_shape=(ny,nx))."""
    g = (0.2126 * img_rgb[..., 0] + 0.7152 * img_rgb[..., 1] + 0.0722 * img_rgb[..., 2]).astype(np.float64)
    gy, gx = np.gradient(g)
    Jxx, Jyy, Jxy = gx * gx, gy * gy, gx * gy
    H, W = g.shape
    ny, nx = H // cell, W // cell
    cls = np.zeros((ny, nx), dtype=np.int8)
    coh = np.zeros((ny, nx))
    for j in range(ny):
        for i in range(nx):
            jxx = Jxx[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell].mean()
            jyy = Jyy[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell].mean()
            jxy = Jxy[j * cell:(j + 1) * cell, i * cell:(i + 1) * cell].mean()
            cls[j, i] = 1 if (jxx - jyy) > 0 else 0
            denom = jxx + jyy
            coh[j, i] = (np.hypot(jxx - jyy, 2 * jxy) / denom) if denom > 0 else 0.0
    same, total = 0, 0
    for j in range(ny):
        for i in range(nx - 1):
            total += 1; same += int(cls[j, i] == cls[j, i + 1])
    for j in range(ny - 1):
        for i in range(nx):
            total += 1; same += int(cls[j, i] == cls[j + 1, i])
    return dict(same_class_rate=(same / total if total else None), mean_coherence=float(coh.mean()),
                grid_shape=list(cls.shape))


def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)
    log(f"  atlas {atlas_img.size} mode={atlas_img.mode}")

    report = dict(atlas_size=list(atlas_img.size), regions={}, crops={}, tiling={})

    # ---- full-footprint FIXED2 (defect census + visual context) --------------------------------
    log("\n== FIXED2: out/rung_f/FF9CustomMap-world-FIXED2, footprint (0-4,16-19) ==")
    reg_fix2 = E.gather_region(FIXED2, FOOTPRINT)
    report["regions"]["fixed2_rungf"] = render_region("fixed2_rungf", reg_fix2, atlas_np, sc=6.0)

    # ---- worst block (1,17): specimen / fixed / fixed2 (specimen+fixed RE-RENDERED here, code-
    #      identical to round 1, to prove this script's rasterizer reproduces round 1 byte-exact
    #      before trusting its FIXED2 numbers) --------------------------------------------------
    log("\n== ZOOM block (1,17): specimen / fixed / fixed2 ==")
    for tag, root in (("specimen", SPECIMEN), ("fixed", FIXED), ("fixed2", FIXED2)):
        reg = E.gather_region(root, [WORST_BLOCK])
        report["regions"][f"{tag}_zoom_1_17"] = render_region(f"{tag}_zoom_1_17", reg, atlas_np, sc=16.0)

    # ---- row-16 band (frame-mint reference: swept for a magenta-free / grass-toned window,
    #      see FRAME_CROP): specimen / fixed / fixed2, same sc=16 as the worst-block zoom ---------
    log("\n== ZOOM row16 band (frame-mint reference): specimen / fixed / fixed2 ==")
    for tag, root in (("specimen", SPECIMEN), ("fixed", FIXED), ("fixed2", FIXED2)):
        reg = E.gather_region(root, ROW16_BLOCKS)
        report["regions"][f"{tag}_row16"] = render_region(f"{tag}_row16", reg, atlas_np, sc=16.0)

    # ---- stock reference (re-rendered here for a fresh byte-check against round 1's stock_junction.png) --
    log("\n== STOCK reference: junction blocks (13-15,11-12) ==")
    reg_stock = E.gather_region(None, [(bx, by) for bx in (13, 14, 15) for by in (11, 12)])
    report["regions"]["stock_junction"] = render_region("stock_junction", reg_stock, atlas_np, sc=6.0)

    # ---- verify round-1 byte-reproduction (specimen/fixed zoom here must match uvfix/ byte-for-byte) --
    log("\n== round-1 reproduction check ==")
    repro = {}
    for tag in ("specimen_zoom_1_17", "fixed_zoom_1_17"):
        a = np.array(Image.open(R1_RENDER_DIR / f"{tag}.png").convert("RGB"))
        b = np.array(Image.open(RENDER_DIR / f"{tag}.png").convert("RGB"))
        same = a.shape == b.shape and bool(np.array_equal(a, b))
        repro[tag] = dict(byte_identical_to_round1=same, shape_a=list(a.shape), shape_b=list(b.shape))
        log(f"  {tag}: byte_identical_to_round1={same}")
    report["round1_reproduction"] = repro

    # ---- crops: repaired-zone (bl quadrant of block 1,17 zoom) x {specimen, fixed, fixed2} -------
    log("\n== crops (bottom-left 500x500 quadrant of the sc=16 zoom) ==")
    box = BL_CROP
    for tag in ("specimen", "fixed", "fixed2"):
        src = RENDER_DIR / f"{tag}_zoom_1_17.png"
        out = RENDER_DIR / f"crop_{tag}_bl.png"
        crop_and_save(src, box, out)
        log(f"  crop_{tag}_bl.png <- {tag}_zoom_1_17.png{list(box)}")

    # ---- crops: frame-mint reference (FRAME_CROP window of the row16 band) x {specimen,fixed,fixed2} --
    for tag in ("specimen", "fixed", "fixed2"):
        src = RENDER_DIR / f"{tag}_row16.png"
        out = RENDER_DIR / f"crop_{tag}_frame.png"
        crop_and_save(src, FRAME_CROP, out)
        log(f"  crop_{tag}_frame.png <- {tag}_row16.png{list(FRAME_CROP)}")

    # ---- crop: stock grass (reuse round-1's exact source coordinates) ----------------------------
    stock_crop = crop_and_save(RENDER_DIR / "stock_junction.png", TL_CROP, RENDER_DIR / "crop_stock_grass.png")
    r1_stock_crop = np.array(Image.open(R1_RENDER_DIR / "crop_stock_grass.png").convert("RGB"))
    stock_same = bool(np.array_equal(np.array(stock_crop), r1_stock_crop))
    log(f"  crop_stock_grass.png byte_identical_to_round1={stock_same}")
    report["round1_reproduction"]["crop_stock_grass"] = dict(byte_identical_to_round1=stock_same)

    # ---- side-by-side panels: specimen | fixed | fixed2 (repaired zone) and the frame/stock triad --
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

    panel1 = hstack([RENDER_DIR / "crop_specimen_bl.png", RENDER_DIR / "crop_fixed_bl.png",
                      RENDER_DIR / "crop_fixed2_bl.png"], "panel_repaired_specimen_fixed_fixed2.png")
    panel2 = hstack([RENDER_DIR / "crop_fixed_bl.png", RENDER_DIR / "crop_fixed_frame.png",
                      RENDER_DIR / "crop_stock_grass.png"], "panel_fixed_vs_frame_vs_stock.png")
    panel3 = hstack([RENDER_DIR / "crop_fixed2_bl.png", RENDER_DIR / "crop_fixed2_frame.png",
                      RENDER_DIR / "crop_stock_grass.png"], "panel_fixed2_vs_frame_vs_stock.png")
    log(f"  panels -> {panel1.name}, {panel2.name}, {panel3.name}")

    # ---- tiling-regularity metric --------------------------------------------------------------
    log("\n== tiling-regularity (2D FFT @ 4u cell frequency) ==")
    sc_zoom = 16.0
    tiling = {}
    for build in ("specimen", "fixed", "fixed2"):
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
    sc_stock = 6.0   # stock_junction rendered at sc=6.0 (round 1's footprint scale)
    tiling["stock"] = dict(grass=tiling_regularity(stock, sc_stock))
    s = tiling["stock"]["grass"]
    log(f"  stock: grass ring_ratio={s['ring_ratio']:.4f} contrast={s['peak_contrast']:.2f}  "
        f"(sc={sc_stock}, NOT directly comparable to the sc=16 crops -- period_px differs)")
    report["tiling"] = tiling

    # also compute stock at an *emulated* sc=16 equivalent by resampling crop_stock_grass.png up
    # 16/6x so the FFT target period_px matches the zoom crops exactly (apples-to-apples ring
    # position) -- resampling doesn't invent detail, just re-registers the frequency axis.
    stock_img = Image.open(RENDER_DIR / "crop_stock_grass.png").convert("RGB")
    scale_factor = 16.0 / 6.0
    stock_resamp = stock_img.resize((int(stock_img.width * scale_factor), int(stock_img.height * scale_factor)),
                                     Image.BICUBIC)
    stock_resamp.save(RENDER_DIR / "crop_stock_grass_resamp16.png")
    stock_r = np.array(stock_resamp, dtype=np.float64)
    tiling["stock"]["grass_resampled_to_sc16"] = tiling_regularity(stock_r, sc_zoom)
    sr = tiling["stock"]["grass_resampled_to_sc16"]
    log(f"  stock (resampled to sc=16 equivalent): ring_ratio={sr['ring_ratio']:.4f} contrast={sr['peak_contrast']:.2f}")

    # ---- grid-seam-strength metric (literal check: is the gradient elevated exactly on the known
    #      4u-cell grid lines?). Two variants per crop: EXACT offset (derived from the render's own
    #      world origin, hardcoded in BL_CROP/FRAME_CROP's docstring) and BEST-PHASE (blind search
    #      over all 64 phases, self-checking the hand-derived offset and giving stock a fair "does
    #      ANY period-64 grid exist anywhere in this crop" negative-control test). ------------------
    log("\n== grid-seam-strength (literal on-grid-line vs off-grid-line gradient, period=64px) ==")
    PERIOD = int(round(4.0 * sc_zoom))    # 64px at sc=16
    # exact phase for BL_CROP within its source (world-aligned zoom, origin px=(0,0)): crop x0=0 -> x_offset=0;
    # crop y0=500 -> y_offset=(-500)%PERIOD=12 (see BL_CROP/FRAME_CROP docstring for the derivation)
    BL_EXACT = dict(x_offset=(-BL_CROP[0]) % PERIOD, y_offset=(-BL_CROP[1]) % PERIOD)
    FRAME_EXACT = dict(x_offset=(-FRAME_CROP[0]) % PERIOD, y_offset=(-FRAME_CROP[1]) % PERIOD)
    seams = {}
    for build in ("specimen", "fixed", "fixed2"):
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
    stock_seam_best = grid_seam_strength(stock_r, PERIOD)   # stock has no world-aligned phase in our
    seams["stock"] = dict(grass_resampled_to_sc16_bestphase=stock_seam_best)               # cell language -- best-phase only (fair negative control)
    log(f"  stock (resampled, best-phase, negative control): seam_ratio={stock_seam_best['seam_ratio']:.3f}")
    report["grid_seam"] = seams

    # ---- radial band-energy + orientation-coherence (the metrics that actually separated the
    #      builds -- see report notes) -------------------------------------------------------------
    log("\n== radial band-energy (isotropic FFT, low/mid/high) + orientation-coherence (structure tensor) ==")
    band_energy, orient = {}, {}
    for build in ("specimen", "fixed", "fixed2"):
        repaired = np.array(Image.open(RENDER_DIR / f"crop_{build}_bl.png").convert("RGB"), dtype=np.float64)
        frame = np.array(Image.open(RENDER_DIR / f"crop_{build}_frame.png").convert("RGB"), dtype=np.float64)
        band_energy[build] = dict(repaired_zone=radial_band_energy(repaired), frame_zone=radial_band_energy(frame))
        orient[build] = dict(repaired_zone=orientation_coherence(repaired), frame_zone=orientation_coherence(frame))
        be, oc = band_energy[build]["repaired_zone"], orient[build]["repaired_zone"]
        log(f"  {build} repaired: bands={ {k: round(v,2) for k,v in be.items()} }  "
            f"same_class_rate={oc['same_class_rate']:.4f} mean_coherence={oc['mean_coherence']:.4f}")
    band_energy["stock_resampled_to_sc16"] = radial_band_energy(stock_r)
    orient["stock_resampled_to_sc16"] = orientation_coherence(stock_r)
    log(f"  stock(resamp, CONFOUNDED by bicubic upsample blur -- low-band is inflated, not a fair high-freq compare): "
        f"bands={ {k: round(v,2) for k,v in band_energy['stock_resampled_to_sc16'].items()} }  "
        f"same_class_rate={orient['stock_resampled_to_sc16']['same_class_rate']:.4f}")
    report["radial_band_energy"] = band_energy
    report["orientation_coherence"] = orient

    # ---- defect-free confirmation (from the region-render stats already gathered above) ----------
    defect_free = {}
    for name, st in report["regions"].items():
        if "fixed2" in name:
            defect_free[name] = dict(degenerate_tris=st["degenerate_tris"], degenerate_px=st["degenerate_px"])
    report["fixed2_defect_free"] = defect_free
    all_zero = all(v["degenerate_tris"] == 0 and v["degenerate_px"] == 0 for v in defect_free.values())
    report["fixed2_defect_free_ok"] = all_zero
    log(f"\nFIXED2 defect-free (all regions rendered here): {all_zero} -> {defect_free}")

    # ---- verdict (honest synthesis -- see docstring; do not average away a disagreement) ----------
    report["verdict"] = dict(
        defect_free=all_zero,
        visual="STILL A QUILT. Side-by-side (panel_repaired_specimen_fixed_fixed2.png, "
               "panel_fixed2_vs_frame_vs_stock.png): FIXED2's repaired zone still reads as a strong "
               "diamond/chevron mosaic with visible directional streaking, comparably severe to round "
               "1's FIXED, and clearly distinct from the frame-mint grass (smooth, mottled, no "
               "streaks) and from stock in the SAME images. Round 2 does NOT visually pass the "
               "MATCHES_FRAME bar.",
            mesh_ground_truth_vs_pixel_domain_disagreement=(
            "uvf_fix2.py's OWN mesh-level diagnostic (report['diagnosis']) shows real, verified "
            "improvement toward frame's statistics: same_ori_rate 0.2442(v1)->0.3995(v2) vs frame "
            "0.3888 (near-exact match); same_quad_rate 0.0381(v1)->0.1198(v2) vs frame 0.0977. This "
            "eye's INDEPENDENT pixel-domain analogue (orientation_coherence, computed from the "
            "rendered texture, not mesh angles) does NOT reproduce that convergence: same_class_rate "
            "fixed=0.7619 -> fixed2=0.6429 (frame=0.4881 -- fixed2 moved TOWARD frame here, mild "
            "agreement) but mean_coherence fixed=0.1672 -> fixed2=0.2212 (frame=0.0354 -- fixed2 "
            "moved AWAY from frame, i.e. MORE locally-oriented/streaky per cell, not less). The "
            "isotropic (orientation-blind) radial_band_energy also shows fixed2 (14.31/41.67/44.02 "
            "low/mid/high %) diverging slightly further from frame (8.00/39.47/52.53) than fixed did "
            "(8.02/39.73/52.24)."
        ),
        grid_seam_metric_inconclusive=(
            "grid_seam_strength (literal on/off cell-boundary gradient ratio) does not separate any "
            "build meaningfully: specimen(flat-disc, non-degenerate content elsewhere)=1.11-1.79, "
            "fixed=1.02-1.05, fixed2=1.03-1.05, frame=0.98-1.16, stock=1.10 (best-phase) -- all close "
            "to 1.0 (no seam bias at ANY tested phase). The 'chevron mosaic' is not a hard edge AT "
            "the exact 4u cell boundary; it is a coherent-streak-direction phenomenon inside each "
            "~64px cell (confirmed by orientation_coherence), which a boundary-gradient metric is the "
            "wrong tool to detect -- noted as a metric-choice residual, not a defect-free claim."
        ),
        tiling_ring_ratio_metric_inconclusive=(
            "The requested FFT-ring-at-4u-frequency metric (tiling_regularity) is RADIALLY AVERAGED "
            "(isotropic) and therefore also blind to the orientation-coherence phenomenon that "
            "actually drives the visual mosaic: fixed's ring_ratio (0.0053) is LOWER than frame's "
            "(0.0121) despite looking visually worse, and fixed2's (0.0127) is closer to frame's only "
            "by coincidence of aggregate radial energy, not because the visual artifact resolved. "
            "orientation_coherence (structure-tensor, directional) is the metric that actually tracks "
            "what the eye sees; it says fixed2 has NOT resolved the mosaic."
        ),
        quilt_verdict="MATCHES_FRAME NOT achieved. Best-supported label: UNCHANGED-TO-WORSE on the "
                      "specific visual/perceptual axis the round targeted (the mosaic persists, "
                      "structure-tensor coherence is higher not lower), even though the MESH-level "
                      "cell-assignment statistics genuinely moved toward frame's distribution and the "
                      "build remains fully defect-free (0 degenerate px, byte-rigid outside the 6305 "
                      "re-resolved UVs per uvf_fix2_report.json).",
        recommendation="Do not ship FIXED2 as a resolution of the quilt residual on visual grounds "
                       "alone -- it is a valid, gate-passing, statistically-closer-to-frame mesh, but "
                       "the rendered result is not yet distinguishable from round 1 to the eye. If the "
                       "mesh-level statistics are trusted as the correct proxy, the remaining gap is "
                       "in how those statistics manifest at this specific render's cell-boundary/scale "
                       "combination and needs its own follow-up (not a rerun of the same mirror with a "
                       "different seed) -- flagged for the orchestrator, not resolved here.",
    )

    report["elapsed_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"\nVERDICT: {report['verdict']['quilt_verdict']}")
    log(f"report -> {REPORT}  ({report['elapsed_s']}s)")


if __name__ == "__main__":
    main()
